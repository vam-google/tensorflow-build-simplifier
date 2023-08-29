from __future__ import annotations

from abc import abstractmethod
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from typing import cast

from buildcleaner.rule import BuiltInRules
from buildcleaner.rule import Rule


class Function:
  def __init__(self, kind: Rule) -> None:
    self.kind = kind
    self.label_list_args: Dict[str, List[TargetNode]] = {}
    self.string_list_args: Dict[str, List[str]] = {}


class Node:
  @abstractmethod
  def __init__(self, kind: Rule, name: str, label: str) -> None:
    self.kind: Rule = kind
    self.name: str
    self.label: str

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

  def get_parent_label(self) -> str:
    return self._get_parent_label(self.label)

  def _get_parent_label(self, label: str) -> str:
    package_label_index: int = label.rfind(":")
    if package_label_index >= 0:
      # label belongs to a target, return parent package label
      return label[:package_label_index]

    # label belongs to a container, its parent is either top-level package,
    # repository or the global root node
    package_label_index = label.rfind("/")

    if package_label_index < 0:
      # label belongs to a global root, as it is the only one without slashes
      # in it
      raise LookupError("Root node cannonot have a parrent")

    if self.label.endswith("//"):
      # label belongs to a repository, return global root label
      return "@" if label.startswith("@") else ""

    if label[package_label_index - 1] == "/":
      # label is the top most package in a repo, return the repo
      return label[:package_label_index + 1]

    # label is a nested package in a repo, return a parent package
    return label[:package_label_index]


class ContainerNode(Node):
  @abstractmethod
  def __init__(self, kind: Rule, name: str, label: str) -> None:
    super().__init__(kind, name, label)
    self.children: Dict[str, Node] = {}

  # shallow search only
  def get_containers(self, kind: Optional[Rule] = None) -> Iterable[
    ContainerNode]:
    for node in self.children.values():
      if isinstance(node, ContainerNode) and (not kind or node.kind == kind):
        yield cast(ContainerNode, node)

  # shallow search only
  def get_targets(self, kind: Optional[Rule] = None) -> Iterable[TargetNode]:
    for node in self.children.values():
      if isinstance(node, TargetNode) and (not kind or (node.kind == kind)):
        yield cast(TargetNode, node)

  # shalow search only
  def get_target(self, name) -> Optional[TargetNode]:
    for label, node in self.children.items():
      if isinstance(node, TargetNode) and node.name == name:
        return node
    return None

  def __getitem__(self, label: str) -> Optional[Node]:
    if not label.startswith(self.label):
      return None

    child_start_index: int = len(self.label)
    if len(label) == child_start_index:
      return self

    child_label_start_char: str = label[child_start_index]
    if child_label_start_char == ":":
      # It must be a target, so must be amoung direct children of this container
      return self.children.get(label)

    child_start_index += 1  # +1 is to skip '/' delimiter
    next_package_index: int
    next_target_index: int
    if label[child_start_index] == "/":
      # self is RootNode as its label ends before '//'
      next_package_index = child_start_index + 1
      next_target_index = -1
    else:
      next_package_index = label.find("/", child_start_index)
      next_target_index = label.rfind(":", child_start_index)

    next_label: str

    if next_package_index < 0 and next_target_index < 0:
      return self.children.get(label)
    elif next_package_index < 0:
      next_label = label[:next_target_index]
    elif next_target_index < 0:
      next_label = label[:next_package_index]
    else:
      next_label = label[:min(next_target_index, next_package_index)]

    next_child: Optional[Node] = self.children.get(next_label)
    if not next_child:
      return None

    # It must be a container node, or this method would have terminated earlier
    return cast(ContainerNode, next_child)[label]

  def __setitem__(self, label: str, child: Node) -> None:
    self._setitem(label, child)

  def __delitem__(self, label: str) -> None:
    self._setitem(label, None)

  def tree_nodes(self) -> Iterable[Node]:
    return self._tree_nodes_preorder(self)

  def _tree_nodes_preorder(self, node: Node) -> Iterable[Node]:
    yield node
    if isinstance(node, ContainerNode):
      container_node: ContainerNode = cast(ContainerNode, node)
      for child in container_node.children.values():
        yield from self._tree_nodes_preorder(child)

  def _setitem(self, label: str, child: Optional[Node]) -> None:
    if child and label != child.label:
      raise ValueError(
          f"Label and child do not match: label = {label}, child = {child}")

    parent_label: Optional[str] = self._get_parent_label(label)
    if parent_label is None:
      raise LookupError(
          f"Cannot put node in container: container = {self}, node = {child}")

    parent: Optional[Node] = self[parent_label]
    if parent is None:
      raise LookupError(
          f"Cannot put node in container: container = {self}, node = {child}")

    container_parent: ContainerNode = cast(ContainerNode, parent)
    if child:
      container_parent.children[label] = child
    else:
      del container_parent.children[label]


class RootNode(ContainerNode):
  _RULE_KIND: Rule = Rule("__root__")

  def __init__(self, name: str) -> None:
    super().__init__(RootNode._RULE_KIND, name, name)


