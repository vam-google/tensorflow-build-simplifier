from buildcleaner.build import Build
from buildcleaner.config import ArtifactTargetsConfig
from buildcleaner.config import BaseTargetsConfig
from buildcleaner.config import MergedTargetsConfig
from buildcleaner.graph import TargetDag
from buildcleaner.parser import BazelBuildTargetsParser
from buildcleaner.rule import BuiltInRules
from buildcleaner.tensorflow.rule import TfRules
from buildcleaner.tensorflow.transformer import ChainedCcLibraryMerger
from buildcleaner.tensorflow.transformer import TfNonsenseTransformer
from buildcleaner.tensorflow.transformer import \
  TrivialPrivateRuleToPublicMacroTransformer
from buildcleaner.transformer import AliasReplacer
from buildcleaner.transformer import ExportFilesTransformer
from buildcleaner.transformer import UnreachableTargetsRemover


class TfBuild(Build):
  def __init__(self, base_targets: BaseTargetsConfig,
      prefix_path: str, merged_targets: MergedTargetsConfig,
      artifact_targets: ArtifactTargetsConfig) -> None:
    super().__init__(base_targets,
                     BazelBuildTargetsParser(prefix_path,
                                             BuiltInRules.rules(
                                                 TfRules.rules()),
                                             TfRules.ignored_rules()))

    AliasReplacer().transform(self.repo_root())
    TrivialPrivateRuleToPublicMacroTransformer().transform(self.repo_root())
    ChainedCcLibraryMerger(merged_targets).transform(self.repo_root())
    ExportFilesTransformer().transform(self.repo_root())
    TfNonsenseTransformer().transform(self.repo_root())

    if artifact_targets.prune_unreachable:
      UnreachableTargetsRemover(artifact_targets.targets).transform(
          self.repo_root())

    dag: TargetDag = TargetDag()
    dag.get_unresolved_targets(self.repo_root().tree_nodes(), [])
