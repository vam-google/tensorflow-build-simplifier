from typing import Union, Dict, List, Sequence, Set, Tuple, Iterable, cast
from node import Function, Node, ContainerNode, TargetNode, FileNode, \
  RepositoryNode, PackageNode
from rule import TensorflowRules


class DebugTreePrinter:
  def print_nodes_tree(self, repo_root, print_files: bool = True,
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
      for _, v in cast(ContainerNode, node).children.items():
        self._print(v, lines, depth + 1, print_files, print_targets, indent)


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
    if node.kind == TensorflowRules.rules()["bind"]:
      return []

    list_args_block: str = self._print_list_args(pkg_node.label,
                                                 node.label_list_args,
                                                 node.string_list_args)
    string_args_block: str = self._print_string_args(pkg_node.label,
                                                     node.label_args,
                                                     node.string_args)
    bool_args_block: str = self._print_bool_args(node.bool_args)
    map_args_block: str = self._print_map_args(node.str_str_map_args)

    target = f"""
# {str(node)}
{node.kind}(
    name = "{node.name}",{list_args_block}{string_args_block}{bool_args_block}{map_args_block}
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
  def print_target_graph(self, root: TargetNode) -> Tuple[str, str]:
    inbound_edges: Dict[TargetNode, List[TargetNode]] = {}
    outbound_edges: Dict[TargetNode, List[TargetNode]] = {}
    path: Dict[str, TargetNode] = {}
    self._dfs_graph(root, outbound_edges, inbound_edges, path)
    inbound_nodes_and_edges = self._sorted_nodes_by_edge_degree(inbound_edges,
                                                                outbound_edges)
    outbound_nodes_and_edges = self._sorted_nodes_by_edge_degree(outbound_edges,
                                                                 inbound_edges)

    in_root, in_dot_nodes, in_dot_edges = self._print_dot_nodes_and_edges(
        inbound_nodes_and_edges, True)
    out_root, out_dot_nodes, out_dot_edges = self._print_dot_nodes_and_edges(
        outbound_nodes_and_edges, False)

    return (
        self._print_dot_graph(in_root, in_dot_nodes, in_dot_edges, "Inbound"),
        self._print_dot_graph(out_root, out_dot_nodes, out_dot_edges,
                              "Outbound"))

  def _print_dot_graph(self, root_node: str, dot_nodes: List[str],
      dot_edges: List[str], graph_name: str) -> str:
    nodes_str = "  \n".join(dot_nodes)
    edges_str = "  \n".join(dot_edges)

    return f"""digraph {graph_name}Targets {{
edge [arrowhead="none",color="red;0.2:grey80:green;0.2"];
node [fillcolor="white",shape="plain",style="filled",height="0.02",fontsize="8",fontname="Arial"];
graph [ranksep="13.0",rankdir="LR",outputorder="edgesfirst",root="{root_node}"];
{nodes_str}
{edges_str}
}}"""

  def _print_dot_nodes_and_edges(self,
      nodes_and_edges: List[
        Tuple[TargetNode, List[TargetNode], Set[TargetNode]]], inbound: bool) -> \
      Tuple[str, List[str], List[str]]:

    root_node: str = str(nodes_and_edges[0][0])
    dot_nodes: List[str] = []
    dot_edges: List[str] = []
    node_no: int = 1
    for the_node, direct_nodes, reverse_nodes in nodes_and_edges:
      dot_nodes.append(
          f'"{the_node}" [label="{node_no}:{len(direct_nodes)}:{len(reverse_nodes)}"];')
      node_no += 1
      for direct_node in direct_nodes:
        if inbound:
          dot_edges.append(f'"{direct_node}" -> "{the_node}";')
        else:
          dot_edges.append(f'"{the_node}" -> "{direct_node}";')

    return root_node, dot_nodes, dot_edges

  def _sorted_nodes_by_edge_degree(self,
      direct_edges: Dict[TargetNode, List[TargetNode]],
      reverse_edges: Dict[TargetNode, List[TargetNode]]) -> List[
    Tuple[TargetNode, List[TargetNode], Set[TargetNode]]]:
    nodes_and_edges: List[
      Tuple[TargetNode, List[TargetNode], Set[TargetNode]]] = []
    for the_node, direct_nodes in direct_edges.items():
      nodes_and_edges.append(
          (the_node, direct_nodes, set(reverse_edges[the_node])))
    nodes_and_edges.sort(key=lambda x: -((len(x[1]) << 15) | len(x[2])))

    return nodes_and_edges

  def _dfs_graph(self, from_target: TargetNode,
      visited: Dict[TargetNode, List[TargetNode]],
      reverse_visited: Dict[TargetNode, List[TargetNode]],
      path: Dict[str, TargetNode]) -> None:
    from_label: str = str(from_target)
    if from_label in path:
      cycle_path = " -> ".join(path) + " -> " + from_label
      raise ValueError(f"Cycle found: {cycle_path}")

    if from_target in visited:
      return

    path[from_label] = from_target
    visited.setdefault(from_target, [])
    # to make sure that root also get to reverse_visited
    reverse_visited.setdefault(from_target, [])

    for to_target in from_target.get_targets():
      if not to_target.is_external() and not isinstance(to_target, FileNode):
        visited[from_target].append(to_target)
        reverse_visited.setdefault(to_target, []).append(from_target)
        self._dfs_graph(to_target, visited, reverse_visited, path)
    del path[from_label]

  # def _construct_pkg_graph_edges(self, direct_edges: Dict[TargetNode, List[TargetNode]],
  #     reverse_edges: Dict[TargetNode, List[TargetNode]]) -> None:
  #   for the_node, direct_nodes in direct_edges:
