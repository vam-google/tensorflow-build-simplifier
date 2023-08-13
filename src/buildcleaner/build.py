from typing import Dict
from typing import cast

from buildcleaner.graph import PackageTreeBuilder
from buildcleaner.node import ContainerNode
from buildcleaner.node import RepositoryNode
from buildcleaner.node import TargetNode
from buildcleaner.parser import BazelBuildTargetsParser
from buildcleaner.runner import BazelRunner
from buildcleaner.runner import CollectedTargets
from buildcleaner.runner import TargetsCollector
from buildcleaner.transformer import RuleTransformer


class Build:
  def __init__(self, root_target: str, bazel_config: str,
      parser: BazelBuildTargetsParser, transformer: RuleTransformer):
    bazel_runner: BazelRunner = BazelRunner()
    targets_collector: TargetsCollector = TargetsCollector(bazel_runner,
                                                           parser)

    targets: CollectedTargets = targets_collector.collect_dependencies(
        root_target, bazel_config)
    print(f"Targets: {len(targets.all_targets)}\n"
          f"Nodes: {len(targets.all_nodes)}\n"
          f"Iterations: {targets.iterations}\n"
          f"Incremental Lengths: {targets.incremental_lengths}")

    tree_builder: PackageTreeBuilder = PackageTreeBuilder()

    self.package_nodes: Dict[
      str, ContainerNode] = tree_builder.build_package_tree(
        targets.all_nodes.values())
    self.targets_by_kind: Dict[
      str, Dict[str, TargetNode]] = targets.nodes_by_kind
    self.repo_root: RepositoryNode = cast(RepositoryNode,
                                          self.package_nodes["//"])
    self.input_target: TargetNode = targets.all_nodes[root_target]

    transformer.transform(self.repo_root)
