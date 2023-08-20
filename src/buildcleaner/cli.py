import os
import time
from abc import abstractmethod
from typing import Dict
from typing import List
from typing import Optional

from buildcleaner.build import Build
from buildcleaner.fileio import BuildFilesWriter
from buildcleaner.fileio import GraphvizWriter
from buildcleaner.graph import DgPkgBuilder
from buildcleaner.node import ContainerNode
from buildcleaner.node import RepositoryNode
from buildcleaner.node import TargetNode
from buildcleaner.printer import BuildFilesPrinter
from buildcleaner.printer import DebugTreePrinter
from buildcleaner.printer import GraphPrinter


class BuildCleanerCli:
  def __init__(self, cli_args: List[str]) -> None:
    self._root_target: str
    self._prefix_path: str = os.getcwd()
    self._bazel_config: str
    self._output_build_path: str = ""
    self._debug_package_graph_path: str = ""
    self._debug_target_graph_path: str = ""
    self._build_file_name: str = "BUILD"
    self._debug_build: bool = False
    self._debug_nodes_by_kind: bool = False
    self._debug_tree: bool = False
    self._merged_targets: List[str] = []

    for cli_arg in cli_args:
      arg_name: str
      arg_val: str
      arg_name, arg_val = cli_arg.split("=", maxsplit=2)
      if arg_name == "--root_target":
        self._root_target = arg_val
      elif arg_name == "--prefix_path":
        self._prefix_path = arg_val
      elif arg_name == "--bazel_config":
        self._bazel_config = arg_val
      elif arg_name == "--output_build_path":
        self._output_build_path = arg_val
      elif arg_name == "--debug_target_graph_path":
        self._debug_target_graph_path = arg_val
      elif arg_name == "--debug_package_graph_path":
        self._debug_package_graph_path = arg_val
      elif arg_name == "--build_file_name":
        self._build_file_name = arg_val
      elif arg_name == "--debug_build":
        self._debug_build = bool(arg_val)
      elif arg_name == "--debug_nodes_by_kind":
        self._debug_nodes_by_kind = bool(arg_val)
      elif arg_name == "--debug_tree":
        self._debug_tree = bool(arg_val)
      elif arg_name == "--merged_targets":
        self._merged_targets = arg_val.split(",")

  def main(self) -> None:
    start: float = time.time()

    print("> Parsing Build Graph ...")
    build: Build = self.generate_build()

    dag_builder: DgPkgBuilder = DgPkgBuilder(build.input_target,
                                             build.package_nodes)

    if self._output_build_path:
      self._generate_build_files(build.repo_root, self._output_build_path,
                                 self._build_file_name)

    if self._debug_build:
      self._print_debug_info(build.repo_root, None, None)
    if self._debug_tree:
      self._print_debug_info(None, None, build.package_nodes)
    if self._debug_nodes_by_kind:
      self._print_debug_info(None, build.targets_by_kind, None)
    if self._debug_target_graph_path:
      self._print_target_graph(dag_builder, self._debug_target_graph_path)
    if self._debug_package_graph_path:
      self._print_package_graph(dag_builder, self._debug_package_graph_path)

    end: float = time.time()
    print(f"Total Time: {end - start}")

  @abstractmethod
  def generate_build(self) -> Build:
    pass

  def _generate_build_files(self, repo: RepositoryNode,
      output_build_path: str, build_file_name: str) -> None:
    print("> Generating Build Files ...")
    build_files_printer: BuildFilesPrinter = BuildFilesPrinter()
    build_files: Dict[str, str] = build_files_printer.print_build_files(repo)
    build_files_writer: BuildFilesWriter = BuildFilesWriter(output_build_path,
                                                            build_file_name)
    build_files_writer.write(build_files)

  def _print_target_graph(self, dag_builder: DgPkgBuilder,
      graph_path: str) -> None:
    print("> Generating Targets Graph ...")
    graph_printer: GraphPrinter = GraphPrinter(dag_builder)
    inbound_graph = graph_printer.print_target_dag(True)
    outbound_graph = graph_printer.print_target_dag(False)
    inbound_path_dot: str = f"{graph_path}.inbound.dot"
    inbound_path_svg: str = f"{graph_path}.inbound.svg"
    outbound_path_dot: str = f"{graph_path}.outbound.dot"
    outbound_path_svg: str = f"{graph_path}.outbound.svg"

    writer: GraphvizWriter = GraphvizWriter()
    writer.write_dot(inbound_graph, inbound_path_dot)
    writer.write_dot(outbound_graph, outbound_path_dot)
    writer.write_svg(inbound_graph, inbound_path_svg)
    writer.write_svg(outbound_graph, outbound_path_svg)

    print("vvvvv DEBUG: Target graph path vvvvv")
    print(f"DOT Inbound: {inbound_path_dot}")
    print(f"SVG Inbound: {inbound_path_svg}")
    print(f"DOT Outbound: {outbound_path_dot}")
    print(f"SVG Outbound: {outbound_path_svg}")
    print("^^^^^ DEBUG: Target graph path ^^^^^\n")

  def _print_package_graph(self, dg_builder: DgPkgBuilder,
      graph_path: str) -> None:
    print("> Generating Package Graph ...")
    graph_printer: GraphPrinter = GraphPrinter(dg_builder)
    inbound_graph: str = graph_printer.print_package_dg(True)
    outbound_graph: str = graph_printer.print_package_dg(False)

    inbound_path_dot: str = f"{graph_path}.inbound.dot"
    inbound_path_svg: str = f"{graph_path}.inbound.svg"
    outbound_path_dot: str = f"{graph_path}.outbound.dot"
    outbound_path_svg: str = f"{graph_path}.outbound.svg"

    writer: GraphvizWriter = GraphvizWriter()
    writer.write_dot(inbound_graph, inbound_path_dot)
    writer.write_dot(outbound_graph, outbound_path_dot)
    writer.write_svg(inbound_graph, inbound_path_svg)
    writer.write_svg(outbound_graph, outbound_path_svg)

    print("vvvvv DEBUG: Package graph path vvvvv")
    print(f"DOT Inbound: {inbound_path_dot}")
    print(f"SVG Inbound: {inbound_path_svg}")
    print(f"DOT Outbound: {outbound_path_dot}")
    print(f"SVG Outbound: {outbound_path_svg}")
    print("^^^^^ DEBUG: Package graph path ^^^^^\n")

  def _print_debug_info(self, repo_root: Optional[RepositoryNode],
      targets_by_kind: Optional[Dict[str, Dict[str, TargetNode]]],
      package_nodes: Optional[Dict[str, ContainerNode]]) -> None:
    targets_printer: BuildFilesPrinter = BuildFilesPrinter()
    tree_printer: DebugTreePrinter = DebugTreePrinter()

    if repo_root:
      print("vvvvv DEBUG: Build vvvvv")
      files_dict: Dict[str, str] = targets_printer.print_build_files(repo_root)
      for file_path, file_body in files_dict.items():
        print()
        print(file_body)
      print("^^^^^ DEBUG: Build ^^^^^\n")
    if targets_by_kind:
      print("vvvvv DEBUG: Nodes by kind vvvvv")
      print(tree_printer.print_nodes_by_kind(targets_by_kind))
      print("^^^^^ DEBUG: Nodes by kind ^^^^^\n")
    if package_nodes:
      print("vvvvv DEBUG: Tree vvvvv")
      print(tree_printer.print_nodes_tree(package_nodes[""], return_string=True,
                                          print_files=False))
      print("^^^^^ DEBUG: Tree ^^^^^\n")
