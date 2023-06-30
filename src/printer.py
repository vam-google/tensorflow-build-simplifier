from typing import Union, Dict, List, Sequence, Iterable, Set, cast
from node import Node, ContainerNode, TargetNode, FileNode, RepositoryNode, \
  PackageNode


class DebugTreePrinter:
  def print(self, repo_root, print_files: bool = True,
      print_targets: bool = True,
      print_deps: bool = True, indent: str = "    ",
      node_types: Sequence[Node] = (),
      return_string: bool = False) -> Union[str, List[str]]:
    lines: List[str] = []
    self._print(repo_root, lines, -1, print_files, print_targets, print_deps,
                indent, node_types)
    return "\n".join(lines) if return_string else lines

  def print_nodes_by_kind(self, nodes_by_kind: Dict[str, Dict[str, TargetNode]]) -> str:
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
  def print_build_file(self, nodes: Iterable[Node],
      file_header: str = "") -> str:
    targets: List[str] = []
    import_statements: Set[str] = set()

    for node in nodes:
      if node.kind.import_statement:
        import_statements.add(node.kind.import_statement)
      if type(node) == TargetNode:
        targets.append(self._print_build_target(cast(TargetNode, node)))
    import_statements_list: List[str] = list(import_statements)
    import_statements_list.sort()

    return file_header + "\n".join(import_statements_list) + "\n" + "\n".join(targets)

  def _print_build_target(self, node: TargetNode) -> str:
    list_args_block: str = ""

    label_list_args_s: Dict[str, List[str]] = {}
    for k, v_list in node.label_list_args.items():
      label_list_args_s[k] = [str(v) for v in v_list]
    for list_args in [label_list_args_s, node.string_list_args]:
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

    string_args_block: str = ""
    label_args_s: Dict[str, str] = {k: str(v) for k, v in
                                    node.label_args.items()}
    for string_args in [label_args_s, node.string_args]:
      string_args_strs: List[str] = []
      for string_arg_name, string_arg_value in string_args.items():
        arg_str = f"    {string_arg_name} = \"{str(string_arg_value)}\","
        string_args_strs.append(arg_str)
      string_args_block += "\n" + "\n".join(
          string_args_strs) if string_args_strs else ""

    bool_args_strs: List[str] = []
    for bool_arg_name, bool_arg_value in node.bool_args.items():
      arg_str = f"    {bool_arg_name} = {str(bool_arg_value)},"
      bool_args_strs.append(arg_str)

    bool_args_block = "\n" + "\n".join(bool_args_strs) if bool_args_strs else ""

    target = f"""
# {str(node)}
{node.kind}(
    name = "{node.name}",{list_args_block}{string_args_block}{bool_args_block}
    visibility = ["//visibility:public"],
)"""
    return target


class BuildFilesPrinter(BuildTargetsPrinter):
  def print_build_files(self, repo_node: RepositoryNode) -> Dict[
    str, str]:
    build_files_dict: Dict[str, str] = {}
    for package_node in repo_node.children.values():
      self._traverse_nodes_tree(build_files_dict,
                                cast(PackageNode, package_node))

    return build_files_dict

  def _traverse_nodes_tree(self, build_files_dict: Dict[str, str],
      node: PackageNode) -> None:
    direct_target_children_list: List[TargetNode] = []

    for label, child in node.children.items():
      if isinstance(child, TargetNode):
        direct_target_children_list.append(child)
      elif isinstance(child, PackageNode):
        self._traverse_nodes_tree(build_files_dict, child)

    if direct_target_children_list:
      build_files_dict[node.get_package_folder_path()] = self.print_build_file(
          direct_target_children_list,
          f"# Package: {node.label}\n")
