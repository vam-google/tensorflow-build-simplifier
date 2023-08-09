from typing import Dict, Optional
from buildcleaner.rule import Rule


class TfRules:
  _RULES: Dict[str, Rule] = {
      "proto_gen": Rule(kind="proto_gen",
                        label_list_args=["srcs", "deps", "outs"],
                        label_args=["protoc"],
                        string_list_args=["includes", "plugin_options"],
                        string_args=["plugin_language"],
                        bool_args=["gen_cc"],
                        import_statement="load(\"@com_google_protobuf//:protobuf.bzl\", \"proto_gen\")"),
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
      "tf_gen_options_header": Rule(kind="tf_gen_options_header",
                                    label_args=["template", "output_header"],
                                    str_str_map_args=["build_settings"],
                                    import_statement="load(\"//tensorflow:tensorflow.bzl\", \"tf_gen_options_header\")"),
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
      "config_setting": Rule(kind="config_setting",
                             str_str_map_args=["values", "flag_values",
                                               "define_values"]),
      "bool_flag": Rule(kind="bool_flag", bool_args=["build_setting_default"],
                        import_statement="load(\"@bazel_skylib//rules:common_settings.bzl\", \"bool_flag\")"),
      "bool_setting": Rule(kind="bool_setting",
                           bool_args=["build_setting_default"],
                           import_statement="load(\"@bazel_skylib//rules:common_settings.bzl\", \"bool_setting\")"),
  }

  _IGNORED_RULES: Dict[str, Rule] = {
      # Should be actually procesed
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
      # "bind": Rule(kind="bind", label_args=["actual"]),
  }

  @staticmethod
  def rules(extra_rules: Optional[Dict[str, Rule]] = None) -> Dict[str, Rule]:
    if extra_rules:
      merged_rules: Dict[str, Rule] = dict(TfRules._RULES)
      merged_rules.update(extra_rules)
      return merged_rules
    return TfRules._RULES

  @staticmethod
  def ignored_rules() -> Dict[str, Rule]:
    return TfRules._IGNORED_RULES
