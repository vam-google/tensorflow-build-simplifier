from __future__ import annotations
from typing import Dict, Optional, List, Iterable, Generator, cast

from rule import Rule

class Function:
  def __init__(self, kind: Rule) -> None:
    self.kind = kind
    self.label_list_args: Dict[str, List[TargetNode]] = {}
    self.string_list_args: Dict[str, List[str]] = {}


class Node:
  def __init__(self, kind: Rule, name: str, label: str,
      copy_node: Optional[Node]) -> None:
    self.kind: Rule = kind
    self.name: str
    self.label: str

    if copy_node:
      self.name = str(copy_node.name)
      self.label = str(copy_node.label)
    else:
      self.name = name
      self.label = label

  def __str__(self) -> str:
    return self.label

  def __eq__(self, other) -> bool:
    if type(self) != type(other):
      return False
    return self.label.__eq__(other.label)

  def __ne__(self, other) -> bool:
    return not self.__eq__(other)

  def __lt__(self, other) -> bool:
    return self.label.__lt__(other.label)

  def __le__(self, other) -> bool:
    return self.label.__le__(other.label)

  def __gt__(self, other) -> bool:
    return self.label.__gt__(other.label)

  def __ge__(self, other) -> bool:
    return self.label.__ge__(other.label)

  def __hash__(self) -> int:
    return self.label.__hash__()


class ContainerNode(Node):
  def __init__(self, kind: Rule, name: str, label: str,
      copy_node: Optional[ContainerNode]) -> None:
    super().__init__(kind, name, label, copy_node)
    self.children: Dict[str, Node] = {}
    if copy_node:
      self.children = dict(copy_node.children)

  def get_containers(self, kind: Optional[Rule] = None) -> Iterable[
    ContainerNode]:
    for node in self.children.values():
      if isinstance(node, ContainerNode) and (not kind or node.kind == kind):
        yield cast(ContainerNode, node)

  def get_targets(self, kind: Optional[Rule]) -> Iterable[TargetNode]:
    for node in self.children.values():
      if isinstance(node, TargetNode) and (not kind or (node.kind == kind)):
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

    self.functions: List[Function] = []

  def get_package_folder_path(self) -> str:
    return self.label.split("//", 1)[1]


class TargetNode(Node):
  target_stub_kind: Rule = Rule("__target_stub__")

  def __init__(self, kind: Rule, name: str, parent_label: str,
      copy_node: Optional[TargetNode] = None) -> None:
    if copy_node:
      super().__init__(kind, "", "", copy_node)
    else:
      super().__init__(kind, name, f"{parent_label}:{name}", None)

    self.label_list_args: Dict[str, List[TargetNode]] = {}
    self.label_args: Dict[str, TargetNode] = {}
    self.string_list_args: Dict[str, List[str]] = {}
    self.string_args: Dict[str, str] = {}
    self.bool_args: Dict[str, bool] = {}
    self.str_str_map_args: Dict[str, Dict[str, str]] = {}

    if copy_node:
      self.label_list_args = dict(copy_node.label_list_args)
      self.label_args = dict(copy_node.label_args)
      self.string_list_args = dict(copy_node.string_list_args)
      self.string_args = dict(copy_node.string_args)
      self.bool_args = dict(copy_node.bool_args)
      self.str_str_map_args = dict(copy_node.str_str_map_args)

  def is_stub(self):
    return self.kind == TargetNode.target_stub_kind

  @staticmethod
  def create_stub(label: str) -> TargetNode:
    pkg_and_name = label.split(":")
    return TargetNode(TargetNode.target_stub_kind, pkg_and_name[1],
                      pkg_and_name[0])

  def get_parent_label(self) -> str:
    return self.label[:self.label.rfind(":")]

  def get_targets(self, kind: Optional[Rule]) -> Iterable[TargetNode]:
    # targets: Dict[str, TargetNode] = {}
    for label_list_arg in self.label_list_args.values():
      for label_list_node in label_list_arg:
        if not kind or label_list_node.kind == kind:
          yield label_list_node

    for label_arg in self.label_args.values():
      if not kind or label_arg.kind == kind:
        yield label_arg


class FileNode(TargetNode):
  source_file_kind: Rule = Rule("source")

  def __init__(self, name: str, parent_label: str) -> None:
    super().__init__(FileNode.source_file_kind, name, parent_label, None)

