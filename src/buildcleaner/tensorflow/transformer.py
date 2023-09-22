from queue import Queue
from typing import Callable
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from typing import Set
from typing import Tuple
from typing import Type
from typing import cast

from buildcleaner.config import MergedTargetsConfig
from buildcleaner.graph import PackageTree
from buildcleaner.node import FileNode
from buildcleaner.node import PackageNode
from buildcleaner.node import RepositoryNode
from buildcleaner.node import TargetNode
from buildcleaner.rule import BuiltInRules
from buildcleaner.rule import Rule
from buildcleaner.tensorflow.rule import TfRules
from buildcleaner.transformer import RuleTransformer


class CcLibraryMerger(RuleTransformer):
  def __init__(self, root_label: str, new_target_prefix: str,
      insert_new_targets: bool = True) -> None:
    self._root_label: str = root_label
    self._cc_library: Rule = BuiltInRules.rules()["cc_library"]
    self._generated: Rule = BuiltInRules.rules()["generated"]
    self._filegroup: Rule = BuiltInRules.rules()["filegroup"]
    self._alias: Rule = BuiltInRules.rules()["alias"]
    self._generate_cc: Rule = TfRules.rules()["generate_cc"]

    self._new_target_prefix = new_target_prefix
    self._insert_new_targets: bool = insert_new_targets

  def transform(self, repo_root: RepositoryNode) -> List[TargetNode]:
    root_target: TargetNode = cast(TargetNode, repo_root[self._root_label])

    next_targets: 'Queue[TargetNode]' = Queue()

    roots: List[TargetNode] = self._get_root_deps(root_target)

    for root in roots:
      next_targets.put_nowait(root)

    agg_label_list_args: Dict[str, Set[TargetNode]]
    agg_string_list_args: Dict[str, Set[str]]
    agg_label_list_args, agg_string_list_args = self._bfs_cpp_info_deps(
        next_targets)

    agg_cc_library: TargetNode = TargetNode(self._cc_library,
                                            f"{self._new_target_prefix}{root_target.name}",
                                            root_target.get_parent_label())

    for arg_name, arg_label_val in agg_label_list_args.items():
      agg_cc_library.label_list_args.setdefault(arg_name, []).extend(
          arg_label_val)

    if "copts" in agg_string_list_args:
      copts: Set[str] = agg_string_list_args["copts"]
      if "-fexceptions" in copts and "-fno-exceptions" in copts:
        copts.remove("-fno-exceptions")
      if "-O3" in copts:
        copts.remove("-O3")
        copts.add("-O2")

    for arg_name, arg_str_val in agg_string_list_args.items():
      agg_cc_library.string_list_args.setdefault(arg_name, []).extend(
          arg_str_val)

    if self._insert_new_targets:
      repo_root[str(agg_cc_library)] = agg_cc_library
    return [agg_cc_library]

  def _get_root_deps(self, root_target: TargetNode):
    return root_target.label_list_args["deps"]

  def _bfs_cpp_info_deps(self,
      next_targets: 'Queue[TargetNode]') -> Tuple[
    Dict[str, Set[TargetNode]], Dict[str, Set[str]]]:

    agg_label_list_args: Dict[str, Set[TargetNode]] = {}
    agg_string_list_args: Dict[str, Set[str]] = {}
    for arg_name in ["hdrs", "srcs", "deps", "textual_hdrs"]:
      agg_label_list_args[arg_name] = set()
    for arg_name in ["copts", "linkopts", "features", "includes",
                     "strip_include_prefix"]:
      agg_string_list_args[arg_name] = set()

    visited: Set[TargetNode] = set()
    expanded_filegroups: Dict[TargetNode, Set[TargetNode]] = {}
    first_level_count: int = next_targets.qsize()

    while not next_targets.empty():
      target: TargetNode = next_targets.get()
      first_level_count -= 1
      if target.kind == self._alias:
        alias_actual: TargetNode = target.label_args["actual"]
        if alias_actual not in visited:
          visited.add(alias_actual)
          next_targets.put_nowait(alias_actual)
        continue

      if target.kind not in [self._cc_library]:
        continue

      for arg_name in agg_label_list_args:
        arg_label_vals: Optional[List[TargetNode]] = target.label_list_args.get(
            arg_name)
        if not arg_label_vals:
          continue

        for arg_label_item in arg_label_vals:
          src_items: Iterable[TargetNode] = self._expand_source_target(
              arg_label_item, expanded_filegroups)
          if not src_items:
            if arg_label_item not in visited:
              visited.add(arg_label_item)
              next_targets.put_nowait(arg_label_item)
            continue

          for src_item in src_items:
            actual_arg_name: str = arg_name
            if actual_arg_name == "textual_hdrs":
              if not src_item.name.endswith(".md"):
                actual_arg_name = "hdrs"
            if actual_arg_name == "srcs":
              if src_item in agg_label_list_args[
                "hdrs"] and src_item.kind != self._generate_cc:
                continue
            if actual_arg_name == "hdrs":
              if src_item in agg_label_list_args["srcs"]:
                agg_label_list_args["srcs"].remove(src_item)

            agg_label_list_args[actual_arg_name].add(src_item)

      for arg_name in agg_string_list_args:
        arg_str_val: Optional[List[str]] = target.string_list_args.get(arg_name)
        if not arg_str_val:
          continue
        agg_string_list_args.setdefault(arg_name, set()).update(arg_str_val)

    return agg_label_list_args, agg_string_list_args

  def _is_src_item(self, arg_label_item) -> bool:
    return isinstance(arg_label_item, FileNode) or arg_label_item.kind in [
        self._generated,
        self._generate_cc] or arg_label_item.is_external() or "strip_include_prefix" in arg_label_item.string_args

  def _expand_source_target(self, source_target: TargetNode,
      expanded_filegroups: Dict[TargetNode, Set[TargetNode]],
      accept_targets: bool = True) -> Set[TargetNode]:
    expanded_files: Set[TargetNode] = set()
    if self._is_src_item(source_target):
      expanded_files.add(source_target)
      return expanded_files
    if source_target.kind != self._filegroup:
      if accept_targets:
        return expanded_files
      raise ValueError(
          f"Wrong filegoup target kind: {source_target.kind}, name: {source_target}")

    if source_target in expanded_filegroups:
      return expanded_filegroups[source_target]

    srcs: Optional[List[TargetNode]] = source_target.label_list_args.get("srcs")
    if srcs:
      for src in source_target.label_list_args["srcs"]:
        expanded_files.update(
            self._expand_source_target(src, expanded_filegroups, False))

    expanded_filegroups[source_target] = expanded_files
    return expanded_files


