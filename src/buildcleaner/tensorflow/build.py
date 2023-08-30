from buildcleaner.build import Build
from buildcleaner.config import ArtifactTargetsConfig
from buildcleaner.config import MergedTargetsConfig
from buildcleaner.parser import BazelBuildTargetsParser
from buildcleaner.rule import BuiltInRules
from buildcleaner.tensorflow.rule import TfRules
from buildcleaner.tensorflow.transformer import \
  CcHeaderOnlyLibraryTransformer
from buildcleaner.tensorflow.transformer import ChainedCcLibraryMerger
from buildcleaner.tensorflow.transformer import GenerateCcTransformer
from buildcleaner.transformer import AliasReplacer
from buildcleaner.transformer import ExportFilesTransformer
from buildcleaner.transformer import UnreachableTargetsRemover


class TfBuild(Build):
  def __init__(self, root_target: str, bazel_config: str,
      prefix_path: str, merged_targets: MergedTargetsConfig,
      artifact_targets: ArtifactTargetsConfig) -> None:
    super().__init__(root_target, bazel_config,
                     BazelBuildTargetsParser(prefix_path,
                                             TfRules.rules(
                                                 BuiltInRules.rules()),
                                             TfRules.ignored_rules()))

    AliasReplacer().transform(self.repo_root())
    CcHeaderOnlyLibraryTransformer().transform(self.repo_root())
    GenerateCcTransformer().transform(self.repo_root())
    ChainedCcLibraryMerger(merged_targets).transform(self.repo_root())
    ExportFilesTransformer().transform(self.repo_root())
    UnreachableTargetsRemover(artifact_targets.targets).transform(
        self.repo_root())
