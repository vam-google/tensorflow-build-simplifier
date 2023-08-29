from typing import List

from buildcleaner.build import Build
from buildcleaner.config import MergedTargetsConfig
from buildcleaner.node import TargetNode
from buildcleaner.parser import BazelBuildTargetsParser
from buildcleaner.rule import BuiltInRules
from buildcleaner.tensorflow.graph import TfTargetDag
from buildcleaner.tensorflow.rule import TfRules
from buildcleaner.tensorflow.transformer import \
  CcHeaderOnlyLibraryTransformer
from buildcleaner.tensorflow.transformer import ChainedCcLibraryMerger
from buildcleaner.tensorflow.transformer import GenerateCcTransformer
from buildcleaner.transformer import ExportFilesTransformer


class TfBuild(Build):
  def __init__(self, root_target: str, bazel_config: str,
      prefix_path: str, merged_targets: MergedTargetsConfig) -> None:
    super().__init__(root_target, bazel_config,
                     BazelBuildTargetsParser(prefix_path,
                                             TfRules.rules(
                                                 BuiltInRules.rules()),
                                             TfRules.ignored_rules()))

    CcHeaderOnlyLibraryTransformer().transform(self.repo_root())
    GenerateCcTransformer().transform(self.repo_root())
    new_targets: List[TargetNode] = ChainedCcLibraryMerger(
        merged_targets).transform(self.repo_root())
    ExportFilesTransformer().transform(self.repo_root())

    dag: TfTargetDag = TfTargetDag()
    dag.prune_unreachable_targets(self.internal_root, new_targets)
