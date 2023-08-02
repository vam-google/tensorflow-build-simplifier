import sys
import os
import time

from typing import Dict, Optional, List, cast

from runner import BazelRunner, TargetsCollector, CollectedTargets
from transformer import NodesGraphBuilder, PackageTargetsTransformer
from parser import BazelBuildTargetsParser
from printer import BuildFilesPrinter, GraphPrinter, DebugTreePrinter
from fileio import BuildFilesWriter, GraphvizWriter
from node import TargetNode, Node, ContainerNode, RepositoryNode


class BuildCleanerCli:
  def __init__(self, cli_args: List[str]):
    self._root_target: str
    self._prefix_path: str = os.getcwd()
    self._bazel_config: str
    self._output_build_path: str
    self._output_package_graph_path: str
    self._build_file_name: str = "BUILD"
    self._debug_build: bool = False
    self._debug_nodes_by_kind: bool = False
    self._debug_tree: bool = False

    for cli_arg in cli_args:
      arg_name, arg_val = cli_arg.split("=", maxsplit=2)
      if arg_name == "--root_target":
        self._root_target = arg_val
      elif arg_name == "--prefix_path":
        self._prefix_path = arg_val
      elif arg_name == "--bazel_config":
        self._bazel_config = arg_val
      elif arg_name == "--output_build_path":
        self._output_build_path = arg_val
      elif arg_name == "--output_package_graph_path":
        self._output_package_graph_path = arg_val
      elif arg_name == "--build_file_name":
        self._build_file_name = arg_val
      elif arg_name == "--debug_build":
        self._debug_build = bool(arg_val)
      elif arg_name == "--debug_nodes_by_kind":
        self._debug_nodes_by_kind = bool(arg_val)
      elif arg_name == "--debug_tree":
        self._debug_tree = bool(arg_val)

  def main(self) -> None:
    start: float = time.time()

    bazel_runner: BazelRunner = BazelRunner()
    bazel_query_parser: BazelBuildTargetsParser = BazelBuildTargetsParser(
        self._prefix_path)
    targets_collector: TargetsCollector = TargetsCollector(bazel_runner,
                                                           bazel_query_parser)

    targets: CollectedTargets = targets_collector.collect_dependencies(
        self._root_target, self._bazel_config)
    print(f"Targets: {len(targets.all_targets)}\n"
          f"Nodes: {len(targets.all_nodes)}\n"
          f"Iterations: {targets.iterations}\n"
          f"Incremental Lengths: {targets.incremental_lengths}")

    # Build targets tree and apply necessary transformations
    tree_builder: NodesGraphBuilder = NodesGraphBuilder()
    tree_nodes: Dict[str, ContainerNode] = tree_builder.build_package_tree(
        targets.all_nodes.values())

    targets_transformer: PackageTargetsTransformer = PackageTargetsTransformer()
    tf_root: RepositoryNode = cast(RepositoryNode, tree_nodes["//"])
    targets_transformer.merge_cc_header_only_library(tf_root)
    targets_transformer.fix_generate_cc_kind(tf_root)
    targets_transformer.populate_export_files(tf_root)

    tf_repo: RepositoryNode = cast(RepositoryNode, tree_nodes["//"])
    if self._output_build_path:
      self._generate_build_files(tf_repo, self._output_build_path,
                                 self._build_file_name)

    if self._output_package_graph_path:
      self._generate_package_visualization(targets.all_nodes[self._root_target],
                                           self._output_package_graph_path)

    if self._debug_build:
      self._print_debug_info(tf_root, None, None)
    if self._debug_nodes_by_kind:
      self._print_debug_info(None, targets.nodes_by_kind, None)
    if self._debug_tree:
      self._print_debug_info(None, None, tree_nodes)

    end: float = time.time()
    print(f"Total Time: {end - start}")

  def _generate_build_files(self, repo: RepositoryNode,
      output_build_path: str, build_file_name: str) -> None:
    build_files_printer: BuildFilesPrinter = BuildFilesPrinter()
    build_files: Dict[str, str] = build_files_printer.print_build_files(repo)
    build_files_writer: BuildFilesWriter = BuildFilesWriter(output_build_path,
                                                            build_file_name)
    build_files_writer.write(build_files)

  def _generate_package_visualization(self, root: TargetNode,
      output_package_graph_path: str) -> None:
    graph_printer: GraphPrinter = GraphPrinter()
    graph: str = graph_printer.print_target_graph(root)
    writer: GraphvizWriter = GraphvizWriter(output_package_graph_path)
    writer.write_as_text(graph)
    writer.write(graph)
    # print(graph)

  def _print_debug_info(self, tf_root: Optional[RepositoryNode],
      nodes_by_kind: Optional[Dict[str, Dict[str, TargetNode]]],
      tree_nodes: Optional[Dict[str, ContainerNode]]) -> None:
    targets_printer: BuildFilesPrinter = BuildFilesPrinter()
    tree_printer: DebugTreePrinter = DebugTreePrinter()

    if tf_root:
      files_dict: Dict[str, str] = targets_printer.print_build_files(tf_root)
      for file_path, file_body in files_dict.items():
        print()
        print(file_body)
    if nodes_by_kind:
      print(tree_printer.print_nodes_by_kind(nodes_by_kind))
    if tree_nodes:
      print(tree_printer.print_nodes_tree(tree_nodes[""], return_string=True))


if __name__ == '__main__':
  cli = BuildCleanerCli(sys.argv[1:])
  cli.main()
