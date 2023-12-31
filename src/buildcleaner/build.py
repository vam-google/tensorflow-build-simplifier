from typing import Dict
from typing import List
from typing import cast

from buildcleaner.config import BaseTargetsConfig
from buildcleaner.graph import PackageTree
from buildcleaner.graph import TargetDag
from buildcleaner.node import RepositoryNode
from buildcleaner.node import RootNode
from buildcleaner.node import TargetNode
from buildcleaner.parser import BazelBuildTargetsParser
from buildcleaner.runner import BazelRunner


class Build:
  def __init__(self, base_targets: BaseTargetsConfig,
      parser: BazelBuildTargetsParser):
    bazel_runner: BazelRunner = BazelRunner()
    targets_collector: TargetsCollector = TargetsCollector(bazel_runner,
                                                           parser)
    all_target_nodes: Dict[
      str, TargetNode] = targets_collector.collect_dependencies(
        [base_targets.target], base_targets.bazel_config,
        base_targets.excluded_targets)

    tree_builder: PackageTree = PackageTree()

    self.internal_root: RootNode
    self.external_root: RootNode
    self.internal_root, self.external_root = tree_builder.build_package_tree(
        all_target_nodes.values())

  def repo_root(self) -> RepositoryNode:
    return cast(RepositoryNode, self.internal_root["//"])


class TargetsCollector:
  def __init__(self, runner: BazelRunner,
      bazel_query_parser: BazelBuildTargetsParser) -> None:
    self._runner: BazelRunner = runner
    self._bazel_query_parser: BazelBuildTargetsParser = bazel_query_parser

  def collect_dependencies(self, targets: List[str],
      bazel_config: str, excluded_targets: List[str]) -> Dict[str, TargetNode]:

    all_nodes: Dict[str, TargetNode] = {}
    unresolved_labels = list(targets)
    actual_excluded_targets = list(excluded_targets)
    excluded_prefixes: List[str] = self._calculate_excluded_target_prefixes(
        excluded_targets)

    runs: int = 0
    while unresolved_labels:
      runs += 1
      internal_nodes: Dict[str, TargetNode]
      query_output: str = self._runner.query_deps_output(unresolved_labels,
                                                         bazel_config,
                                                         "build",
                                                         actual_excluded_targets)
      internal_nodes, _, _ = self._bazel_query_parser.parse_query_build_output(
          query_output)
      all_nodes.update(internal_nodes)

      # Resolve references
      query_output = self._runner.query_deps_output(unresolved_labels,
                                                    bazel_config,
                                                    "label_kind",
                                                    actual_excluded_targets)
      nodes_by_kind: Dict[str, Dict[
        str, TargetNode]] = self._bazel_query_parser.parse_query_label_kind_output(
          query_output)
      all_nodes.update(
          self.resolve_label_references(all_nodes, nodes_by_kind["source"]))

      # The only allowed unresolved references are the ones which were excluded by
      # excluded_targets.
      tree: TargetDag = TargetDag()
      unresolved_targets: Dict[
        TargetNode, List[str]] = tree.get_unresolved_targets(all_nodes.values(),
                                                             excluded_prefixes)

      unresolved_labels = [str(k) for k, _ in unresolved_targets.items()]

      # The excluded targets matter only on the first run, on the subsequent run
      # we gather excluded targets on which the non-excluded targets depend on,
      # thus un-excluding that subset of excluded targets.
      actual_excluded_targets = []
      excluded_prefixes = []

    # dag: TargetDag = TargetDag()
    # visited: Dict[TargetNode, Set[TargetNode]] = {}
    # dag.dfs_graph()

    return all_nodes

  def _calculate_excluded_target_prefixes(self, excluded_targets: List[str]) -> \
      List[str]:
    package_prefixes: List[str] = []
    for t in excluded_targets:
      package_prefixes.append(t.replace("/...", "").split(":")[0])

    return package_prefixes

  def resolve_label_references(self, nodes_dict: Dict[str, TargetNode],
      files_dict: Dict[str, TargetNode]) -> Dict[str, TargetNode]:
    new_nodes: Dict[str, TargetNode] = {}
    for label, generic_node in nodes_dict.items():
      if not isinstance(generic_node, TargetNode):
        continue
      target_node: TargetNode = cast(TargetNode, generic_node)
      ref_str: str
      resolved_ref: TargetNode

      for label_list_arg_name in target_node.label_list_args:
        refs: List[TargetNode] = target_node.label_list_args[
          label_list_arg_name]
        target_node.label_list_args[label_list_arg_name] = []
        for ref in refs:
          resolved_ref = ref
          ref_str = str(ref)
          if ref_str in nodes_dict:
            resolved_ref = nodes_dict[ref_str]
          elif ref_str in files_dict:
            resolved_ref = files_dict[ref_str]
            new_nodes[ref_str] = resolved_ref
          target_node.label_list_args[label_list_arg_name].append(resolved_ref)

      for label_arg_name in target_node.label_args:
        resolved_ref = target_node.label_args[label_arg_name]
        ref_str = str(resolved_ref)
        if ref_str in nodes_dict:
          resolved_ref = nodes_dict[ref_str]
        elif ref_str in files_dict:
          resolved_ref = files_dict[ref_str]
          new_nodes[ref_str] = resolved_ref
        target_node.label_args[label_arg_name] = resolved_ref

    return new_nodes
