# kai_system リアーキテクチャ

## Phase 1: コアリファクタリング
- [x] ディレクトリ構造の作成
- [x] `core/config_manager.py` - YAML設定読み込みシステム
- [x] `core/action_base.py` - アクション基底クラス
- [x] `core/action_manager.py` - アクション管理・実行（テンプレート展開統合）
- [x] `core/group_manager.py` - グループ管理
- [x] `core/template_engine.py` - URLテンプレート変数展開（{today}等）
- [x] `actions/csv_download.py` - CSVダウンロードプラグイン
- [x] `actions/scraper.py` - スクレーピングプラグイン（4モード: auto_table, css_selector, browser_session, browser_csv）
- [x] `actions/shell_cmd.py` - シェルコマンドプラグイン
- [x] `gui/main_window.py` - メインウィンドウ
- [x] `gui/action_panel.py` - アクションボタンパネル
- [x] `gui/history_panel.py` - 履歴パネル
- [x] `infra/logger.py` - ログモジュール
- [x] `infra/notifier.py` - 通知モジュール
- [x] `config/actions.yaml` & `config/groups.yaml` - サンプル設定
- [x] `src/app.py` - 新エントリーポイント
- [x] `requirements.txt` 更新
- [ ] 本番環境でのテスト（pip install pyyaml が必要）

## Phase 2: スクレーピング機能（後日）
- [ ] ScrapingAction のテスト・調整
- [ ] ブラウザセッション接続テスト
- [ ] 結果プレビュー

## Phase 3: 拡張機能（後日）
- [ ] FileOperationAction
- [ ] 通知統合
