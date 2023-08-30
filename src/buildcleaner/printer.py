from functools import cmp_to_key
from typing import Any
from typing import Dict
from typing import List
from typing import Set
from typing import Tuple
from typing import Type
from typing import Union
from typing import cast

from buildcleaner.graph import TargetDagBuilder
from buildcleaner.node import ContainerNode
from buildcleaner.node import FileNode
from buildcleaner.node import Function
from buildcleaner.node import GeneratedFileNode
from buildcleaner.node import Node
from buildcleaner.node import PackageNode
from buildcleaner.node import RepositoryNode
from buildcleaner.node import RootNode
from buildcleaner.node import TargetNode


class NodeComparators:
  _TYPE_ORDER: Dict[Type, int] = {
      FileNode: 1,
      GeneratedFileNode: 2,
      TargetNode: 3,
      PackageNode: 4,
      RepositoryNode: 5,
      RootNode: 6,
  }

  def __init__(self, group_by_generator_name: bool) -> None:
    self.targets_in_container_key = cmp_to_key(self._compare_nodes_in_container)
    self._group_by_generator_name: bool = group_by_generator_name

  def _compare_nodes_in_container(self, left: Node, right: Node) -> int:
    # if left.generator_function != right.generator_function:
    #   return self._cmp_objs(left.generator_function, right.generator_function)

    if isinstance(left, ContainerNode):
      if not isinstance(right, ContainerNode):
        self._compare_types(left, right)
    else:
      if not isinstance(right, TargetNode):
        self._compare_types(left, right)
      elif self._group_by_generator_name:
        left_target = cast(TargetNode, left)
        right_target = cast(TargetNode, right)
        if left_target.generator_name != right_target.generator_name:
          return self._compare_objects(left_target.generator_name,
                                       right_target.generator_name)

    if left.kind != right.kind:
      return self._compare_objects(left.kind.kind, right.kind.kind)
    return self._compare_objects(left.label, right.label)

  def _compare_objects(self, left: Any, right: Any) -> int:
    if left < right:
      return -1
    if left > right:
      return 1
    return 0

  def _compare_types(self, left: Node, right: Node):
    return self._compare_objects(NodeComparators._TYPE_ORDER[type(left)],
                                 NodeComparators._TYPE_ORDER[type(right)])


class DebugTreePrinter:
  def __init__(self) -> None:
    self._targets_in_container_key = NodeComparators(
        False).targets_in_container_key

  def print_nodes_tree(self, repo_root: RootNode, print_files: bool = True,
      print_targets: bool = True, indent: str = "    ",
      return_string: bool = False) -> Union[str, List[str]]:
    lines: List[str] = []
    self._print(repo_root, lines, -1, print_files, print_targets, indent)
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
      count_lines.append(f"    {k}: {len(sorted_labels)}")

    lines.append("\nNodes by kind summary:")
    lines.extend(count_lines)
    lines.append(f"\nTotal Nodes: {total_count}")

    return "\n".join(lines)

  # does preorder traversal
  def _print(self, node: Node, lines: List[str], depth: int, print_files: bool,
      print_targets: bool, indent: str) -> None:
    if isinstance(node, FileNode):
      if print_files:
        target_kind = f"{node.kind} " if isinstance(node, TargetNode) else ""
        lines.append(f"{indent * depth}{target_kind}{str(node)}")
    else:
      if (not isinstance(node, TargetNode) or print_targets):
        target_kind = f"{node.kind} " if isinstance(node, TargetNode) else ""
        lines.append(f"{indent * depth}{target_kind}{str(node)}")

    if isinstance(node, ContainerNode):
      container_node: ContainerNode = cast(ContainerNode, node)
      children: List[Node] = sorted(container_node.children.values(),
                                    key=self._targets_in_container_key)

      for v in children:
        self._print(v, lines, depth + 1, print_files, print_targets, indent)


