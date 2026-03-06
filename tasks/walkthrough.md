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
│   ├── browser_csv_date_only.yaml
│   ├── browser_csv_multi_input.yaml
│   └── browser_csv_url_only.yaml
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

### Phase 5: 実運用テンプレート + UX磨き込み

| 項目 | 内容 |
|---|---|
| テンプレート刷新 | デモ用2種を削除、実運用3パターン(日付のみ/複数項目/URL直接)に置換 |
| UIテキスト平易化 | param_schema.py のラベル・help、server.py のエラーメッセージを非エンジニア向けに |
| トースト通知 | index.html の alert() を全廃し、showToast() に統一 |
| モバイル対応 | style.css に @media 480px、editor.html に @media 640px 追加 |
| エディタUX | 新規作成ガイドメッセージ、タイプ説明の動的表示 |
| ルール更新 | .agent/rules を旧Tkinter構成から現行Flask/YAML構成に全面改訂 |

### コミット履歴

- `1650c64` - Phase 2-4 全実装 + エディタUI改善
- `7fecdbf` - テスト追加 + プレビューAPIバリデーション修正

---

## Phase 6: 非エンジニア向けUX強化

### 6-1. SSEリアルタイム進捗

| 項目 | 内容 |
|---|---|
| SSEエンドポイント | GET /api/events - Server-Sent Events でリアルタイム通知 |
| イベント種別 | status, progress, history, execution_start, execution_complete |
| フォールバック | SSE切断時は5秒ごとのポーリングに自動フォールバック |
| 接続インジケータ | ヘッダーに緑/赤のドットでSSE接続状態を表示 |

### 6-2. ドライラン (テスト実行)

| 項目 | 内容 |
|---|---|
| API | POST /api/dryrun/action/<id> - テンプレート変数展開 + バリデーション |
| UI | 実行確認モーダルに「テスト実行」ボタン |
| 結果表示 | 展開後のパラメータ一覧 + バリデーション結果をモーダル内に表示 |

### 6-3. ダッシュボードの視認性改善

| 項目 | 内容 |
|---|---|
| 履歴アイコン | 成功/失敗/警告/情報にアイコンバッジ付与 |
| 最終実行結果 | アクションボタン右端に最終成功/失敗時刻を表示 |
| ウェルカムガイド | アクション0件時に設定エディタへの誘導メッセージ |
| 日別棒グラフ | 統計パネルに直近7日のCSS棒グラフ (成功=緑, 失敗=赤) |
| 日別API | GET /api/stats に daily フィールド追加 |

### 6-4. エディタのガイド強化

| 項目 | 内容 |
|---|---|
| ヘルプアイコン | 各フィールドに ? アイコン + ツールチップ |
| タイプ説明 | アクションタイプ選択時に用途説明パネル (カード型) |
| バリデーション | 必須項目未入力時に赤枠ハイライト + エラートースト |
| 保存フラッシュ | 保存成功時にサイドバーアイテムを緑フラッシュアニメーション |

### 6-5. エラーガイダンス + 完了通知改善

| 項目 | 内容 |
|---|---|
| 完了サマリーカード | 成功/失敗を背景色付きカードで表示、所要時間・詳細付き |
| エラーガイダンス | timeout/接続/404/権限/Excel/セレクタ等のパターン別対処法 |
| 経過時間タイマー | 実行中にリアルタイムで「○分○秒」を表示 |
| トースト改善 | アイコン付き・メッセージ幅拡大 |

### テスト結果

| テストファイル | passed | skipped | 新規テスト |
|---|---|---|---|
| test_server_api.py | 21 | 0 | DryrunAPI(2) + SSE(1) + StatsDaily(1) |
| 他テスト合計 | 28 | 7 | - |
| **合計** | **49** | **7** | **+4テスト** |

---

## Phase 7-11: ヘルプ/設定管理高度化/テスト拡充/運用支援

### Phase 7: ヘルプシステム + ログビューア

| 項目 | 内容 |
|---|---|
| /help ページ | はじめかたガイド、アクションタイプ解説、テンプレート変数リファレンス表、FAQ、ショートカット一覧 |
| ログAPI | GET /api/logs (末尾N行, レベルフィルタ, テキスト検索, 日付指定) |
| ログパネル | ダッシュボードにトグル表示パネル、レベルフィルタ+検索 |

### Phase 8: 設定管理の高度化

| 項目 | 内容 |
|---|---|
| アクション複製 | POST /api/config/actions/<id>/duplicate + エディタに複製ボタン |
| 削除Undo | ソフトデリート + 5秒Undoトースト (メモリバッファ方式) |
| エクスポート | GET /api/config/export でYAMLダウンロード |
| インポート | POST /api/config/import でYAMLから追加インポート |
| 検索 | GET /api/config/search + エディタサイドバー検索バー |

