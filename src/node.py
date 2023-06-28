from __future__ import annotations
from typing import Dict, Optional, List, Iterable, cast

from rule import Rule


class Node:
  def __init__(self, kind: Rule, name: str, label: str,
      copy_node: Optional[Node]) -> None:
    self.name: str = name
    self.label: str = label
    self.kind: Rule = kind

    if copy_node:
      self.name = str(copy_node.name)
      self.label = str(copy_node.label)
      self.kind = kind

  def __str__(self) -> str:
    return self.label

  def __eq__(self, other) -> bool:
    if type(self) != type(other):
      return False
    return self.label.__eq__(other.label)

  def __ne__(self, other) -> bool:
    return not self.__eq__(other)

  def __hash__(self) -> int:
    return self.label.__hash__()


class ContainerNode(Node):
  def __init__(self, kind: Rule, name: str, label: str,
      copy_node: Optional[ContainerNode]) -> None:
    super().__init__(kind, name, label, copy_node)
    self.children: Dict[str, Node] = {}
    if copy_node:
      self.children = dict(copy_node.children)

  def get_containers(self, rule: Optional[Rule] = None) -> Iterable[
    ContainerNode]:
    for node in self.children.values():
      if isinstance(node, ContainerNode) and (not rule or node.kind == rule):
        yield cast(ContainerNode, node)

  def get_targets(self, rule: Optional[Rule]) -> Iterable[TargetNode]:
    for node in self.children.values():
      if isinstance(node, TargetNode) and (not rule or (node.kind == rule)):
        yield cast(TargetNode, node)

  def get_target(self, name) -> Optional[TargetNode]:
    for label, node in self.children.items():
      if isinstance(node, TargetNode) and node.name == name:
        return node
    return None


class RootNode(ContainerNode):
  _rule_kind: Rule = Rule("__root__")

  def __init__(self, name: str) -> None:
    super().__init__(RootNode._rule_kind, name, name, None)


class RepositoryNode(ContainerNode):
  _rule_kind: Rule = Rule("__repository__")

  def __init__(self, name: str, parent_label: str) -> None:
    super().__init__(RepositoryNode._rule_kind, name, f"{parent_label}{name}//",
                     None)

class PackageNode(ContainerNode):
  _rule_kind: Rule = Rule("__package__")

  def __init__(self, name: str, parent_label: str, depth: int,
      copy_node: Optional[PackageNode] = None) -> None:
    if copy_node:
      super().__init__(PackageNode._rule_kind, "", "", copy_node)
    else:
      super().__init__(PackageNode._rule_kind, name,
                       f"{parent_label}{'' if depth <= 2 else '/'}{name}",
                       None)

  def get_package_folder_path(self) -> str:
    return self.label.split("//", 1)[1]


class TargetNode(Node):
  _target_stub_kind: Rule = Rule("__target_stub__")

  def __init__(self, kind: Rule, name: str, parent_label: str,
      copy_node: Optional[TargetNode] = None) -> None:
    if copy_node:
      super().__init__(kind, "", "", copy_node)
    else:
      super().__init__(kind, name, f"{parent_label}:{name}", None)

    self.label_list_args: Dict[str, List[Node]] = {}
    self.label_args: Dict[str, Node] = {}
    self.string_list_args: Dict[str, List[str]] = {}
    self.string_args: Dict[str, str] = {}
    self.bool_args: Dict[str, bool] = {}

    if copy_node:
      self.label_list_args = dict(copy_node.label_list_args)
      self.label_args = dict(copy_node.label_args)
      self.string_list_args = dict(copy_node.string_list_args)
      self.string_args = dict(copy_node.string_args)
      self.bool_args = dict(copy_node.bool_args)

  @staticmethod
  def create_stub(label: str) -> TargetNode:
    pkg_and_name = label.split(":")
    return TargetNode(TargetNode._target_stub_kind, pkg_and_name[1],
                      pkg_and_name[0])


class FileNode(TargetNode):
  _rule_kind: Rule = Rule("source")

  def __init__(self, name: str, parent_label: str) -> None:
    super().__init__(FileNode._rule_kind, name, f"{parent_label}:{name}", None)
