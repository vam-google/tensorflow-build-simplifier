import json
import os
import subprocess
from typing import Dict
from typing import cast

from buildcleaner.config import Config


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
      print(f"    {full_file_path}")


class GraphvizWriter:
  def write_dot(self, graph: str, output_path: str) -> None:
    with open(output_path, "w") as graph_file:
      graph_file.write(graph)
      graph_file.flush()

  def write_svg(self, graph: str, output_path: str) -> None:
    proc: subprocess.Popen = subprocess.Popen(['twopi', "-Tsvg"],
                                              stdin=subprocess.PIPE,
                                              stdout=subprocess.PIPE)
    stdout, stderr = proc.communicate(input=bytes(graph, "utf-8"))

    with open(output_path, "w") as graph_file:
      graph_file.write(stdout.decode("utf-8"))
      graph_file.flush()


class ConfigFileReader:
  def read(self, config_path: str) -> Config:
    with open(config_path, "r") as f:
      config_json: Dict = json.load(f)

    config: Config = Config()
    self._populate_config(config, config_json)

    return config

  def _populate_config(self, config: object, config_json: Dict) -> None:
    for k, v in config_json.items():
      if isinstance(v, (str, int, bool)):
        setattr(config, k, v)
      elif isinstance(v, list):
        cast(list, getattr(config, k)).extend(cast(list, v))
      else:  # dict
        self._populate_config(getattr(config, k), v)
