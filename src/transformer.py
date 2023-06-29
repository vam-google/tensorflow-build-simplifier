from typing import Pattern, List, Dict, Iterable, Tuple, Set, cast
from node import Node, ContainerNode, TargetNode, RootNode, RepositoryNode, \
  PackageNode
from rule import TensorflowRules
import re


class NodesGraphBuilder:
  def __init__(self) -> None:
    self._label_splitter_regex: Pattern = re.compile(
        r"(?P<external>@?)(?P<repo>\w*)//(?P<package>[0-9a-zA-Z\-\._\@/]+)*:(?P<name>[0-9a-zA-Z\-\._\+/]+)$")

  def resolve_label_references(self, nodes_dict: Dict[str, TargetNode],
      nodes_by_type: Dict[str, Dict[str, TargetNode]]) -> Dict[str, TargetNode]:
    files_dict = nodes_by_type["source"]
    new_nodes: Dict[str, TargetNode] = {}
    for label, generic_node in nodes_dict.items():
      if not isinstance(generic_node, TargetNode):
        continue
      node: TargetNode = cast(TargetNode, generic_node)
      for label_list_arg_name in node.label_list_args:
        refs = node.label_list_args[label_list_arg_name]
        node.label_list_args[label_list_arg_name] = []
        for ref in refs:
          if str(ref) in nodes_dict:
            node.label_list_args[label_list_arg_name].append(
                nodes_dict[str(ref)])
          elif str(ref) in files_dict:
            node.label_list_args[label_list_arg_name].append(
                files_dict[str(ref)])
            new_nodes[str(ref)] = files_dict[str(ref)]
          else:
            node.label_list_args[label_list_arg_name].append(ref)

      for label_arg_name in node.label_args:
        label_val = node.label_args[label_arg_name]
        if label_val in nodes_dict:
          node.label_args[label_arg_name] = label_val

    return new_nodes

  def get_label_components(self, label: str) -> Tuple[bool, str, str, str]:
    match = self._label_splitter_regex.search(label)
    if not match:
      raise ValueError(f"{label} is not a valid label")
    return match.group("external") == "@", match.group("repo"), match.group(
        "package"), match.group("name")

  def build_package_tree(self, target_nodes_list: Iterable[Node]) -> Dict[
    str, Node]:
    external_root = RootNode("@")
    internal_root = RootNode("")
    all_nodes: Dict[str, Node] = {external_root.label: external_root,
                                  internal_root.label: internal_root}
    for node in target_nodes_list:
      external, repo, pkg, name = self.get_label_components(node.label)
      root_node = external_root if external else internal_root
      repo_node: RepositoryNode = RepositoryNode(repo, root_node.label)
      # all_nodes.get(str(repo_node))
      if str(repo_node) not in all_nodes:
        root_node.children[str(repo_node)] = repo_node
        all_nodes[str(repo_node)] = repo_node
      else:
        repo_node = cast(RepositoryNode, all_nodes[str(repo_node)])

      folders = pkg.split("/")
      container_node: ContainerNode = repo_node
      all_nodes[str(container_node)] = container_node
      package_depth: int = 2
      for folder in folders:
        next_package_node: PackageNode = PackageNode(folder,
                                                     str(container_node),
                                                     package_depth)
        next_package_node = cast(PackageNode,
                                 all_nodes.setdefault(str(next_package_node),
                                                      next_package_node))
        package_depth += 1
        container_node.children[str(next_package_node)] = next_package_node
        container_node = next_package_node
      container_node.children[str(node)] = node

    return all_nodes


class PackageTargetsTransformer:
  def __init__(self):
    self._cc_header_only_library = TensorflowRules.rules()[
      "cc_header_only_library"]
    self._generate_cc = TensorflowRules.rules()["generate_cc"]
    self._private_generate_cc = TensorflowRules.rules()["_generate_cc"]
    self._transitive_hdrs = TensorflowRules.rules()["_transitive_hdrs"]
    self._transitive_parameters_library = TensorflowRules.rules()[
      "_transitive_parameters_library"]

  def merge_cc_header_only_library(self, node: ContainerNode) -> None:
    for child in node.get_containers():
      self.merge_cc_header_only_library(child)

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

  def fix_generate_cc_kind(self, node: Node) -> None:
    if isinstance(node, ContainerNode):
      for child in cast(ContainerNode, node).children.values():
        self.fix_generate_cc_kind(child)
    else:
      if node.kind == self._private_generate_cc:
        node.kind = self._generate_cc
