#!/usr/bin/env python3
"""Qualify the opt-in native SQLite bridge and a locked package consumer."""

from __future__ import annotations

import json
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import tempfile


PACKAGE = Path(__file__).resolve().parents[1]


class QualificationError(RuntimeError):
    pass


def run(argv: list[str], *, cwd: Path,
        env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        argv,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
    )
    if result.returncode != 0:
        raise QualificationError(
            "command failed (%d): %s\nstdout:\n%s\nstderr:\n%s"
            % (result.returncode, " ".join(argv), result.stdout, result.stderr)
        )
    return result


def find_tool(name: str, env: dict[str, str]) -> str | None:
    return shutil.which(name, path=env.get("PATH"))


def pkg_config(package: str, mode: str, env: dict[str, str]) -> list[str]:
    tool = find_tool("pkg-config", env)
    if tool is None:
        raise QualificationError("official/sqlite requires pkg-config for qualification")
    return shlex.split(run([tool, mode, package], cwd=PACKAGE, env=env).stdout)


def optional_pkg_libs(package: str, env: dict[str, str]) -> list[str]:
    tool = find_tool("pkg-config", env)
    if tool is None:
        return []
    probe = subprocess.run(
        [tool, "--libs", package], cwd=PACKAGE, env=env, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120,
    )
    return shlex.split(probe.stdout) if probe.returncode == 0 else []


def resolve_toolchain(env: dict[str, str]) -> tuple[Path, Path, Path, Path, Path]:
    root_is_set = "TOKA_ROOT" in env
    explicit_keys = ("TOKA", "TOKAC", "TOKA_LIB")
    explicit_set = [key for key in explicit_keys if key in env]
    if root_is_set and explicit_set:
        raise QualificationError(
            "set either TOKA_ROOT or TOKA/TOKAC/TOKA_LIB, not both"
        )
    if root_is_set:
        if not env["TOKA_ROOT"].strip():
            raise QualificationError("TOKA_ROOT must not be empty")
        root = Path(env["TOKA_ROOT"]).expanduser().resolve()
        toka = root / "build" / "bin" / "toka"
        tokac = root / "build" / "bin" / "tokac"
        library = root / "lib"
        runtime = library / "sys" / "toka_rt.o"
        build_driver = root / "tools" / "scripts" / "toka_build.py"
    else:
        if len(explicit_set) != len(explicit_keys):
            missing = ", ".join(key for key in explicit_keys if key not in env)
            raise QualificationError(
                "set TOKA_ROOT or all of TOKA/TOKAC/TOKA_LIB"
                + (" (missing: " + missing + ")" if missing else "")
            )
        empty = [key for key in explicit_keys if not env[key].strip()]
        if empty:
            raise QualificationError(
                "toolchain variables must not be empty: " + ", ".join(empty)
            )
        toka = Path(env["TOKA"]).expanduser().resolve()
        tokac = Path(env["TOKAC"]).expanduser().resolve()
        library = Path(env["TOKA_LIB"]).expanduser().resolve()
        runtime = library / "sys" / "toka_rt.o"
        build_driver = library / "toolchain" / "toka_build.py"

    required_files = {
        "toka": toka,
        "tokac": tokac,
        "toka_rt.o": runtime,
        "toka_build.py": build_driver,
    }
    missing_files = [name for name, path in required_files.items() if not path.is_file()]
    if not library.is_dir():
        missing_files.append("TOKA_LIB")
    if missing_files:
        raise QualificationError(
            "incomplete Toka toolchain (missing: %s)" % ", ".join(missing_files)
        )
    return toka, tokac, library, runtime, build_driver


def compiler_command(env: dict[str, str]) -> list[str]:
    configured = env.get("CC")
    if configured is not None:
        command = shlex.split(configured)
        if not command:
            raise QualificationError("CC must name a C compiler")
        resolved = find_tool(command[0], env)
        if resolved is None:
            raise QualificationError("CC compiler was not found: " + command[0])
        command[0] = resolved
        return command
    for candidate in ("clang-20", "clang"):
        resolved = find_tool(candidate, env)
        if resolved is not None:
            return [resolved]
    raise QualificationError("official/sqlite requires CC, clang-20, or clang")


def make_sdk(work: Path, source_library: Path, runtime: Path,
             build_driver: Path) -> Path:
    library = work / "sdk" / "lib"
    shutil.copytree(
        source_library,
        library,
        ignore=shutil.ignore_patterns("*.pyc", "__pycache__"),
    )
    runtime_dir = library / "sys"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(runtime, runtime_dir / "toka_rt.o")
    toolchain = library / "toolchain"
    toolchain.mkdir(parents=True, exist_ok=True)
    shutil.copy2(build_driver, toolchain / "toka_build.py")
    return library


