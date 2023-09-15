import re
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
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


class TargetDag:
  def dfs_graph(self, from_target: TargetNode,
      visited: Dict[TargetNode, Set[TargetNode]],
      reverse_visited: Optional[Dict[TargetNode, Set[TargetNode]]],
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
    if reverse_visited is not None:
      reverse_visited.setdefault(from_target, set())

    for to_target in from_target.get_targets():
      if not to_target.is_external():
        actual_to_target: TargetNode = to_target
        if isinstance(to_target, GeneratedFileNode):
          actual_to_target = cast(GeneratedFileNode, to_target).maternal_target
        if not isinstance(actual_to_target, FileNode):
          visited[from_target].add(actual_to_target)
          if reverse_visited is not None:
            reverse_visited.setdefault(actual_to_target, set()).add(from_target)
          self.dfs_graph(actual_to_target, visited, reverse_visited,
                         path)

    del path[from_label]

  def prune_unreachable_targets(self, root: ContainerNode,
      artifact_nodes: List[TargetNode]) -> None:
    visited: Dict[TargetNode, Set[TargetNode]] = {}
    path: Dict[str, TargetNode] = {}

    for artifact_node in artifact_nodes:
      self.dfs_graph(artifact_node, visited, None, path)

    unreachable_nodes: List[TargetNode] = []
    for node in root.tree_nodes():
      if not self.is_removable_node(node):
        continue
      target: TargetNode = cast(TargetNode, node)
      if target in visited:
        continue
      unreachable_nodes.append(target)

    for unreachable_node in unreachable_nodes:
      del root[str(unreachable_node)]
      for unreachable_out_targets in unreachable_node.out_label_list_args.values():
        for unreachable_out_target in unreachable_out_targets:
          del root[str(unreachable_out_target)]

      for unreachable_out_target in unreachable_node.out_label_args.values():
        del root[str(unreachable_out_target)]

  def is_removable_node(self, node: Node) -> bool:
    return not isinstance(node, (FileNode, GeneratedFileNode, ContainerNode))


class PackageTree:
  def __init__(self) -> None:
    self._label_splitter_regex: Pattern = re.compile(
        r"(?P<external>@?)(?P<repo>\w*)//(?P<package>[0-9a-zA-Z\-\._\@/]*):(?P<name>[0-9a-zA-Z\-\._\+/]+)$")

  def get_label_components(self, label: str) -> Tuple[bool, str, str, str]:
    match = self._label_splitter_regex.search(label)
    if not match:
      raise ValueError(f"{label} is not a valid label")
    return match.group("external") == "@", match.group("repo"), match.group(
        "package"), match.group("name")

  def build_package_tree(self, target_nodes_list: Iterable[Node]) -> Tuple[
    RootNode, RootNode]:
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

      folders = pkg.split("/") if pkg else []
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

    return internal_root, external_root

  def replace_targets(self, container: ContainerNode,
      new_targets: Dict[str, TargetNode]) -> None:
    children_to_replace: List[TargetNode] = []
    for child in container.children.values():
      if isinstance(child, ContainerNode):
        self.replace_targets(cast(ContainerNode, child), new_targets)
      if not isinstance(child, TargetNode):
        continue

      target_child: TargetNode = cast(TargetNode, child)

      if target_child.label in new_targets:
        children_to_replace.append(target_child)
        continue

      new_target: Optional[TargetNode]

      for label_arg_list in target_child.label_list_args.values():
        for i in range(len(label_arg_list)):
          new_target = new_targets.get(str(label_arg_list[i]))
          if new_target:
            label_arg_list[i] = new_target
            # there can be no label duplicates in same arg
            break

      labels_to_replace: List[str] = []
      for arg_name, label_arg in target_child.label_args.items():
        new_target = new_targets.get(str(label_arg))
        if new_target:
          labels_to_replace.append(arg_name)
      for label_to_replace in labels_to_replace:
        target_child.label_args[label_to_replace] = new_targets[
          str(target_child.label_args[label_to_replace])]


class TargetDagBuilder(TargetDag):
  def __init__(self, root: TargetNode):
    self._inbound_edges: Dict[TargetNode, Set[TargetNode]] = {}
    self._outbound_edges: Dict[TargetNode, Set[TargetNode]] = {}
    path: Dict[str, TargetNode] = {}
    self.dfs_graph(root, self._outbound_edges, self._inbound_edges,
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
