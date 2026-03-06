# kai_system プロジェクトルール

## 1. コーディング規約

### エンコーディング
- すべてのPythonファイルはUTF-8でエンコード
- ファイル冒頭に `# -*- coding: utf-8 -*-` を記載

### ドキュメント
- docstringは日本語で記載
- 複雑なロジックにはインラインコメントを追加

### 型ヒント
- 関数の引数・戻り値には型ヒントを付与
- `typing` モジュールを活用（`List`, `Dict`, `Optional` など）

### データ構造
- 設定データには `@dataclass` を使用
- 不変データには `frozen=True` を検討

---

## 2. モジュール構成

```
src/
├── app.py                     # エントリーポイント（Flask Web UI起動）
├── core/
│   ├── config_manager.py      # YAML設定管理 + webhook_url対応
│   ├── action_base.py         # プラグイン基底クラス (ActionBase)
│   ├── action_manager.py      # 実行管理 + プラグインレジストリ
│   ├── group_manager.py       # グループ管理
│   ├── param_schema.py        # パラメータスキーマ (show_when, key_value, form_fills)
│   └── template_engine.py     # URL日付テンプレート ({today}, {from_date_jp} 等)
├── actions/
│   ├── csv_download.py        # CSVダウンロード + Excel転記
│   ├── scraper.py             # スクレーピング (auto_table / css_selector / browser_csv)
│   ├── file_ops.py            # ファイル操作 (copy / move / archive)
│   └── shell_cmd.py           # シェルコマンド実行
├── web/
│   ├── server.py              # Flask Web サーバー + JSON API
│   ├── templates/
│   │   ├── index.html         # ダッシュボード (統計パネル + トースト通知)
│   │   └── editor.html        # 設定エディタ (動的フォーム + テンプレート管理)
│   └── static/style.css       # ダークテーマCSS (レスポンシブ対応)
└── infra/
    ├── logger.py              # クロスプラットフォームログ
    └── notifier.py            # デスクトップ通知 + Slack/Discord Webhook
```

### 責務の分離
- **app.py**: Flask起動とアクション/グループの初期化のみ
- **core/**: ビジネスロジック（UI非依存）
- **actions/**: ActionBase を継承したプラグイン群
- **web/**: Flask ルーティング + API + UI テンプレート
- **infra/**: ログ・通知などの横断的関心事

---

## 3. 設定ファイル

### パス
| ファイル | 用途 |
|---------|------|
| `config/actions.yaml` | アクション定義 |
| `config/groups.yaml` | グループ定義 |
| `config/templates/*.yaml` | スクレーピングテンプレート |
| `config/execution_history.json` | 実行履歴（自動生成、500件上限） |

### テンプレート変数
`template_engine.py` が展開する変数: `{today}`, `{from_date}`, `{to_date}`, `{today_jp}`, `{from_date_jp}`, `{to_date_jp}`, `{from_epoch}`, `{to_epoch}` 等

### バリデーション
- 各アクションの `validate()` メソッドで起動時に検証
- param_schema.py の `show_when` で条件付きフィールドの表示を制御

---

## 4. ログ

### 出力先
`logs/kai_YYYYMMDD.log`（日次ローテーション）

### 形式
```
[YYYY-MM-DD HH:MM:SS] [LEVEL] メッセージ
```

### レベル
| レベル | 用途 |
|--------|------|
| INFO | 通常の処理情報 |
| WARNING | 注意が必要な状況 |
| ERROR | エラー発生 |

---

## 5. テスト

### 配置
`tests/` ディレクトリ

### 命名規則
- ファイル: `test_*.py`
- クラス: `Test*`
- メソッド: `test_*`

### フレームワーク
pytest

### テスト構成
| ファイル | 対象 |
|---------|------|
| `test_scraper.py` | scraper バリデーション + モード別テスト |
| `test_file_ops.py` | copy/move/archive + バリデーション |
| `test_notifier.py` | Webhook ペイロード + 送信テスト |
| `test_server_api.py` | 全API + テンプレートCRUD + HTMLレンダリング |

---

## 6. 起動方法

```bash
python -m src.app
# Flask 開発サーバーが http://localhost:5000 で起動
```

---

## 7. Git運用

### コミットしないもの（.gitignoreに登録済み）
- `config/execution_history.json` - 実行履歴
- `logs/` - 実行ログ
- `__pycache__/` - Pythonキャッシュ
- `venv/` - 仮想環境

### ブランチ戦略
- `main`: 安定版
- 機能追加時: feature ブランチを作成

### コミットメッセージ
Conventional Commits 形式（例: `feat: テンプレート3パターン追加`）

---

## 8. タスク・計画管理

### 保存先
- 設計書・タスク管理ファイルは `tasks/` ディレクトリに保存する

### ファイル構成
```
tasks/
├── todo.md                # 進行中のタスクチェックリスト
├── implementation_plan.md # 設計・実装計画
└── walkthrough.md         # 完了報告・検証結果
```

### ルール
- 3ステップ以上の作業やアーキテクチャ決定を伴うタスクは、事前に `tasks/todo.md` に記述
- 設計変更時は `tasks/implementation_plan.md` を更新してレビューを依頼
- 完了時は `tasks/walkthrough.md` に結果を記録

---

## 9. 設計原則

- 外部依存は最小限にする（notifier は urllib のみ、requests は scraper 限定）
- テンプレートは YAML ファイル単位管理、ファイル名がID
- UIラベル・エラーメッセージは非エンジニアにもわかる平易な日本語を使う
- ダークテーマ + モバイルレスポンシブ対応
- alert() は使わず、トースト通知を使う
