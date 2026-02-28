# kai_system Phase 1 リアーキテクチャ Walkthrough

## 実施内容

スケジュール駆動型RPA -> **アクション駆動型 Web UI** に全面リアーキテクチャを実施。

## 新構造

```text
src/
├── app.py                     # エントリーポイント（Flask Web UI起動）
├── core/
│   ├── config_manager.py      # YAML設定管理 + webhook_url対応
│   ├── action_base.py         # プラグイン基底クラス
│   ├── action_manager.py      # 実行管理 + プラグインレジストリ
│   ├── group_manager.py       # グループ管理
│   ├── param_schema.py        # パラメータスキーマ (show_when, key_value対応)
│   └── template_engine.py     # URL日付テンプレート ({today}, {today_jp} 等)
├── actions/
│   ├── csv_download.py        # CSVダウンロード+Excel転記
│   ├── scraper.py             # スクレーピング (3モード: auto_table/css_selector/browser_csv)
│   ├── file_ops.py            # ファイル操作 (copy/move/archive)
│   └── shell_cmd.py           # シェルコマンド実行
├── web/
│   ├── server.py              # Flask Web サーバー + JSON API (統計/テンプレート/プレビュー)
│   ├── templates/
│   │   ├── index.html         # ダッシュボード (統計パネル付き)
│   │   └── editor.html        # 設定エディタ (show_when/key_value/テンプレート/Webhook)
│   └── static/style.css       # ダークテーマCSS
├── infra/
│   ├── logger.py              # クロスプラットフォームログ
│   └── notifier.py            # デスクトップ通知 + Slack/Discord Webhook通知
config/
├── actions.yaml               # アクション定義
├── groups.yaml                # グループ定義
├── templates/                 # スクレーピングテンプレート
│   ├── wikipedia_table.yaml
│   └── css_extract.yaml
└── execution_history.json     # 実行履歴 (自動生成)
tests/
├── conftest.py
├── test_scraper.py            # scraper バリデーション + モード別テスト
├── test_file_ops.py           # copy/move/archive テスト
├── test_notifier.py           # Webhook ペイロード + 送信テスト
└── test_server_api.py         # 全APIエンドポイント + HTMLレンダリングテスト
```

---

## Phase 2-4 完了報告

### Phase 2: スクレーピング機能拡充

| 項目 | 内容 |
|---|---|
| auto_table モード | requests + pandas.read_html でテーブル自動検出 |
| css_selector モード | requests + BeautifulSoup でCSSセレクタ抽出 |
| browser_csv モード | Playwright でブラウザCSVダウンロード (既存) |
| プレビューAPI | POST /api/scrape/preview で先頭10行をJSON返却 |
| show_when 条件 | モード切替でエディタUIのフィールドを出し分け |
| key_value フィールド | selectors のキー:値ペアをUI上で編集可能に |

### Phase 3: 拡張機能

| 項目 | 内容 |
|---|---|
| FileOperationAction | copy/move/archive(ZIP) + globパターン対応 |
| Webhook通知 | Slack/Discord自動判別、urllib.requestのみで外部依存なし |
| Webhook連携 | アクション設定にwebhook_url追加、実行完了時に自動通知 |

### Phase 4: UI/UX 強化

| 項目 | 内容 |
|---|---|
| 統計ダッシュボード | 総実行数/成功/失敗/成功率 + 直近7日統計 |
| 実行履歴永続化 | config/execution_history.json (500件上限) |
| テンプレート管理 | CRUD API + サイドバーUI + テンプレ保存ボタン |
| エディタUI改善 | show_when出し分け、key_value入力、Webhook設定 |

### テスト結果

| テストファイル | passed | skipped | 対象機能 |
|---|---|---|---|
| test_file_ops.py | 10 | 0 | copy/move/archive + バリデーション |
| test_notifier.py | 11 | 0 | Slack/Discord ペイロード + Webhook送信 |
| test_scraper.py | 7 | 7 | バリデーション(7) + モード別(7, 要pandas) |
| test_server_api.py | 17 | 0 | API + テンプレートCRUD + HTMLページ |
| **合計** | **45** | **7** | skipped = pandas/requests/bs4 未インストール時 |

### ハマったポイント

- scraper.py は pandas/requests をメソッド内でimportする設計のため、`patch("actions.scraper.pd")` が効かない -> テストは `patch("requests.get")` でモジュール直接パッチに変更
- プレビューAPIの css_selector バリデーションが import 後にあったため、依存ライブラリ未インストール時に500 -> バリデーションをimport前に移動して修正

### コミット履歴

- `1650c64` - Phase 2-4 全実装 + エディタUI改善
- `7fecdbf` - テスト追加 + プレビューAPIバリデーション修正
