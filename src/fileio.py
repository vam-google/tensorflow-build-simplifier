from typing import Dict

import os


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
