# Rust Module Hello World

Demonstrates writing a custom Ansible module in Rust and testing it from a playbook.

## Overview
Ansible modules are typically Python scripts, but any executable that speaks the Ansible module JSON protocol can be used. This example compiles a Rust binary and places it in the `library/` directory so Ansible picks it up as a custom module.

## Files
- **`module-src/`** — Rust source code (`Cargo.toml`, `src/`) for the `rust_helloworld` module.
- **`library/rust_helloworld`** — Compiled binary (built by `make`).
- **`Makefile`** — Builds the Rust module with `cargo build` and copies the binary to `library/`.
- **`rust.yml`** — Test playbook that exercises the module.

## Building

```bash
make
```

This runs `cargo build` in `module-src/` and copies `target/debug/helloworld` to `library/rust_helloworld`.

## Playbook: `rust.yml`
Tests the `rust_helloworld` custom module with:
- Synchronous calls with and without a `name` argument
- Async calls (using `async`/`poll`)
- Assertions that the returned `msg` matches expected values (`"Hello, World!"`, `"Hello, Ansible!"`)

## Requirements
- Rust toolchain (`cargo`) for building
- Ansible with `library/` on the module path
