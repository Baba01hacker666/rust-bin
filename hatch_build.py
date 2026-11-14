from __future__ import annotations

import os
import re
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

PARTS = ("main", "llvm", "driver")
HOST_TARGET = "x86_64-unknown-linux-gnu"


def _download(url: str, path: str) -> None:
    if not os.path.exists(path):
        urllib.request.urlretrieve(url, path)


def _merge_tree(src: str, dst: str) -> None:
    os.makedirs(dst, exist_ok=True)
    for item in os.listdir(src):
        source = os.path.join(src, item)
        target = os.path.join(dst, item)
        if os.path.isdir(source) and not os.path.islink(source):
            shutil.copytree(source, target, dirs_exist_ok=True)
        else:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copy2(source, target)


def _strip_elf(path: str, strip: str, env: dict[str, str]) -> None:
    with open(path, "rb") as handle:
        if handle.read(4) != b"\x7fELF":
            return
    subprocess.run([strip, "--strip-unneeded", path], check=True, env=env)


def _llvm_strip(version: str, temp_dir: str, root: str) -> tuple[str, dict[str, str]]:
    archive_name = f"llvm-tools-{version}-{HOST_TARGET}.tar.gz"
    archive_path = os.path.join(root, archive_name)
    _download("https://static.rust-lang.org/dist/" + archive_name, archive_path)

    member_root = (
        f"llvm-tools-{version}-{HOST_TARGET}/llvm-tools-preview/lib/rustlib/{HOST_TARGET}"
    )
    with tarfile.open(archive_path, "r:gz") as tar:
        members = [
            member
            for member in tar.getmembers()
            if member.name == f"{member_root}/bin/llvm-strip"
            or member.name.startswith(f"{member_root}/lib/")
        ]
        tar.extractall(path=temp_dir, members=members)

    tool_dir = os.path.join(temp_dir, member_root)
    env = os.environ.copy()
    lib_dir = os.path.join(tool_dir, "lib")
    env["LD_LIBRARY_PATH"] = lib_dir + os.pathsep + env.get("LD_LIBRARY_PATH", "")
    return os.path.join(tool_dir, "bin", "llvm-strip"), env


class RustBinaryBuildHook(BuildHookInterface):
    def initialize(self, version, build_data) -> None:  # noqa: ANN001
        if version == "editable":
            return
        build_data["pure_python"] = False

        part = os.getenv("RUST_PART", "main")
        if part not in PARTS:
            raise RuntimeError(f"RUST_PART must be one of {PARTS}")

        rust_target = os.getenv("RUST_TARGET")
        wheel_tag = os.getenv("WHEEL_TAG")
        if not (rust_target and wheel_tag):
            raise RuntimeError("RUST_TARGET and WHEEL_TAG must be set for non-editable builds")

        build_data["tag"] = "py3-none-" + wheel_tag

        tag = os.environ["GITHUB_REF_NAME"]
        match = re.search(r"v?(\d+\.\d+\.\d+)", tag)
        assert match is not None, "GITHUB_REF_NAME must contain a version"
        version = match.group(1)

        is_windows = "windows" in rust_target
        rust_dir = os.path.join(self.root, "rust")

        if not os.path.exists(rust_dir):
            with tempfile.TemporaryDirectory() as temp_dir:
                strip = None
                strip_env: dict[str, str] = {}
                if part in ("llvm", "driver") and "linux" in rust_target:
                    strip, strip_env = _llvm_strip(version, temp_dir, self.root)

                if part == "main":
                    components = (
                        ("rustc", "rustc"),
                        ("cargo", "cargo"),
                        ("rust-std", f"rust-std-{rust_target}"),
                    )
                else:
                    components = (("rustc", "rustc"),)

                for component, inner in components:
                    archive_name = f"{component}-{version}-{rust_target}.tar.gz"
                    _download(
                        "https://static.rust-lang.org/dist/" + archive_name,
                        os.path.join(self.root, archive_name),
                    )

                    with tarfile.open(os.path.join(self.root, archive_name), "r:gz") as tar:
                        if part == "main":
                            tar.extractall(path=temp_dir)
                        else:
                            if part == "llvm":
                                prefix = f"rustc-{version}-{rust_target}/rustc/lib/"
                                wanted = "libLLVM"
                            elif is_windows:
                                prefix = f"rustc-{version}-{rust_target}/rustc/bin/"
                                wanted = "rustc_driver"
                            else:
                                prefix = f"rustc-{version}-{rust_target}/rustc/lib/"
                                wanted = "librustc_driver"
                            members = [
                                member
                                for member in tar.getmembers()
                                if member.name.startswith(prefix)
                                and os.path.basename(member.name).startswith(wanted)
                                and not member.name.endswith(".pdb")
                            ]
                            tar.extractall(path=temp_dir, members=members)

                    comp_top = os.path.join(temp_dir, f"{component}-{version}-{rust_target}")
                    src_prefix = os.path.join(comp_top, inner)

                    if part == "main":
                        _merge_tree(src_prefix, rust_dir)
                    elif is_windows:
                        _merge_tree(os.path.join(src_prefix, "bin"), os.path.join(rust_dir, "bin"))
                    else:
                        src_lib = os.path.join(src_prefix, "lib")
                        if strip is not None:
                            for item in os.listdir(src_lib):
                                item_path = os.path.join(src_lib, item)
                                if os.path.isfile(item_path):
                                    _strip_elf(item_path, strip, strip_env)
                        _merge_tree(src_lib, os.path.join(rust_dir, "lib"))

        if part == "main" and is_windows:
            for root_dir, _dirs, files in os.walk(rust_dir):
                for filename in files:
                    if filename.endswith(".pdb") or (
                        filename.startswith("rustc_driver-") and filename.endswith(".dll")
                    ):
                        os.remove(os.path.join(root_dir, filename))

        if part == "main":
            dependencies = [f"rustc-bin-driver=={version}"]
            if not is_windows:
                dependencies.append(f"rustc-bin-llvm=={version}")
            build_data["dependencies"] = dependencies
            build_data["force_include"] = {
                "rust/bin": "rust/bin",
                "rust/lib/rustlib": "rust/lib/rustlib",
                "rust/libexec": "rust/libexec",
                "rust/etc": "rust/etc",
                "src/rust/__init__.py": "rust/__init__.py",
                "src/rust/_version.py": "rust/_version.py",
            }
        elif is_windows:
            build_data["force_include"] = {
                "rust/bin": "rust/bin",
            }
        else:
            build_data["force_include"] = {
                "rust/lib": "rust/lib",
            }