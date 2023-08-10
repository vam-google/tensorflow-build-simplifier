from buildcleaner.build import Build
from buildcleaner.parser import BazelBuildTargetsParser
from buildcleaner.tensorflow.transformer import DebugOptsCollector
from buildcleaner.transformer import ChainTransformer
from buildcleaner.transformer import ExportFilesTransformer
from buildcleaner.tensorflow.transformer import \
  CcHeaderOnlyLibraryTransformer
from buildcleaner.tensorflow.transformer import TotalCcLibraryMergeTransformer
from buildcleaner.tensorflow.transformer import GenerateCcTransformer
from buildcleaner.rule import BuiltInRules
from buildcleaner.tensorflow.rule import TfRules


class TfBuild(Build):
  def __init__(self, root_target: str, bazel_config: str,
      prefix_path: str) -> None:
    self.debug_opts_collector: DebugOptsCollector = DebugOptsCollector()
    super().__init__(root_target, bazel_config,
                     BazelBuildTargetsParser(prefix_path,
                                             TfRules.rules(
                                               BuiltInRules.rules()),
                                             TfRules.ignored_rules()),
                     ChainTransformer([
                         CcHeaderOnlyLibraryTransformer(),
                         GenerateCcTransformer(),
                         # self.debug_opts_collector,
                     ]))

    # cc_merge_tranformer: TotalCcLibraryMergeTransformer = TotalCcLibraryMergeTransformer(
    #   self.input_target)
    # cc_merge_tranformer.transform(
    #     self.package_nodes[self.input_target.get_parent_label()])

    export_files_tranformer: ExportFilesTransformer = ExportFilesTransformer()
    export_files_tranformer.transform(self.package_nodes["//"])