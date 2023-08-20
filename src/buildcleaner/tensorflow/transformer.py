from queue import Queue
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from typing import Set
from typing import Tuple
from typing import cast

from buildcleaner.node import ContainerNode
from buildcleaner.node import FileNode
from buildcleaner.node import Node
from buildcleaner.node import PackageNode
from buildcleaner.node import TargetNode
from buildcleaner.rule import BuiltInRules
from buildcleaner.rule import Rule
from buildcleaner.tensorflow.rule import TfRules
from buildcleaner.transformer import RuleTransformer


class CcHeaderOnlyLibraryTransformer(RuleTransformer):
  def __init__(self) -> None:
    self._cc_header_only_library: Rule = TfRules.rules()[
      "cc_header_only_library"]
    self._transitive_hdrs: Rule = TfRules.rules()["_transitive_hdrs"]
    self._transitive_parameters_library: Rule = TfRules.rules()[
      "_transitive_parameters_library"]

  def transform(self, node: Node) -> List[TargetNode]:
    self._merge_cc_header_only_library(cast(ContainerNode, node))
    return []

  def _merge_cc_header_only_library(self, node: ContainerNode) -> None:
    for child in node.get_containers():
      self._merge_cc_header_only_library(child)

    transitive_hdrs: List[TargetNode] = list(
        node.get_targets(self._transitive_hdrs))
    if not transitive_hdrs:
      return
    transitive_parameters: List[TargetNode] = list(node.get_targets(
        self._transitive_parameters_library))
    cc_library: List[TargetNode] = []
    for child_node in transitive_hdrs:
      cc_library_name = child_node.name[:-len("_gather")]
      cc_library_child = node.get_target(cc_library_name)
      if cc_library_child:
        cc_library.append(cc_library_child)

    for i in range(len(transitive_hdrs)):
      hdrs_node = transitive_hdrs[i]
      parameters_node = transitive_parameters[i]
      cc_node = cc_library[i]

      new_node = TargetNode(self._cc_header_only_library,
                            cc_node.name, node.label, cc_node)
      for j in range(len(new_node.label_list_args["deps"])):
        if str(new_node.label_list_args["deps"][j]) == str(parameters_node):
          new_node.label_list_args["deps"].pop(j)
          break

      new_node.label_list_args["extra_deps"] = new_node.label_list_args["deps"]
      new_node.label_list_args["deps"] = list(hdrs_node.label_list_args["deps"])
      del new_node.label_list_args["hdrs"]
      del node.children[str(hdrs_node)]
      del node.children[str(parameters_node)]
      del node.children[str(cc_node)]
      node.children[str(new_node)] = new_node


class GenerateCcTransformer(RuleTransformer):
  def __init__(self) -> None:
    self._generate_cc: Rule = TfRules.rules()["generate_cc"]
    self._private_generate_cc: Rule = TfRules.rules()["_generate_cc"]

  def transform(self, node: Node) -> List[TargetNode]:
    self._fix_generate_cc_kind(node)
    return []

  def _fix_generate_cc_kind(self, node: Node) -> None:
    if isinstance(node, ContainerNode):
      for child in cast(ContainerNode, node).children.values():
        self._fix_generate_cc_kind(child)
    elif node.kind == self._private_generate_cc:
      target_node = cast(TargetNode, node)
      target_node.kind = self._generate_cc
      well_known_protos_arg: Optional[
        TargetNode] = target_node.label_args.get(
          "well_known_protos")
      if well_known_protos_arg:
        target_node.bool_args["well_known_protos"] = True
        del target_node.bool_args["well_known_protos"]
      else:
        target_node.bool_args["well_known_protos"] = False


class PackageCcLibraryMergeTransformer(RuleTransformer):
  def __init__(self, root_target: TargetNode) -> None:
    self._root_target: TargetNode = root_target
    self._cc_library: Rule = BuiltInRules.rules()["cc_library"]
    self._generated: Rule = BuiltInRules.rules()["generated"]
    self._filegroup: Rule = BuiltInRules.rules()["filegroup"]
    self._alias: Rule = BuiltInRules.rules()["alias"]
    self._cc_shared_library: Rule = BuiltInRules.rules()["cc_shared_library"]

    self._generate_cc: Rule = TfRules.rules()["generate_cc"]


