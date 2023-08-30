from typing import Dict
from typing import cast

from buildcleaner.graph import PackageTree
from buildcleaner.node import RepositoryNode
from buildcleaner.node import RootNode
from buildcleaner.node import TargetNode
from buildcleaner.parser import BazelBuildTargetsParser
from buildcleaner.runner import BazelRunner
from buildcleaner.runner import TargetsCollector


class Build:
  def __init__(self, root_target: str, bazel_config: str,
      parser: BazelBuildTargetsParser):
    bazel_runner: BazelRunner = BazelRunner()
    targets_collector: TargetsCollector = TargetsCollector(bazel_runner,
                                                           parser)
    all_target_nodes: Dict[
      str, TargetNode] = targets_collector.collect_dependencies(
        root_target, bazel_config)

    tree_builder: PackageTree = PackageTree()

    self.internal_root: RootNode
    self.external_root: RootNode
    self.internal_root, self.external_root = tree_builder.build_package_tree(
        all_target_nodes.values())

  def repo_root(self) -> RepositoryNode:
    return cast(RepositoryNode, self.internal_root["//"])
