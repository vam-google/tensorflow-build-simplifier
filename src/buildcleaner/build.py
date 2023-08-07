from typing import Dict, cast

from buildcleaner.runner import BazelRunner, TargetsCollector, CollectedTargets
from buildcleaner.transformer import CcHeaderOnlyLibraryTransformer, \
  GenerateCcTransformer, ExportFilesTransformer, ChainTransformer
from buildcleaner.graph import NodesTreeBuilder
from buildcleaner.parser import BazelBuildTargetsParser
from buildcleaner.node import TargetNode, ContainerNode, RepositoryNode


class Build:
  def __init__(self, root_target: str, bazel_config: str, prefix_path: str):
    bazel_runner: BazelRunner = BazelRunner()
    bazel_query_parser: BazelBuildTargetsParser = BazelBuildTargetsParser(
        prefix_path)
    targets_collector: TargetsCollector = TargetsCollector(bazel_runner,
                                                           bazel_query_parser)

    targets: CollectedTargets = targets_collector.collect_dependencies(
        root_target, bazel_config)
    print(f"Targets: {len(targets.all_targets)}\n"
          f"Nodes: {len(targets.all_nodes)}\n"
          f"Iterations: {targets.iterations}\n"
          f"Incremental Lengths: {targets.incremental_lengths}")

    tree_builder: NodesTreeBuilder = NodesTreeBuilder()

    self.package_nodes: Dict[
      str, ContainerNode] = tree_builder.build_package_tree(
        targets.all_nodes.values())
    self.targets_by_kind: Dict[
      str, Dict[str, TargetNode]] = targets.nodes_by_kind
    self.repo_root: RepositoryNode = cast(RepositoryNode,
                                          self.package_nodes["//"])
    self.input_target: TargetNode = targets.all_nodes[root_target]

    chain_transformer: ChainTransformer = ChainTransformer([
        CcHeaderOnlyLibraryTransformer(),
        GenerateCcTransformer(),
        ExportFilesTransformer()
    ])
    chain_transformer.transform(self.repo_root)
