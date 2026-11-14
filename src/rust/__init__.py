from __future__ import annotations

import os
import sys


def main() -> None:
    root = os.path.abspath(os.path.dirname(__file__))
    bin_dir = os.path.join(root, "bin")
    name = os.path.basename(sys.argv[0])
    # Fall back to cargo when invoked under an unrecognized name.
    if not os.path.exists(os.path.join(bin_dir, name)):
        name = "cargo"
    tool = os.path.join(bin_dir, name)
    os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
    if os.name == "posix":
        os.execv(tool, [tool, *sys.argv[1:]])  # noqa: S606
    else:
        import subprocess  # noqa: PLC0415

        sys.exit(subprocess.call([tool, *sys.argv[1:]]))  # noqa: S603