from __future__ import annotations

import os
import re

# Manual workflow dispatches pass the version via RUST_REF_NAME; tag pushes
# rely on GITHUB_REF_NAME.
_tag = os.environ.get("RUST_REF_NAME") or os.environ.get("GITHUB_REF_NAME", "v0.0.0")
_match = re.search(r"v?(\d+\.\d+\.\d+(?:\.post\d+)?)", _tag)
__version__ = _match.group(1) if _match else "0.0.0"