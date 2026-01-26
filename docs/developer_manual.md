# Co-worker Bot 開発・配布マニュアル

## 1. 開発環境の構築 (Python導入済み前提)

### 1-1. 仮想環境 (venv) の作成と有効化
プロジェクトのルートディレクトリで以下のコマンドを実行し、専用の仮想環境を作成します。

```powershell
# 仮想環境の作成
python -m venv venv

# 仮想環境の有効化 (Windows)
.\venv\Scripts\activate
```
※ 左端に `(venv)` と表示されれば成功です。

### 1-2. 依存ライブラリのインストール
`requirements.txt` から必要なライブラリを一括インストールします。

```powershell
pip install -r requirements.txt
```

---
 
 ## 2. 設定ファイルの構造 (Task_Master.xlsx)
 
 設定ファイルは日本語・英語の両方の列名をサポートしています（`src/config_loader.py` でマッピング）。
 
 ### 主な設定項目
 - **Active / 有効**: タスクの有効化フラグ
 - **Group / グループ**: 実行グループ名
 - **StartTime / 開始時刻**: 実行開始時間
 - **FilePath / ファイルパス**: 対象Excelファイルのパス
 - **TargetSheet / CSV転記シート**: データ転記先シート名
 - **MacroName / マクロ名**: 実行するVBAマクロ名 (New!)
 
 ※ 詳細は `SETTINGS_GUIDE.md` または `docs/user_manual.md` を参照してください。
 
 ---
 
 ## 3. アプリケーションの実行

### 3-1. 本番設定での実行
```powershell
python src/main.py
```
※ `settings/production/Task_Master.xlsx` が読み込まれます。

### 2-2. テスト設定での実行
```powershell
python src/main.py --env=test
```
※ `settings/test/Task_Master.xlsx` が読み込まれます。

---

## 3. Exe化 (配布用ファイルの作成)

PyInstallerを使用して単一の実行ファイル (`.exe`) を生成します。

### 3-1. ビルドコマンド
```powershell
pyinstaller --onefile --windowed --name "Co-worker_Bot" --clean src/main.py
```

*   `--onefile`: 1つのexeファイルにまとめる
*   `--windowed`: 実行時に黒いコンソール画面を出さない（GUIアプリ用）
*   `--name`: 生成されるファイル名
*   `--clean`: キャッシュをクリアしてビルド

### 3-2. 生成物の場所
ビルドが成功すると、`dist` フォルダに `Co-worker_Bot.exe` が生成されます。

---

## 4. 配布パッケージの作成

配布する際は、以下の構成でフォルダを作成し、ユーザーに渡します。

```text
Co-worker_Bot_v1.0/
│
├── Co-worker_Bot.exe      # 生成された実行ファイル
│
├── settings/              # 設定フォルダ (※必須)
│   └── Task_Master.xlsx   # マスタファイル (production用をコピー)
│
└── manual.pdf (任意)       # マニュアルなど
```

> [!IMPORTANT]
> `settings/Task_Master.xlsx` はプログラム実行に必要な外部ファイルです。Exeファイル内に含まれないため、**必ずExeと同じ階層の `settings` フォルダに入れて配布** してください。
