from typing import Dict, List, Set, Iterable, Tuple

from parser import BazelBuildTargetsParser
from node import  TargetNode

import subprocess


class BazelRunner:
  def query_output(self, targets: Set[str], config: str = "pycpp_filters",
      output: str = "build", chunk_size: int = 1500) -> str:
    bazel_query_stdouts: List[str] = []
    for target_chunk in self._split_into_chunks(targets, chunk_size):
      chunk = "'" + "' union '".join(target_chunk) + "'"
      proc = subprocess.run([
          "bazel",
          "cquery",
          f"--config={config}" if config else "",
          chunk,
          "--output",
          f"{output}"
      ], stdout=subprocess.PIPE)

      bazel_query_stdouts.append(proc.stdout.decode('utf-8'))
    return "\n".join(bazel_query_stdouts)

  def _split_into_chunks(self, targets: Set[str], chunk_size) -> Iterable[
    Iterable[str]]:
    if len(targets) <= chunk_size:
      yield targets
      return
    cur_chunk: List[str] = []
    for target in targets:
      if len(cur_chunk) >= chunk_size:
        yield cur_chunk
        cur_chunk = []
      cur_chunk.append(target)

    if cur_chunk:
      yield cur_chunk


class TargetsCollector:
  def __init__(self, runner: BazelRunner,
      bazel_query_parser: BazelBuildTargetsParser) -> None:
    self._runner: BazelRunner = runner
    self._bazel_query_parser: BazelBuildTargetsParser = bazel_query_parser

  def clollect_targets(self, root_target: str, bazel_config: str) -> Tuple[
    Dict[str, TargetNode], Set[str], int, List[int]]:
    next_level_internal_targets: Set[str] = {root_target}

    all_targets: Set[str] = set()
    all_nodes: Dict[str, TargetNode] = {}

    iteration: int = 0
    incremental_lengths: List[int] = []
    while len(next_level_internal_targets) > 0:
      iteration += 1
      incremental_lengths.append(len(next_level_internal_targets))
      print(
          f"Iteration: {iteration}, Next Level Targets: {len(next_level_internal_targets)}")
      all_targets.update(next_level_internal_targets)
      bazel_query_stdout = self._runner.query_output(
          next_level_internal_targets,
          config=bazel_config)
      internal_nodes, external_targets, internal_targets = self._bazel_query_parser.parse_query_build_output(
          bazel_query_stdout)
      all_nodes.update(internal_nodes)
      next_level_internal_targets = internal_targets - all_targets

    return all_nodes, all_targets, iteration, incremental_lengths