class CcLibraryMerger(RuleTransformer):
  def __init__(self, root_target: TargetNode) -> None:
    self._root_target: TargetNode = root_target
    self._cc_library: Rule = BuiltInRules.rules()["cc_library"]
    self._generated: Rule = BuiltInRules.rules()["generated"]
    self._filegroup: Rule = BuiltInRules.rules()["filegroup"]
    self._alias: Rule = BuiltInRules.rules()["alias"]
    self._cc_shared_library: Rule = BuiltInRules.rules()["cc_shared_library"]

    self._generate_cc: Rule = TfRules.rules()["generate_cc"]

  def transform(self, node: Node) -> List[TargetNode]:
    root_node_package: PackageNode = cast(PackageNode, node)

    next_targets: 'Queue[TargetNode]' = Queue()
    roots_arg_name: str = "roots" if self._root_target.kind == self._cc_shared_library else "deps"
    roots: List[TargetNode] = self._root_target.label_list_args[roots_arg_name]

    for root in roots:
      next_targets.put_nowait(root)

    agg_label_list_args: Dict[str, Set[TargetNode]]
    agg_string_list_args: Dict[str, Set[str]]
    agg_label_list_args, agg_string_list_args = self._bfs_cpp_info_deps(
        next_targets)

    agg_cc_library: TargetNode = TargetNode(self._cc_library,
                                            f"aggregated_{self._root_target.name}",
                                            self._root_target.get_parent_label())

    for arg_name, arg_label_val in agg_label_list_args.items():
      agg_cc_library.label_list_args.setdefault(arg_name, []).extend(
          arg_label_val)

    if "copts" in agg_string_list_args:
      copts: Set[str] = agg_string_list_args["copts"]
      if "-fexceptions" in copts and "-fno-exceptions" in copts:
        copts.remove("-fno-exceptions")

    for arg_name, arg_str_val in agg_string_list_args.items():
      agg_cc_library.string_list_args.setdefault(arg_name, []).extend(
          arg_str_val)

    root_node_package.children[str(agg_cc_library)] = agg_cc_library
    return [agg_cc_library]

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


class DebugOptsCollector(RuleTransformer):
  def __init__(self) -> None:
    self._cc_library: Rule = BuiltInRules.rules()["cc_library"]
    self._str_list_args: Dict[str, Set[str]] = {"copts": set(),
                                                "linkopts": set()}

  def transform(self, node: Node) -> List[TargetNode]:
    container_node: ContainerNode = cast(ContainerNode, node)
    # str_list_args: Dict[str, Set[str]] = {"copts": set(), "linkopts": set()}
    self._collect_args(container_node, self._str_list_args)
    return []

  def _collect_args(self, node: ContainerNode,
      str_list_args: Dict[str, Set[str]]) -> None:
    for child in node.children.values():
      if isinstance(child, ContainerNode):
        self._collect_args(cast(ContainerNode, child), str_list_args)
      elif child.kind == self._cc_library:
        target_node: TargetNode = cast(TargetNode, child)
        for str_arg_name, str_arg_vals in str_list_args.items():
          arg_val: Optional[List[str]] = target_node.string_list_args.get(
              str_arg_name)
          if arg_val is not None:
            str_arg_vals.update(arg_val)

# class PackageCcLibraryMerger(RuleTransformer):
#   def __init__(self) -> None:
#     self._cc_library: Rule = BuiltInRules.rules()["cc_library"]
#
#   def transform(self, node: Node) -> List[TargetNode]:
#     pkg_node: PackageNode = cast(PackageNode, node)
#
#     agg_cc_deps: Dict[str, Set[TargetNode]] = {}
#
#     for target in pkg_node.get_targets():
#       if target.kind != self._cc_library:
#         continue
#
#       strip_include_prefix: Optional[str] = target.string_args.get(
#           "strip_include_prefix")
#       if strip_include_prefix:
#         agg_cc_deps.setdefault(strip_include_prefix, set()).add(target)
#
#     tmp_cc_libraries: List[TargetNode] = []
#     for strip_include_prefix, agg_deps in agg_cc_deps.items():
#       suffix: str = strip_include_prefix.replace("/", "_").replace(".", "dot")
#       agg_cc_library = TargetNode(self._cc_library,
#                                   f"aggregated_{pkg_node.name}__{suffix}",
#                                   str(pkg_node))
#       agg_cc_library.label_list_args["deps"] = list(agg_deps)
#       agg_cc_library.string_args["strip_include_prefix"] = strip_include_prefix
#       tmp_cc_libraries.append(agg_cc_library)
#
#     # for agg_cc_lib in agg_cc_libraries:
#     #   pkg_node.children[str(agg_cc_lib)] = agg_cc_lib
#
#     agg_cc_libraries: List[TargetNode] = []
#     for tmp_cc_lib in tmp_cc_libraries:
#       agg_cc_lib: TargetNode = CcLibraryMerger(tmp_cc_lib).transform(pkg_node)[
#         0]
#       agg_cc_lib.string_args.update(tmp_cc_lib.string_args)
#       agg_cc_libraries.append(agg_cc_lib)
#
#     # for agg_cc_lib in agg_cc_libraries:
#     #   pkg_node.children[str(agg_cc_lib)] = agg_cc_lib
#
#     return agg_cc_libraries
