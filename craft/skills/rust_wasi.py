"""Run a small Rust program on a machine with no C linker: build for wasm32-wasip1, run with wasmtime.

Why: cargo needs `cc` to link a normal Linux binary, and this machine has none. The
wasm32-wasip1 target links with rust-lld, which ships inside rustc. So a repro that only
prints things can still run as real Rust.

Limit: any dependency with a build script (build.rs: num-traits, so chrono, chrono-tz)
still compiles that script for the host and fails on `cc`. Keep repro deps to crates
with no build.rs. `--check` lists which locked deps have one.

Setup once (df -h / first; about 700 MB):
    export RUSTUP_HOME=/tmp/rs/rustup CARGO_HOME=/tmp/rs/cargo
    curl -sSf https://sh.rustup.rs -o /tmp/rs/rustup-init.sh
    sh /tmp/rs/rustup-init.sh -y --profile minimal --target wasm32-wasip1 --no-modify-path
    python3 -m venv /tmp/rs/py && /tmp/rs/py/bin/pip install wasmtime

Use:
    /tmp/rs/py/bin/python -I rust_wasi.py /tmp/rs/repro            # build + run
    /tmp/rs/py/bin/python -I rust_wasi.py /tmp/rs/repro --check    # which deps have build.rs

First used 2026-11-11: tzdb_data 0.2.5 run as Rust, matched the Python decode.
"""
import argparse
import os
import pathlib
import subprocess
import sys

HOME = pathlib.Path(os.environ.get("RUST_WASI_HOME", "/tmp/rs"))
TARGET = "wasm32-wasip1"


def rust_env(home=HOME, base=None):
    env = dict(os.environ if base is None else base)
    env["RUSTUP_HOME"] = str(home / "rustup")
    env["CARGO_HOME"] = str(home / "cargo")
    env["PATH"] = str(home / "cargo" / "bin") + os.pathsep + env.get("PATH", "")
    return env


def wasm_path(project, release=True):
    project = pathlib.Path(project)
    name = None
    for line in (project / "Cargo.toml").read_text().splitlines():
        s = line.strip()
        if s.startswith("name") and "=" in s:
            name = s.split("=", 1)[1].strip().strip('"')
            break
    if not name:
        raise ValueError("no package name in Cargo.toml")
    return project / "target" / TARGET / ("release" if release else "debug") / (name.replace("-", "_") + ".wasm")


def deps_with_build_scripts(registry_src):
    """Crate dirs under cargo's registry/src that ship a build.rs (they need a host `cc`)."""
    out = []
    for idx in pathlib.Path(registry_src).glob("*"):
        for crate in sorted(idx.glob("*")):
            if (crate / "build.rs").exists():
                out.append(crate.name)
    return out


def run_wasm(path, argv=()):
    import wasmtime  # only needed for running

    eng = wasmtime.Engine()
    store = wasmtime.Store(eng)
    cfg = wasmtime.WasiConfig()
    cfg.inherit_stdout()
    cfg.inherit_stderr()
    cfg.argv = [pathlib.Path(path).stem, *argv]
    store.set_wasi(cfg)
    linker = wasmtime.Linker(eng)
    linker.define_wasi()
    inst = linker.instantiate(store, wasmtime.Module.from_file(eng, str(path)))
    try:
        inst.exports(store)["_start"](store)
    except wasmtime.ExitTrap as e:
        return e.code
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("args", nargs="*")
    a = ap.parse_args(argv)
    env = rust_env()
    if a.check:
        subprocess.run(["cargo", "fetch"], cwd=a.project, env=env, check=True)
        for c in deps_with_build_scripts(HOME / "cargo" / "registry" / "src"):
            print("build.rs:", c)
        return 0
    r = subprocess.run(["cargo", "build", "--release", "--target", TARGET], cwd=a.project, env=env)
    if r.returncode:
        return r.returncode
    return run_wasm(wasm_path(a.project), a.args)


if __name__ == "__main__":
    sys.exit(main())
