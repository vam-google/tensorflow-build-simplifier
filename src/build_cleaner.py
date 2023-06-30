import sys
import os
import time

from typing import Set, List, Dict, cast

from runner import BazelRunner, TargetsCollector
from transformer import NodesGraphBuilder, PackageTargetsTransformer
from parser import BazelBuildTargetsParser
from printer import BuildFilesPrinter, BuildTargetsPrinter, DebugTreePrinter
from fileio import BuildFilesWriter
from node import TargetNode, Node, ContainerNode, RepositoryNode


def main(root_target, prefix_path, bazel_config, output_path,
    build_file_name) -> None:
  start: float = time.time()

  # Collect targets info
  bazel_runner: BazelRunner = BazelRunner()
  bazel_query_parser: BazelBuildTargetsParser = BazelBuildTargetsParser(
    prefix_path)
  targets_collector: TargetsCollector = TargetsCollector(bazel_runner,
                                                         bazel_query_parser)
  # all_nodes: Dict[str, TargetNode]
  # nodes_by_kind: Dict[str, Dict[str, TargetNode]]
  # all_targets: Set[str]
  # iterations: int
  # incremental_lengths: List[int]

  all_nodes, nodes_by_kind, all_targets, iterations, incremental_lengths = targets_collector.clollect_targets(
      root_target, bazel_config)
  print(f"Targets: {len(all_targets)}\n"
        f"Nodes: {len(all_nodes)}\n"
        f"Iterations: {iterations}\n"
        f"Incremental Lengths: {incremental_lengths}")


  # Build targets tree and apply necessary transformations
  tree_builder: NodesGraphBuilder = NodesGraphBuilder()
  tree_nodes: Dict[str, Node] = tree_builder.build_package_tree(
    all_nodes.values())
  targets_transformer: PackageTargetsTransformer = PackageTargetsTransformer()
  targets_transformer.merge_cc_header_only_library(
    cast(ContainerNode, tree_nodes["//"]))
  targets_transformer.fix_generate_cc_kind(tree_nodes["//"])


  # Populate BUILD files
  build_files_printer: BuildFilesPrinter = BuildFilesPrinter()
  build_files: Dict[str, str] = build_files_printer.print_build_files(
    cast(RepositoryNode, tree_nodes["//"]))
  build_files_writer: BuildFilesWriter = BuildFilesWriter(output_path,
                                                          build_file_name)
  build_files_writer.write(build_files)


  # Debug info
  targets_printer: BuildTargetsPrinter = BuildTargetsPrinter()
  tree_printer: DebugTreePrinter = DebugTreePrinter()
  print(targets_printer.print_build_file(all_nodes.values()))
  print(tree_printer.print_nodes_by_kind(nodes_by_kind))
  print(tree_printer.print(tree_nodes[""], return_string=True))

  end: float = time.time()
  print(f"Total Time: {end - start}")


def parse_args():
  args = {}
  for arg in sys.argv[1:]:
    a = arg.split("=")
    args[a[0]] = a[1]

  if "--prefix_path" not in args:
    args["--prefix_path"] = os.getcwd()
  if "--build_file_name" not in args:
    args["--build_file_name"] = "BUILD"

  return args


if __name__ == '__main__':
  args = parse_args()
  main(args["--root_target"],
       args["--prefix_path"],
       args["--bazel_config"],
       args["--output_path"],
       args["--build_file_name"])
