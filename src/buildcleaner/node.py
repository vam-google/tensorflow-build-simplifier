from __future__ import annotations

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

  def get_targets(self, kind: Optional[Rule] = None) -> Iterable[TargetNode]:
    for node in self.children.values():
      if isinstance(node, TargetNode) and (not kind or (node.kind == kind)):
        yield cast(TargetNode, node)

  def get_target(self, name) -> Optional[TargetNode]:
    for label, node in self.children.items():
      if isinstance(node, TargetNode) and node.name == name:
        return node
    return None


class RootNode(ContainerNode):
  _RULE_KIND: Rule = Rule("__root__")

  def __init__(self, name: str) -> None:
    super().__init__(RootNode._RULE_KIND, name, name, None)


class RepositoryNode(ContainerNode):
  _RULE_KIND: Rule = Rule("__repository__")

  def __init__(self, name: str, parent_label: str) -> None:
    super().__init__(RepositoryNode._RULE_KIND, name, f"{parent_label}{name}//",
                     None)


class PackageNode(ContainerNode):
  _RULE_KIND: Rule = Rule("__package__")

  def __init__(self, name: str, parent_label: str, depth: int,
      copy_node: Optional[PackageNode] = None) -> None:
    if copy_node:
      super().__init__(PackageNode._RULE_KIND, "", "", copy_node)
    else:
      super().__init__(PackageNode._RULE_KIND, name,
                       f"{parent_label}{'' if depth <= 2 else '/'}{name}",
                       None)

    self.functions: List[Function] = []

  def get_packages(self) -> Iterable[PackageNode]:
    return cast(Iterable[PackageNode], self.get_containers())

  def get_package_folder_path(self) -> str:
    return self.label.split("//", 1)[1]


class TargetNode(Node):
  _TARGET_STUB_KIND: Rule = Rule("__target_stub__")

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
    self.out_label_list_args: Dict[str, List[TargetNode]] = {}
    self.out_label_args: Dict[str, TargetNode] = {}

    self.generator_name: str = ""
    self.generator_function: str = ""

    if copy_node:
      self.label_list_args = dict(copy_node.label_list_args)
      self.label_args = dict(copy_node.label_args)
      self.string_list_args = dict(copy_node.string_list_args)
      self.string_args = dict(copy_node.string_args)
      self.bool_args = dict(copy_node.bool_args)
      self.str_str_map_args = dict(copy_node.str_str_map_args)

      self.out_label_list_args = dict(copy_node.out_label_list_args)
      self.out_label_args = dict(copy_node.out_label_args)

      self.generator_function = copy_node.generator_function
      self.generator_name = copy_node.generator_name

  def is_stub(self) -> bool:
    return self.kind == TargetNode._TARGET_STUB_KIND

  def is_external(self) -> bool:
    return self.label.startswith("@")

  @staticmethod
  def create_stub(label: str) -> TargetNode:
    pkg_and_name: List[str] = label.split(":")
    return TargetNode(TargetNode._TARGET_STUB_KIND, pkg_and_name[1],
                      pkg_and_name[0])

  def get_parent_label(self) -> str:
    return self.label[:self.label.rfind(":")]

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
    super().__init__(FileNode.SOURCE_FILE_KIND, name, parent_label, None)


class GeneratedFileNode(TargetNode):
  GENERATED_FILE_KIND: Rule = BuiltInRules.rules()["generated"]

  def __init__(self, name: str, parent_label: str,
      maternal_target: TargetNode) -> None:
    super().__init__(GeneratedFileNode.GENERATED_FILE_KIND, name, parent_label,
                     None)
    self.maternal_target: TargetNode = maternal_target

  @staticmethod
  def create_gen_file(label: str,
      maternal_target: TargetNode) -> GeneratedFileNode:
    pkg_and_name = label.split(":")
    return GeneratedFileNode(pkg_and_name[1], pkg_and_name[0], maternal_target)
