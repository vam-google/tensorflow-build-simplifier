from typing import List, Optional, Set, cast

from buildcleaner.node import ContainerNode
from buildcleaner.node import Node
from buildcleaner.node import TargetNode
from buildcleaner.tensorflow.rule import TensorflowRules
from buildcleaner.transformer import RuleTransformer


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
