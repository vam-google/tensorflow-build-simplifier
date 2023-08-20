import sys
from typing import List

from buildcleaner.build import Build
from buildcleaner.cli import BuildCleanerCli
from buildcleaner.tensorflow.build import TfBuild


class TfBuildCleanerCli(BuildCleanerCli):
  def __init__(self, cli_args: List[str]) -> None:
    super().__init__(cli_args)

  def generate_build(self) -> Build:
    return TfBuild(self._root_target, self._bazel_config, self._prefix_path,
                   self._merged_targets)


if __name__ == '__main__':
  cli = TfBuildCleanerCli(sys.argv[1:])
  cli.main()
