# -*- coding: utf-8 -*-
"""scraper.py のユニットテスト"""
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from actions.scraper import ScrapingAction

# pandas/requests/bs4 がインストールされているか
try:
    import pandas as pd
    import requests
    from bs4 import BeautifulSoup
    HAS_SCRAPE_DEPS = True
except ImportError:
    HAS_SCRAPE_DEPS = False

skip_no_deps = pytest.mark.skipif(not HAS_SCRAPE_DEPS, reason="pandas/requests/bs4 not installed")


class TestScrapingValidation:
    """validate_params のテスト"""

    def setup_method(self):
        self.action = ScrapingAction()

    def test_browser_csv_requires_url_and_button(self):
        issues = self.action.validate_params({"mode": "browser_csv"})
        assert any("URL" in i for i in issues)
        assert any("download_button" in i or "ダウンロードボタン" in i for i in issues)

    def test_browser_csv_valid(self):
        issues = self.action.validate_params({
            "mode": "browser_csv",
            "url": "http://example.com",
            "download_button": "#btn",
        })
        assert issues == []

    def test_auto_table_requires_url_and_output(self):
        issues = self.action.validate_params({"mode": "auto_table"})
        assert any("URL" in i for i in issues)
        assert any("output" in i or "出力先" in i for i in issues)

    def test_auto_table_valid(self):
        issues = self.action.validate_params({
            "mode": "auto_table",
            "url": "http://example.com",
            "output": "out.csv",
        })
        assert issues == []

    def test_css_selector_requires_selectors_and_output(self):
        issues = self.action.validate_params({"mode": "css_selector"})
        assert any("URL" in i for i in issues)
        assert any("selectors" in i or "セレクタ" in i for i in issues)
        assert any("output" in i or "出力先" in i for i in issues)

    def test_css_selector_valid(self):
        issues = self.action.validate_params({
            "mode": "css_selector",
            "url": "http://example.com",
            "selectors": {"title": "h1"},
            "output": "out.csv",
        })
        assert issues == []

    def test_default_mode_is_browser_csv(self):
        issues = self.action.validate_params({"url": "http://x", "download_button": "#b"})
        assert issues == []


@skip_no_deps
class TestAutoTable:
    """auto_table モードのテスト"""

    def setup_method(self):
        self.action = ScrapingAction()

    @patch("requests.get")
    def test_auto_table_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.text = "<html><table><tr><th>A</th></tr><tr><td>1</td></tr><tr><td>2</td></tr><tr><td>3</td></tr></table></html>"
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            result = self.action.execute({
                "mode": "auto_table",
                "url": "http://example.com",
                "output": f.name,
                "table_index": 0,
            })

        assert result.success is True

    @patch("requests.get")
    def test_auto_table_no_tables(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.text = "<html><body>no tables</body></html>"
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = self.action.execute({
            "mode": "auto_table",
            "url": "http://example.com",
            "output": "out.csv",
        })
        assert result.success is False

    @patch("requests.get")
    def test_auto_table_index_out_of_range(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.text = "<html><table><tr><td>1</td></tr></table></html>"
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = self.action.execute({
            "mode": "auto_table",
            "url": "http://example.com",
            "output": "out.csv",
            "table_index": 5,
        })
        assert result.success is False
        assert "範囲外" in result.message


@skip_no_deps
class TestCssSelector:
    """css_selector モードのテスト"""

    def setup_method(self):
        self.action = ScrapingAction()

    @patch("requests.get")
    def test_css_selector_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.text = """
        <html><body>
            <h1 class="t">Title1</h1>
            <h1 class="t">Title2</h1>
            <p class="d">Desc1</p>
            <p class="d">Desc2</p>
        </body></html>
        """
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            result = self.action.execute({
                "mode": "css_selector",
                "url": "http://example.com",
                "selectors": {"title": "h1.t", "desc": "p.d"},
                "output": f.name,
            })

        assert result.success is True
        assert "2行" in result.message

    @patch("requests.get")
    def test_css_selector_no_match(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.text = "<html><body></body></html>"
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            result = self.action.execute({
                "mode": "css_selector",
                "url": "http://example.com",
                "selectors": {"x": "div.nonexistent"},
                "output": f.name,
            })
        assert result.success is False


@skip_no_deps
class TestWriteOutput:
    """_write_output のテスト"""

    def setup_method(self):
        self.action = ScrapingAction()

    def test_write_csv(self):
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            self.action._write_output(df, f.name, "Sheet1")
            content = Path(f.name).read_text(encoding="utf-8-sig")
        assert "a,b" in content
        assert "1,3" in content

    def test_write_xlsx(self):
        df = pd.DataFrame({"x": [10]})
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            self.action._write_output(df, f.name, "Data")
            assert Path(f.name).stat().st_size > 0