def write_consumer(project: Path, dependency: Path) -> None:
    (project / "src").mkdir(parents=True)
    (project / "package.tk").write_text(
        "pub const PACKAGE = (\n"
        '    name = "sqlite_consumer",\n'
        '    version = "0.1.0",\n'
        "    dependencies = (\n"
        "        sqlite = %s,\n"
        "    )\n"
        ")\n" % json.dumps(str(dependency)),
        encoding="utf-8",
    )
    (project / "build.tk").write_text(
        "import build::{Executable, run_build}\n\n"
        "fn main() -> i32 {\n"
        '    auto app# = Executable::make(c"sqlite_consumer", c"src/main.tk")\n'
        "    return run_build(app)\n"
        "}\n",
        encoding="utf-8",
    )
    (project / "src" / "main.tk").write_text(
        "import official/sqlite::{Database}\n\n"
        "fn main() -> i32 {\n"
        '    auto db# = Database::open(":memory:").unwrap()\n'
        '    if db#.execute("CREATE TABLE t (value INTEGER)").is_err() { return 1 }\n'
        "    if db#.close().is_err() { return 2 }\n"
        "    return 0\n"
        "}\n",
        encoding="utf-8",
    )


def main() -> int:
    host_env = dict(os.environ)
    toka, tokac, source_library, runtime, build_driver = resolve_toolchain(host_env)
    compiler = compiler_command(host_env)
    host_env["CC"] = shlex.join(compiler)

    with tempfile.TemporaryDirectory(prefix="toka-sqlite-package-") as temporary:
        work = Path(temporary)
        sdk = make_sdk(work, source_library, runtime, build_driver)
        sdk_runtime = sdk / "sys" / "toka_rt.o"
        base_env = dict(host_env)
        base_env.update({"TOKAC": str(tokac), "TOKA_LIB": str(sdk)})
        base_env.pop("TOKA_ROOT", None)
        base_env.pop("TOKA", None)
        base_env.pop("TOKA_OFFLINE", None)

        dependency = work / "sqlite"
        shutil.copytree(
            PACKAGE,
            dependency,
            ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
        )
        bridge_object = work / "sqlite_preflight.o"
        run([*compiler, "-Wall", "-Wextra", "-Werror", "-c",
             str(dependency / "native" / "sqlite_preflight.c"),
             "-o", str(bridge_object),
             *pkg_config("sqlite3", "--cflags", base_env)],
            cwd=PACKAGE, env=base_env)

        for source_name in ("preflight", "vertical"):
            program_ir = work / (source_name + ".ll")
            program = work / source_name
            run([str(tokac), "-I", str(sdk), "-I", str(dependency / "lib"),
                 "--emit-llvm", str(dependency / "tests" / (source_name + ".tk")),
                 "-o", str(program_ir)], cwd=PACKAGE, env=base_env)

            link_args = [*compiler, str(program_ir), str(bridge_object),
                         str(sdk_runtime), "-o", str(program),
                         *pkg_config("sqlite3", "--libs", base_env)]
            # A runtime built with optional TLS support still needs its own link
            # dependencies when this package performs a standalone native link.
            # This is inherited runtime configuration, not a SQLite dependency.
            link_args.extend(optional_pkg_libs("openssl", base_env))
            if platform.system() == "Darwin":
                macos_sdk = run(
                    ["xcrun", "--show-sdk-path"], cwd=PACKAGE, env=base_env
                ).stdout.strip()
                link_args.extend(["-isysroot", macos_sdk])
            run(link_args, cwd=PACKAGE, env=base_env)
            run([str(program)], cwd=PACKAGE, env=base_env)

        consumer = work / "consumer"
        write_consumer(consumer, dependency)
        run([str(toka), "fetch"], cwd=consumer, env=base_env)
        lock = consumer / "package.lock"
        locked = lock.read_bytes()
        if not locked.startswith(b"toka-lock-v1\n") or b"sqlite" not in locked:
            raise QualificationError(
                "SQLite consumer did not produce a v1 lock with sqlite"
            )

        offline_env = dict(base_env)
        offline_env["TOKA_OFFLINE"] = "1"
        run([str(toka), "fetch"], cwd=consumer, env=offline_env)
        if lock.read_bytes() != locked:
            raise QualificationError("offline SQLite fetch changed package.lock")
        run([str(toka), "build"], cwd=consumer, env=offline_env)
        program = consumer / "target" / "debug" / "sqlite_consumer"
        if not program.is_file():
            raise QualificationError("toka build did not produce SQLite consumer")
        run([str(program)], cwd=consumer, env=offline_env)

    print("official/sqlite qualification: PASSED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, QualificationError, subprocess.TimeoutExpired) as error:
        print("FAIL: " + str(error))
        raise SystemExit(1)
