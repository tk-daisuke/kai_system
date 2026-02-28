# kai_system TODO

## Phase 2: スクレーピング機能拡充
- [x] scraper.py にモード分岐追加 (auto_table / css_selector / browser_csv)
- [x] auto_table モード実装 (requests + pandas.read_html)
- [x] css_selector モード実装 (requests + BeautifulSoup)
- [x] param_schema.py に mode フィールド + show_when 条件追加
- [x] POST /api/scrape/preview エンドポイント追加
- [x] requirements.txt に requests, beautifulsoup4, pandas, openpyxl 追加

## Phase 3: 拡張機能
- [x] FileOperationAction (copy / move / archive) 新規作成
- [x] file_ops スキーマを param_schema.py に追加
- [x] app.py に file_ops import 追加
- [x] notifier.py に Webhook 通知 (Slack / Discord) 追加

## Phase 4: UI/UX 強化
- [x] 実行履歴の永続化 (JSON)
- [x] 統計API (GET /api/stats, GET /api/execution-history)
- [x] index.html に統計セクション追加
- [x] style.css に統計パネルスタイル追加
- [x] テンプレート管理API (GET/POST/DELETE /api/templates)
- [x] config/templates/ にサンプルテンプレート作成

## エディタUI改善
- [x] evaluateShowWhen を {field, value} 形式に修正
- [x] key_value フィールドタイプ追加 (css_selector の selectors 用)
- [x] テンプレート選択・適用UI追加 (サイドバー + applyTemplate)
- [x] テンプレート保存ボタン追加 (saveAsTemplate)
- [x] Webhook通知URL フィールドをアクション設定に追加
- [x] ActionConfig に webhook_url フィールド追加
- [x] 実行完了時の Webhook 通知連携
