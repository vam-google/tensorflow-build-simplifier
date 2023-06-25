from typing import Dict, List, Callable, Tuple, Set, Optional, Sequence
from typing import Pattern, Match

from nodes import Node, TargetNode
import re


class BazelBuildTargetsParser:
  def __init__(self, path_prefix) -> None:
    self._target_splitter_regex: Pattern = re.compile(r"(?:\r?\n){2,}")
    self._package_name_regex: Pattern = re.compile(
        fr"#\s*{path_prefix}/(?P<value>[0-9a-zA-Z\-\._\@/]+)/BUILD(.bazel)?:")
    self._label_kind_regex: Pattern = re.compile(
        r"\s*(?P<kind>[\w]+)\s*\w*\s+(?P<package>@?//.*):(?P<name>.*)\s+\(")
    self._label_regex: Pattern = re.compile(
        r"^(//|@)[0-9a-zA-Z\-\._\@/]+:[0-9a-zA-Z\-\._\+/]+$")

    self._arg_label_list_regex: Dict[str, Pattern] = {}
    for p in ["deps", "srcs", "hdrs", "textual_hdrs", "tools", "original_deps",
              "exports", "outs", "roots", "td_srcs"]:
      self._arg_label_list_regex[p] = re.compile(
          fr"\b{p}\b\s*=\s*\[(?P<values>.+)\][,\s]*\n")

    self._arg_label_regex: Dict[str, Pattern] = {}
    for p in ["actual", "protoc", "tblgen", "td_file", "template",
              "plugin_language", "out", "plugin", "cmd", "shared_library",
              "interface_library"]:
      self._arg_label_regex[p] = re.compile(fr"\b{p}\b\s*=\s*\"(?P<value>.*)\"")

    self._arg_string_list_regex: Dict[str, Pattern] = {}
    for p in ["copts", "features", "linkopts", "includes", "flags", "tags",
              "opts", "plugin_options"]:
      self._arg_string_list_regex[p] = re.compile(
          fr"\b{p}\b\s*=\s*\[(?P<values>.+)\][,\s]*\n")

    self._arg_string_regex: Dict[str, Pattern] = {}
    self._arg_string_regex["name"] = re.compile(
        r"\bname\b\s*=\s*\"(?P<value>[0-9a-zA-Z\-\._\+/]+)\"")
    for p in ["plugin_language", "cmd"]:
      self._arg_string_regex[p] = re.compile(
          fr"\b{p}\b\s*=\s*\"(?P<value>.*)\"")

    self._arg_bool_regex: Dict[str, Pattern] = {}
    for p in ["alwayslink", "linkstatic", "gen_cc", "testonly",
              "generate_mocks", "system_provided"]:
      self._arg_bool_regex[p] = re.compile(fr"\b{p}\b\s*=\s*(?P<value>\w+)")

    self._rule_parsers: List[
      Tuple[
        Pattern, Callable[[str], Tuple[Optional[TargetNode], Set[str]]]]] = [
        self._rule_parser("cc_library",
                          label_list_args=["srcs", "hdrs", "deps",
                                           "textual_hdrs"],
                          string_list_args=["copts", "features", "tags"],
                          bool_args=["linkstatic", "alwayslink"]),
        self._rule_parser("filegroup", label_list_args=["srcs"]),
        self._rule_parser("alias", label_args=["actual"]),
        self._rule_parser("proto_gen",
                          label_list_args=["srcs", "deps", "outs"],
                          label_args=["protoc"],
                          string_list_args=["includes", "plugin_options"],
                          string_args=["plugin_language"],
                          bool_args=["gen_cc"]),
        self._rule_parser("genrule", label_list_args=["srcs", "tools", "outs"],
                          string_args=["cmd"]),
        self._rule_parser("cc_binary",
                          label_list_args=["srcs", "deps"],
                          string_list_args=["copts", "linkopts"]),
        self._rule_parser("bind", label_args=["actual"]),
        self._rule_parser("gentbl_rule",
                          label_list_args=["deps", "td_srcs"],
                          label_args=["tblgen", "td_file", "out"],
                          string_list_args=["includes", "opts"]),
        self._rule_parser("_generate_cc",
                          label_list_args=["srcs"],
                          label_args=["plugin"],
                          string_list_args=["flags"],
                          bool_args=["generate_mocks", "testonly"]),
        self._rule_parser("td_library",
                          label_list_args=["srcs", "deps"],
                          string_list_args=["includes"]),
        self._rule_parser("py_binary", label_list_args=["srcs", "deps"]),
        self._rule_parser("proto_library",
                          label_list_args=["srcs", "deps", "exports"],
                          string_list_args=["tags"],
                          bool_args=["testonly"]),
        self._rule_parser("cc_import",
                          label_args=["shared_library", "interface_library"],
                          bool_args=["system_provided"]),
        self._rule_parser("tf_gen_options_header", label_args=["template"]),
        self._rule_parser("cc_shared_library", label_list_args=["roots"]),
        self._rule_parser("_transitive_hdrs", label_list_args=["deps"]),
        self._rule_parser("_transitive_parameters_library",
                          label_list_args=["original_deps"]),
    ]

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
          node, targets = rule_parser[1](target_rule)
          for t in targets:
            if t and t[0] == "@":
              external_targets.add(t)
            else:
              internal_targets.add(t)
          if node:
            internal_nodes[str(node)] = node
          unknown_rule = False
          break
      if unknown_rule:
        print(f"------------\nUnknown Rule: {target_rule}\n------------")

    return internal_nodes, external_targets, internal_targets

  def _rule_parser(self, rule_kind: str,
      label_list_args: Sequence[str] = (),
      label_args: Sequence[str] = (),
      string_list_args: Sequence[str] = (),
      string_args: Sequence[str] = (),
      bool_args: Sequence[str] = ()) -> Tuple[
    Pattern, Callable[[str], Tuple[Optional[TargetNode], Set[str]]]]:

    def args_parser_cosure(target_rule: str) -> Tuple[
      Optional[TargetNode], Set[str]]:
      targets: Set[str] = set()
      node: Optional[TargetNode] = None

      rule_name: Optional[Match[str]] = self._arg_string_regex["name"].search(
          target_rule)
      if not rule_name:
        return node, targets

      rule_pkg: Optional[Match[str]] = self._package_name_regex.search(
          target_rule)

      if not rule_pkg:
        if rule_kind == "bind":
          node = TargetNode(rule_name.group('value'), f"//external")
        else:
          return node, targets
      else:
        node = TargetNode(rule_name.group("value"),
                          f"//{rule_pkg.group('value')}")

      targets.add(node.label)

      node.kind = rule_kind

      for label_list_arg in label_list_args:
        match = self._arg_label_list_regex[label_list_arg].search(target_rule)
        if match:
          for arg_value in match.group("values").split(", "):
            t = self._normalize_value(arg_value)
            targets.add(t)
            node.label_list_args.setdefault(label_list_arg, []).append(t)

      for label_arg in label_args:
        match = self._arg_label_regex[label_arg].search(target_rule)
        if match:
          t = self._normalize_value(match.group("value"))
          targets.add(t)
          node.label_args[label_arg] = t

      for string_list_arg in string_list_args:
        match = self._arg_string_list_regex[string_list_arg].search(target_rule)
        if match:
          for arg_value in match.group("values").split(", "):
            t = self._normalize_value(arg_value)
            node.string_list_args.setdefault(string_list_arg, []).append(t)

      for string_arg in string_args:
        match = self._arg_string_regex[string_arg].search(target_rule)
        if match:
          t = self._normalize_value(match.group("value"))
          node.string_args[string_arg] = t

      for bool_arg in bool_args:
        match = self._arg_bool_regex[bool_arg].search(target_rule)
        if match:
          t = self._normalize_value(match.group("value"))
          node.bool_args[bool_arg] = t == "True" or t == "1"

      return node, targets

    return re.compile(fr"^{rule_kind}\(", re.MULTILINE), args_parser_cosure

  def _normalize_value(self, target: str) -> str:
    val = target.strip()
    return val[1:-1] if val[0] == "\"" else val

  def parse_query_label_kind_output(self, query_label_kind_output: str) -> Dict[
    str, List[Node]]:
    target_rules: List[str] = query_label_kind_output.splitlines()
    internal_nodes: Dict[str, Node] = {}
    for target_rule in target_rules:
      match = self._label_kind_regex.search(target_rule)
      if not match:
        continue
      node = TargetNode(match.group("name"), match.group("package"))
      node.kind = match.group("kind")
      internal_nodes[str(node)] = node

    nodes_by_kind: Dict[str, List[Node]] = {}
    for v in internal_nodes.values():
      nodes_by_kind.setdefault(v.kind, []).append(v)

    nodes_by_kind_count: List[Tuple[str, List[Node]]] = []
    for k, list_v in nodes_by_kind.items():
      list_v.sort(key=lambda x: str(x))
      nodes_by_kind_count.append((k, list_v))

    nodes_by_kind_count.sort(key=lambda x: -len(x[1]))
    nodes_by_kind.clear()
    for n in nodes_by_kind_count:
      nodes_by_kind[n[0]] = n[1]

    return nodes_by_kind
