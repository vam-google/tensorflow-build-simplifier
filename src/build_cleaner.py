import sys
import os
import time

from typing import Dict, Optional, cast

from runner import BazelRunner, TargetsCollector, CollectedTargets
from transformer import NodesGraphBuilder, PackageTargetsTransformer
from parser import BazelBuildTargetsParser
from printer import BuildFilesPrinter, DebugTreePrinter
from fileio import BuildFilesWriter
from node import TargetNode, Node, RepositoryNode


def main(root_target, prefix_path, bazel_config, output_path,
    build_file_name) -> None:
  start: float = time.time()

  bazel_runner: BazelRunner = BazelRunner()
  bazel_query_parser: BazelBuildTargetsParser = BazelBuildTargetsParser(
      prefix_path)
  targets_collector: TargetsCollector = TargetsCollector(bazel_runner,
                                                         bazel_query_parser)
  targets: CollectedTargets = targets_collector.clollect_targets(
      root_target, bazel_config)
  print(f"Targets: {len(targets.all_targets)}\n"
        f"Nodes: {len(targets.all_nodes)}\n"
        f"Iterations: {targets.iterations}\n"
        f"Incremental Lengths: {targets.incremental_lengths}")

  # Build targets tree and apply necessary transformations
  tree_builder: NodesGraphBuilder = NodesGraphBuilder()
  tree_nodes: Dict[str, Node] = tree_builder.build_package_tree(
      targets.all_nodes.values())

  targets_transformer: PackageTargetsTransformer = PackageTargetsTransformer()
  tf_root: RepositoryNode = cast(RepositoryNode, tree_nodes["//"])
  targets_transformer.merge_cc_header_only_library(tf_root)
  targets_transformer.fix_generate_cc_kind(tf_root)
  targets_transformer.populate_export_files(tf_root)

  populate_build_files(output_path, build_file_name, tree_nodes)
  #
  print_nodes_representations(tf_root, None, None)
  # print_nodes_representations(None, nodes_by_kind, None)
  # print_nodes_representations(None, None, tree_nodes)

  end: float = time.time()
  print(f"Total Time: {end - start}")


def populate_build_files(output_path: str, build_file_name: str,
    tree_nodes: Dict[str, Node]) -> None:
  # Populate BUILD files
  build_files_printer: BuildFilesPrinter = BuildFilesPrinter()
  build_files: Dict[str, str] = build_files_printer.print_build_files(
      cast(RepositoryNode, tree_nodes["//"]))
  build_files_writer: BuildFilesWriter = BuildFilesWriter(output_path,
                                                          build_file_name)
  build_files_writer.write(build_files)


def print_nodes_representations(tf_root: Optional[RepositoryNode],
    nodes_by_kind: Optional[Dict[str, Dict[str, TargetNode]]],
    tree_nodes: Optional[Dict[str, Node]]) -> None:
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
