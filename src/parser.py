from typing import Dict, List, Callable, Tuple, Set, Optional
from typing import Pattern, Match

from node import Node, TargetNode
from rule import Rule, TensorflowRules
from transformer import NodesGraphBuilder

import re


class BazelBuildTargetsParser:
  def __init__(self, path_prefix) -> None:
    self._target_splitter_regex: Pattern = re.compile(r"(?:\r?\n){2,}")
    self._package_name_regex: Pattern = re.compile(
        fr"#\s*{path_prefix}/(?P<value>[0-9a-zA-Z\-\._\@/]+)/BUILD(.bazel)?:")
    self._label_kind_regex: Pattern = re.compile(
        r"\s*(?P<kind>[\w]+)\s*\w*\s+(?P<package>@?//.*):(?P<name>.*)\s+\(")

    self._arg_label_list_regex: Dict[str, Pattern] = {}
    self._arg_label_regex: Dict[str, Pattern] = {}
    self._arg_string_list_regex: Dict[str, Pattern] = {}
    self._arg_string_regex: Dict[str, Pattern] = {}
    self._arg_string_regex["name"] = re.compile(
        r"\bname\b\s*=\s*\"(?P<value>[0-9a-zA-Z\-\._\+/]+)\"")
    self._arg_bool_regex: Dict[str, Pattern] = {}

    self._rule_parsers: List[
      Tuple[Pattern, Callable[[str], Optional[TargetNode]]]] = []

    for r in TensorflowRules.rules().values():
      for arg in r.label_list_args:
        self._arg_label_list_regex[arg] = re.compile(
            fr"\b{arg}\b\s*=\s*\[(?P<values>.+)\][,\s]*\n")
      for arg in r.label_args:
        self._arg_label_regex[arg] = re.compile(
            fr"\b{arg}\b\s*=\s*\"(?P<value>.*)\"")
      for arg in r.string_list_args:
        self._arg_string_list_regex[arg] = re.compile(
            fr"\b{arg}\b\s*=\s*\[(?P<values>.+)\][,\s]*\n")
      for arg in r.string_args:
        self._arg_string_regex[arg] = re.compile(
            fr"\b{arg}\b\s*=\s*\"(?P<value>.*)\"")
      for arg in r.bool_args:
        self._arg_bool_regex[arg] = re.compile(
            fr"\b{arg}\b\s*=\s*(?P<value>\w+)")
      self._rule_parsers.append(self._rule_parser(r))

    self._nodes_builder = NodesGraphBuilder()

  def parse_query_build_output(self, query_build_output: str) -> Tuple[
    Dict[str, TargetNode], Set[str], Set[str]]:
    target_rules = self._target_splitter_regex.split(query_build_output.strip())
    internal_targets: Set[str] = set()
    external_targets: Set[str] = set()
    internal_nodes: Dict[str, TargetNode] = {}

    for target_rule in target_rules:
      unknown_rule = True
      if not target_rule:
        continue
      for rule_parser in self._rule_parsers:
        if rule_parser[0].search(target_rule):
          unknown_rule = False
          node = rule_parser[1](target_rule)
          if not node:
            continue
          internal_nodes[str(node)] = node
          internal_targets.add(node.label)
          for targets in node.label_list_args.values():
            for t in targets:
              if t.label[0] == "@":
                external_targets.add(t.label)
              else:
                internal_targets.add(t.label)
          for t in node.label_args.values():
            if t.label[0] == "@":
              external_targets.add(t.label)
            else:
              internal_targets.add(t.label)
          break
      if unknown_rule:
        print(f"------------\nUnknown Rule: {target_rule}\n------------")

    return internal_nodes, external_targets, internal_targets

  def _rule_parser(self, rule: Rule) -> Tuple[
    Pattern, Callable[[str], Optional[TargetNode]]]:

    def args_parser_cosure(target_rule: str) -> Optional[TargetNode]:
      node: Optional[TargetNode] = None

      rule_name: Optional[Match[str]] = self._arg_string_regex["name"].search(
          target_rule)
      if not rule_name:
        return node

      rule_pkg: Optional[Match[str]] = self._package_name_regex.search(
          target_rule)

      if not rule_pkg:
        if rule.kind == "bind":
          node = TargetNode(rule, rule_name.group('value'), f"//external")
        else:
          return node
      else:
        node = TargetNode(rule, rule_name.group("value"),
                          f"//{rule_pkg.group('value')}")

      for label_list_arg in rule.label_list_args:
        match = self._arg_label_list_regex[label_list_arg].search(target_rule)
        if match:
          for arg_value in match.group("values").split(", "):
            t = self._normalize_value(arg_value)
            t_node = TargetNode.create_stub(t)
            node.label_list_args.setdefault(label_list_arg, []).append(t_node)

      for label_arg in rule.label_args:
        match = self._arg_label_regex[label_arg].search(target_rule)
        if match:
          t = self._normalize_value(match.group("value"))
          t_node = TargetNode.create_stub(t)
          node.label_args[label_arg] = t_node

      for string_list_arg in rule.string_list_args:
        match = self._arg_string_list_regex[string_list_arg].search(target_rule)
        if match:
          for arg_value in match.group("values").split(", "):
            t = self._normalize_value(arg_value)
            node.string_list_args.setdefault(string_list_arg, []).append(t)

      for string_arg in rule.string_args:
        match = self._arg_string_regex[string_arg].search(target_rule)
        if match:
          t = self._normalize_value(match.group("value"))
          node.string_args[string_arg] = t

      for bool_arg in rule.bool_args:
        match = self._arg_bool_regex[bool_arg].search(target_rule)
        if match:
          t = self._normalize_value(match.group("value"))
          node.bool_args[bool_arg] = t == "True" or t == "1"

      return node

    return re.compile(fr"^{rule.kind}\(", re.MULTILINE), args_parser_cosure

  def _normalize_value(self, target: str) -> str:
    val = target.strip()
    return val[1:-1] if val[0] == "\"" else val

  def parse_query_label_kind_output(self, query_label_kind_output: str) -> Dict[
    str, List[Node]]:
    target_rules: List[str] = query_label_kind_output.splitlines()
    internal_nodes: Dict[str, Node] = {}
    kinds: Dict[str, Rule] = {}
    for target_rule in target_rules:
      match = self._label_kind_regex.search(target_rule)
      if not match:
        continue
      rule_kind:str = match.group("kind")
      if rule_kind not in kinds:
        kinds[rule_kind] = Rule(rule_kind)
      node = TargetNode(kinds[rule_kind], match.group("name"), match.group("package"))
      internal_nodes[str(node)] = node

    nodes_by_kind: Dict[str, List[Node]] = {}
    for v in internal_nodes.values():
      nodes_by_kind.setdefault(v.kind.kind, []).append(v)

    nodes_by_kind_count: List[Tuple[str, List[Node]]] = []
    for k, list_v in nodes_by_kind.items():
      list_v.sort(key=lambda x: str(x))
      nodes_by_kind_count.append((k, list_v))

    nodes_by_kind_count.sort(key=lambda x: -len(x[1]))
    nodes_by_kind.clear()
    for n in nodes_by_kind_count:
      nodes_by_kind[n[0]] = n[1]

    return nodes_by_kind
