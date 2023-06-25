import sys
import os

import transformers
import parsers
import runners
import time
import printers
import fileio


def main(root_target, prefix_path, bazel_config, output_path, build_file_name):
  start = time.time()

  bazel_runner = runners.BazelRunner()
  bazel_query_parser = parsers.BazelBuildTargetsParser(prefix_path)
  targets_collector = runners.TargetsCollector(bazel_runner, bazel_query_parser)

  all_nodes, all_targets, iterations, incremental_lengths = targets_collector.clollect_targets(
      root_target, bazel_config)

  print(f"Targets: {len(all_targets)}\n"
        f"Nodes: {len(all_nodes)}\n"
        f"Iterations: {iterations}\n"
        f"Incremental Lengths: {incremental_lengths}")

  tree_builder = transformers.NodesGraphBuilder()
  # tree_builder.resolve_label_references(all_nodes)
  tree_nodes = tree_builder.build_package_tree(all_nodes.values())
  targets_merger = transformers.PackageTargetsTransformer()
  targets_merger.merge_cc_header_only_library(tree_nodes["//"])
  targets_merger.fix_generate_cc_kind(tree_nodes["//"])


  # tree_printer = printers.RepoTreePrinter()
  # print(tree_printer.print(tree_nodes[""], return_string=True))

  build_files_printer = printers.BuildFilesPrinter()
  build_files = build_files_printer.print_build_files(tree_nodes["//"])
  build_files_writer = fileio.BuildFilesWriter(output_path, build_file_name)
  build_files_writer.write(build_files)

  # nodes_by_kind = bazel_query_parser.parse_query_label_kind_output(
  #   bazel_runner.query_output(all_targets, output="label_kind"))
  # node_kind_printer = printers.BasicPrinter()
  # print(node_kind_printer.print_nodes_by_kind(nodes_by_kind))

  # printer = printers.BasicPrinter()
  # print(printer.print_build_file(all_nodes.values()))

  end = time.time()
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