class CcSharedLibraryMerger(CcLibraryMerger):
  def __init__(self, root_label: str, new_target_prefix: str) -> None:
    super().__init__(root_label, f"_{new_target_prefix}internal_", False)
    self._cc_shared_library: Rule = BuiltInRules.rules()["cc_shared_library"]
    self._actual_target_prefix = new_target_prefix

  def transform(self, repo_root: RepositoryNode) -> List[TargetNode]:
    internal_cc_library: TargetNode = super().transform(repo_root)[0]
    root_target: TargetNode = cast(TargetNode, repo_root[self._root_label])

    agg_cc_shared_library: TargetNode = root_target.duplicate(None,
                                                              f"{self._actual_target_prefix}{root_target.name}",
                                                              None)
    old_shared_lib_name: str = agg_cc_shared_library.string_args[
      "shared_lib_name"]
    agg_cc_shared_library.string_args[
      "shared_lib_name"] = f"{self._actual_target_prefix}{old_shared_lib_name}"

    agg_cc_shared_library.label_list_args[
      self._get_roots_arg_name(root_target)].clear()
    agg_cc_shared_library.label_list_args[
      self._get_roots_arg_name(root_target)].append(
        internal_cc_library)

    repo_root[str(internal_cc_library)] = internal_cc_library
    tree_builder: PackageTree = PackageTree()
    tree_builder.replace_targets(repo_root,
                                 {str(root_target): agg_cc_shared_library})

    # repo_root[str(agg_cc_shared_library)] = agg_cc_shared_library

    return [internal_cc_library, agg_cc_shared_library]

  def _get_root_deps(self, root_target: TargetNode) -> List[TargetNode]:
    return root_target.label_list_args[self._get_roots_arg_name(root_target)]

  def _get_roots_arg_name(self, root_target: TargetNode) -> str:
    return "roots" if "roots" in root_target.label_list_args else "deps"


