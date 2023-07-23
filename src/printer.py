from typing import Union, Dict, List, Sequence, Iterable, Set, cast
from node import Function, Node, ContainerNode, TargetNode, FileNode, \
  RepositoryNode, PackageNode
from rule import TensorflowRules


class DebugTreePrinter:
  def print_nodes_tree(self, repo_root, print_files: bool = True,
      print_targets: bool = True,
      print_deps: bool = True, indent: str = "    ",
      node_types: Sequence[Node] = (),
      return_string: bool = False) -> Union[str, List[str]]:
    lines: List[str] = []
    self._print(repo_root, lines, -1, print_files, print_targets, print_deps,
                indent, node_types)
    return "\n".join(lines) if return_string else lines

  def print_nodes_by_kind(self,
      nodes_by_kind: Dict[str, Dict[str, TargetNode]]) -> str:
    lines: List[str] = []
    total_count: int = 0
    count_lines: List[str] = []
    for k, v in nodes_by_kind.items():
      sorted_labels: List[str] = [node_label for node_label in v]
      sorted_labels.sort()
      lines.append(f"{k}: {len(sorted_labels)}")
      lines.append("    " + "\n    ".join(sorted_labels))
      total_count += len(sorted_labels)
      count_lines.append(f"{k}: {len(sorted_labels)}")

    lines.extend(count_lines)
    lines.append(f"\nTotal Items: {total_count}")

    return "\n".join(lines)

  def _print(self, node: Node, lines: List[str], depth: int, print_files: bool,
      print_targets: bool, print_deps: bool, indent: str, node_types) -> None:
    print_node = not node_types
    for node_type in node_types:
      if isinstance(node, node_type):
        print_node = True
        break

    if isinstance(node, FileNode):
      if print_node and print_files:
        target_kind = f"{node.kind} " if isinstance(node, TargetNode) else ""
        lines.append(f"{indent * depth}{target_kind}{str(node)}")
    else:
      if print_node and (
          not isinstance(node, TargetNode) or print_targets):
        target_kind = f"{node.kind} " if isinstance(node, TargetNode) else ""
        lines.append(f"{indent * depth}{target_kind}{str(node)}")

    if isinstance(node, ContainerNode):
      for _, v in cast(ContainerNode, node).children.items():
        self._print(v, lines, depth + 1, print_files, print_targets, print_deps,
                    indent, node_types)


