# Prebuilt Rust toolchain

This package provides a prebuilt Rust toolchain (rustc, cargo) for integrating
Rust artifacts into Python projects.

Rust's compiler runtime is too large for a single PyPI wheel, so it is split
into three distributions:

- `rustc-bin` — compiler binaries, standard library and launcher
- `rustc-bin-llvm` — LLVM runtime library (not used on Windows)
- `rustc-bin-driver` — Rust compiler driver library

Installing `rustc-bin` pulls in the other two automatically.

## Using the binaries

```
uvx --from=rustc-bin cargo build
uvx --from=rustc-bin rustc --version
```

## Building the wheels locally

Each part is built separately for a target:

```
RUST_PART=main RUST_TARGET=x86_64-unknown-linux-gnu \
  WHEEL_TAG=manylinux_2_17_x86_64 GITHUB_REF_NAME=v1.100.0 uv build --wheel

cd packages/rustc-bin-llvm
RUST_PART=llvm RUST_TARGET=x86_64-unknown-linux-gnu \
  WHEEL_TAG=manylinux_2_17_x86_64 GITHUB_REF_NAME=v1.100.0 uv build --wheel

cd packages/rustc-bin-driver
RUST_PART=driver RUST_TARGET=x86_64-unknown-linux-gnu \
  WHEEL_TAG=manylinux_2_17_x86_64 GITHUB_REF_NAME=v1.100.0 uv build --wheel
```

The `llvm` part is skipped for Windows targets, where the driver DLL contains
LLVM statically.