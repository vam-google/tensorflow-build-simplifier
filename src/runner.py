from typing import Dict, List, Set, Iterable, Tuple, cast

from parser import BazelBuildTargetsParser
from node import TargetNode, Node

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
    Dict[str, TargetNode], Dict[str, Dict[str, TargetNode]], Set[str], int,
    List[int]]:
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

    # Resolve references
    nodes_by_kind: Dict[str, Dict[
      str, TargetNode]] = self._bazel_query_parser.parse_query_label_kind_output(
        self._runner.query_output(all_targets, output="label_kind"))
    new_all_nodes: Dict[str, TargetNode] = self.resolve_label_references(
        all_nodes, nodes_by_kind)
    new_all_nodes.update(all_nodes)
    all_nodes = new_all_nodes

    # Make sure nodes_by_kind and all_nodes share the same node references for
    # the same label

    for node_key, node in all_nodes.items():
      nodes_of_a_kind: Dict[str, TargetNode] = nodes_by_kind[node.kind.kind]
      if nodes_of_a_kind:
        nodes_of_a_kind[str(node)] = node

    return all_nodes, nodes_by_kind, all_targets, iteration, incremental_lengths

  def resolve_label_references(self, nodes_dict: Dict[str, TargetNode],
      nodes_by_kind: Dict[str, Dict[str, TargetNode]]) -> Dict[str, TargetNode]:
    files_dict = nodes_by_kind["source"]
    new_nodes: Dict[str, TargetNode] = {}
    for label, generic_node in nodes_dict.items():
      if not isinstance(generic_node, TargetNode):
        continue
      node: TargetNode = cast(TargetNode, generic_node)
      for label_list_arg_name in node.label_list_args:
        refs = node.label_list_args[label_list_arg_name]
        node.label_list_args[label_list_arg_name] = []
        for ref in refs:
          if str(ref) in nodes_dict:
            node.label_list_args[label_list_arg_name].append(
                nodes_dict[str(ref)])
          elif str(ref) in files_dict:
            node.label_list_args[label_list_arg_name].append(
                files_dict[str(ref)])
            new_nodes[str(ref)] = files_dict[str(ref)]
          else:
            node.label_list_args[label_list_arg_name].append(ref)

      for label_arg_name in node.label_args:
        label_val = node.label_args[label_arg_name]
        if label_val in nodes_dict:
          node.label_args[label_arg_name] = label_val

    return new_nodes
