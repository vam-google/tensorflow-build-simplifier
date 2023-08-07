from typing import Dict, List, Set, Iterable, Union, cast

from parser import BazelBuildTargetsParser
from node import TargetNode, PackageNode

import subprocess


class BazelRunner:
  def query_output(self, targets: Set[str], config: str = "pycpp_filters",
      output: str = "build", chunk_size: int = 1500) -> str:
    bazel_query_stdouts: List[str] = []
    for target_chunk in self._split_into_chunks(targets, chunk_size):
      chunk: str = "'" + "' union '".join(target_chunk) + "'"
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

  def query_deps_output(self, target: str, config: str = "pycpp_filters",
      output: str = "label_kind") -> str:
    proc = subprocess.run([
        "bazel",
        "cquery",
        f"--config={config}" if config else "",
        # f"'//tensorflow'",
        f"deps({target})",
        "--output",
        f"{output}"
    ], stdout=subprocess.PIPE)

    return proc.stdout.decode('utf-8')

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


class CollectedTargets:
  def __init__(self) -> None:
    self.all_nodes: Dict[str, TargetNode] = {}
    self.nodes_by_kind: Dict[str, Dict[str, TargetNode]] = {}
    self.all_targets: Set[str] = set()
    self.iterations: int = 0
    self.incremental_lengths: List[int] = []


class TargetsCollector:
  def __init__(self, runner: BazelRunner,
      bazel_query_parser: BazelBuildTargetsParser) -> None:
    self._runner: BazelRunner = runner
    self._bazel_query_parser: BazelBuildTargetsParser = bazel_query_parser

  def collect_dependencies(self, root_target: str,
      bazel_config: str) -> CollectedTargets:

    res: CollectedTargets = CollectedTargets()
    res.iterations = 1
    res.incremental_lengths.append(1)

    internal_nodes: Dict[str, TargetNode]
    internal_nodes, external_targets, internal_targets = self._bazel_query_parser.parse_query_build_output(
        self._runner.query_deps_output(root_target, config=bazel_config,
                                       output="build"))
    res.all_nodes.update(internal_nodes)
    res.all_targets.update(internal_targets)

    # Resolve references
    nodes_by_kind: Dict[str, Dict[
      str, TargetNode]] = self._bazel_query_parser.parse_query_label_kind_output(
        self._runner.query_deps_output(root_target, config=bazel_config,
                                       output="label_kind"))
    self._resolve_references(res, nodes_by_kind)
    res.nodes_by_kind = nodes_by_kind

    return res

  def collect_targets(self, root_target: str,
      bazel_config: str) -> CollectedTargets:
    next_level_internal_targets: Set[str] = {root_target}

    res: CollectedTargets = CollectedTargets()
    while len(next_level_internal_targets) > 0:
      res.iterations += 1
      res.incremental_lengths.append(len(next_level_internal_targets))
      print(
          f"Iteration: {res.iterations}, Next Level Targets: {len(next_level_internal_targets)}")
      res.all_targets.update(next_level_internal_targets)
      bazel_query_stdout = self._runner.query_output(
          next_level_internal_targets,
          config=bazel_config)
      internal_nodes, external_targets, internal_targets = self._bazel_query_parser.parse_query_build_output(
          bazel_query_stdout)
      res.all_nodes.update(internal_nodes)
      next_level_internal_targets = internal_targets - res.all_targets

    # Resolve references
    nodes_by_kind: Dict[str, Dict[
      str, TargetNode]] = self._bazel_query_parser.parse_query_label_kind_output(
        self._runner.query_output(res.all_targets, output="label_kind"))

    self._resolve_references(res, nodes_by_kind)
    res.nodes_by_kind = nodes_by_kind

    return res

  def _resolve_references(self, res: CollectedTargets,
      nodes_by_kind: Dict[str, Dict[str, TargetNode]]) -> None:
    new_all_nodes: Dict[str, TargetNode] = self.resolve_label_references(
        res.all_nodes, nodes_by_kind["source"])
    new_all_nodes.update(res.all_nodes)
    res.all_nodes = new_all_nodes

    # Make sure nodes_by_kind and all_nodes share the same node references for
    # the same label
    for node_key, node in res.all_nodes.items():
      nodes_of_a_kind: Dict[str, TargetNode] = nodes_by_kind[node.kind.kind]
      if nodes_of_a_kind:
        nodes_of_a_kind[str(node)] = node

  def resolve_label_references(self, nodes_dict: Dict[str, TargetNode],
      files_dict: Dict[str, TargetNode]) -> Dict[str, TargetNode]:
    new_nodes: Dict[str, TargetNode] = {}
    for label, generic_node in nodes_dict.items():
      if not isinstance(generic_node, TargetNode):
        continue
      target_node: TargetNode = cast(TargetNode, generic_node)
      ref_str: str
      resolved_ref: TargetNode

      for label_list_arg_name in target_node.label_list_args:
        refs: List[TargetNode] = target_node.label_list_args[
          label_list_arg_name]
        target_node.label_list_args[label_list_arg_name] = []
        for ref in refs:
          resolved_ref = ref
          ref_str = str(ref)
          if ref_str in nodes_dict:
            resolved_ref = nodes_dict[ref_str]
          elif ref_str in files_dict:
            resolved_ref = files_dict[ref_str]
            new_nodes[ref_str] = resolved_ref
          target_node.label_list_args[label_list_arg_name].append(resolved_ref)

      for label_arg_name in target_node.label_args:
        resolved_ref = target_node.label_args[label_arg_name]
        ref_str = str(resolved_ref)
        if ref_str in nodes_dict:
          resolved_ref = nodes_dict[ref_str]
        elif ref_str in files_dict:
          resolved_ref = files_dict[ref_str]
          new_nodes[ref_str] = resolved_ref
        target_node.label_args[label_arg_name] = resolved_ref

    return new_nodes
