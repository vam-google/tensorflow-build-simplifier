import re
import sys
from typing import List
from typing import Match
from typing import Optional
from typing import Pattern
from typing import TextIO


# This is WIP
class AstParser:
  def __init__(self, cli_args: List[str]) -> None:
    self._cli_args: List[str] = cli_args
    self._tu_decl_regex: Pattern = re.compile(r"^TranslationUnitDecl")
    self._tu_local_def_regex: Pattern = re.compile(
        r"(VarDecl .*static cinit$)|(FunctionDecl .* static$)|(NamespaceDecl .* line:\d+:\d+$)")
    # self._tu_local_def_regex: Pattern = re.compile(r"(NamespaceDecl .* line:\d+:\d+$)")

  def find_translaton_unit_local_definitions(self, stream: TextIO):

    tu_counter = -1
    for line in stream:
      match: Optional[Match[str]] = self._tu_decl_regex.search(line)
      if match:
        tu_counter += 1

        print(f"{self._cli_args[tu_counter]}:{tu_counter}")
      else:
        match = self._tu_local_def_regex.search(line)
        if match:
          print(f"{self._cli_args[tu_counter]}: {line.strip()}")


if __name__ == '__main__':
  cli = AstParser(sys.argv[1:])
  cli.find_translaton_unit_local_definitions(sys.stdin)
