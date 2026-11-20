"""Keep business policy independent of HTTP and database implementations."""

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1] / "src/vi_api"


@pytest.mark.parametrize("layer", ["domain", "app"])
def test_inner_layers_do_not_import_frameworks_or_infrastructure(layer):
    forbidden = (
        "fastapi",
        "starlette",
        "sqlalchemy",
        "pydantic",
        "httpx",
        "celery",
        "vi_api.infrastructure",
        "vi_api.interfaces",
        "vi_api.container",
        "vi_api.bootstrap",
    )
    if layer == "domain":
        forbidden += ("vi_api.app",)
    for path in (ROOT / layer).rglob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            modules = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules = [node.module]
            for module in modules:
                assert not any(
                    module == item or module.startswith(item + ".") for item in forbidden
                ), f"{path.relative_to(ROOT)} imports {module}, violating layer boundaries"
