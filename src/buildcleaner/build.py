from typing import cast

from buildcleaner.graph import PackageTreeBuilder
from buildcleaner.node import RepositoryNode
from buildcleaner.node import RootNode
from buildcleaner.node import TargetNode
from buildcleaner.parser import BazelBuildTargetsParser
from buildcleaner.runner import BazelRunner
from buildcleaner.runner import CollectedTargets
from buildcleaner.runner import TargetsCollector


class Build:
  def __init__(self, root_target: str, bazel_config: str,
      parser: BazelBuildTargetsParser):
    bazel_runner: BazelRunner = BazelRunner()
    targets_collector: TargetsCollector = TargetsCollector(bazel_runner,
                                                           parser)
    targets: CollectedTargets = targets_collector.collect_dependencies(
        root_target, bazel_config)

    tree_builder: PackageTreeBuilder = PackageTreeBuilder()

    self.internal_root: RootNode
    self.external_root: RootNode
    self.internal_root, self.external_root = tree_builder.build_package_tree(
        targets.all_nodes.values())
    self.input_target: TargetNode = targets.all_nodes[root_target]

  def repo_root(self) -> RepositoryNode:
    return cast(RepositoryNode, self.internal_root["//"])
