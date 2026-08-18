# `official/sqlite`

Official opt-in SQLite package for Toka. Package version `0.1.1` upgrades the
compiler baseline to `1.0.0-rc.6`. The API implements the safe synchronous database
lifecycle slice.

## Migration status

The canonical source for `official/sqlite` is this repository. Releases `v0.1.0`
and `v0.1.1` are in the public catalog.

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

The required qualification toolchain is Toka `v1.0.0-rc.6` SDK.
Provide the installed SDK path via:

```sh
TOKA_SDK=/path/to/extracted-sdk python3 tests/qualify_preflight.py
```
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
