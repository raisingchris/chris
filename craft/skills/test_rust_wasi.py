import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import rust_wasi  # noqa: E402


def test_rust_env_puts_cargo_bin_first(tmp_path):
    env = rust_wasi.rust_env(tmp_path, base={"PATH": "/usr/bin"})
    assert env["RUSTUP_HOME"] == str(tmp_path / "rustup")
    assert env["CARGO_HOME"] == str(tmp_path / "cargo")
    assert env["PATH"].split(":")[0] == str(tmp_path / "cargo" / "bin")


def test_wasm_path_uses_package_name(tmp_path):
    (tmp_path / "Cargo.toml").write_text('[package]\nname = "tz-repro"\nversion = "0.1.0"\n')
    p = rust_wasi.wasm_path(tmp_path)
    assert p == tmp_path / "target" / "wasm32-wasip1" / "release" / "tz_repro.wasm"


def test_deps_with_build_scripts(tmp_path):
    idx = tmp_path / "index.crates.io-abc"
    (idx / "num-traits-0.2.19").mkdir(parents=True)
    (idx / "num-traits-0.2.19" / "build.rs").write_text("fn main(){}")
    (idx / "tz-rs-0.7.3").mkdir()
    assert rust_wasi.deps_with_build_scripts(tmp_path) == ["num-traits-0.2.19"]