class BuildTargetsPrinter:
  def print_build_file(self, pkg_node: PackageNode) -> str:
    nodes: List[TargetNode] = []
    for t in pkg_node.get_targets(None):
      if type(t) == TargetNode:
        nodes.append(t)
    nodes.sort()

    import_statements: Set[str] = set()
    targets: List[str] = []
    file_blocks: List[str] = []

    for node in nodes:
      if node.kind.import_statement:
        import_statements.add(node.kind.import_statement)
      targets.extend(
          self._print_build_target(pkg_node, cast(TargetNode, node)))
    import_statements_list: List[str] = list(import_statements)
    import_statements_list.sort()

    functions_str: List[str] = [self._print_function(pkg_node, p) for p in
                                pkg_node.functions]

    file_blocks.append(f"# Package: {pkg_node.label}")
    if import_statements:
      file_blocks.append("\n".join(import_statements_list))
    if functions_str:
      file_blocks.append("\n".join(functions_str))
    if targets:
      file_blocks.append("\n".join(targets))

    return "" if len(file_blocks) == 1 else "\n".join(file_blocks)

  def _print_build_target(self, pkg_node: PackageNode,
      node: TargetNode) -> List[str]:
    if node.kind == TensorflowRules.rules()["bind"]:
      return []

    list_args_block: str = self._print_list_args(pkg_node.label,
                                                 node.label_list_args,
                                                 node.string_list_args)
    string_args_block: str = self._print_string_args(pkg_node.label,
                                                     node.label_args,
                                                     node.string_args)
    bool_args_block: str = self._print_bool_args(node.bool_args)
    target = f"""
# {str(node)}
{node.kind}(
    name = "{node.name}",{list_args_block}{string_args_block}{bool_args_block}
    visibility = ["//visibility:public"],
)"""
    return [target]

  def _print_function(self, pkg_node: PackageNode, func: Function) -> str:
    list_args_block: str = self._print_list_args(pkg_node.label,
                                                 func.label_list_args,
                                                 func.string_list_args)
    function_str = f"""
{func.kind}({list_args_block}
)"""

    return function_str

  def _print_list_args(self, pkg_label: str,
      label_list_args: Dict[str, List[TargetNode]],
      string_list_args: Dict[str, List[str]]) -> str:
    list_args_block: str = ""

    label_list_args_s: Dict[str, List[str]] = {}
    pkg_prefix: str = pkg_label + ":"
    for k, v_list in label_list_args.items():
      label_list_args_s[k] = [self._shorten_label(pkg_prefix, v) for v in
                              v_list]
    for list_args in [label_list_args_s, string_list_args]:
      list_args_strs: List[str] = []
      for list_arg_name, list_arg_values in list_args.items():
        if not list_arg_values:
          continue
        elif len(list_arg_values) == 1:
          arg_str = f"    {list_arg_name} = [\"{list_arg_values[0]}\"],"
        else:
          list_arg_str_values = "\"" + "\",\n        \"".join(
              list_arg_values) + "\","
          arg_str = f"""    {list_arg_name} = [
        {list_arg_str_values}
    ],"""
        list_args_strs.append(arg_str)
      list_args_block += "\n" + "\n".join(
          list_args_strs) if list_args_strs else ""

    return list_args_block

  def _shorten_label(self, pkg_prefix: str, target: TargetNode):
    label = str(target)
    if label.startswith(pkg_prefix):
      prefix_len = len(pkg_prefix) if isinstance(target, FileNode) else len(
        pkg_prefix) - 1
      return label[prefix_len:]
    return label

  def _print_string_args(self, pkg_label: str,
      label_args: Dict[str, TargetNode],
      string_args: Dict[str, str]) -> str:
    string_args_block: str = ""
    pkg_prefix: str = pkg_label + ":"
    label_args_s: Dict[str, str] = {k: self._shorten_label(pkg_prefix, v)
                                    for k, v in
                                    label_args.items()}
    for string_args in [label_args_s, string_args]:
      string_args_strs: List[str] = []
      for string_arg_name, string_arg_value in string_args.items():
        arg_str = f"    {string_arg_name} = \"{str(string_arg_value)}\","
        string_args_strs.append(arg_str)
      string_args_block += "\n" + "\n".join(
          string_args_strs) if string_args_strs else ""

    return string_args_block

  def _print_bool_args(self, bool_args: Dict[str, bool]) -> str:
    bool_args_strs: List[str] = []
    for bool_arg_name, bool_arg_value in bool_args.items():
      arg_str = f"    {bool_arg_name} = {str(bool_arg_value)},"
      bool_args_strs.append(arg_str)

    bool_args_block = "\n" + "\n".join(bool_args_strs) if bool_args_strs else ""

    return bool_args_block


class BuildFilesPrinter(BuildTargetsPrinter):
  def print_build_files(self, repo_node: RepositoryNode) -> Dict[
    str, str]:
    build_files_dict: Dict[str, str] = {}
    for package_node in repo_node.children.values():
      self._traverse_nodes_tree(build_files_dict,
                                cast(PackageNode, package_node))

    return build_files_dict

  def _traverse_nodes_tree(self, build_files_dict: Dict[str, str],
      pkg_node: PackageNode) -> None:
    for label, child in pkg_node.children.items():
      if isinstance(child, PackageNode):
        self._traverse_nodes_tree(build_files_dict, child)

    file_body = self.print_build_file(pkg_node)
    if file_body:
      build_files_dict[pkg_node.get_package_folder_path()] = file_body