class ChainedCcLibraryMerger(RuleTransformer):
  _MERGERS_BY_RULE_KIND: Dict[Rule, Type[CcLibraryMerger]] = {
      BuiltInRules.rules()["cc_shared_library"]: CcSharedLibraryMerger,
      BuiltInRules.rules()["cc_library"]: CcLibraryMerger,
  }

  def __init__(self, merged_targets: MergedTargetsConfig) -> None:
    self._transformers: List[CcLibraryMerger] = []
    self._cc_shared_library: Rule = BuiltInRules.rules()["cc_shared_library"]
    self.merged_targets: MergedTargetsConfig = merged_targets

  def transform(self, repo_root: RepositoryNode) -> List[TargetNode]:
    rv: List[TargetNode] = []
    for original_label in self.merged_targets.targets:
      oritinal_target: TargetNode = cast(TargetNode, repo_root[original_label])
      transformer: CcLibraryMerger = \
        ChainedCcLibraryMerger._MERGERS_BY_RULE_KIND[oritinal_target.kind](
            original_label, self.merged_targets.new_targets_prefix)
      rv.extend(transformer.transform(repo_root))

    return rv


class TrivialPrivateRuleToPublicMacroTransformer(RuleTransformer):
  def __init__(self) -> None:
    self._generating_macros: Dict[
      str, Callable[
        [PackageNode, Dict[Rule, List[TargetNode]]], List[TargetNode]]] = {}

    self._genrule: Rule = BuiltInRules.rules()["genrule"]
    self._filegroup: Rule = BuiltInRules.rules()["filegroup"]
    self._py_library: Rule = BuiltInRules.rules()["py_library"]
    self._cc_library: Rule = BuiltInRules.rules()["cc_library"]

    self._private_empty_test: Rule = TfRules.rules()["_empty_test"]
    self.build_test: Rule = BuiltInRules.rules()["build_test"]
    self._generating_macros[self.build_test.kind] = self._transform_build_test

    self._private_filegroup_as_file: Rule = TfRules.rules()[
      "_filegroup_as_file"]
    self._filegroup_as_file: Rule = TfRules.rules()["filegroup_as_file"]
    self._generating_macros[
      self._filegroup_as_file.kind] = self._transform_filegroup_as_file

    self._private_pkg_tar_impl: Rule = BuiltInRules.rules()["pkg_tar_impl"]
    self._pkg_tar: Rule = BuiltInRules.rules()["pkg_tar"]
    self._generating_macros[self._pkg_tar.kind] = self._transform_pkg_tar

    self._flatbuffer_py_library: Rule = TfRules.rules()["flatbuffer_py_library"]
    self._private_concat_flatbuffer_py_srcs: Rule = TfRules.rules()[
      "_concat_flatbuffer_py_srcs"]
    self._private_gen_flatbuffer_srcs: Rule = TfRules.rules()[
      "_gen_flatbuffer_srcs"]
    self._generating_macros[
      self._flatbuffer_py_library.kind] = self._transform_flatbuffer_py_library

    self._private_transitive_hdrs: Rule = TfRules.rules()["_transitive_hdrs"]
    self._private_transitive_parameters_library: Rule = TfRules.rules()[
      "_transitive_parameters_library"]
    self._cc_header_only_library: Rule = TfRules.rules()[
      "cc_header_only_library"]
    self._generating_macros[
      self._cc_header_only_library.kind] = self._transform_cc_header_only_library
    self._generating_macros[
      "tf_profiler_pybind_cc_library_wrapper"] = self._transform_cc_header_only_library
    self._generating_macros[
      "tf_pybind_cc_library_wrapper_opensource"] = self._transform_cc_header_only_library

    self._transitive_hdrs: Rule = TfRules.rules()["transitive_hdrs"]
    self._generating_macros[
      self._transitive_hdrs.kind] = self._transform_transitive_hdrs

    self._private_generate_cc: Rule = TfRules.rules()["_generate_cc"]
    self._generate_cc: Rule = TfRules.rules()["generate_cc"]
    # two possible generating functions for the same rule
    self._generating_macros[
      self._generate_cc.kind] = self._transform_generate_cc
    self._generating_macros["tf_proto_library"] = self._transform_generate_cc
    self._generating_macros["cc_grpc_library"] = self._transform_generate_cc

    self._private_local_genrule_internal = TfRules.rules()[
      "_local_genrule_internal"]
    self._tf_py_build_info_genrule = TfRules.rules()["tf_py_build_info_genrule"]
    self._generating_macros[
      self._tf_py_build_info_genrule.kind] = self._transform_tf_py_build_info_genrule

    self._tf_version_info_genrule = TfRules.rules()["tf_version_info_genrule"]
    self._generating_macros[
      self._tf_version_info_genrule.kind] = self._transform_tf_version_info_genrule

    self._private_tfcompile_model_library = TfRules.rules()[
      "_tfcompile_model_library"]
    self._tfcompile_model_library = TfRules.rules()["tfcompile_model_library"]
    self._generating_macros[
      "tf_library"] = self._transform_tfcompile_model_library

    self._private_append_init_to_versionscript = TfRules.rules()[
      "_append_init_to_versionscript"]
    self._append_init_to_versionscript = TfRules.rules()[
      "append_init_to_versionscript"]
    self._generating_macros[
      "pywrap_tensorflow_macro_opensource"] = self._transform_append_init_to_versionscript

  def transform(self, repo_root: RepositoryNode) -> List[TargetNode]:
    new_tagets: List[TargetNode] = []
    for child in repo_root.get_containers():
      self._dfs_packages(cast(PackageNode, child), new_tagets)

    new_tagets_dict: Dict[str, TargetNode] = {str(t): t for t in new_tagets}

    tree_builder: PackageTree = PackageTree()
    tree_builder.replace_targets(repo_root, new_tagets_dict)

    return new_tagets

  def _dfs_packages(self, pkg: PackageNode, new_tagets: List[TargetNode]):
    for child in pkg.get_containers():
      self._dfs_packages(cast(PackageNode, child), new_tagets)

    generated_targets: Dict[str, Dict[str, Dict[Rule, List[TargetNode]]]] = {}

    for target in pkg.get_targets():
      if target.generator_function and target.generator_function in self._generating_macros:
        generated_targets.setdefault(target.generator_function, {}).setdefault(
            target.generator_name, {}).setdefault(target.kind, []).append(
            target)

    for gen_function, gen_rules in generated_targets.items():
      for gen_name, merger_func_params in gen_rules.items():
        new_tagets.extend(
            self._generating_macros[gen_function](pkg, merger_func_params))

    # update graph references

  def _transform_build_test(self, package: PackageNode,
      targets: Dict[Rule, List[TargetNode]]) -> List[TargetNode]:
    targets_param: List[TargetNode] = []

    if self._private_empty_test not in targets:
      # this is another build_test macro (macro name collision):
      return []

    build_test: TargetNode = targets[self._private_empty_test][0].duplicate(
        self.build_test, None, None)
    build_test.generator_name = ""
    build_test.generator_function = ""
    del build_test.bool_args["is_windows"]
    del build_test.label_list_args["data"]

    for genrule_target in targets[self._genrule]:
      targets_param.extend(genrule_target.label_list_args["srcs"])
      for reused_arg in ["compatible_with", "restricted_to", "tags"]:
        if reused_arg in genrule_target.label_list_args:
          build_test.label_list_args[reused_arg] = \
            genrule_target.label_list_args[reused_arg]

    build_test.label_list_args["targets"] = targets_param

    for old_targets in targets.values():
      for old_target in old_targets:
        del package[str(old_target)]

    package[str(build_test)] = build_test

    return [build_test]

  def _transform_filegroup_as_file(self, package: PackageNode,
      targets: Dict[Rule, List[TargetNode]]) -> List[TargetNode]:

    _filegroup_as_file: TargetNode = targets[self._private_filegroup_as_file][0]
    filegroup: TargetNode = targets[self._filegroup][0]

    filegroup_as_file: TargetNode = _filegroup_as_file.duplicate(
        self._filegroup_as_file, None, None)

    del package[str(_filegroup_as_file)]
    del package[str(filegroup)]

    package[str(filegroup_as_file)] = filegroup_as_file

    return [filegroup_as_file]

  def _transform_pkg_tar(self, package: PackageNode,
      targets: Dict[Rule, List[TargetNode]]) -> List[TargetNode]:

    pkg_tar_impl: TargetNode = targets[self._private_pkg_tar_impl][0]

    pkg_tar: TargetNode = pkg_tar_impl.duplicate(self._pkg_tar, None, None)
    del pkg_tar.bool_args["private_stamp_detect"]
    del package[str(pkg_tar_impl)]

    package[str(pkg_tar)] = pkg_tar

    return [pkg_tar]

  def _transform_flatbuffer_py_library(self, package: PackageNode,
      targets: Dict[Rule, List[TargetNode]]) -> List[TargetNode]:

    _gen_flatbuffer_srcs: List[TargetNode] = targets[
      self._private_gen_flatbuffer_srcs]
    _concat_flatbuffer_py_srcs: TargetNode = \
      targets[self._private_concat_flatbuffer_py_srcs][0]

    py_library: TargetNode = targets[self._py_library][0]

    flatbuffer_py_library: TargetNode = TargetNode(self._flatbuffer_py_library,
                                                   py_library.name,
                                                   py_library.get_parent_label())

    flatbuffer_py_library.label_list_args["srcs"] = \
      _gen_flatbuffer_srcs[0].label_list_args["srcs"]
    deps: Optional[
      List[TargetNode]] = _gen_flatbuffer_srcs[0].label_list_args.get("deps")
    if deps:
      flatbuffer_py_library.label_list_args["deps"] = deps
    include_paths: Optional[
      List[str]] = _gen_flatbuffer_srcs[0].string_list_args.get("include_paths")
    if include_paths:
      flatbuffer_py_library.string_list_args["include_paths"] = include_paths

    del package[str(_gen_flatbuffer_srcs[0])]
    if len(_gen_flatbuffer_srcs) > 1:
      del package[str(_gen_flatbuffer_srcs[1])]
    del package[str(_concat_flatbuffer_py_srcs)]

    package[str(flatbuffer_py_library)] = flatbuffer_py_library

    return [flatbuffer_py_library]

  def _transform_cc_header_only_library(self, package: PackageNode,
      targets: Dict[Rule, List[TargetNode]]) -> List[TargetNode]:

    _transitive_hdrs: TargetNode = targets[self._private_transitive_hdrs][0]
    _transitive_parameters_library: TargetNode = \
      targets[self._private_transitive_parameters_library][0]
    cc_library: TargetNode = targets[self._cc_library][0]

    cc_header_only_library: TargetNode = cc_library.duplicate(
        self._cc_header_only_library, None, None)
    del cc_header_only_library.label_list_args["hdrs"]

    deps_arg: List[TargetNode] = cc_header_only_library.label_list_args["deps"]
    for j in range(len(deps_arg)):
      if str(deps_arg[j]) == str(_transitive_parameters_library):
        deps_arg.pop(j)
        break

    cc_header_only_library.label_list_args["extra_deps"] = \
      cc_header_only_library.label_list_args["deps"]
    cc_header_only_library.label_list_args["deps"] = list(
        _transitive_hdrs.label_list_args["deps"])

    del package[str(_transitive_hdrs)]
    del package[str(_transitive_parameters_library)]
    del package[str(cc_library)]

    package[str(cc_header_only_library)] = cc_header_only_library

    return [cc_header_only_library]

  def _transform_generate_cc(self, package: PackageNode,
      targets: Dict[Rule, List[TargetNode]]) -> List[TargetNode]:

    if self._private_generate_cc not in targets:
      # must be tf_proto_library macro, not all of them call _generate_cc
      return []

    _generate_cc: TargetNode = targets[self._private_generate_cc][0]
    generate_cc: TargetNode = _generate_cc.duplicate(self._generate_cc, None,
                                                     None)

    well_known_protos_arg: Optional[
      TargetNode] = generate_cc.label_args.get(
        "well_known_protos")
    if well_known_protos_arg:
      generate_cc.bool_args["well_known_protos"] = True
      del generate_cc.bool_args["well_known_protos"]
    else:
      generate_cc.bool_args["well_known_protos"] = False

    del package[str(_generate_cc)]
    package[str(generate_cc)] = generate_cc

    return [generate_cc]

  def _transform_transitive_hdrs(self, package: PackageNode,
      targets: Dict[Rule, List[TargetNode]]) -> List[TargetNode]:

    _transitive_hdrs: TargetNode = targets[self._private_transitive_hdrs][0]
    filegroup: TargetNode = targets[self._filegroup][0]

    transitive_hdrs: TargetNode = TargetNode(self._transitive_hdrs,
                                             filegroup.name,
                                             filegroup.get_parent_label())
    transitive_hdrs.label_list_args["deps"] = _transitive_hdrs.label_list_args[
      "deps"]

    del package[str(_transitive_hdrs)]
    del package[str(filegroup)]

    package[str(transitive_hdrs)] = transitive_hdrs

    return [transitive_hdrs]

  def _transform_tf_py_build_info_genrule(self, package: PackageNode,
      targets: Dict[Rule, List[TargetNode]]) -> List[TargetNode]:

    _local_genrule_internal: TargetNode = \
      targets[self._private_local_genrule_internal][0]
    tf_py_build_info_genrule: TargetNode = TargetNode(
        self._tf_py_build_info_genrule, _local_genrule_internal.name,
        _local_genrule_internal.get_parent_label())

    tf_py_build_info_genrule.out_label_args["out"] = \
      _local_genrule_internal.out_label_args["out"]

    del package[str(_local_genrule_internal)]
    package[str(tf_py_build_info_genrule)] = tf_py_build_info_genrule

    return [tf_py_build_info_genrule]

  def _transform_tf_version_info_genrule(self, package: PackageNode,
      targets: Dict[Rule, List[TargetNode]]) -> List[TargetNode]:

    _local_genrule_internal: TargetNode = \
      targets[self._private_local_genrule_internal][0]
    tf_version_info_genrule: TargetNode = TargetNode(
        self._tf_version_info_genrule, _local_genrule_internal.name,
        _local_genrule_internal.get_parent_label())

    tf_version_info_genrule.out_label_args["out"] = \
      _local_genrule_internal.out_label_args["out"]

    del package[str(_local_genrule_internal)]
    package[str(tf_version_info_genrule)] = tf_version_info_genrule

    return [tf_version_info_genrule]

  def _transform_tfcompile_model_library(self, package: PackageNode,
      targets: Dict[Rule, List[TargetNode]]) -> List[TargetNode]:
    # Ho is this possible?
    if self._private_tfcompile_model_library not in targets:
      return []

    new_targets: List[TargetNode] = []

    for _private_tfcompile_model_library in targets[
      self._private_tfcompile_model_library]:
      _tfcompile_model_library: TargetNode = _private_tfcompile_model_library.duplicate(
          self._tfcompile_model_library, None, None)

      del package[str(_private_tfcompile_model_library)]
      package[str(_tfcompile_model_library)] = _tfcompile_model_library
      new_targets.append(_tfcompile_model_library)

    return new_targets

  def _transform_append_init_to_versionscript(self, package: PackageNode,
      targets: Dict[Rule, List[TargetNode]]) -> List[TargetNode]:
    # Ho is this possible?
    if self._private_append_init_to_versionscript not in targets:
      return []

    new_targets: List[TargetNode] = []

    for _private_append_init_to_versionscript in targets[
      self._private_append_init_to_versionscript]:
      _append_init_to_versionscript: TargetNode = _private_append_init_to_versionscript.duplicate(
          self._append_init_to_versionscript, None, None)

      del package[str(_private_append_init_to_versionscript)]
      package[
        str(_append_init_to_versionscript)] = _append_init_to_versionscript
      new_targets.append(_append_init_to_versionscript)

    return new_targets