### Phase 9: インタラクション強化 (部分)

| 項目 | 内容 |
|---|---|
| キーボードショートカット | Ctrl+S(保存), Ctrl+N(新規), /(検索), Escape(閉じる) |

### Phase 10: テスト拡充

| 項目 | 内容 |
|---|---|
| 新規テスト | Duplicate(2), Undo(2), Export/Import(4), Search(2), Health(1), Logs(2), CSV Export(1), Help HTML(1) |

### Phase 11: 運用支援

| 項目 | 内容 |
|---|---|
| 履歴CSVエクスポート | GET /api/execution-history/export |
| ヘルスチェック | GET /api/health (アクション数/グループ数/実行状態) |
| ログローテーション | Logger.rotate_logs(max_days=30) で古いログ自動削除 |
| ヘルプリンク | ダッシュボード/エディタのヘッダーにヘルプリンク追加 |

### テスト結果

| テストファイル | passed | skipped | 新規テスト |
|---|---|---|---|
| test_server_api.py | 36 | 0 | +15 (Duplicate/Undo/Export/Import/Search/Health/Logs/CSV/Help) |
| 他テスト合計 | 28 | 7 | - |
| **合計** | **64** | **7** | **+15テスト** |

### 未実装 (スコープ外に判断)

- ウィザードモード (4ステップ) - エディタのガイドパネルで十分
- ダッシュボードコンテキストメニュー - 操作が少なく優先度低
- ドラッグ&ドロップ並び替え - reorder APIは既存、UI側は工数対効果低

---

## Phase 12-16: ワークフロー / UI強化 / テスト拡充 / 拡張機能

### Phase 12: ワークフロー機能

| 項目 | 内容 |
|---|---|
| WorkflowConfig | id, name, description, action_ids, stop_on_error, display_order, icon |
| CRUD API | GET/POST /api/workflows, PUT/DELETE /api/workflows/<id> |
| 実行API | POST /api/run/workflow/<id> - 選択アクションを順次実行 |
| ダッシュボードUI | ワークフローパネル + 実行ボタン |
| エディタUI | ワークフロー編集フォーム + アクション選択チェックボックス |
| バグ修正 | update_workflow でIDが消える問題 (setdefault追加) |

### Phase 13: Visual UI強化

| 項目 | 内容 |
|---|---|
| テーマ切替 | ダーク/ライト切替、CSS変数でライトテーマ定義、localStorage保存 |
| 変数ピッカー | URL/コマンド/ソース/デスティネーションフィールドに{x}ボタン |
| バックアップ管理UI | モーダルでバックアップ一覧+復元+新規作成 |
| テンプレート変数API | GET /api/template-variables (13種の変数一覧) |
| 履歴詳細API | GET /api/execution-history/<index> |

### Phase 14: セキュリティ + コード品質

| 項目 | 内容 |
|---|---|
| パストラバーサル防止 | template_id, log date, backup timestamp にバリデーション |
| XSS防止 | showToast, 履歴表示でescapeHtml使用 |
| update_actionバグ修正 | ソート後のインデックスずれ (返値を変数保持) |

### Phase 15: テスト拡充

| 項目 | 内容 |
|---|---|
| ConfigManager単体 | 29テスト (Load/Query/CRUD/Persistence/Backup/DataClass) |
| Backup API | 3テスト (一覧/不正タイムスタンプ/存在しないバックアップ) |
| Template Variables | 1テスト |
| 履歴詳細 | 1テスト |

### Phase 16: 拡張機能

| 項目 | 内容 |
|---|---|
| バルク有効/無効切替 | POST /api/config/actions/bulk-toggle |
| APIドキュメント | GET /api/docs (全エンドポイント自動列挙) |

### テスト結果

| テストファイル | passed | skipped | 新規テスト |
|---|---|---|---|
| test_config_manager.py | 29 | 0 | 新規 (ConfigManager単体) |
| test_server_api.py | 49 | 0 | +13 (Workflow/Backup/Bulk/Docs/Variables/Detail) |
| test_scraper.py | 7 | 7 | - |
| test_file_ops.py | 10 | 0 | - |
| test_notifier.py | 11 | 0 | - |
| 合計 | 106 | 7 | +42テスト |

### ハマったポイント

- update_workflow で data に id が含まれない場合、WorkflowConfig の id が空になる -> setdefault で解決
- update_action の返値がソート後のインデックスで別のアクションを返していた -> 変数に保持して返すよう修正
- バックアップ復元テストのパストラバーサル: Flask のルーティングが `../` を含むURLを404にするため、テストの入力値を修正
