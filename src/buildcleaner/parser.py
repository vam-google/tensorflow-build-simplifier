import re
from itertools import chain
from typing import Callable
from typing import Dict
from typing import List
from typing import Match
from typing import Optional
from typing import Pattern
from typing import Set
from typing import Tuple

from buildcleaner.node import FileNode
from buildcleaner.node import GeneratedFileNode
from buildcleaner.node import TargetNode
from buildcleaner.rule import Rule


class BazelBuildTargetsParser:
  def __init__(self, path_prefix: str, rules_to_parse: Dict[str, Rule],
      rules_to_ignore: Dict[str, Rule]) -> None:
    self._rules_to_parse: Dict[str, Rule] = rules_to_parse.copy()
    self._rules_to_ignore: Dict[str, Rule] = rules_to_ignore.copy()
    self._target_splitter_regex: Pattern = re.compile(r"(?:\r?\n){2,}")
    self._package_name_regex: Pattern = re.compile(
        fr"#\s*{path_prefix}/(?P<value>[0-9a-zA-Z\-\._\@/]+)/BUILD(.bazel)?:")
    self._label_kind_regex: Pattern = re.compile(
        r"\s*(?P<kind>[\w]+)\s*\w*\s+(?P<package>@?//.*):(?P<name>.*)\s+\(")

    self._arg_label_list_regex: Dict[str, Pattern] = {}
    self._arg_label_regex: Dict[str, Pattern] = {}
    self._arg_string_list_regex: Dict[str, Pattern] = {}
    self._arg_string_regex: Dict[str, Pattern] = {}

    for build_in_arg in ["name", "generator_name", "generator_function"]:
      self._arg_string_regex[build_in_arg] = re.compile(
          fr"\b{build_in_arg}\b\s*=\s*\"(?P<value>[0-9a-zA-Z\-\._\+/]+)\"")

    self._arg_bool_regex: Dict[str, Pattern] = {}
    self._arg_int_regex: Dict[str, Pattern] = {}
    self._arg_str_str_map_regex: Dict[str, Pattern] = {}

    self._arg_out_label_list_regex: Dict[str, Pattern] = {}
    self._arg_out_label_regex: Dict[str, Pattern] = {}

    self._rule_parsers: List[
      Tuple[Pattern, Callable[[str], Optional[TargetNode]]]] = []
    self._ignored_rule_parsers: List[
      Tuple[Pattern, Callable[[str], Optional[TargetNode]]]] = []

    for rule in rules_to_parse.values():
      self._init_args_parsers(rule)
      self._rule_parsers.append(self._rule_parser(rule))

    for rule in rules_to_ignore.values():
      self._init_args_parsers(rule)
      self._ignored_rule_parsers.append(self._rule_parser(rule))

  def _init_args_parsers(self, rule: Rule) -> None:
    for arg in rule.label_list_args:
      self._arg_label_list_regex[arg] = re.compile(
          fr"\b{arg}\b\s*=\s*\[(?P<values>.*)\][,\s]*\n")
    for arg in rule.label_args:
      self._arg_label_regex[arg] = re.compile(
          fr"\b{arg}\b\s*=\s*\"(?P<value>.*)\"")
    for arg in rule.string_list_args:
      self._arg_string_list_regex[arg] = re.compile(
          fr"\b{arg}\b\s*=\s*\[(?P<values>.*)\][,\s]*\n")
    for arg in rule.string_args:
      self._arg_string_regex[arg] = re.compile(
          fr"\b{arg}\b\s*=\s*\"(?P<value>.*)\"")
    for arg in rule.bool_args:
      self._arg_bool_regex[arg] = re.compile(
          fr"\b{arg}\b\s*=\s*(?P<value>\w+)")
    for arg in rule.int_args:
      self._arg_int_regex[arg] = re.compile(
          fr"\b{arg}\b\s*=\s*(?P<value>\d+)")
    for arg in rule.str_str_map_args:
      self._arg_str_str_map_regex[arg] = re.compile(
          fr"\b{arg}\b\s*=\s*\{{(?P<values>.+)\}}[,\s]*\n")

    for arg in rule.out_label_list_args:
      self._arg_out_label_list_regex[arg] = re.compile(
          fr"\b{arg}\b\s*=\s*\[(?P<values>.+)\][,\s]*\n")
    for arg in rule.out_label_args:
      self._arg_out_label_regex[arg] = re.compile(
          fr"\b{arg}\b\s*=\s*\"(?P<value>.*)\"")

  def parse_query_build_output(self, query_build_output: str) -> Tuple[
    Dict[str, TargetNode], Set[str], Set[str]]:
    target_rules = self._target_splitter_regex.split(query_build_output.strip())
    internal_targets: Set[str] = set()
    external_targets: Set[str] = set()
    internal_nodes: Dict[str, TargetNode] = {}

    unknown_rules: List[str] = []

    for target_rule in target_rules:
      unknown_rule: bool = True
      if not target_rule:
        continue
      for rule_parser in self._rule_parsers:
        if rule_parser[0].search(target_rule):
          unknown_rule = False
          node = rule_parser[1](target_rule)
          if not node:
            continue
          internal_nodes[str(node)] = node
          # Put out nodes to list of all nodes so dependency on them can be
          # properly resolved
          for out_nodes in node.out_label_list_args.values():
            for out_node in out_nodes:
              internal_nodes[str(out_node)] = out_node
          for out_node in chain(node.out_label_args.values(), node.outputs):
            internal_nodes[str(out_node)] = out_node
          internal_targets.add(node.label)

          for targets in chain(node.label_list_args.values(),
                               node.out_label_list_args.values()):
            for t in targets:
              if t.label[0] == "@":
                external_targets.add(t.label)
              else:
                internal_targets.add(t.label)
          for t in chain(node.label_args.values(),
                         node.out_label_args.values(),
                         node.outputs):
            if t.label[0] == "@":
              external_targets.add(t.label)
            else:
              internal_targets.add(t.label)
          break
      if unknown_rule:
        for rule_parser in self._ignored_rule_parsers:
          if rule_parser[0].search(target_rule):
            # Found a known rule that should be ignored
            unknown_rule = False
            break
      if unknown_rule:
        unknown_rules.append(target_rule)
        # Trully unknown rule. Either parse it or add to list of uknown ones
        # raise ValueError(f"Unknown Rule: {target_rule}")

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
          # Must be an external node
          return node
      else:
        node = TargetNode(rule, rule_name.group("value"),
                          f"//{rule_pkg.group('value')}")

      generator_name: Optional[Match[str]] = self._arg_string_regex[
        "generator_name"].search(target_rule)
      if generator_name:
        node.generator_name = generator_name.group("value")
      generator_function: Optional[Match[str]] = self._arg_string_regex[
        "generator_function"].search(target_rule)
      if generator_function:
        node.generator_function = generator_function.group("value")
      t: str
      match: Optional[Match[str]]
      values: Optional[str]
      t_node: TargetNode
      for label_list_arg in rule.label_list_args:
        match = self._arg_label_list_regex[label_list_arg].search(target_rule)
        if match:
          values = match.group("values")
          node.label_list_args.setdefault(label_list_arg, [])
          if values:
            for arg_value in values.split(", "):
              t = self._normalize_value(arg_value)
              t_node = TargetNode.create_stub(t)
              node.label_list_args[label_list_arg].append(t_node)

      for label_arg in rule.label_args:
        match = self._arg_label_regex[label_arg].search(target_rule)
        if match:
          t = self._normalize_value(match.group("value"))
          t_node = TargetNode.create_stub(t)
          node.label_args[label_arg] = t_node

      for string_list_arg in rule.string_list_args:
        match = self._arg_string_list_regex[string_list_arg].search(target_rule)
        if match:
          values = match.group("values")
          node.string_list_args.setdefault(string_list_arg, [])
          if values:
            for arg_value in values.split('", "'):
              t = self._normalize_value(arg_value)
              node.string_list_args[string_list_arg].append(t)

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

      for int_arg in rule.int_args:
        match = self._arg_int_regex[int_arg].search(target_rule)
        if match:
          t = self._normalize_value(match.group("value"))
          node.int_args[int_arg] = int(t)

      for str_str_map_arg in rule.str_str_map_args:
        match = self._arg_str_str_map_regex[str_str_map_arg].search(target_rule)
        if match:
          for arg_value in match.group("values").split('", "'):
            arg_k_v: List[str] = arg_value.split(": ")
            node.str_str_map_args.setdefault(str_str_map_arg, dict())[
              self._normalize_value(arg_k_v[0])] = self._normalize_value(
                arg_k_v[1])

      for out_label_list_arg in rule.out_label_list_args:
        match = self._arg_out_label_list_regex[out_label_list_arg].search(
            target_rule)
        if match:
          for arg_value in match.group("values").split(", "):
            t = self._normalize_value(arg_value)
            t_node = GeneratedFileNode.create_gen_file(t, node)
            node.out_label_list_args.setdefault(out_label_list_arg, []).append(
                t_node)

      for out_label_arg in rule.out_label_args:
        match = self._arg_out_label_regex[out_label_arg].search(target_rule)
        if match:
          t = self._normalize_value(match.group("value"))
          t_node = GeneratedFileNode.create_gen_file(t, node)
          node.out_label_args[out_label_arg] = t_node

      for output_value in rule.outputs:
        t = f"{node.get_parent_label()}:{output_value.format(node.name)}"
        t_node = GeneratedFileNode.create_gen_file(t, node)
        node.outputs.append(t_node)

      if "target_compatible_with" in node.label_list_args:
        target_compatible_with: List[TargetNode] = node.label_list_args[
          "target_compatible_with"]
        if len(target_compatible_with) == 1 and target_compatible_with[
          0].label == "@platforms//:incompatible":
          return None

      return node

    return re.compile(fr"^{rule.kind}\(", re.MULTILINE), args_parser_cosure

  def _normalize_value(self, string: str) -> str:
    # This is very fragile and does not accomodate many potential corner cases
    # and escaped quotes in target itself, but it seems to be good enough on
    # practice. Improve if ever needed.
    v = string.strip()
    if v and v[0] == '"':
      v = v[1:]
    if v and v[-1] == '"' and (len(v) < 2 or v[-2] != "\\"):
      v = v[:-1]
    return v

  def parse_query_label_kind_output(self, query_label_kind_output: str) -> Dict[
    str, Dict[str, TargetNode]]:
    target_rules: List[str] = query_label_kind_output.splitlines()
    internal_nodes: Dict[str, TargetNode] = {}
    for target_rule in target_rules:
      match = self._label_kind_regex.search(target_rule)
      if not match:
        continue
      rule_kind: str = match.group("kind")
      node: TargetNode
      if rule_kind == "source":
        node = FileNode(match.group("name"), match.group("package"))
      else:
        kind: Optional[Rule] = self._rules_to_parse.get(rule_kind)
        if not kind:
          if rule_kind not in self._rules_to_ignore:
            raise ValueError(f"Unknown Rule: {target_rule}")
          continue
        node = TargetNode(kind, match.group("name"), match.group("package"))
      internal_nodes[str(node)] = node

    nodes_by_kind: Dict[str, Dict[str, TargetNode]] = {}
    for v in internal_nodes.values():
      nodes_by_kind.setdefault(v.kind.kind, dict())[str(v)] = v

    nodes_by_kind_count: List[Tuple[str, Dict[str, TargetNode]]] = []
    for k, dict_v in nodes_by_kind.items():
      nodes_by_kind_count.append((k, dict_v))

    nodes_by_kind_count.sort(key=lambda x: -len(x[1]))
    nodes_by_kind.clear()
    for n in nodes_by_kind_count:
      nodes_by_kind[n[0]] = n[1]

    return nodes_by_kind
