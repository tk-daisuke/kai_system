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
