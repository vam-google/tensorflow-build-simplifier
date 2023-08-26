from abc import abstractmethod
from typing import Dict
from typing import List
from typing import Set
from typing import cast

from buildcleaner.node import ContainerNode
from buildcleaner.node import FileNode
from buildcleaner.node import Function
from buildcleaner.node import PackageNode
from buildcleaner.node import RepositoryNode
from buildcleaner.node import TargetNode
from buildcleaner.rule import PackageFunctions


class RuleTransformer:
  @abstractmethod
  def transform(self, repo_root: RepositoryNode) -> List[TargetNode]:
    pass


class ExportFilesTransformer(RuleTransformer):
  def transform(self, repo_root: RepositoryNode) -> List[TargetNode]:
    self._populate_export_files(repo_root)
    return []

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
      for source_file in pkg_node.get_targets(kind=FileNode.SOURCE_FILE_KIND):
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
        for file_dep in target_child.get_targets(FileNode.SOURCE_FILE_KIND):
          file_dep_parent_label: str = file_dep.get_parent_label()
          if file_dep_parent_label != str(cont_node):
            file_to_packages.setdefault(str(file_dep), set()).add(
                cast(PackageNode, cont_node))