class RepositoryNode(ContainerNode):
  _RULE_KIND: Rule = Rule("__repository__")

  def __init__(self, name: str, parent_label: str) -> None:
    super().__init__(RepositoryNode._RULE_KIND, name, f"{parent_label}{name}//")


class PackageNode(ContainerNode):
  _RULE_KIND: Rule = Rule("__package__")

  def __init__(self, name: str, parent_label: str, depth: int) -> None:
    super().__init__(PackageNode._RULE_KIND, name,
                     f"{parent_label}{'' if depth <= 2 else '/'}{name}")
    self.functions: List[Function] = []

  def get_packages(self) -> Iterable[PackageNode]:
    return cast(Iterable[PackageNode], self.get_containers())

  def get_package_folder_path(self) -> str:
    return self.label.split("//", 1)[1]


class TargetNode(Node):
  _TARGET_STUB_KIND: Rule = Rule("__target_stub__")

  def __init__(self, kind: Rule, name: str, parent_label: str) -> None:
    super().__init__(kind, name, f"{parent_label}:{name}")

    self.label_list_args: Dict[str, List[TargetNode]] = {}
    self.label_args: Dict[str, TargetNode] = {}
    self.string_list_args: Dict[str, List[str]] = {}
    self.string_args: Dict[str, str] = {}
    self.bool_args: Dict[str, bool] = {}
    self.str_str_map_args: Dict[str, Dict[str, str]] = {}
    self.out_label_list_args: Dict[str, List[TargetNode]] = {}
    self.out_label_args: Dict[str, TargetNode] = {}

    self.generator_name: str = ""
    self.generator_function: str = ""

  def duplicate(self, kind: Optional[Rule], name: Optional[str],
      parent_label: Optional[str]) -> TargetNode:
    copy: TargetNode = TargetNode(kind if kind else self.kind,
                                  name if name else self.name,
                                  parent_label if parent_label else self.get_parent_label())
    copy.label_list_args = self._deep_copy_label_list_args(self.label_list_args)
    copy.label_args = dict(self.label_args)
    copy.string_list_args = self._deep_copy_str_list_args(self.string_list_args)
    copy.string_args = dict(self.string_args)
    copy.bool_args = dict(self.bool_args)
    copy.str_str_map_args = self._deep_copy_str_str_map_args(
        self.str_str_map_args)
    copy.out_label_list_args = self._deep_copy_label_list_args(
        self.out_label_list_args)
    copy.out_label_args = dict(self.out_label_args)
    copy.generator_function = self.generator_function
    copy.generator_name = self.generator_name

    return copy

  def _deep_copy_label_list_args(self,
      list_args: Dict[str, List[TargetNode]]) -> Dict[str, List[TargetNode]]:
    deep_copy: Dict[str, List[TargetNode]] = dict()
    for k, v in list_args.items():
      deep_copy[k] = list(v)
    return deep_copy

  def _deep_copy_str_list_args(self, list_args: Dict[str, List[str]]) -> Dict[
    str, List[str]]:
    deep_copy: Dict[str, List[str]] = dict()
    for k, v in list_args.items():
      deep_copy[k] = list(v)
    return deep_copy

  def _deep_copy_str_str_map_args(self, list_args: Dict[str, Dict[str, str]]) -> \
      Dict[str, Dict[str, str]]:
    deep_copy: Dict[str, Dict[str, str]] = dict()
    for k, v in list_args.items():
      deep_copy[k] = dict(v)
    return deep_copy

  def is_stub(self) -> bool:
    return self.kind == TargetNode._TARGET_STUB_KIND

  def is_external(self) -> bool:
    return self.label.startswith("@")

  @staticmethod
  def create_stub(label: str) -> TargetNode:
    pkg_and_name: List[str] = label.split(":")
    return TargetNode(TargetNode._TARGET_STUB_KIND, pkg_and_name[1],
                      pkg_and_name[0])

  def get_targets(self, kind: Optional[Rule] = None) -> Iterable[TargetNode]:
    # targets: Dict[str, TargetNode] = {}
    for label_list_arg in self.label_list_args.values():
      for label_list_node in label_list_arg:
        if not kind or label_list_node.kind == kind:
          yield label_list_node

    for label_arg in self.label_args.values():
      if not kind or label_arg.kind == kind:
        yield label_arg


class FileNode(TargetNode):
  SOURCE_FILE_KIND: Rule = Rule("source")

  def __init__(self, name: str, parent_label: str) -> None:
    super().__init__(FileNode.SOURCE_FILE_KIND, name, parent_label)


class GeneratedFileNode(TargetNode):
  GENERATED_FILE_KIND: Rule = BuiltInRules.rules()["generated"]

  def __init__(self, name: str, parent_label: str,
      maternal_target: TargetNode) -> None:
    super().__init__(GeneratedFileNode.GENERATED_FILE_KIND, name, parent_label)
    self.maternal_target: TargetNode = maternal_target

  @staticmethod
  def create_gen_file(label: str,
      maternal_target: TargetNode) -> GeneratedFileNode:
    pkg_and_name = label.split(":")
    return GeneratedFileNode(pkg_and_name[1], pkg_and_name[0], maternal_target)
