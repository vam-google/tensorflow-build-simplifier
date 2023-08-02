from typing import Dict

import os
import subprocess


class BuildFilesWriter:
  def __init__(self, root_dir_path: str, build_file_name: str) -> None:
    self._root_dir_path: str = root_dir_path
    self._build_file_name: str = build_file_name

  def write(self, build_files_dict: Dict[str, str]) -> None:
    for file_dir_path, file_body in build_files_dict.items():
      full_dir_path = os.path.join(self._root_dir_path, file_dir_path)
      if not os.path.exists(full_dir_path):
        os.makedirs(full_dir_path)
      full_file_path = os.path.join(full_dir_path, self._build_file_name)
      build_file = open(full_file_path, "w")
      build_file.write(file_body)
      build_file.flush()
      build_file.close()


class GraphvizWriter:
  def __init__(self, graph_output_path: str) -> None:
    self._graph_output_path: str = graph_output_path

  def write(self, graph: str) -> None:
    proc: subprocess.Popen = subprocess.Popen(['twopi', "-Tsvg"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    stdout, stderr = proc.communicate(input=bytes(graph, "utf-8"))

    with open(self._graph_output_path, "w") as graph_file:
      graph_file.write(stdout.decode("utf-8"))
      graph_file.flush()

  def write_as_text(self, graph: str) -> None:
    with open(f"{self._graph_output_path}.txt", "w") as graph_file:
      graph_file.write(graph)
      graph_file.flush()
