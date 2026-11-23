# Prebuilt Rust toolchain

This package provides a prebuilt Rust toolchain (rustc, cargo) for integrating
Rust artifacts into Python projects. Installing `rustc-bin` pulls in the two
companion distributions automatically, so users only ever install one package.

A single PyPI wheel would exceed PyPI's default 100 MB per-file upload limit
(the full x86_64 Linux toolchain is about 198 MB), and getting that limit raised
takes weeks. Splitting the payload into three wheels keeps every upload well
below the limit while `pip install rustc-bin` still installs the whole toolchain:

- `rustc-bin` — compiler binaries, standard library, bundled LLD linker and launcher (~74 MB)
- `rustc-bin-llvm` — LLVM runtime library (only where LLVM is not statically linked, ~63 MB)
- `compiler-driver-runtime` — Rust compiler driver library (~61 MB)

All wheels install into the same `rust/` package directory and are merged at
install time.

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

cd ../compiler-driver-runtime
RUST_PART=driver RUST_TARGET=x86_64-unknown-linux-gnu \
  WHEEL_TAG=manylinux_2_17_x86_64 GITHUB_REF_NAME=v1.100.0 uv build --wheel
```

The `llvm` part is skipped for targets where LLVM is statically linked (i686,
musl and Windows); `rustc-bin` omits that dependency automatically on those
targets. The build hook downloads the llvm-tools component at build time to
strip every shipped ELF file; the stripper itself is not shipped. Windows PDB
debug symbols are dropped.

## Publishing

Pushing a `v*.*.*` tag builds every wheel and publishes it with trusted
publishing. PyPI identifies a trusted publisher by repository, workflow and
environment and ignores the project name, so each of the three projects is
published by its own job with its own environment:

| Project                  | Environment   |
| ------------------------ | ------------- |
| `rustc-bin`              | (none)        |
| `rustc-bin-llvm`         | `pypi-llvm`   |
| `compiler-driver-runtime`| `pypi-driver` |

The GitHub environment name stays `pypi-driver` so existing repository settings
keep working; only the PyPI project name changed.

`rustc-bin` is published only after both companions, so its dependencies always
exist on PyPI by the time it lands. Re-running a release is safe: uploads use
`--check-url`, which skips files that are already on the index.
