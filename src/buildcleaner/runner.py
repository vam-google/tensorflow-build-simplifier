import subprocess
from typing import Iterable
from typing import List
from typing import Sequence
from typing import Set


class BazelRunner:
  def query_deps_output(self, targets: List[str], config: str = "pycpp_filters",
      output: str = "label_kind", excluded_targets: Sequence[str] = ()) -> str:

    chunk: str = "'" + "' union '".join(targets) + "'"
    query: List[str] = [
        "bazel",
        "cquery",
        f"--config={config}" if config else "",
        # f"'//tensorflow'",
        f"deps({chunk})",
        "--keep_going",
        "--output",
        f"{output}"
    ]
    if excluded_targets:
      query.append("--")
      query.extend([f"-{t}" for t in excluded_targets])

    proc = subprocess.run(query, stdout=subprocess.PIPE)

    return proc.stdout.decode('utf-8')

  # def query_output(self, targets: Set[str], config: str = "pycpp_filters",
  #     output: str = "build", excluded_targets: Sequence[str] = (),
  #     chunk_size: int = 1500) -> str:
  #   bazel_query_stdouts: List[str] = []
  #   for target_chunk in self._split_into_chunks(targets, chunk_size):
  #     chunk: str = "'" + "' union '".join(target_chunk) + "'"
  #     query: List[str] = [
  #         "bazel",
  #         "cquery",
  #         f"--config={config}" if config else "",
  #         chunk,
  #         "--output",
  #         "--keep_going",
  #         f"{output}"
  #     ]
  #     if excluded_targets:
  #       query.append("--")
  #       query.extend([f"-{t}" for t in excluded_targets])
  #
  #     proc = subprocess.run(query, stdout=subprocess.PIPE)
  #
  #     bazel_query_stdouts.append(proc.stdout.decode('utf-8'))
  #   return "\n".join(bazel_query_stdouts)

  def _split_into_chunks(self, targets: Set[str], chunk_size) -> Iterable[
    Iterable[str]]:
    if len(targets) <= chunk_size:
      yield targets
      return
    cur_chunk: List[str] = []
    for target in targets:
      if len(cur_chunk) >= chunk_size:
        yield cur_chunk
        cur_chunk = []
      cur_chunk.append(target)

    if cur_chunk:
      yield cur_chunk
