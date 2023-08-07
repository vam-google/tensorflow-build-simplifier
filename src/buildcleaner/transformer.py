from typing import List, Dict, Set, Optional, cast
from buildcleaner.node import Node, Function, ContainerNode, TargetNode, \
  PackageNode, FileNode
from buildcleaner.rule import TensorflowRules, PackageFunctions


class RuleTransformer:
  def transform(self, node: Node) -> None:
    pass


class ChainTransformer(RuleTransformer):
  def __init__(self, transformers_chain: List[RuleTransformer]) -> None:
    self.transformers_chain: List[RuleTransformer] = list(transformers_chain)

  def transform(self, node: Node) -> None:
    for transformer in self.transformers_chain:
      transformer.transform(node)


class CcHeaderOnlyLibraryTransformer(RuleTransformer):
  def __init__(self) -> None:
    self._cc_header_only_library = TensorflowRules.rules()[
      "cc_header_only_library"]
    self._transitive_hdrs = TensorflowRules.rules()["_transitive_hdrs"]
    self._transitive_parameters_library = TensorflowRules.rules()[
      "_transitive_parameters_library"]

  def transform(self, node: Node) -> None:
    self._merge_cc_header_only_library(cast(ContainerNode, node))

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
  def __init__(self):
    self._generate_cc = TensorflowRules.rules()["generate_cc"]
    self._private_generate_cc = TensorflowRules.rules()["_generate_cc"]

  def transform(self, node: Node) -> None:
    self._fix_generate_cc_kind(node)

  def _fix_generate_cc_kind(self, node: Node) -> None:
    if isinstance(node, ContainerNode):
      for child in cast(ContainerNode, node).children.values():
        self._fix_generate_cc_kind(child)
    else:
      if node.kind == self._private_generate_cc:
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


class ExportFilesTransformer(RuleTransformer):
  def transform(self, node: Node) -> None:
    self._populate_export_files(cast(ContainerNode, node))

  def _populate_export_files(self, root: ContainerNode):
    file_to_packages: Dict[str, Set[PackageNode]] = {}
    self._collect_files_referenced_from_other_pkgs(root, file_to_packages)
    self._populate_export_files_property(root, file_to_packages)
    pass

  def _populate_export_files_property(self, node: ContainerNode,
      file_to_packages: Dict[str, Set[PackageNode]]) -> None:

    if isinstance(node, PackageNode):
      pkg_node: PackageNode = cast(PackageNode, node)
      exports_files_prop: Function = Function(
          PackageFunctions.functions()["exports_files"])
      # Export all exported files with public visibility for now
      # refaine it later.
      for source_file in pkg_node.get_targets(kind=FileNode.source_file_kind):
        if str(source_file) in file_to_packages:
          exports_files_prop.label_list_args.setdefault("srcs", []).append(
              source_file)
      if exports_files_prop.label_list_args:
        exports_files_prop.string_list_args.setdefault("visibility", []).append(
            "//visibility:public")
        pkg_node.functions.append(exports_files_prop)

    for child in node.get_containers():
      self._populate_export_files_property(child, file_to_packages)

  def _collect_files_referenced_from_other_pkgs(self, cont_node: ContainerNode,
      file_to_packages: Dict[str, Set[PackageNode]]) -> None:
    for child in cont_node.children.values():
      if isinstance(child, ContainerNode):
        self._collect_files_referenced_from_other_pkgs(child, file_to_packages)
      elif type(child) == TargetNode and isinstance(cont_node, PackageNode):
        target_child = cast(TargetNode, child)
        for file_dep in target_child.get_targets(FileNode.source_file_kind):
          file_dep_parent_label: str = file_dep.get_parent_label()
          if file_dep_parent_label != str(cont_node):
            file_to_packages.setdefault(str(file_dep), set()).add(
                cast(PackageNode, cont_node))
