from __future__ import annotations

import os
import re
import shutil
import tarfile
import tempfile
import urllib.request

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class RustBinaryBuildHook(BuildHookInterface):
    def initialize(self, version, build_data) -> None:  # noqa: ANN001
        if version == "editable":
            return
        build_data["pure_python"] = False

        rust_target = os.getenv("RUST_TARGET")
        wheel_tag = os.getenv("WHEEL_TAG")
        if not (rust_target and wheel_tag):
            raise RuntimeError("RUST_TARGET and WHEEL_TAG must be set for non-editable builds")

        build_data["tag"] = "py3-none-" + wheel_tag

        tag = os.environ["GITHUB_REF_NAME"]
        match = re.search(r"v?(\d+\.\d+\.\d+)", tag)
        assert match is not None, "GITHUB_REF_NAME must contain a version"
        version = match.group(1)

        components = ("rustc", "cargo", "rust-std")

        if not os.path.exists("rust"):
            with tempfile.TemporaryDirectory() as temp_dir:
                for component in components:
                    if component == "rust-std":
                        archive_name = f"rust-std-{version}-{rust_target}.tar.gz"
                        inner = f"rust-std-{rust_target}"
                    elif component == "rustc":
                        archive_name = f"rustc-{version}-{rust_target}.tar.gz"
                        inner = "rustc"
                    else:
                        archive_name = f"cargo-{version}-{rust_target}.tar.gz"
                        inner = "cargo"

                    if not os.path.exists(archive_name):
                        urllib.request.urlretrieve(
                            "https://static.rust-lang.org/dist/" + archive_name,
                            archive_name,
                        )

                    with tarfile.open(archive_name, "r:gz") as tar:
                        tar.extractall(path=temp_dir)

                    comp_top = os.path.join(temp_dir, f"{component}-{version}-{rust_target}")
                    src_prefix = os.path.join(comp_top, inner)

                    os.makedirs("rust", exist_ok=True)
                    for item in os.listdir(src_prefix):
                        src = os.path.join(src_prefix, item)
                        dst = os.path.join("rust", item)
                        if os.path.isdir(src) and not os.path.islink(src):
                            shutil.copytree(src, dst, dirs_exist_ok=True)
                        else:
                            os.makedirs(os.path.dirname(dst), exist_ok=True)
                            shutil.copy2(src, dst)

        build_data["force_include"] = {
            "rust/bin": "rust/bin",
            "rust/lib": "rust/lib",
            "rust/libexec": "rust/libexec",
            "rust/etc": "rust/etc",
            "src/rust/__init__.py": "rust/__init__.py",
            "src/rust/_version.py": "rust/_version.py",
        }