class BuildTargetsPrinter:
  def __init__(self) -> None:
    self._targets_in_container_key = NodeComparators(
        True).targets_in_container_key

  def print_build_file(self, pkg_node: PackageNode) -> str:
    nodes: List[TargetNode] = []
    for t in pkg_node.get_targets():
      if type(t) == TargetNode:
        nodes.append(t)
    nodes.sort(key=self._targets_in_container_key)

    import_statements: Set[str] = set()
    targets: List[str] = []
    file_blocks: List[str] = []

    for node in nodes:
      if node.kind.import_statement:
        import_statements.add(node.kind.import_statement)
      targets.extend(
          self._print_target(pkg_node, cast(TargetNode, node)))
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

  def _print_target(self, pkg_node: PackageNode,
      node: TargetNode) -> List[str]:
    if node.kind.kind == "bind":
      return []

    list_args_block: str = self._print_list_args(pkg_node.label,
                                                 node.label_list_args,
                                                 node.string_list_args,
                                                 node.out_label_list_args)
    string_args_block: str = self._print_string_args(pkg_node.label,
                                                     node.label_args,
                                                     node.string_args,
                                                     node.out_label_args)
    bool_args_block: str = self._print_bool_args(node.bool_args)
    map_args_block: str = self._print_map_args(node.str_str_map_args)

    generator_info: str = ""
    if node.generator_name:
      generator_info = f"\n# generator_function = {node.generator_function}\n# generator_name = {node.generator_name}"

    target = f"""
# {node}{generator_info}
{node.kind}(
    name = "{node.name}",{list_args_block}{string_args_block}{bool_args_block}{map_args_block}
    visibility = ["//visibility:public"],
)"""
    return [target]

  def _print_function(self, pkg_node: PackageNode, func: Function) -> str:
    list_args_block: str = self._print_list_args(pkg_node.label,
                                                 func.label_list_args,
                                                 func.string_list_args,
                                                 {})
    function_str = f"""
{func.kind}({list_args_block}
)"""

    return function_str

  def _print_list_args(self, pkg_label: str,
      label_list_args: Dict[str, List[TargetNode]],
      string_list_args: Dict[str, List[str]],
      out_label_list_args: Dict[str, List[TargetNode]]) -> str:
    list_args_block: str = ""

    label_list_args_s: Dict[str, List[str]] = {}
    pkg_prefix: str = pkg_label + ":"
    for k, v_list in label_list_args.items():
      label_list_args_s[k] = [self._shorten_label(pkg_prefix, v) for v in
                              v_list]
    for k, v_list in out_label_list_args.items():
      label_list_args_s[k] = [self._shorten_label(pkg_prefix, v) for v in
                              v_list]

    label_block: str = self._print_list_args_internal(label_list_args_s, True)
    str_block: str = self._print_list_args_internal(string_list_args, False)

    return label_block + str_block

  def _print_list_args_internal(self, list_args: Dict[str, List[str]],
      sort_vals: bool) -> str:
    list_args_strs: List[str] = []
    for list_arg_name, list_arg_values in list_args.items():
      if not list_arg_values:
        continue
      elif len(list_arg_values) == 1:
        arg_str = f"    {list_arg_name} = [\"{list_arg_values[0]}\"],"
      else:
        list_arg_str_values = "\"" + "\",\n        \"".join(
            sorted(list_arg_values) if sort_vals else list_arg_values) + "\","
        arg_str = f"""    {list_arg_name} = [
        {list_arg_str_values}
    ],"""
      list_args_strs.append(arg_str)
    return "\n" + "\n".join(list_args_strs) if list_args_strs else ""

  def _print_map_args(self, str_str_map_args: Dict[str, Dict[str, str]]) -> str:
    map_args_strs: List[str] = []
    for arg_name, arg_v in str_str_map_args.items():
      if not arg_v:
        continue
      elif len(arg_v) == 1:
        v_pair: Tuple[str, str] = next(iter(arg_v.items()))
        arg_str = f"    {arg_name} = {{\"{v_pair[0]}\": \"{v_pair[1]}\"}},"
      else:
        vals_pairs: List[str] = [f"\"{k}\": \"{v}\"" for k, v in arg_v.items()]
        map_arg_str_values = ",\n        ".join(vals_pairs) + ","
        arg_str = f"""    {arg_name} = {{
        {map_arg_str_values}
    }},"""
      map_args_strs.append(arg_str)

    map_args_block: str = "\n" + "\n".join(map_args_strs)
    return map_args_block

  def _print_string_args(self, pkg_label: str,
      label_args: Dict[str, TargetNode],
      string_args: Dict[str, str],
      out_label_args: Dict[str, TargetNode]) -> str:
    string_args_block: str = ""
    pkg_prefix: str = pkg_label + ":"
    label_args_s: Dict[str, str] = {k: self._shorten_label(pkg_prefix, v)
                                    for k, v in
                                    label_args.items()}
    out_label_args_s: Dict[str, str] = {k: self._shorten_label(pkg_prefix, v)
                                        for k, v in
                                        out_label_args.items()}
    for string_args in [label_args_s, out_label_args_s, string_args]:
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

  def _shorten_label(self, pkg_prefix: str, target: TargetNode):
    label = str(target)
    if label.startswith(pkg_prefix):
      prefix_len = len(pkg_prefix) if isinstance(target, FileNode) else len(
          pkg_prefix) - 1
      return label[prefix_len:]
    return label


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


