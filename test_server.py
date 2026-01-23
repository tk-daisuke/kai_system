# -*- coding: utf-8 -*-
"""
テスト用CSVサーバー
ローカルでCSVファイルを配信するシンプルなHTTPサーバー
"""

import http.server
import socketserver
import os
from pathlib import Path

PORT = 8888
CSV_DIR = Path(__file__).parent / "test_csv"

# テスト用CSVファイルを作成
CSV_DIR.mkdir(exist_ok=True)

# サンプルCSVデータ
csv_files = {
    "sales.csv": """日付,商品名,数量,金額
2026-01-23,商品A,10,5000
2026-01-23,商品B,5,3000
2026-01-23,商品C,8,4000
""",
    "inventory.csv": """商品コード,商品名,在庫数,発注点
A001,商品A,100,20
A002,商品B,50,10
A003,商品C,80,15
""",
    "afternoon.csv": """時刻,項目,ステータス,備考
13:00,レポート作成,完了,OK
13:30,データ確認,完了,異常なし
14:00,集計処理,完了,
""",
    "daily.csv": """日付,売上合計,件数,平均単価
2026-01-23,120000,45,2667
2026-01-22,115000,42,2738
2026-01-21,108000,40,2700
""",
    "test.csv": """テストA,テストB,テストC
値1,値2,値3
データ1,データ2,データ3
"""
}

# CSVファイルを作成
for filename, content in csv_files.items():
    (CSV_DIR / filename).write_text(content, encoding="utf-8-sig")
    print(f"Created: {CSV_DIR / filename}")

# HTTPサーバーを起動
os.chdir(CSV_DIR)

class DownloadHandler(http.server.SimpleHTTPRequestHandler):
    """ダウンロードを強制するHTTPハンドラー"""
    
    def end_headers(self):
        """Content-Dispositionヘッダーを追加してダウンロードを強制"""
        if self.path.endswith('.csv'):
            filename = os.path.basename(self.path)
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.send_header('Content-Type', 'text/csv; charset=utf-8')
        super().end_headers()
    
    def log_message(self, format, *args):
        print(f"[CSV Server] {args[0]}")

print(f"\n=== テスト用CSVサーバー起動 ===")
print(f"URL例: http://localhost:{PORT}/sales.csv")
print(f"停止するには Ctrl+C を押してください\n")

with socketserver.TCPServer(("", PORT), DownloadHandler) as httpd:
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nサーバーを停止しました")
