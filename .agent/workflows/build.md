---
description: EXEファイルをビルドする
---

# ビルドワークフロー

## 前提条件
- Python 3.10以上がインストール済み
- 仮想環境が有効化済み（`.\venv\Scripts\activate`）
- PyInstallerがインストール済み（`pip install pyinstaller`）

## 実行手順

1. プロジェクトルートに移動
```powershell
cd c:\Users\tyow\home\kai_system
```

2. テストを実行して問題がないことを確認
```powershell
python -m pytest tests/ -v
```

3. EXEをビルド
```powershell
pyinstaller --onefile --windowed --name "Co-worker_Bot" --clean src/main.py
```

4. 生成物を確認
```powershell
ls dist\
```

## 成果物の場所
`dist/Co-worker_Bot.exe`

## 配布パッケージ作成
5. 配布用フォルダを作成
```powershell
mkdir Co-worker_Bot_vX.X
cp dist\Co-worker_Bot.exe Co-worker_Bot_vX.X\
mkdir Co-worker_Bot_vX.X\settings
cp settings\production\Task_Master.xlsx Co-worker_Bot_vX.X\settings\
```

> **重要**: `settings\Task_Master.xlsx` は必ず同梱すること
