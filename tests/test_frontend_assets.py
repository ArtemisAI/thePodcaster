from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = PROJECT_ROOT / "frontend"


def test_index_html_exists():
    index_path = FRONTEND_DIR / "index.html"
    assert index_path.is_file(), f"{index_path} should exist"


def test_index_references_assets():
    index_path = FRONTEND_DIR / "index.html"
    html = index_path.read_text(encoding="utf-8")
    assert "style.css" in html, "style.css link missing"
    assert "script.js" in html, "script.js script tag missing"
