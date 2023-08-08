from buildcleaner.build import Build
from buildcleaner.parser import BazelBuildTargetsParser
from buildcleaner.transformer import ChainTransformer
from buildcleaner.transformer import ExportFilesTransformer
from buildcleaner.tensorflow.tf_transformer import CcHeaderOnlyLibraryTransformer
from buildcleaner.tensorflow.tf_transformer import GenerateCcTransformer
from buildcleaner.tensorflow.rule import TensorflowRules


class TfBuild(Build):
  def __init__(self, root_target: str, bazel_config: str,
      prefix_path: str) -> None:
    super().__init__(root_target, bazel_config,
                     BazelBuildTargetsParser(prefix_path,
                                             TensorflowRules.rules(),
                                             TensorflowRules.ignored_rules()),
                     ChainTransformer([
                         CcHeaderOnlyLibraryTransformer(),
                         GenerateCcTransformer(),
                         ExportFilesTransformer()
                     ]))
