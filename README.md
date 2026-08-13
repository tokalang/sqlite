# `official/sqlite`

Official opt-in SQLite package for Toka. Package version `0.1.0` is the first
standalone release line. The API currently implements the phase 1 database
lifecycle slice.

## Migration status

The one-way cutover completed on 2026-08-13. This repository is now the
canonical source for `official/sqlite`; its immutable `v0.1.0` release is in
the public catalog, and both the minimal registry consumer and service-kit
replay the locked package online and offline. The former compiler-repository
copy has been retired rather than retained as a mirror or submodule.

## API

`official/sqlite` is a synchronous, safe bridge to the system SQLite C
library. SQLite handles and raw C pointers remain in the package's private
native boundary. The public Toka API uses owned values and structured errors
only.

The current slice includes:

- `Database::open`, `execute`, explicit idempotent `close`, and RAII close;
- `prepare` and `Statement` bind, step, reset, and finalization;
- integer, text, and null binding with owned scalar and text reads;
- exactly-once statement finalization;
- explicit `Transaction` commit or rollback, with rollback on ordinary scope
  cleanup;
- structured SQLite code and message errors.

The bridge excludes an ORM, SQL parser, connection pool, async API, migrations,
extensions, nested transactions, and cross-database abstraction. Transactions
do not promise rollback after Toka's fail-fast `panic` or process termination.

## Native boundary

The manifest declares system `sqlite3` as required only when this package is
selected. `toka build` compiles the package-private C shim and links SQLite for
a locked consumer only. Compiler, `std`, and `stdx` builds do not acquire a
SQLite dependency.

## Qualification

The required qualification toolchain is the published Toka `v1.0.0-rc.4` SDK.
Install SQLite, OpenSSL, pkg-config, and Clang, then provide either an installed
SDK explicitly:

```sh
TOKA=/path/to/bin/toka \
TOKAC=/path/to/bin/tokac \
TOKA_LIB=/path/to/lib \
python3 tests/qualify_preflight.py
```

or a Toka source checkout whose `build/bin/toka`, `build/bin/tokac`, and
`lib/sys/toka_rt.o` have already been built:

```sh
TOKA_ROOT=/path/to/toka python3 tests/qualify_preflight.py
```

Qualification builds and runs the ABI preflight and vertical lifecycle suite,
then builds and runs an isolated local path-dependency consumer.

## Migration provenance

Package history was imported with `git subtree split` from
[`tokalang/toka`](https://github.com/tokalang/toka) at source snapshot
`07d86771cc5b28d73f75e8ab560284315a904685`, original path
`official/sqlite`. The last source commit affecting that path before the
snapshot was `0eb95497662c6588f439f5279ee5c8f5a3333ae1`; the split history tip is
`dcf7d5db98bea0a52b97373c7d2657307afbdbca`.

The standalone scaffold is retained as the first parent of the import merge;
the package's extracted Toka history is retained as the second parent.

## License

Apache License 2.0. See [LICENSE](LICENSE). System SQLite remains subject to its
own public-domain dedication; this repository does not vendor SQLite source.
