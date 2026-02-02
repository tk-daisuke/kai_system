---
description: テストを実行する
---

# テスト実行ワークフロー

## 前提条件
- Python 3.10以上がインストール済み
- 仮想環境が有効化済み（`.\venv\Scripts\activate`）
- 依存ライブラリがインストール済み（`pip install -r requirements.txt`）

## 実行手順

// turbo-all

1. プロジェクトルートに移動
```powershell
cd c:\Users\tyow\home\kai_system
```

2. pytest でテストを実行
```powershell
python -m pytest tests/ -v
```

3. カバレッジ付きで実行する場合（オプション）
```powershell
python -m pytest tests/ -v --cov=src --cov-report=term-missing
```

## 期待される結果
- すべてのテストが PASSED であること
- 新機能追加時は対応するテストを追加すること
