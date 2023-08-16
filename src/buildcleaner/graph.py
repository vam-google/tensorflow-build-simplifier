import re
from typing import Dict
from typing import Iterable
from typing import List
from typing import Pattern
from typing import Set
from typing import Tuple
from typing import cast

from buildcleaner.node import ContainerNode
from buildcleaner.node import FileNode
from buildcleaner.node import GeneratedFileNode
from buildcleaner.node import Node
from buildcleaner.node import PackageNode
from buildcleaner.node import RepositoryNode
from buildcleaner.node import RootNode
from buildcleaner.node import TargetNode


class PackageTreeBuilder:
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


class DagBuilder:
  def __init__(self, root: TargetNode):
    self._inbound_edges: Dict[TargetNode, Set[TargetNode]] = {}
    self._outbound_edges: Dict[TargetNode, Set[TargetNode]] = {}
    path: Dict[str, TargetNode] = {}
    self._dfs_graph_internal(root, self._outbound_edges, self._inbound_edges,
                             path)

  def build_target_dag(self, sort_by_indegree: bool) -> List[
    Tuple[TargetNode, Set[TargetNode], Set[TargetNode]]]:
    nodes_by_degree: List[Tuple[TargetNode, Set[TargetNode], Set[TargetNode]]]
    if sort_by_indegree:
      nodes_by_degree = self._sorted_nodes_by_edge_degree(self._inbound_edges,
                                                          self._outbound_edges)
    else:
      nodes_by_degree = self._sorted_nodes_by_edge_degree(self._outbound_edges,
                                                          self._inbound_edges)
    return nodes_by_degree

  def _sorted_nodes_by_edge_degree(self,
      direct_edges: Dict[TargetNode, Set[TargetNode]],
      reverse_edges: Dict[TargetNode, Set[TargetNode]]) -> List[
    Tuple[TargetNode, Set[TargetNode], Set[TargetNode]]]:
    nodes_and_edges: List[
      Tuple[TargetNode, Set[TargetNode], Set[TargetNode]]] = []
    for the_node, direct_nodes in direct_edges.items():
      nodes_and_edges.append(
          (the_node, direct_nodes, set(reverse_edges[the_node])))
    nodes_and_edges.sort(key=lambda x: -((len(x[1]) << 15) | len(x[2])))

    return nodes_and_edges

  def _dfs_graph_internal(self, from_target: TargetNode,
      visited: Dict[TargetNode, Set[TargetNode]],
      reverse_visited: Dict[TargetNode, Set[TargetNode]],
      path: Dict[str, TargetNode]) -> None:
    from_label: str = str(from_target)
    if from_label in path:
      cycle_path = " -> ".join(path) + " -> " + from_label
      raise ValueError(f"Cycle found: {cycle_path}")

    if from_target in visited:
      return

    path[from_label] = from_target
    visited.setdefault(from_target, set())
    # to make sure that root also get to reverse_visited
    reverse_visited.setdefault(from_target, set())

    for to_target in from_target.get_targets():
      if not to_target.is_external():
        actual_to_target: TargetNode = to_target
        if isinstance(to_target, GeneratedFileNode):
          actual_to_target = cast(GeneratedFileNode, to_target).maternal_target
        if not isinstance(actual_to_target, FileNode):
          visited[from_target].add(actual_to_target)
          reverse_visited.setdefault(actual_to_target, set()).add(from_target)
          self._dfs_graph_internal(actual_to_target, visited, reverse_visited,
                                   path)

    del path[from_label]


class DgPkgBuilder(DagBuilder):
  def __init__(self, root: TargetNode,
      tree_nodes: Dict[str, ContainerNode]) -> None:
    super().__init__(root)
    self._inbound_pkg_edges: Dict[
      PackageNode, Set[PackageNode]] = self._build_package_edges(
        self._inbound_edges, tree_nodes)
    self._outbound_pkg_edges: Dict[
      PackageNode, Set[PackageNode]] = self._build_package_edges(
        self._outbound_edges, tree_nodes)

  def build_package_dg(self, sort_by_indegree: bool) -> List[
    Tuple[PackageNode, Set[PackageNode], Set[PackageNode]]]:
    pkgs_by_degree: List[Tuple[PackageNode, Set[PackageNode], Set[PackageNode]]]
    if sort_by_indegree:
      pkgs_by_degree = self._sorted_pkgs_by_edge_degree(self._inbound_pkg_edges,
                                                        self._outbound_pkg_edges)
    else:
      pkgs_by_degree = self._sorted_pkgs_by_edge_degree(
          self._outbound_pkg_edges,
          self._inbound_pkg_edges)
    return pkgs_by_degree

  def _sorted_pkgs_by_edge_degree(self,
      direct_edges: Dict[PackageNode, Set[PackageNode]],
      reverse_edges: Dict[PackageNode, Set[PackageNode]]):
    pkgs_and_edges: List[
      Tuple[PackageNode, Set[PackageNode], Set[PackageNode]]] = []
    for the_node, direct_nodes in direct_edges.items():
      pkgs_and_edges.append(
          (the_node, direct_nodes, set(reverse_edges[the_node])))
    pkgs_and_edges.sort(key=lambda x: -((len(x[1]) << 15) | len(x[2])))

    return pkgs_and_edges

  def _build_package_edges(self,
      direct_edges: Dict[TargetNode, Set[TargetNode]],
      tree_nodes: Dict[str, ContainerNode]) -> Dict[
    PackageNode, Set[PackageNode]]:
    pkg_edges: Dict[PackageNode, Set[PackageNode]] = {}
    for the_node, edge in direct_edges.items():
      the_pkg: PackageNode = cast(PackageNode,
                                  tree_nodes[str(the_node.get_parent_label())])
      cur_pkg_edges = pkg_edges.setdefault(the_pkg, set())
      for direct_node in edge:
        direct_pkg: PackageNode = cast(PackageNode, tree_nodes[
          direct_node.get_parent_label()])
        # do not put reflexive edges
        if direct_pkg != the_pkg:
          cur_pkg_edges.add(direct_pkg)

    return pkg_edges
