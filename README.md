# `official/sqlite`

Standalone home for Toka's official SQLite package.

## Migration status

This repository is a migration scaffold and is not yet the canonical package
source. Until standalone qualification, release, and registry consumer replay
are complete, the authoritative source remains
[`tokalang/toka/official/sqlite`](https://github.com/tokalang/toka/tree/main/official/sqlite).

Cutover will be one-way. The compiler repository copy will be removed after a
successful standalone release; this repository will not become a long-lived
mirror or submodule. Native dependency provenance and installed-SDK
qualification must move with the package.

## License

Apache License 2.0. See [LICENSE](LICENSE). Migrated native dependencies must
retain their applicable third-party notices and licenses.
Official SQLite package for Toka
