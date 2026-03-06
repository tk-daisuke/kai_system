# kai_system リアーキテクチャ設計提案書

## 現状の分析

現在の **Co-worker Bot** は以下の特性を持つ Windows RPA ツール:

| 項目 | 現状 |
|---|---|
| GUI | Tkinter (550x650 固定) |
| 設定 | Excel (`Task_Master.xlsx`) |
| スケジュール | `StartTime` / `EndTime` による時間帯実行 |
| タスク | CSV ダウンロード → Excel 転記 のみ |
| OS依存 | Windows 専用 (win32com, ctypes) |

---

## 設計方針: 3つの柱

### 1. スケジュール性の撤廃 -> アクション駆動型へ
- `StartTime` / `EndTime` を完全撤廃
- 各タスク（アクション）を個別のボタンとして表示
- グループは「まとめて実行」用のラベルとして残す

### 2. プラグイン型アクションシステム
- ActionBase 基底クラスから派生してプラグイン化
- csv_download, scraper, file_ops, shell_cmd の4種を実装

### 3. 設定の YAML 化
- Excel -> YAML ベースへ移行

---

## 実装フェーズ計画と実施状況

### Phase 1: コアリファクタリング [完了]
- YAML 設定システム構築
- ActionBase 基底クラス作成
- 既存 CSV ダウンロード機能を ActionPlugin化
- Web UI (Flask) でアクションボタン表示

### Phase 2: スクレーピング機能拡充 [完了]
- scraper.py にモード分岐追加 (auto_table / css_selector / browser_csv)
- auto_table: requests + pandas.read_html でテーブル自動検出
- css_selector: requests + BeautifulSoup で要素抽出
- param_schema.py に show_when 条件付きフィールド追加
- POST /api/scrape/preview プレビューAPI追加
- requirements.txt に依存パッケージ追加

#### 設計判断
- scraper は単一クラスにモード分岐で実装。_write_output() の共有とアクション登録の簡潔さを優先
- show_when は field/value 形式で、value に配列も許容（複数モードで共通表示）

### Phase 3: 拡張機能 [完了]
- FileOperationAction (copy / move / archive) を src/actions/file_ops.py に新規実装
- notifier.py に Webhook 通知 (Slack / Discord) を追加。urllib のみで外部依存なし
- URL に "discord" を含むかで自動判別

#### 設計判断
- Webhook は urllib.request のみで実装。requests は scraper 用途に限定し、notifier に追加依存を持ち込まない
- Slack は attachments 形式、Discord は embeds 形式でペイロード分離

### Phase 4: UI/UX 強化 [完了]
- 実行履歴の永続化 (config/execution_history.json)、最新500件制限
- 統計API (GET /api/stats, GET /api/execution-history)
- index.html に統計セクション(総実行数/成功/失敗/成功率)追加
- テンプレート管理API (CRUD: GET/POST/DELETE /api/templates)
- config/templates/ にサンプルテンプレート2種作成

#### 設計判断
- 履歴は SQLite ではなく JSON ファイル。500件上限で十分なスケール
- テンプレートは YAML ファイル単位管理。ファイル名がID

### Phase 5: 実運用テンプレート + UX磨き込み [完了]
- デモ用テンプレート (wikipedia_table, css_extract) を削除
- 実運用3パターンのテンプレートを追加:
  - browser_csv_date_only: 日付入力 → CSVダウンロード
  - browser_csv_multi_input: 日付+複数項目入力 → CSVダウンロード
  - browser_csv_url_only: URLアクセスでCSVダウンロード
- param_schema.py のラベル・ヘルプテキストを非エンジニア向けに平易化
- server.py のエラーメッセージを一般ユーザー向けに書き換え
- index.html の alert() をトースト通知に全面置換
- editor.html にモバイル対応 + 新規作成ガイドメッセージ追加
- style.css にモバイルレスポンシブ (@media 480px) 追加
- .agent/rules/PROJECT_RULES.md を現行アーキテクチャに全面改訂

#### 設計判断
- テンプレートは実運用パターンに集約。共通の前段は「ブラウザ起動 → ユーザーがログイン → セッション利用」
- UIテキストは「技術者が理解できる」から「非エンジニアが迷わない」に方針転換

### Phase 6: 非エンジニア向けUX強化 [完了]
- SSE (Server-Sent Events) でリアルタイム進捗・完了通知
- ドライランAPI (テスト実行) で設定の事前検証
- ダッシュボード視認性改善 (アイコン・最終結果・棒グラフ・ウェルカムガイド)
- エディタのガイド強化 (ヘルプアイコン・タイプ説明・バリデーション・保存フラッシュ)
- エラーガイダンス (パターン別対処法) + 完了サマリーカード + 経過時間タイマー

#### 設計判断
- SSEは queue.Queue ベースのシンプル実装。外部ライブラリ不要、Flask標準のResponse + generator で実現
- ドライランは独立エンドポイント (/api/dryrun/action/<id>) として実装。既存の /api/run への副作用を避ける
- エラーガイダンスはクライアントサイドのパターンマッチで実装。サーバー側に余計なロジックを持ち込まない
- 日別統計は stats API に daily フィールドを追加。専用APIを増やさず既存を拡張

### Phase 7: ヘルプシステム + ログビューア [完了]
- /help ルート + help.html にはじめかたガイド、アクションタイプ解説、テンプレート変数リファレンス、FAQ、ショートカット一覧
- GET /api/logs でログファイル読み込み (レベルフィルタ + テキスト検索 + 日付指定)
- ダッシュボードにログパネル追加 (トグル表示、レベルフィルタ、検索)

#### 設計判断
- ヘルプはSPAパターン (タブ切替) で単一ページに集約。ルーティングの複雑化を避ける
- ログAPIはファイルを直接読み込む (SQLite等は不使用)。末尾N行の逆順読み取りでメモリ効率を確保

### Phase 8: 設定管理の高度化 [完了]
- POST /api/config/actions/<id>/duplicate でアクション複製
- DELETE /api/config/actions/<id>/soft-delete + POST /api/config/undo で5秒Undo
- GET /api/config/export (YAML) + POST /api/config/import (YAML)
- GET /api/config/search でアクション・グループ横断検索
- エディタサイドバーに検索バー追加

#### 設計判断
- Undoはサーバー側にメモリバッファ (threading.Timer) で実装。5秒後にバッファをクリア
- インポートは既存IDとの重複は無視 (追加のみ)。破壊的マージは避ける
- 複製はIDに `_copy` サフィックス + 重複時はカウンター付与

### Phase 9: インタラクション強化 [部分完了]
- キーボードショートカット: Ctrl+S (保存), Ctrl+N (新規), / (検索), Escape (閉じる)

### Phase 10: テスト大幅拡充 [部分完了]
- 新APIテスト15件追加: Duplicate(2), Undo(2), Export/Import(4), Search(2), Health(1), Logs(2), CSV Export(1), Help HTML(1)

### Phase 11: 運用支援 [完了]
- GET /api/execution-history/export でCSVダウンロード
- GET /api/health ヘルスチェック (アクション数/グループ数/実行状態)
- Logger.rotate_logs() で30日超のログファイル自動削除
