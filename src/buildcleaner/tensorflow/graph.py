from typing import cast

from buildcleaner.graph import TargetDag
from buildcleaner.node import Node
from buildcleaner.node import TargetNode
from buildcleaner.rule import BuiltInRules
from buildcleaner.rule import Rule
from buildcleaner.tensorflow.rule import TfRules


class TfTargetDag(TargetDag):
  def __init__(self) -> None:
    self._config_setting: Rule = BuiltInRules.rules()["config_setting"]
    self._alias: Rule = BuiltInRules.rules()["alias"]
    self._bool_flag: Rule = TfRules.rules()["bool_flag"]

  def is_removable_node(self, node: Node) -> bool:
    if not super().is_removable_node(node):
      return False

    actual_node: Node = node

    if node.kind == self._alias:
      alias_node: TargetNode = cast(TargetNode, node)
      actual_node = cast(TargetNode, node).label_args["actual"]

    if actual_node.kind == self._config_setting:
      if node.get_parent_label() == "//tensorflow/tsl":
        return False

    if actual_node.kind == self._bool_flag:
      # if str(node) == "//tensorflow:enable_registration_v2":
      return False

    return True
