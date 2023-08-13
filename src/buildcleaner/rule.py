from typing import Dict
from typing import Sequence


class Rule:
  def __init__(self, kind: str,
      label_list_args: Sequence[str] = (),
      label_args: Sequence[str] = (),
      string_list_args: Sequence[str] = (),
      string_args: Sequence[str] = (),
      bool_args: Sequence[str] = (),
      str_str_map_args: Sequence[str] = (),
      out_label_list_args: Sequence[str] = (),
      out_label_args: Sequence[str] = (),
      import_statement: str = "") -> None:
    self.kind: str = kind
    self.label_list_args: Sequence[str] = label_list_args
    self.label_args: Sequence[str] = label_args
    self.string_list_args: Sequence[str] = string_list_args
    self.string_args: Sequence[str] = string_args
    self.bool_args: Sequence[str] = bool_args
    self.str_str_map_args: Sequence[str] = str_str_map_args
    self.out_label_list_args: Sequence[str] = out_label_list_args
    self.out_label_args: Sequence[str] = out_label_args
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


class BuiltInRules:
  _RULES: Dict[str, Rule] = {
      "cc_library": Rule(kind="cc_library",
                         label_list_args=["srcs", "hdrs", "deps",
                                          "textual_hdrs"],
                         string_list_args=["copts", "linkopts", "features",
                                           "tags",
                                           "includes"],
                         string_args=["strip_include_prefix"],
                         bool_args=["linkstatic", "alwayslink"]),
      "filegroup": Rule(kind="filegroup", label_list_args=["srcs"]),
      "alias": Rule(kind="alias", label_args=["actual"]),
      "genrule": Rule(kind="genrule", label_list_args=["srcs", "tools"],
                      string_args=["cmd"], out_label_list_args=["outs"]),
      "cc_binary": Rule(kind="cc_binary",
                        label_list_args=["srcs", "deps"],
                        string_list_args=["copts", "linkopts"]),
      "bind": Rule(kind="bind", label_args=["actual"]),
      "py_binary": Rule(kind="py_binary", label_list_args=["srcs", "deps"]),
      "proto_library": Rule(kind="proto_library",
                            label_list_args=["srcs", "deps", "exports"],
                            string_list_args=["tags"],
                            bool_args=["testonly"]),
      "cc_import": Rule(kind="cc_import",
                        label_args=["shared_library", "interface_library"],
                        bool_args=["system_provided"]),
      "cc_shared_library": Rule(kind="cc_shared_library",
                                label_list_args=["roots",
                                                 "additional_linker_inputs",
                                                 "dynamic_deps"],
                                string_list_args=["exports_filter",
                                                  "user_link_flags"],
                                string_args=["shared_lib_name"]),
      "generated": Rule(kind="generated"),
      "config_setting": Rule(kind="config_setting",
                             str_str_map_args=["values", "flag_values",
                                               "define_values"]),
  }

  @staticmethod
  def rules() -> Dict[str, Rule]:
    return BuiltInRules._RULES


class PackageFunctions:
  _FUNCTIONS: Dict[str, Rule] = {
      "exports_files": Rule(kind="exports_files",
                            label_list_args=["srcs"],
                            string_list_args=["visibility"])
  }

  @staticmethod
  def functions() -> Dict[str, Rule]:
    return PackageFunctions._FUNCTIONS
