from typing import Dict

from buildcleaner.rule import Rule


class TfRules:
  _RULES: Dict[str, Rule] = {
      "gentbl_rule": Rule(kind="gentbl_rule",
                          label_list_args=["deps", "td_srcs"],
                          label_args=["tblgen", "td_file"],
                          string_list_args=["includes", "opts"],
                          out_label_args=["out"],
                          import_statement='load("@llvm-project//mlir:tblgen.bzl", "gentbl_rule")'),
      "proto_gen": Rule(kind="proto_gen",
                        label_list_args=["srcs", "deps"],
                        label_args=["protoc"],
                        string_list_args=["includes", "plugin_options"],
                        string_args=["plugin_language"],
                        bool_args=["gen_cc"],
                        out_label_list_args=["outs"],
                        import_statement='load("@com_google_protobuf//:protobuf.bzl", "proto_gen")'),
      "td_library": Rule(kind="td_library",
                         label_list_args=["srcs", "deps"],
                         string_list_args=["includes"],
                         import_statement='load("@llvm-project//mlir:tblgen.bzl", "td_library")'),
      "generate_op_reg_offsets": Rule(kind="generate_op_reg_offsets",
                                      label_list_args=["deps",
                                                       "tf_binary_additional_srcs"],
                                      bool_args=["testonly"],
                                      out_label_args=["out"]),
      "_generate_cc": Rule(kind="_generate_cc",
                           label_list_args=["srcs"],
                           label_args=["plugin"],
                           string_list_args=["flags"],
                           bool_args=["generate_mocks", "testonly"]),
      "tf_gen_options_header": Rule(kind="tf_gen_options_header",
                                    label_args=["template"],
                                    str_str_map_args=["build_settings"],
                                    out_label_args=["output_header"],
                                    import_statement='load("//tensorflow:tensorflow.bzl", "tf_gen_options_header")'),
      "_tfcompile_model_library": Rule(kind="_tfcompile_model_library",
                                       label_list_args=["srcs",
                                                        "dfsan_abilists"],
                                       label_args=["tfcompile_tool",
                                                   "tfcompile_graph",
                                                   "tfcompile_config"],
                                       string_list_args=["tags", "extra_flags"],
                                       string_args=["model_name", "cmd",
                                                    "entry_point", "cpp_class",
                                                    "target_triple",
                                                    "target_cpu", "flags",
                                                    "xla_flags"],
                                       bool_args=["testonly", "dfsan",
                                                  "is_linux",
                                                  "gen_compiler_log"],
                                       out_label_args=["header_out"]),
      "_transitive_hdrs": Rule(kind="_transitive_hdrs",
                               label_list_args=["deps"]),
      "_transitive_parameters_library": Rule(
          kind="_transitive_parameters_library",
          label_list_args=["original_deps"]),
      #
      # Marginaly importan (not needed?) rules, occur a few times among in 20k+
      # total targets.
      #
      "_empty_test": Rule(kind="_empty_test", label_list_args=["data"],
                          string_args=["size"], bool_args=["is_windows"]),
      "check_deps": Rule(kind="check_deps",
                         label_list_args=["deps", "disallowed_deps",
                                          "required_deps"]),
      "gentbl_test": Rule(kind="gentbl_test",
                          label_list_args=["deps", "td_srcs"],
                          label_args=["tblgen", "td_file"],
                          string_list_args=["opts", "includes"]),
      "_local_genrule_internal": Rule(kind="_local_genrule_internal",
                                      label_list_args=["srcs"],
                                      label_args=["exect_tool",
                                                  "_whitelist_function_transition"],
                                      string_args=["arguments"],
                                      out_label_args=["out"]),
      "api_gen_rule": Rule(kind="api_gen_rule", label_list_args=["srcs"],
                           label_args=["api_gen_binary_target"],
                           string_list_args=["flags"],
                           string_args=["loading_value"],
                           out_label_list_args=["outs"]),
      "_filegroup_as_file": Rule(kind="_filegroup_as_file", label_args=["dep"]),
      "closure_proto_library": Rule(kind="closure_proto_library",
                                    label_list_args=["deps"],
                                    import_statement='load("@io_bazel_rules_closure//closure:defs.bzl", "closure_proto_library")'),
      "pkg_tar_impl": Rule(kind="pkg_tar_impl",
                           label_list_args=["srcs", "deps"],
                           string_list_args=["tags"], string_args=["extension"],
                           out_label_args=["out"],
                           bool_args=["private_stamp_detect"]),
      "bool_flag": Rule(kind="bool_flag", bool_args=["build_setting_default"],
                        import_statement='load("@bazel_skylib//rules:common_settings.bzl", "bool_flag")'),
      "bool_setting": Rule(kind="bool_setting",
                           bool_args=["build_setting_default"],
                           import_statement='load("@bazel_skylib//rules:common_settings.bzl", "bool_setting")'),
      "_gen_flatbuffer_srcs": Rule(kind="_gen_flatbuffer_srcs",
                                   label_list_args=["srcs", "deps"],
                                   string_list_args=["outputs",
                                                     "include_paths"],
                                   string_args=["language_flag"],
                                   bool_args=["no_includes"]),

      "_concat_flatbuffer_py_srcs": Rule(kind="_concat_flatbuffer_py_srcs",
                                         label_list_args=["deps"],
                                         outputs=["{}.py"]),
      "_append_init_to_versionscript": Rule(
          kind="_append_init_to_versionscript", label_args=["template_file"],
          string_args=["module_name"], bool_args=["is_version_script"],
          outputs=["{}.lds"]),

      #
      # Macros
      #
      "cc_header_only_library": Rule(kind="cc_header_only_library",
                                     label_list_args=["extra_deps", "srcs",
                                                      "hdrs", "deps",
                                                      "textual_hdrs"],
                                     string_list_args=["copts", "features",
                                                       "tags"],
                                     bool_args=["linkstatic", "alwayslink"],
                                     import_statement='load("//tensorflow/tsl:tsl.bzl", "cc_header_only_library")'),
      "generate_cc": Rule(kind="generate_cc",
                          label_list_args=["srcs"],
                          label_args=["plugin"],
                          string_list_args=["flags"],
                          bool_args=["generate_mocks", "testonly"],
                          import_statement='load("@com_github_grpc_grpc//bazel:generate_cc.bzl", "generate_cc")'),

  }

  _IGNORED_RULES: Dict[str, Rule] = {
      # TODO: these are used but most likely not important rules, process them
      # eventually once more important problems are solved
      "string_flag": Rule(kind="string_flag"),

      # Really ingored
      "java_toolchain_alias": Rule(kind="java_toolchain_alias"),
      "cc_flags_supplier": Rule(kind="cc_flags_supplier"),
      "constraint_value": Rule(kind="constraint_value"),
      "_copy_file": Rule(kind="_copy_file"),
      "cc_toolchain_suite": Rule(kind="cc_toolchain_suite"),
      "enable_cuda_flag": Rule(kind="enable_cuda_flag"),
      "py_runtime_pair": Rule(kind="py_runtime_pair"),
      "closure_js_library": Rule(kind="closure_js_library"),
      "enum_targets_gen": Rule(kind="enum_targets_gen"),
      "_write_file": Rule(kind="_write_file"),
      "constraint_setting": Rule(kind="constraint_setting"),
      "cc_toolchain_config": Rule(kind="cc_toolchain_config"),
      "_license_kind": Rule(kind="_license_kind"),
      "java_plugins_flag_alias": Rule(kind="java_plugins_flag_alias"),
      "platform": Rule(kind="platform"),
      "internal_gen_well_known_protos_java": Rule(
          kind="internal_gen_well_known_protos_java"),
      "_license": Rule(kind="_license"),
      "compiler_flag": Rule(kind="compiler_flag"),
      "adapt_proto_library": Rule(kind="adapt_proto_library"),
      "py_runtime": Rule(kind="py_runtime"),
      "java_runtime_version_alias": Rule(kind="java_runtime_version_alias"),
      "java_toolchain": Rule(kind="java_toolchain"),
      "unittest_toolchain": Rule(kind="unittest_toolchain"),
      "cc_toolchain_alias": Rule(kind="cc_toolchain_alias"),
      "_bootclasspath": Rule(kind="_bootclasspath"),
      "java_runtime_alias": Rule(kind="java_runtime_alias"),
      "java_runtime": Rule(kind="java_runtime"),
      "toolchain_type": Rule(kind="toolchain_type"),
      "_python_version_flag": Rule(kind="_python_version_flag"),
      "java_import": Rule(kind="java_import"),
      "java_host_runtime_alias": Rule(kind="java_host_runtime_alias"),
      "cc_toolchain": Rule(kind="cc_toolchain"),
      "armeabi_cc_toolchain_config": Rule(kind="armeabi_cc_toolchain_config"),
      "proto_lang_toolchain": Rule(kind="proto_lang_toolchain"),
      "package": Rule(kind="package"),

  }

  @staticmethod
  def rules() -> Dict[str, Rule]:
    return TfRules._RULES

  @staticmethod
  def ignored_rules() -> Dict[str, Rule]:
    return TfRules._IGNORED_RULES
