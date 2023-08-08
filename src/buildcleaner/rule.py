from typing import Sequence, Dict


class Rule:
  def __init__(self, kind: str,
      label_list_args: Sequence[str] = (),
      label_args: Sequence[str] = (),
      string_list_args: Sequence[str] = (),
      string_args: Sequence[str] = (),
      bool_args: Sequence[str] = (),
      str_str_map_args: Sequence[str] = (),
      import_statement: str = "") -> None:
    self.kind: str = kind
    self.label_list_args: Sequence[str] = label_list_args
    self.label_args: Sequence[str] = label_args
    self.string_list_args: Sequence[str] = string_list_args
    self.string_args: Sequence[str] = string_args
    self.bool_args: Sequence[str] = bool_args
    self.str_str_map_args: Sequence[str] = str_str_map_args
    self.import_statement: str = import_statement

  def __str__(self) -> str:
    return self.kind

  def __eq__(self, other) -> bool:
    if type(self) != type(other):
      return False
    return self.kind.__eq__(other.kind)

  def __ne__(self, other) -> bool:
    return not self.__eq__(other)

  def __hash__(self) -> int:
    return self.kind.__hash__()


class PackageFunctions:
  _functions: Dict[str, Rule] = {
      "exports_files": Rule(kind="exports_files",
                            label_list_args=["srcs"],
                            string_list_args=["visibility"])
  }

  @staticmethod
  def functions() -> Dict[str, Rule]:
    return PackageFunctions._functions
