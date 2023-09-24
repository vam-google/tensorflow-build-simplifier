from typing import Dict
from typing import Optional
from typing import Sequence


class Rule:
  def __init__(self, kind: str,
      label_list_args: Sequence[str] = (),
      label_args: Sequence[str] = (),
      string_list_args: Sequence[str] = (),
      string_args: Sequence[str] = (),
      bool_args: Sequence[str] = (),
      int_args: Sequence[str] = (),
      str_str_map_args: Sequence[str] = (),
      out_label_list_args: Sequence[str] = (),
      out_label_args: Sequence[str] = (),
      import_statement: str = "",
      outputs: Sequence[str] = (),
      macro: bool = False,
      visibility: bool = True) -> None:
    self.kind: str = kind
    self.label_list_args: Sequence[str] = label_list_args
    self.label_args: Sequence[str] = label_args
    self.string_list_args: Sequence[str] = string_list_args
    self.string_args: Sequence[str] = string_args
    self.bool_args: Sequence[str] = bool_args
    self.int_args: Sequence[str] = int_args
    self.str_str_map_args: Sequence[str] = str_str_map_args
    self.out_label_list_args: Sequence[str] = out_label_list_args
    self.out_label_args: Sequence[str] = out_label_args
    self.import_statement: str = import_statement
    # For simplicity, we support only {name} substitution in outputs.
    # Support other parameters subsitutions if ever needed
    self.outputs: Sequence[str] = outputs
    self.macro: bool = macro

    # Visibility should not be here, its a hack, remove once visiblity is
    # handled properly
    self.visibility = visibility

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
                                          "textual_hdrs",
                                          "target_compatible_with"],
                         string_list_args=["copts", "linkopts", "features",
                                           "tags", "includes", "defines"],
                         string_args=["strip_include_prefix"],
                         bool_args=["linkstatic", "alwayslink", "testonly"]),
      "py_test": Rule(kind="py_test", label_list_args=["srcs", "deps", "data"],
                      label_args=["main"],
                      string_list_args=["tags", "args"],
                      string_args=["srcs_version", "python_version", "size"],
                      bool_args=[],
                      int_args=["shard_count"],
                      str_str_map_args=["exec_properties"]),
      "cc_test": Rule(kind="cc_test", label_list_args=["srcs", "deps", "data"],
                      string_list_args=["tags", "copts", "linkopts"],
                      string_args=["size"],
                      bool_args=["linkstatic"],
                      int_args=["shard_count"],
                      str_str_map_args=["exec_properties"]),
      "py_library": Rule(kind="py_library",
                         label_list_args=["srcs", "deps", "data"],
                         label_args=["main"], string_list_args=["imports"],
                         string_args=["srcs_version"], bool_args=["testonly"]),
      "filegroup": Rule(kind="filegroup", label_list_args=["srcs", "data"],
                        string_args=["output_group"], bool_args=["testonly"]),
      "cc_binary": Rule(kind="cc_binary",
                        label_list_args=["srcs", "deps", "data"],
                        string_list_args=["copts", "linkopts", "tags",
                                          "features"],
                        bool_args=["testonly", "linkshared"],
                        str_str_map_args=["exec_properties"]),
      "test_suite": Rule(kind="test_suite", label_list_args=["tests"],
                         string_list_args=["tags"]),
      "genrule": Rule(kind="genrule", label_list_args=["srcs", "tools",
                                                       "target_compatible_with",
                                                       "restricted_to",
                                                       "toolchains"],
                      string_list_args=["tags"], string_args=["cmd"],
                      bool_args=["testonly"], out_label_list_args=["outs"]),
      "generated": Rule(kind="generated"),
      "alias": Rule(kind="alias", label_args=["actual"]),
      "config_setting": Rule(kind="config_setting",
                             str_str_map_args=["values", "flag_values",
                                               "define_values"]),
      "proto_library": Rule(kind="proto_library",
                            label_list_args=["srcs", "deps", "exports"],
                            string_list_args=["tags"], bool_args=["testonly"]),
      "py_binary": Rule(kind="py_binary",
                        label_list_args=["srcs", "deps", "data"],
                        label_args=["main"],
                        string_args=["srcs_version", "python_version"],
                        bool_args=["testonly"]),
      "sh_test": Rule(kind="sh_test", label_list_args=["srcs", "deps", "data"],
                      string_list_args=["args", "tags"], string_args=["size"],
                      int_args=["shard_count"], ),

      #
      # Marginaly importan (not needed?) rules, occur a few times among in 20k+
      # total targets.
      #
      "bind": Rule(kind="bind", label_args=["actual"]),
      "cc_import": Rule(kind="cc_import",
                        label_args=["shared_library", "interface_library"],
                        bool_args=["system_provided"]),
      "cc_shared_library": Rule(kind="cc_shared_library",
                                label_list_args=["roots", "deps",
                                                 "additional_linker_inputs",
                                                 "dynamic_deps"],
                                string_list_args=["exports_filter",
                                                  "user_link_flags"],
                                string_args=["shared_lib_name"]),
      "pkg_tar_impl": Rule(kind="pkg_tar_impl",
                           label_list_args=["srcs", "deps"],
                           label_args=["package_dir_file"],
                           string_list_args=["tags"],
                           string_args=["extension", "package_dir",
                                        "strip_prefix", "extension"],
                           out_label_args=["out"],
                           bool_args=["private_stamp_detect"],
                           str_str_map_args=["symlinks"]),
      "java_test": Rule(kind="java_test", label_list_args=["deps", "srcs"],
                        string_list_args=["javacopts"],
                        string_args=["size", "test_class"]),
      "bzl_library": Rule(kind="bzl_library", label_list_args=["srcs", "deps"],
                          import_statement='load("@bazel_skylib//:bzl_library.bzl", "bzl_library")'),
      "sh_binary": Rule(kind="sh_binary", label_list_args=["data", "srcs"]),
      "java_library": Rule(kind="java_library",
                           label_list_args=["srcs", "deps", "resources",
                                            "plugins"],
                           string_list_args=["javacopts"],
                           outputs=["lib{}.jar", "lib{}-src.jar"]),
      "sh_library": Rule(kind="sh_library", label_list_args=["srcs", "deps"]),
      "java_proto_library": Rule(kind="java_proto_library",
                                 label_list_args=["deps"]),
      "java_plugin": Rule(kind="java_plugin", label_list_args=["deps"],
                          string_list_args=["tags", "output_licenses"],
                          string_args=["processor_class"]),
      "java_binary": Rule(kind="java_binary", label_list_args=["srcs", "deps"],
                          string_list_args=["jvm_flags"],
                          string_args=["main_class"]),
      "expand_template": Rule(kind="expand_template", label_args=["template"],
                              str_str_map_args=["substitutions"],
                              out_label_args=["out"],
                              import_statement='load("@bazel_skylib//rules:expand_template.bzl", "expand_template")'),
      "cc_proto_library": Rule(kind="cc_proto_library",
                               label_list_args=["deps", "compatible_with"]),

      #
      # Macros
      #
      "build_test": Rule(kind="build_test", label_list_args=["targets"],
                         macro=True,
                         import_statement='load("@bazel_skylib//rules:build_test.bzl", "build_test")'),
      "pkg_tar": Rule(kind="pkg_tar",
                      label_list_args=["srcs", "deps"],
                      label_args=["package_dir_file"],
                      string_list_args=["tags"],
                      string_args=["extension", "package_dir",
                                   "strip_prefix", "extension"],
                      out_label_args=["out"],
                      str_str_map_args=["symlinks"],
                      macro=True,
                      import_statement='load("@rules_pkg//pkg:tar.bzl", "pkg_tar")'),

  }

  @staticmethod
  def rules(extra_rules: Optional[Dict[str, Rule]] = None) -> Dict[str, Rule]:
    if extra_rules:
      merged_rules: Dict[str, Rule] = dict(BuiltInRules._RULES)
      merged_rules.update(extra_rules)
      return merged_rules
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
