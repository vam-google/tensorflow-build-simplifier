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


class TensorflowRules:
  _rules: Dict[str, Rule] = {
      "cc_library": Rule(kind="cc_library",
                         label_list_args=["srcs", "hdrs", "deps",
                                          "textual_hdrs"],
                         string_list_args=["copts", "features", "tags"],
                         bool_args=["linkstatic", "alwayslink"]),
      "filegroup": Rule(kind="filegroup", label_list_args=["srcs"]),
      "alias": Rule(kind="alias", label_args=["actual"]),
      "proto_gen": Rule(kind="proto_gen",
                        label_list_args=["srcs", "deps", "outs"],
                        label_args=["protoc"],
                        string_list_args=["includes", "plugin_options"],
                        string_args=["plugin_language"],
                        bool_args=["gen_cc"],
                        import_statement="load(\"@com_google_protobuf//:protobuf.bzl\", \"proto_gen\")"),
      "genrule": Rule(kind="genrule", label_list_args=["srcs", "tools", "outs"],
                      string_args=["cmd"]),
      "cc_binary": Rule(kind="cc_binary",
                        label_list_args=["srcs", "deps"],
                        string_list_args=["copts", "linkopts"]),
      "bind": Rule(kind="bind", label_args=["actual"]),
      "gentbl_rule": Rule(kind="gentbl_rule",
                          label_list_args=["deps", "td_srcs"],
                          label_args=["tblgen", "td_file", "out"],
                          string_list_args=["includes", "opts"],
                          import_statement="load(\"@llvm-project//mlir:tblgen.bzl\", \"gentbl_rule\")"),
      "_generate_cc": Rule(kind="_generate_cc",
                           label_list_args=["srcs"],
                           label_args=["plugin"],
                           string_list_args=["flags"],
                           bool_args=["generate_mocks", "testonly"]),
      "generate_cc": Rule(kind="generate_cc",
                          label_list_args=["srcs"],
                          label_args=["plugin"],
                          string_list_args=["flags"],
                          bool_args=["generate_mocks", "testonly"],
                          import_statement="load(\"@com_github_grpc_grpc//bazel:generate_cc.bzl\", \"generate_cc\")"),
      "td_library": Rule(kind="td_library",
                         label_list_args=["srcs", "deps"],
                         string_list_args=["includes"],
                         import_statement="load(\"@llvm-project//mlir:tblgen.bzl\", \"td_library\")"),
      "py_binary": Rule(kind="py_binary", label_list_args=["srcs", "deps"]),
      "proto_library": Rule(kind="proto_library",
                            label_list_args=["srcs", "deps", "exports"],
                            string_list_args=["tags"],
                            bool_args=["testonly"]),
      "cc_import": Rule(kind="cc_import",
                        label_args=["shared_library", "interface_library"],
                        bool_args=["system_provided"]),
      "tf_gen_options_header": Rule(kind="tf_gen_options_header",
                                    label_args=["template", "output_header"],
                                    str_str_map_args=["build_settings"],
                                    import_statement="load(\"//tensorflow:tensorflow.bzl\", \"tf_gen_options_header\")"),
      "cc_shared_library": Rule(kind="cc_shared_library",
                                label_list_args=["roots",
                                                 "additional_linker_inputs",
                                                 "dynamic_deps"],
                                string_list_args=["exports_filter",
                                                  "user_link_flags"],
                                string_args=["shared_lib_name"]),

      "_transitive_hdrs": Rule(kind="_transitive_hdrs",
                               label_list_args=["deps"]),
      "_transitive_parameters_library": Rule(
          kind="_transitive_parameters_library",
          label_list_args=["original_deps"]),
      # Macros
      "cc_header_only_library": Rule(kind="cc_header_only_library",
                                     label_list_args=["extra_deps", "srcs",
                                                      "hdrs", "deps",
                                                      "textual_hdrs"],
                                     string_list_args=["copts", "features",
                                                       "tags"],
                                     bool_args=["linkstatic", "alwayslink"],
                                     import_statement="load(\"//tensorflow/tsl:tsl.bzl\", \"cc_header_only_library\")"),
      "generated": Rule(kind="generated"),
      "config_setting": Rule(kind="config_setting",
                             str_str_map_args=["values", "flag_values",
                                               "define_values"]),
      "bool_flag": Rule(kind="bool_flag", bool_args=["build_setting_default"],
                        import_statement="load(\"@bazel_skylib//rules:common_settings.bzl\", \"bool_flag\")"),
  }

  _ignored_rules: Dict[str, Rule] = {
      # Should be actually procesed
      "bool_flag": Rule(kind="bool_flag"),
      "bool_setting": Rule(kind="bool_setting"),
      "string_flag": Rule(kind="string_flag"),

      # Really ingored
      "py_library": Rule(kind="py_library"),
      "toolchain_type": Rule(kind="toolchain_type"),
      "adapt_proto_library": Rule(kind="adapt_proto_library"),
      "armeabi_cc_toolchain_config": Rule(kind="armeabi_cc_toolchain_config"),
      "cc_toolchain_alias": Rule(kind="cc_toolchain_alias"),
      "cc_toolchain_config": Rule(kind="cc_toolchain_config"),
      "cc_toolchain": Rule(kind="cc_toolchain"),
      "cc_toolchain_suite": Rule(kind="cc_toolchain_suite"),
      "compiler_flag": Rule(kind="compiler_flag"),
      "constraint_setting": Rule(kind="constraint_setting"),
      "constraint_value": Rule(kind="constraint_value"),
      "enable_cuda_flag": Rule(kind="enable_cuda_flag"),
      "enum_targets_gen": Rule(kind="enum_targets_gen"),
      "expand_template": Rule(kind="expand_template"),
      "package": Rule(kind="package"),
      "platform": Rule(kind="platform"),
      "py_runtime_pair": Rule(kind="py_runtime_pair"),
      "py_runtime": Rule(kind="py_runtime"),
      "_write_file": Rule(kind="_write_file"),
  }

  @staticmethod
  def rules() -> Dict[str, Rule]:
    return TensorflowRules._rules

  @staticmethod
  def ignored_rules() -> Dict[str, Rule]:
    return TensorflowRules._ignored_rules


class PackageFunctions:
  _functions: Dict[str, Rule] = {
      "exports_files": Rule(kind="exports_files",
                            label_list_args=["srcs"],
                            string_list_args=["visibility"])
  }

  @staticmethod
  def functions() -> Dict[str, Rule]:
    return PackageFunctions._functions
