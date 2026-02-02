# Co-worker Bot プロジェクトルール

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
├── main.py           # GUI/起動制御（エントリーポイント）
├── config_loader.py  # Task_Master.xlsx からの設定読み込み
├── logic_robot.py    # タスク実行ロジック（Excel操作、ダウンロード）
├── utils.py          # 共通関数、ログ出力
├── notifier.py       # Windows通知機能
└── holiday_checker.py # 曜日・祝日・日付条件チェック
```

### 責務の分離
- **main.py**: GUIとユーザーインタラクションのみ
- **logic_robot.py**: ビジネスロジックのみ（GUI非依存）
- **utils.py**: 汎用ユーティリティのみ

---

## 3. 設定ファイル

### パス
| 環境 | パス |
|------|------|
| 本番 | `settings/production/Task_Master.xlsx` |
| テスト | `settings/test/Task_Master.xlsx` |

### 列名マッピング
日本語と英語の両方の列名をサポート（`config_loader.py` で変換）

### バリデーション
起動時に設定ファイルのバリデーションを行い、問題があれば警告表示

---

## 4. ログ

### 出力先
`logs/log_YYYYMMDD.txt`（日次ローテーション）

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
| SUCCESS | タスク成功 |
| SKIP | タスクスキップ |

---

## 5. テスト

### 配置
`tests/` ディレクトリ

### 命名規則
- ファイル: `test_*.py`
- クラス: `Test*`
- メソッド: `test_*`

### フレームワーク
pytest または unittest

### カバレッジ対象（優先度順）
1. 時間判定ロジック（`is_within_session`）
2. 設定パース（`TaskConfig.from_row`）
3. 条件チェック（曜日・祝日・日付）

---

## 6. ビルド・配布

### ビルドコマンド
```powershell
pyinstaller --onefile --windowed --name "Co-worker_Bot" --clean src/main.py
```

### 配布パッケージ構成
```
Co-worker_Bot_vX.X/
├── Co-worker_Bot.exe      # 実行ファイル
└── settings/
    └── Task_Master.xlsx   # 設定ファイル（必須）
```

> **重要**: settings フォルダはexeと同階層に配置必須

---

## 7. Git運用

### コミットしないもの（.gitignoreに登録済み）
- `settings/production/` - 本番設定（機密）
- `logs/` - 実行ログ
- `__pycache__/` - Pythonキャッシュ
- `*.exe` - ビルド成果物
- `venv/` - 仮想環境

### ブランチ戦略
- `main`: 安定版
- 機能追加時: feature ブランチを作成

### コミットメッセージ
日本語で簡潔に記載（例: `タスク待機機能を追加`）
