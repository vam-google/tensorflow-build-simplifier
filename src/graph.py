from typing import Pattern, List, Dict, Iterable, Tuple, Set, cast
from node import Node, ContainerNode, TargetNode, RootNode, RepositoryNode, \
  PackageNode, FileNode
import re

class NodesTreeBuilder:
  def __init__(self) -> None:
    self._label_splitter_regex: Pattern = re.compile(
        r"(?P<external>@?)(?P<repo>\w*)//(?P<package>[0-9a-zA-Z\-\._\@/]+)*:(?P<name>[0-9a-zA-Z\-\._\+/]+)$")

  def get_label_components(self, label: str) -> Tuple[bool, str, str, str]:
    match = self._label_splitter_regex.search(label)
    if not match:
      raise ValueError(f"{label} is not a valid label")
    return match.group("external") == "@", match.group("repo"), match.group(
        "package"), match.group("name")

  def build_package_tree(self, target_nodes_list: Iterable[Node]) -> Dict[
    str, ContainerNode]:
    external_root = RootNode("@")
    internal_root = RootNode("")
    all_containers: Dict[str, ContainerNode] = {
        external_root.label: external_root,
        internal_root.label: internal_root
    }
    for node in target_nodes_list:
      external, repo, pkg, name = self.get_label_components(node.label)
      root_node = external_root if external else internal_root
      repo_node: RepositoryNode = RepositoryNode(repo, root_node.label)
      if str(repo_node) not in all_containers:
        root_node.children[str(repo_node)] = repo_node
        all_containers[str(repo_node)] = repo_node
      else:
        repo_node = cast(RepositoryNode, all_containers[str(repo_node)])

      folders = pkg.split("/")
      container_node: ContainerNode = repo_node
      all_containers[str(container_node)] = container_node
      package_depth: int = 2
      for folder in folders:
        next_package_node: PackageNode = PackageNode(folder,
                                                     str(container_node),
                                                     package_depth)
        next_package_node = cast(PackageNode,
                                 all_containers.setdefault(
                                     str(next_package_node),
                                     next_package_node))
        package_depth += 1
        container_node.children[str(next_package_node)] = next_package_node
        container_node = next_package_node
      container_node.children[str(node)] = node

    return all_containers



class DagNodesBuilder:
  def print_target_graph(self, root: TargetNode, sort_by_indegree: bool) -> List[
      Tuple[TargetNode, List[TargetNode], Set[TargetNode]]]:
    inbound_edges: Dict[TargetNode, List[TargetNode]] = {}
    outbound_edges: Dict[TargetNode, List[TargetNode]] = {}
    path: Dict[str, TargetNode] = {}
    self._dfs_graph(root, outbound_edges, inbound_edges, path)

    if sort_by_indegree:
      nodes_by_degree = self._sorted_nodes_by_edge_degree(inbound_edges,
                                                          outbound_edges)
    else:
      nodes_by_degree = self._sorted_nodes_by_edge_degree(outbound_edges,
                                                          inbound_edges)
    return nodes_by_degree

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