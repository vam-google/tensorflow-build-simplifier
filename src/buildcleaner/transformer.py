from abc import abstractmethod
from typing import Dict
from typing import List
from typing import Optional
from typing import Set
from typing import cast

from buildcleaner.node import ContainerNode
from buildcleaner.node import FileNode
from buildcleaner.node import Function
from buildcleaner.node import Node
from buildcleaner.node import PackageNode
from buildcleaner.node import RepositoryNode
from buildcleaner.node import TargetNode
from buildcleaner.rule import BuiltInRules
from buildcleaner.rule import PackageFunctions
from buildcleaner.rule import Rule
from buildcleaner.tensorflow.graph import TfTargetDag


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


class UnreachableTargetsRemover(RuleTransformer):
  def __init__(self, artifact_targets: List[str]) -> None:
    self._artifact_targets = artifact_targets

  def transform(self, repo_root: RepositoryNode) -> List[TargetNode]:
    dag: TfTargetDag = TfTargetDag()

    artifacts: List[TargetNode] = []
    for t in self._artifact_targets:
      t_node: Optional[Node] = repo_root[t]
      if t_node:
        artifacts.append(cast(TargetNode, t_node))

    dag.prune_unreachable_targets(repo_root, artifacts)
    return []


class AliasReplacer(RuleTransformer):
  def __init__(self) -> None:
    self._alias: Rule = BuiltInRules.rules()["alias"]
    self._genrule: Rule = BuiltInRules.rules()["genrule"]

  def transform(self, repo_root: RepositoryNode) -> List[TargetNode]:
    self._prune_alias(repo_root)
    return []

  def _prune_alias(self, container: ContainerNode) -> None:
    for container_child in container.get_containers():
      self._prune_alias(container_child)

    for target_child in container.get_targets():
      for label_arg_list in target_child.label_list_args.values():
        for i in range(len(label_arg_list)):
          if label_arg_list[i].kind != self._alias:
            continue
          alias = label_arg_list[i]
          label_arg_list[i] = self._resolve_alias(label_arg_list[i])
          self._fix_genrule_cmd(alias, label_arg_list[i], target_child)

      labels_to_replace: List[str] = []
      for arg_name, label_arg in target_child.label_args.items():
        if label_arg.kind == self._alias:
          labels_to_replace.append(arg_name)
      for label_to_replace in labels_to_replace:
        alias = target_child.label_args[label_to_replace]
        target_child.label_args[label_to_replace] = \
          self._resolve_alias(target_child.label_args[label_to_replace])

        self._fix_genrule_cmd(alias, target_child.label_args[label_to_replace],
                              target_child)

  def _resolve_alias(self, alias: TargetNode) -> TargetNode:
    resolved_label: TargetNode = alias

    while resolved_label.kind == self._alias:
      resolved_label = resolved_label.label_args["actual"]

    return resolved_label

  def _fix_genrule_cmd(self, alias: TargetNode, actual: TargetNode,
      genrule: TargetNode) -> None:
    if genrule.kind != self._genrule:
      return
    genrule.string_args["cmd"] = genrule.string_args["cmd"].replace(alias.label,
                                                                    actual.label)