class GraphPrinter:
  def __init__(self, dg_builder: TargetDagBuilder) -> None:
    self.dg_builder = dg_builder

  def print_target_dag(self, inbound: bool) -> str:
    dot_root, dot_nodes, dot_edges = self._print_dot_nodes_and_edges(
        cast(List[Tuple[Node, Set[Node], Set[Node]]],
             self.dg_builder.build_target_dag(inbound)), inbound)
    return self._print_dot_graph(dot_root, dot_nodes, dot_edges,
                                 "InboundTargets" if inbound else "OutboundTargets")

  def _print_dot_graph(self, root_node: str, dot_nodes: List[str],
      dot_edges: List[str], graph_name: str) -> str:
    nodes_str = "  \n".join(dot_nodes)
    edges_str = "  \n".join(dot_edges)

    return f"""# Total Nodes: {len(dot_nodes)}
# Total Edges: {len(dot_edges)}
digraph {graph_name} {{
edge [arrowhead="none",color="red;0.2:grey80:green;0.2"];
node [fillcolor="white",shape="plain",style="filled",height="0.02",fontsize="11",fontname="Arial"];
graph [ranksep="11.0",rankdir="LR",outputorder="edgesfirst",root="{root_node}"];
{nodes_str}
{edges_str}
}}"""

  def _print_dot_nodes_and_edges(self,
      nodes_and_edges: List[
        Tuple[Node, Set[Node], Set[Node]]], inbound: bool) -> Tuple[
    str, List[str], List[str]]:

    root_node: str = str(nodes_and_edges[0][0])
    dot_nodes: List[str] = []
    dot_edges: List[str] = []
    node_no: int = 1

    undirected_edges: Set[str] = set()

    for the_node, direct_nodes, reverse_nodes in nodes_and_edges:
      node_kind: str = f"{the_node.kind}"
      if the_node.kind.kind == "alias":
        actual_node: TargetNode = cast(TargetNode, the_node).label_args[
          "actual"]
        node_kind += f" -> {actual_node.kind} {actual_node}"
      dot_nodes.append(
          f'"{the_node}" [label="{node_no}:{len(direct_nodes)}:{len(reverse_nodes)}"]; # {node_kind}')
      node_no += 1
      for direct_node in direct_nodes:
        if direct_node == the_node:
          continue
        if direct_node in reverse_nodes:
          undirected_edge = f'"{the_node}" -> "{direct_node}";'
          if undirected_edge in undirected_edges:
            continue
          undirected_edges.add(f'"{direct_node}" -> "{the_node}";')
          dot_edges.append(
              f'"{direct_node}" -> "{the_node}" [dir="none",color="blue;0.2:grey80:blue;0.2"];')
        elif inbound:
          dot_edges.append(f'"{direct_node}" -> "{the_node}";')
        else:
          dot_edges.append(f'"{the_node}" -> "{direct_node}";')

    return root_node, dot_nodes, dot_edges
