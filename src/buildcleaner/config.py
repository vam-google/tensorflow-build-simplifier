import os
from typing import List


class MergedTargetsConfig:
  def __init__(self) -> None:
    self.new_targets_prefix: str = ""
    self.original_targets: List[str] = []


class Config:
  def __init__(self) -> None:
    self.root_target: str = ""
    self.prefix_path: str = os.getcwd()
    self.bazel_config: str = ""
    self.output_build_path: str = ""
    self.debug_package_graph_path: str = ""
    self.debug_target_graph_path: str = ""
    self.build_file_name: str = "BUILD"
    self.debug_build: bool = False
    self.debug_nodes_by_kind: bool = False
    self.debug_tree: bool = False
    self.merged_targets: MergedTargetsConfig = MergedTargetsConfig()
