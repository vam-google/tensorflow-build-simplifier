from __future__ import annotations
from typing import Union, Dict, Optional, List, Type, cast


class Node:
  def __init__(self, name: str, label: str, copy_node: Optional[Node]) -> None:
    self.name: str = name
    self.label: str = label
    self.kind: str = ""

    if copy_node:
      self.name = str(copy_node.name)
      self.label = str(copy_node.label)
      self.kind = str(copy_node.kind)

  def __str__(self) -> str:
    return self.label

  def __eq__(self, other) -> bool:
    if type(self) != type(other):
      return False
    return self.label.__eq__(other.label)

  def __ne__(self, other) -> bool:
    if type(self) != type(other):
      return False
    return self.label.__ne__(other.label)

  def __hash__(self) -> int:
    return self.label.__hash__()


class ContainerNode(Node):
  def __init__(self, name: str, label: str,
      copy_node: Optional[ContainerNode]) -> None:
    super().__init__(name, label, copy_node)
    self.children: Dict[str, Node] = {}
    if copy_node:
      self.children = dict(copy_node.children)

  def get_containers(self, rule_kind: Optional[str] = None) -> List[
    ContainerNode]:
    children_of_kind: List[ContainerNode] = []
    for node in self.children.values():
      if isinstance(node, ContainerNode) and (
          not rule_kind or node.kind == rule_kind):
        children_of_kind.append(cast(ContainerNode, node))
    return children_of_kind

  def get_targets(self, rule_kind: Optional[str]) -> List[TargetNode]:
    children_of_kind: List[TargetNode] = []
    for node in self.children.values():
      if isinstance(node, TargetNode) and (
          not rule_kind or (node.kind == rule_kind)):
        children_of_kind.append(cast(TargetNode, node))
    return children_of_kind

  def get_target(self, name) -> Optional[TargetNode]:
    for label, node in self.children.items():
      if isinstance(node, TargetNode) and node.name == name:
        return node
    return None


class RootNode(ContainerNode):
  def __init__(self, name: str) -> None:
    super().__init__(name, name, None)
    self.kind = "_root"


class RepositoryNode(ContainerNode):
  def __init__(self, name: str, parent_label: str) -> None:
    super().__init__(name, f"{parent_label}{name}//", None)

    self.kind = "_repository"


class PackageNode(ContainerNode):
  def __init__(self, name: str, parent_label: str, depth: int,
      copy_node: Optional[PackageNode] = None) -> None:
    if copy_node:
      super().__init__("", "", copy_node)
    else:
      super().__init__(name, f"{parent_label}{'' if depth <= 2 else '/'}{name}",
                       None)
    self.kind = "_package"

  def get_package_folder_path(self) -> str:
    return self.label.split("//", 1)[1]


class TargetNode(Node):
  def __init__(self, name: str, parent_label: str,
      copy_node: Optional[TargetNode] = None) -> None:
    if copy_node:
      super().__init__("", "", copy_node)
    else:
      super().__init__(name, f"{parent_label}:{name}", None)

    self.label_list_args: Dict[str, List[Union[str, Node]]] = {}
    self.label_args: Dict[str, Union[str, Node]] = {}
    self.string_list_args: Dict[str, List[str]] = {}
    self.string_args: Dict[str, str] = {}
    self.bool_args: Dict[str, bool] = {}
    if copy_node:
      self.label_list_args = dict(copy_node.label_list_args)
      self.label_args = dict(copy_node.label_args)
      self.string_list_args = dict(copy_node.string_list_args)
      self.string_args = dict(copy_node.string_args)
      self.bool_args = dict(copy_node.bool_args)


class FileNode(TargetNode):
  def __init__(self, name: str, parent_label: str) -> None:
    super().__init__(name, f"{parent_label}:{name}", None)
