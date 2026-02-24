# -*- coding: utf-8 -*-
"""
kai_system - エントリーポイント
アクション駆動型タスク自動化ツール（Web UI版）
"""

import sys
from pathlib import Path

# src フォルダをパスに追加
if getattr(sys, "frozen", False):
    base_path = Path(sys.executable).parent
else:
    base_path = Path(__file__).parent
    # src 自身をパスに追加（パッケージインポート用）
    if str(base_path) not in sys.path:
        sys.path.insert(0, str(base_path))

# vendor ライブラリのパス追加
vendor_path = base_path.parent / "vendor"
if vendor_path.exists() and str(vendor_path) not in sys.path:
    sys.path.insert(0, str(vendor_path))


def main():
    """メインエントリーポイント"""
    from infra.logger import logger

    # アクションプラグインを自動ロード（レジストリに登録される）
    import actions.csv_download   # noqa: F401
    import actions.scraper        # noqa: F401
    import actions.shell_cmd      # noqa: F401

    logger.info("kai_system を起動します")

    # コマンドライン引数の解析
    config_dir = None
    port = 5000
    no_browser = False

    for arg in sys.argv[1:]:
        if arg.startswith("--config="):
            config_dir = Path(arg.split("=", 1)[1])
        elif arg.startswith("--port="):
            port = int(arg.split("=", 1)[1])
        elif arg == "--no-browser":
            no_browser = True

    # 設定読み込み
    from core.config_manager import ConfigManager
    config = ConfigManager(config_dir=config_dir)
    config.load()

    # Web UI 起動
    from web.server import WebServer
    server = WebServer(config, port=port)
    server.run(open_browser=not no_browser)


if __name__ == "__main__":
    main()
