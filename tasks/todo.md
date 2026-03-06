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

## Phase 5: 実運用テンプレート + UX磨き込み
- [x] デモ用テンプレート (wikipedia_table, css_extract) 削除
- [x] 実運用3パターンのテンプレート追加 (日付のみ/複数項目/URL直接)
- [x] テストの旧テンプレート参照を更新
- [x] param_schema.py のラベル・ヘルプを非エンジニア向けに平易化
- [x] server.py のエラーメッセージを一般ユーザー向けに書き換え
- [x] index.html の alert() をトースト通知に置換
- [x] editor.html にモバイル対応 + 新規作成ガイド追加
- [x] style.css にモバイルレスポンシブ追加
- [x] .agent/rules/PROJECT_RULES.md を現行アーキテクチャに全面改訂

## Phase 6: 非エンジニア向けUX強化
### 6-1. SSEリアルタイム進捗
- [x] GET /api/events SSEエンドポイント追加
- [x] index.html のポーリングをEventSourceに置換
- [x] 実行開始/進捗/完了/エラーのリアルタイムプッシュ

### 6-2. ドライラン (テスト実行)
- [x] POST /api/dryrun/action/<id> エンドポイント追加
- [x] テンプレート変数展開結果 + バリデーション結果を返す
- [x] モーダルに「テスト実行」ボタン追加

### 6-3. ダッシュボードの視認性改善
- [x] 実行履歴にアイコン付きステータスバッジ
- [x] アクションボタンに最終実行結果を表示
- [x] アクション0件時のウェルカムガイド
- [x] 統計パネルにCSS棒グラフ (直近7日)

### 6-4. エディタのガイド強化
- [x] フィールドにツールチップ付きヘルプアイコン追加
- [x] アクションタイプ選択時の説明パネル
- [x] 必須項目の未入力リアルタイムバリデーション
- [x] 保存成功時のフィードバック改善

### 6-5. エラーガイダンス + 完了通知改善
- [x] エラー時に「考えられる原因」「次にやること」を表示
- [x] 完了時にサマリーカード表示
- [x] 実行中の経過時間表示
