from __future__ import annotations

import importlib.util
from pathlib import Path


def load_windows_assets_module():
    path = Path(__file__).parents[1] / "packaging" / "render_windows_assets.py"
    spec = importlib.util.spec_from_file_location("modterm_windows_assets", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_windows_version_tuple() -> None:
    module = load_windows_assets_module()

    assert module.version_tuple("1.2.0") == (1, 2, 0, 0)
    assert module.version_tuple("2.5.7.9") == (2, 5, 7, 9)


def test_windows_version_resource_generation(tmp_path) -> None:
    module = load_windows_assets_module()
    destination = tmp_path / "version_info.txt"

    module.create_version_info(destination, "1.2.0")
    content = destination.read_text(encoding="utf-8")

    assert "filevers=(1, 2, 0, 0)" in content
    assert "StringStruct('ProductName', 'ModTerm')" in content
