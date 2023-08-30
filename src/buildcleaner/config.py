import os
from typing import List


class Config:
  def __init__(self) -> None:
    self.root_target: str = ""
    self.prefix_path: str = os.getcwd()
    self.bazel_config: str = ""
    self.output_build_path: str = ""
    self.debug_target_graph: DebugTargetGraph = DebugTargetGraph()
    self.build_file_name: str = "BUILD"
    self.debug_build: bool = False
    self.debug_tree: bool = False
    self.merged_targets: MergedTargetsConfig = MergedTargetsConfig()
    self.artifact_targets: ArtifactTargetsConfig = ArtifactTargetsConfig()


class ArtifactTargetsConfig:
  def __init__(self) -> None:
    self.targets: List[str] = []


class MergedTargetsConfig:
  def __init__(self) -> None:
    self.new_targets_prefix: str = ""
    self.targets: List[str] = []


class DebugTargetGraph:
  def __init__(self) -> None:
    self.path: str = ""
    self.targets: List[str] = []
