from buildcleaner.build import Build
from buildcleaner.parser import BazelBuildTargetsParser
from buildcleaner.tensorflow.tf_transformer import DebugOptsCollector
from buildcleaner.transformer import ChainTransformer
from buildcleaner.transformer import ExportFilesTransformer
from buildcleaner.tensorflow.tf_transformer import \
  CcHeaderOnlyLibraryTransformer
from buildcleaner.tensorflow.tf_transformer import GenerateCcTransformer
from buildcleaner.rule import BuiltInRules
from buildcleaner.tensorflow.tf_rule import TensorflowRules


class TfBuild(Build):
  def __init__(self, root_target: str, bazel_config: str,
      prefix_path: str) -> None:
    self.debug_opts_collector: DebugOptsCollector = DebugOptsCollector()
    super().__init__(root_target, bazel_config,
                     BazelBuildTargetsParser(prefix_path,
                                             TensorflowRules.rules(BuiltInRules.rules()),
                                             TensorflowRules.ignored_rules()),
                     ChainTransformer([
                         CcHeaderOnlyLibraryTransformer(),
                         GenerateCcTransformer(),
                         ExportFilesTransformer(),
                         self.debug_opts_collector,
                     ]))
