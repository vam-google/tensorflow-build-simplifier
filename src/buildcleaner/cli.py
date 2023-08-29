import os
import time
from abc import abstractmethod
from typing import Dict
from typing import List
from typing import Optional
from typing import cast

from buildcleaner.build import Build
from buildcleaner.config import Config
from buildcleaner.config import DebugTargetGraph
from buildcleaner.fileio import BuildFilesWriter
from buildcleaner.fileio import ConfigFileReader
from buildcleaner.fileio import GraphvizWriter
from buildcleaner.graph import TargetDagBuilder
from buildcleaner.node import RepositoryNode
from buildcleaner.node import RootNode
from buildcleaner.node import TargetNode
from buildcleaner.printer import BuildFilesPrinter
from buildcleaner.printer import DebugTreePrinter
from buildcleaner.printer import GraphPrinter


class BuildCleanerCli:
  def __init__(self, cli_args: List[str]) -> None:
    self._config: Config

    for cli_arg in cli_args:
      arg_name: str
      arg_val: str
      arg_name, arg_val = cli_arg.split("=", maxsplit=2)
      if arg_name == "--config":
        self._config = ConfigFileReader().read(arg_val)

  def main(self) -> None:
    start: float = time.time()

    print(">>>>> Parsing Build Graph ...")
    build: Build = self.generate_build()

    if self._config.output_build_path:
      self._generate_build_files(build.repo_root(),
                                 self._config.output_build_path,
                                 self._config.build_file_name)
    if self._config.debug_build:
      self._print_debug_info(build.repo_root(), None)
    if self._config.debug_tree:
      self._print_debug_info(None, build.internal_root)
    if self._config.debug_target_graph.path:
      self._print_target_graphs(build.repo_root(),
                                self._config.debug_target_graph)

    end: float = time.time()
    print(f"Total Time: {end - start}")

  @abstractmethod
  def generate_build(self) -> Build:
    pass

  def _generate_build_files(self, repo: RepositoryNode,
      output_build_path: str, build_file_name: str) -> None:
    print(f"\n>>>>> Generating Build Files in '{output_build_path}' ...")
    build_files_printer: BuildFilesPrinter = BuildFilesPrinter()
    build_files: Dict[str, str] = build_files_printer.print_build_files(repo)
    build_files_writer: BuildFilesWriter = BuildFilesWriter(output_build_path,
                                                            build_file_name)
    build_files_writer.write(build_files)

  def _print_target_graphs(self, repo_root: RepositoryNode,
      debug_graph_config: DebugTargetGraph) -> None:
    for target_label in debug_graph_config.targets:
      root_target: TargetNode = cast(TargetNode, repo_root[target_label])
      self._print_target_graph(root_target, debug_graph_config.path)

  def _print_target_graph(self, root_target: TargetNode,
      graph_base_path: str) -> None:
    dag_builder: TargetDagBuilder = TargetDagBuilder(root_target)
    graph_path: str = os.path.join(graph_base_path, root_target.name)
    print(f">>>>> Generating Targets Graph for '{root_target}' ...")
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

    print(f"    DOT Inbound: {inbound_path_dot}")
    print(f"    SVG Inbound: {inbound_path_svg}")
    print(f"    DOT Outbound: {outbound_path_dot}")
    print(f"    SVG Outbound: {outbound_path_svg}\n")

  def _print_debug_info(self, repo_root: Optional[RepositoryNode],
      internal_root: Optional[RootNode]) -> None:
    targets_printer: BuildFilesPrinter = BuildFilesPrinter()
    tree_printer: DebugTreePrinter = DebugTreePrinter()

    if repo_root:
      print("vvvvv DEBUG: Build vvvvv")
      files_dict: Dict[str, str] = targets_printer.print_build_files(repo_root)
      for file_path, file_body in files_dict.items():
        print()
        print(file_body)
      print("^^^^^ DEBUG: Build ^^^^^\n")
    if internal_root:
      print("vvvvv DEBUG: Tree vvvvv")
      print(tree_printer.print_nodes_tree(internal_root, return_string=True,
                                          print_files=False))
      print("^^^^^ DEBUG: Tree ^^^^^\n")
