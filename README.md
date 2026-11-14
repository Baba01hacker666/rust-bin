# Prebuilt Rust toolchain

This package provides a prebuilt Rust toolchain (rustc, cargo) for integrating
Rust artifacts into Python projects.

## Using the binaries

```
uvx --from=rust-bin cargo build
uvx --from=rust-bin rustc --version
```

## Building the wheel locally

```
RUST_TARGET=x86_64-unknown-linux-gnu WHEEL_TAG=manylinux_2_17_x86_64 \
  GITHUB_REF_NAME=v1.100.0 uv build --wheel
```