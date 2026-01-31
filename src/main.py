# -*- coding: utf-8 -*-
"""
Co-worker Bot - メインエントリーポイント
TkinterによるGUI制御とタスクオーケストレーション
"""

import sys
import os
import tkinter as tk
from tkinter import ttk, scrolledtext
from pathlib import Path
from typing import List
from datetime import datetime
import webbrowser

# srcフォルダをパスに追加
if getattr(sys, 'frozen', False):
    # PyInstallerでexe化された場合
    base_path = Path(sys.executable).parent
else:
    base_path = Path(__file__).parent.parent
    sys.path.insert(0, str(Path(__file__).parent))

from config_loader import ConfigLoader, TaskConfig
from logic_robot import TaskRunner
from utils import logger, show_info, show_error, show_warning
from notifier import notify_task_complete


class CoworkerBotGUI:
    """Co-worker Bot のメインGUIクラス"""
    
    WINDOW_TITLE = "Co-worker Bot"
    WINDOW_WIDTH = 550
    WINDOW_HEIGHT = 650
    
    def __init__(self, env: str = "production"):
        self.env = env
        self.root = tk.Tk()
        self.root.title(f"{self.WINDOW_TITLE} ({self.env})")
        self.root.geometry(f"{self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}")
        self.root.resizable(False, False)
        
        # 中央に配置
        self._center_window()
        
        # スタイル設定
        self._setup_styles()
        
        # コンポーネント初期化
        self.config_loader = ConfigLoader(env=self.env)
        self.task_runner = TaskRunner()
        self.task_runner.set_progress_callback(self._on_progress_update)
        self.groups: List[str] = []
        self.all_tasks: List[TaskConfig] = []  # 全タスクリスト（ソート済み）
        
        # 進捗履歴
        self.history_entries: List[dict] = []
        self.current_file_name: str = ""
        self.task_start_time: datetime = None
        self.dark_mode: bool = False  # ダークモードフラグ
        
        # GUI構築
        self._build_ui()
        
        # 設定ファイルの値を更新（TODAY関数などを最新化）
        self.config_loader.refresh_master_file()

        # セレクター読み込み
        self._load_selectors()
        
        # 設定バリデーション
        self._validate_settings()

        # 起動時のチェック（ブラウザ起動・警告）
        self.root.after(500, self._startup_check)
    
    def _startup_check(self) -> None:
        """起動時の警告とブラウザ起動を行う"""
        # ブラウザを起動（ログインしてない場合のため）
        # about:blank だと反応しない場合があるため、Googleを開く
        target_url = "https://www.google.com"
        browser_opened = False
        
        try:
            # 方法1: os.startfile (Windows専用、最も確実)
            if hasattr(os, 'startfile'):
                os.startfile(target_url)
                browser_opened = True
            else:
                # 方法2: webbrowserモジュール
                import webbrowser
                webbrowser.open(target_url)
                browser_opened = True
        except Exception as e:
            logger.error(f"ブラウザ起動失敗: {e}")
            # エラーでもポップアップは出す
            
        # 警告ダイアログを表示
        message = (
            "【実行前の重要なお知らせ】\n\n"
            "1. 業務サイトへのログイン\n"
            "   ブラウザが起動します。必要なサイトにログイン済みか確認してください。\n"
            "   （ログインしていない場合、誤ったデータがダウンロードされる可能性があります）\n\n"
            "2. クリップボードの使用禁止\n"
            "   本ツールはコピー＆ペースト機能を使用します。\n"
            "   実行中は他の作業で「コピー」や「貼り付け」を行わないでください。"
        )
        show_warning("実行前の確認", message)
    
    def _center_window(self) -> None:
        """ウィンドウを画面中央に配置"""
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - self.WINDOW_WIDTH) // 2
        y = (screen_height - self.WINDOW_HEIGHT) // 2
        self.root.geometry(f"{self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}+{x}+{y}")
    
    def _setup_styles(self) -> None:
        """ttk スタイルを設定"""
        style = ttk.Style()
        style.configure(
            "Group.TButton",
            font=("Yu Gothic UI", 11),
            padding=8
        )
        style.configure(
            "Title.TLabel",
            font=("Yu Gothic UI", 14, "bold"),
            padding=10
        )
        style.configure(
            "Progress.TLabel",
            font=("Yu Gothic UI", 10),
            padding=3
        )
        style.configure(
            "Current.TLabel",
            font=("Yu Gothic UI", 10, "bold"),
            foreground="#0066cc"
        )
    
    def _create_menu_bar(self) -> None:
        """メニューバーを作成"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 表示メニュー
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="表示", menu=view_menu)
        
        self.dark_mode_var = tk.BooleanVar(value=False)
        view_menu.add_checkbutton(
            label="ダークモード",
            variable=self.dark_mode_var,
            command=self._toggle_dark_mode
        )
    
    def _toggle_dark_mode(self) -> None:
        """ダークモードの切り替え"""
        self.dark_mode = self.dark_mode_var.get()
        
        if self.dark_mode:
            # ダークテーマ
            self.root.configure(bg="#2b2b2b")
            style = ttk.Style()
            style.configure("TFrame", background="#2b2b2b")
            style.configure("TLabel", background="#2b2b2b", foreground="#ffffff")
            style.configure("TLabelframe", background="#2b2b2b", foreground="#ffffff")
            style.configure("TLabelframe.Label", background="#2b2b2b", foreground="#ffffff")
            style.configure("TButton", background="#404040")
            if hasattr(self, 'history_text'):
                self.history_text.configure(bg="#1e1e1e", fg="#d4d4d4")
        else:
            # ライトテーマ
            self.root.configure(bg="#f0f0f0")
            style = ttk.Style()
            style.configure("TFrame", background="#f0f0f0")
            style.configure("TLabel", background="#f0f0f0", foreground="#000000")
            style.configure("TLabelframe", background="#f0f0f0", foreground="#000000")
            style.configure("TLabelframe.Label", background="#f0f0f0", foreground="#000000")
            style.configure("TButton", background="#e1e1e1")
            if hasattr(self, 'history_text'):
                self.history_text.configure(bg="#f8f8f8", fg="#000000")
    
    def _build_ui(self) -> None:
        """UIを構築"""
        # メニューバー
        self._create_menu_bar()
        
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        self.main_frame = main_frame  # 参照保存
        
        # タイトル
        title_label = ttk.Label(
            main_frame,
            text="どの業務を実行しますか？",
            style="Title.TLabel"
        )
        title_label.pack(pady=(0, 10))
        
        # === グループボタンコンテナ ===
        self.button_frame = ttk.Frame(main_frame)
        self.button_frame.pack(fill=tk.X, pady=(0, 5))
        
        # === やり直し用: StartTime選択エリア ===
        retry_frame = ttk.LabelFrame(main_frame, text="🔄 やり直し（StartTimeから選択）", padding=8)
        retry_frame.pack(fill=tk.X, pady=(0, 5))
        
        retry_inner = ttk.Frame(retry_frame)
        retry_inner.pack(fill=tk.X)
        
        # タスク選択ドロップダウン
        ttk.Label(retry_inner, text="指定タスク:", font=("Yu Gothic UI", 10)).pack(side=tk.LEFT, padx=(0, 5))
        
        self.task_selector_var = tk.StringVar()
        self.task_selector = ttk.Combobox(
            retry_inner,
            textvariable=self.task_selector_var,
            state="readonly",
            width=40,
            font=("Yu Gothic UI", 9)
        )
        self.task_selector.pack(side=tk.LEFT, padx=(0, 10))
        
        # 「ここから実行」ボタン
        self.retry_btn = ttk.Button(
            retry_inner,
            text="ここから実行 ▶",
            command=self._on_retry_from_here
        )
        self.retry_btn.pack(side=tk.LEFT, padx=5)
        
        # 「このタスクのみ」ボタン
        self.only_btn = ttk.Button(
            retry_inner,
            text="このタスクのみ",
            command=self._on_retry_only
        )
        self.only_btn.pack(side=tk.LEFT, padx=5)
        
        # === 現在の進捗エリア ===
        current_frame = ttk.LabelFrame(main_frame, text="📍 現在の処理", padding=10)
        current_frame.pack(fill=tk.X, pady=(5, 5))
        
        # プログレスバー
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            current_frame,
            variable=self.progress_var,
            maximum=100,
            mode='determinate',
            length=480
        )
        self.progress_bar.pack(fill=tk.X, pady=(0, 8))
        
        # 現在のタスク情報
        current_info_frame = ttk.Frame(current_frame)
        current_info_frame.pack(fill=tk.X)
        
        # 左側: タスクカウント & ファイル名
        left_frame = ttk.Frame(current_info_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 一時停止ボタン（カウントの横に配置）
        self.pause_btn = ttk.Button(
            left_frame,
            text="⏸ 一時停止",
            width=10,
            state="disabled",
            command=self._on_pause_clicked
        )
        self.pause_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.progress_count_var = tk.StringVar(value="待機中")
        progress_count_label = ttk.Label(
            left_frame,
            textvariable=self.progress_count_var,
            style="Current.TLabel"
        )
        progress_count_label.pack(anchor=tk.W)
        
        self.current_file_var = tk.StringVar(value="")
        current_file_label = ttk.Label(
            left_frame,
            textvariable=self.current_file_var,
            font=("Yu Gothic UI", 9),
            foreground="gray"
        )
        current_file_label.pack(anchor=tk.W)
        
        # 右側: 経過時間
        right_frame = ttk.Frame(current_info_frame)
        right_frame.pack(side=tk.RIGHT)
        
        self.elapsed_time_var = tk.StringVar(value="")
        elapsed_time_label = ttk.Label(
            right_frame,
            textvariable=self.elapsed_time_var,
            font=("Yu Gothic UI", 9),
            foreground="#666666"
        )
        elapsed_time_label.pack(anchor=tk.E)
        
        # 詳細ステータス
        self.detail_status_var = tk.StringVar(value="グループを選択してください")
        detail_status_label = ttk.Label(
            current_frame,
            textvariable=self.detail_status_var,
            style="Progress.TLabel",
            foreground="#333333"
        )
        detail_status_label.pack(anchor=tk.W, pady=(5, 0))
        
        # === 処理履歴エリア ===
        history_frame = ttk.LabelFrame(main_frame, text="📋 処理履歴", padding=10)
        history_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 5))
        
        # スクロール可能なテキストエリア
        self.history_text = scrolledtext.ScrolledText(
            history_frame,
            height=10,
            font=("Consolas", 9),
            wrap=tk.WORD,
            state=tk.DISABLED,
            background="#f8f8f8"
        )
        self.history_text.pack(fill=tk.BOTH, expand=True)
        
        # タグ設定（色分け用）
        self.history_text.tag_configure("timestamp", foreground="#888888")
        self.history_text.tag_configure("success", foreground="#28a745")
        self.history_text.tag_configure("error", foreground="#dc3545")
        self.history_text.tag_configure("info", foreground="#0066cc")
        self.history_text.tag_configure("skip", foreground="#ffc107")
        
        # フィルターボタンフレーム
        filter_frame = ttk.Frame(history_frame)
        filter_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(filter_frame, text="フィルタ:", font=("Yu Gothic UI", 9)).pack(side=tk.LEFT)
        
        self.filter_var = tk.StringVar(value="all")
        filters = [("全て", "all"), ("成功", "success"), ("失敗", "error"), ("スキップ", "skip")]
        for text, value in filters:
            rb = ttk.Radiobutton(filter_frame, text=text, value=value, 
                                 variable=self.filter_var, command=self._apply_filter)
            rb.pack(side=tk.LEFT, padx=3)
        
        # クリアボタン
        clear_btn = ttk.Button(
            filter_frame,
            text="履歴クリア",
            command=self._clear_history
        )
        clear_btn.pack(side=tk.RIGHT)
        
        # ステータスバー
        self.status_var = tk.StringVar(value="準備完了")
        status_label = ttk.Label(
            main_frame,
            textvariable=self.status_var,
            font=("Yu Gothic UI", 9),
            foreground="gray"
        )
        status_label.pack(side=tk.BOTTOM, pady=3)
    
    def _add_history(self, message: str, level: str = "info") -> None:
        """履歴にエントリを追加"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # 履歴エントリを保存（フィルタ用）
        self.history_entries.append({
            "timestamp": timestamp,
            "message": message,
            "level": level
        })
        
        # 現在のフィルタに合致するか確認
        current_filter = getattr(self, 'filter_var', None)
        if current_filter and current_filter.get() != "all" and current_filter.get() != level:
            return  # フィルタに合致しない場合は表示しない
        
        self.history_text.configure(state=tk.NORMAL)
        self.history_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
        self.history_text.insert(tk.END, f"{message}\n", level)
        self.history_text.see(tk.END)  # 最下部にスクロール
        self.history_text.configure(state=tk.DISABLED)
        
        self.root.update()
    
    def _apply_filter(self) -> None:
        """フィルタを適用して履歴を再表示"""
        selected = self.filter_var.get()
        
        self.history_text.configure(state=tk.NORMAL)
        self.history_text.delete(1.0, tk.END)
        
        for entry in self.history_entries:
            if selected == "all" or entry["level"] == selected:
                self.history_text.insert(tk.END, f"[{entry['timestamp']}] ", "timestamp")
                self.history_text.insert(tk.END, f"{entry['message']}\n", entry["level"])
        
        self.history_text.see(tk.END)
        self.history_text.configure(state=tk.DISABLED)
    
    def _clear_history(self) -> None:
        """履歴をクリア"""
        self.history_entries = []  # 保存された履歴もクリア
        self.history_text.configure(state=tk.NORMAL)
        self.history_text.delete(1.0, tk.END)
        self.history_text.configure(state=tk.DISABLED)
    
    def _on_progress_update(self, current: int, total: int, message: str) -> None:
        """進捗コールバック - TaskRunnerから呼ばれる"""
        now = datetime.now()
        
        if total > 0:
            progress_percent = (current / total) * 100
            self.progress_var.set(progress_percent)
            self.progress_count_var.set(f"タスク {current} / {total}")
        else:
            self.progress_var.set(0)
            self.progress_count_var.set("準備中...")
        
        # ファイル名を抽出（メッセージから）
        if ":" in message:
            parts = message.split(":", 1)
            action = parts[0].strip()
            target = parts[1].strip() if len(parts) > 1 else ""
            self.current_file_var.set(f"📁 {target}")
        else:
            self.current_file_var.set("")
        
        # 経過時間
        if self.task_start_time:
            elapsed = now - self.task_start_time
            minutes = int(elapsed.total_seconds() // 60)
            seconds = int(elapsed.total_seconds() % 60)
            self.elapsed_time_var.set(f"⏱ {minutes:02d}:{seconds:02d}")
        
        self.detail_status_var.set(f"▶ {message}")
        
        # 履歴に追加（重要なステップのみ）
        if any(keyword in message for keyword in ["開始", "完了", "スキップ", "エラー", "失敗"]):
            if "完了" in message:
                self._add_history(message, "success")
            elif "エラー" in message or "失敗" in message:
                self._add_history(message, "error")
            elif "スキップ" in message:
                self._add_history(message, "skip")
            else:
                self._add_history(message, "info")
        
        self.root.update()
    
    def _reset_progress(self) -> None:
        """進捗表示をリセット"""
        self.progress_var.set(0)
        self.progress_count_var.set("待機中")
        self.current_file_var.set("")
        self.elapsed_time_var.set("")
        self.detail_status_var.set("処理開始...")
        self.task_start_time = datetime.now()
    
    def _load_selectors(self) -> None:
        """グループボタンとStartTimeセレクターを読み込み"""
        try:
            self.groups = self.config_loader.get_groups()
            self.all_tasks = self.config_loader.get_all_tasks_sorted()
            
            if not self.groups:
                self.status_var.set("⚠ グループが見つかりません")
                show_warning(
                    self.WINDOW_TITLE,
                    "タスクマスタファイルにアクティブなグループがありません。\n"
                    "settings/Task_Master.xlsx を確認してください。"
                )
                return
            
            # グループごとにボタンを作成（横並び）
            for i, group_name in enumerate(self.groups):
                btn = ttk.Button(
                    self.button_frame,
                    text=group_name,
                    style="Group.TButton",
                    command=lambda g=group_name: self._on_group_selected(g)
                )
                btn.pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
                
                # 右クリックメニューをバインド
                btn.bind("<Button-3>", lambda e, g=group_name: self._show_group_context_menu(e, g))
            
            # タスクコンボボックスに値を設定
            task_labels = [
                f"[{t.group}] {t.start_time_str()} - {Path(t.file_path).name}"
                for t in self.all_tasks
            ]
            self.task_selector['values'] = task_labels
            if task_labels:
                self.task_selector.current(0)
            
            self.status_var.set(f"{len(self.groups)} グループ / {len(self.all_tasks)} タスク")
            self._add_history(f"起動完了: {len(self.groups)} グループ, {len(self.all_tasks)} タスクをロード", "info")
            logger.info(f"GUI起動完了: {len(self.groups)} グループ, {len(self.all_tasks)} Tasks")
            
        except Exception as e:
            logger.error(f"データ読み込みエラー: {e}")
            show_error(self.WINDOW_TITLE, f"データの読み込みに失敗しました:\n{e}")
    
    def _validate_settings(self) -> None:
        """設定ファイルのバリデーションを行い、問題があれば警告表示"""
        try:
            issues = self.config_loader.validate_tasks()
            
            if issues:
                # 最大5件まで表示
                msg_lines = ["以下のタスクに設定の問題があります:\n"]
                for i, item in enumerate(issues[:5]):
                    task = item["task"]
                    task_name = Path(task.file_path).name if task.file_path else "(パスなし)"
                    msg_lines.append(f"• [{task.group}] {task_name}")
                    for issue in item["issues"][:2]:
                        msg_lines.append(f"    - {issue}")
                
                if len(issues) > 5:
                    msg_lines.append(f"\n...他 {len(issues) - 5} 件")
                
                msg_lines.append("\n\n処理は続行できますが、該当タスクでエラーになる可能性があります。")
                
                show_warning("設定チェック", "\n".join(msg_lines))
                self._add_history(f"設定警告: {len(issues)} 件のタスクに問題あり", "skip")
                
        except Exception as e:
            logger.warning(f"設定バリデーション中にエラー: {e}")
    
    def _show_group_context_menu(self, event, group_name: str) -> None:
        """グループボタンの右クリックメニューを表示"""
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(
            label="▶ 通常実行",
            command=lambda: self._on_group_selected(group_name)
        )
        menu.add_command(
            label="⚡ 強制実行（時間チェック無視）",
            command=lambda: self._on_group_force_execute(group_name)
        )
        menu.add_separator()
        menu.add_command(
            label="📂 設定ファイルを開く",
            command=lambda: self._open_master_file()
        )
        menu.tk_popup(event.x_root, event.y_root)
    
    def _on_group_force_execute(self, group_name: str) -> None:
        """グループを強制実行（時間チェック無視）"""
        logger.info(f"強制実行: {group_name}")
        self.status_var.set(f"強制実行中: {group_name}...")
        self._reset_progress()
        self._add_history(f"=== {group_name} 強制実行 ===", "info")
        self.task_start_time = datetime.now()
        
        self.stop_btn.configure(state="normal")
        self.pause_btn.configure(state="normal", text="⏸ 一時停止")
        
        try:
            tasks = self.config_loader.get_tasks_by_group_optimized(group_name)
            if not tasks:
                show_warning(self.WINDOW_TITLE, f"'{group_name}' にはアクティブなタスクがありません。")
                return
            
            # force=True で実行
            results = self.task_runner.run_group(tasks, force=True)
            self._show_results(group_name, results)
            
        except Exception as e:
            logger.error(f"強制実行エラー: {e}")
            show_error(self.WINDOW_TITLE, f"エラー: {e}")
        finally:
            self.stop_btn.configure(state="disabled")
            self.pause_btn.configure(state="disabled")
    
    def _open_master_file(self) -> None:
        """設定ファイルを開く"""
        import os
        try:
            os.startfile(self.config_loader.master_path)
        except Exception as e:
            logger.error(f"ファイルオープンエラー: {e}")
    
    def _on_group_selected(self, group_name: str) -> None:
        """グループボタンがクリックされた時の処理"""
        logger.info(f"グループ選択: {group_name}")
        self.status_var.set(f"実行中: {group_name}...")
        self._reset_progress()
        self._add_history(f"=== {group_name} 開始 ===", "info")
        self.root.update()
        
        # ボタンを無効化
        self._set_buttons_enabled(False)
        self.pause_btn.configure(state="normal", text="⏸ 一時停止")
        
        try:
            # タスク取得（ファイルパスで最適化）
            tasks = self.config_loader.get_tasks_by_group_optimized(group_name)
            
            if not tasks:
                show_warning(
                    self.WINDOW_TITLE,
                    f"'{group_name}' にはアクティブなタスクがありません。"
                )
                self._add_history(f"{group_name}: タスクなし", "skip")
                return
            
            self._add_history(f"{len(tasks)} 件のタスクを実行します", "info")
            
            # タスク実行
            results = self.task_runner.run_group(tasks)
            
            # 経過時間計算
            elapsed = datetime.now() - self.task_start_time
            minutes = int(elapsed.total_seconds() // 60)
            seconds = int(elapsed.total_seconds() % 60)
            
            # 結果を履歴に追加
            self._add_history(
                f"=== {group_name} 完了 (所要時間: {minutes:02d}:{seconds:02d}) ===",
                "success" if results['failed'] == 0 else "error"
            )
            self._add_history(
                f"結果: 成功={results['success']}, 失敗={results['failed']}, スキップ={results['skipped']}",
                "info"
            )
            
            # 結果表示
            message = (
                f"【{group_name}】の処理が完了しました。\n\n"
                f"✓ 成功: {results['success']} 件\n"
                f"✗ 失敗: {results['failed']} 件\n"
                f"⊘ スキップ: {results['skipped']} 件\n\n"
                f"⏱ 所要時間: {minutes}分{seconds}秒"
            )
            show_info(self.WINDOW_TITLE, message)
            
            # トースト通知
            notify_task_complete(
                results['success'], results['failed'], results['skipped'],
                f"{minutes}分{seconds}秒"
            )
            
            self.status_var.set("完了しました")
            self.detail_status_var.set("✓ 全タスク完了")
            self.progress_count_var.set("完了")
            
        except Exception as e:
            logger.error(f"タスク実行エラー: {e}")
            self._add_history(f"エラー: {str(e)}", "error")
            show_error(self.WINDOW_TITLE, f"エラーが発生しました:\n{e}")
            self.status_var.set("エラーが発生しました")
            self.detail_status_var.set(f"✗ エラー: {str(e)[:50]}")
        
        finally:
            # ボタンを有効化
            self._set_buttons_enabled(True)
            self.pause_btn.configure(state="disabled", text="⏸ 一時停止")
    
    def _set_buttons_enabled(self, enabled: bool) -> None:
        """全ボタンの有効/無効を切り替え"""
        state = "normal" if enabled else "disabled"
        for widget in self.button_frame.winfo_children():
            widget.configure(state=state)
        self.retry_btn.configure(state=state)
        self.only_btn.configure(state=state)
        self.task_selector.configure(state="readonly" if enabled else "disabled")
    
    def _on_retry_from_here(self) -> None:
        """『ここから実行』ボタン - 選択したタスク以降を実行"""
        idx = self.task_selector.current()
        if idx < 0:
            show_warning(self.WINDOW_TITLE, "タスクを選択してください。")
            return
            
        selected_task = self.all_tasks[idx]
        task_label = f"[{selected_task.group}] {selected_task.start_time_str()} - {Path(selected_task.file_path).name}"
        
        logger.info(f"タスク選択（以降）: {task_label}")
        self.status_var.set(f"実行中: {task_label} 以降...")
        self._reset_progress()
        self._add_history(f"=== {task_label} 以降 のタスクを開始 ===", "info")
        self.root.update()
        
        self._set_buttons_enabled(False)
        self.pause_btn.configure(state="normal", text="⏸ 一時停止")
        
        try:
            # 選択位置以降の全タスクを取得し、同じグループのみに絞る
            selected_group = selected_task.group
            tasks = [t for t in self.all_tasks[idx:] if t.group == selected_group]
            
            self._add_history(f"{len(tasks)} 件のタスクを実行します (グループ: {selected_group})", "info")
            
            # タスク実行（強制実行モード）
            results = self.task_runner.run_group(tasks, force=True)
            
            # 結果表示
            self._show_results(f"{selected_group} の {task_label} 以降", results)
            
        except Exception as e:
            logger.error(f"タスク実行エラー: {e}")
            self._add_history(f"エラー: {str(e)}", "error")
            show_error(self.WINDOW_TITLE, f"エラーが発生しました:\n{e}")
            self.status_var.set("エラーが発生しました")
        
        finally:
            self._set_buttons_enabled(True)
            self.pause_btn.configure(state="disabled")
    
    def _on_retry_only(self) -> None:
        """『このタスクのみ』ボタン - 選択したタスク単体を実行"""
        idx = self.task_selector.current()
        if idx < 0:
            show_warning(self.WINDOW_TITLE, "タスクを選択してください。")
            return
            
        selected_task = self.all_tasks[idx]
        task_label = f"[{selected_task.group}] {selected_task.start_time_str()} - {Path(selected_task.file_path).name}"
        
        logger.info(f"タスク選択（のみ）: {task_label}")
        self.status_var.set(f"実行中: {task_label} のみ...")
        self._reset_progress()
        self._add_history(f"=== {task_label} を開始 ===", "info")
        self.root.update()
        
        self._set_buttons_enabled(False)
        self.pause_btn.configure(state="normal", text="⏸ 一時停止")
        
        try:
            # 選択されたタスク単体
            tasks = [selected_task]
            
            self._add_history(f"単独タスクを実行します", "info")
            
            # タスク実行（強制実行モード）
            results = self.task_runner.run_group(tasks, force=True)
            
            # 結果表示
            self._show_results(f"{task_label}", results)
            
        except Exception as e:
            logger.error(f"タスク実行エラー: {e}")
            self._add_history(f"エラー: {str(e)}", "error")
            show_error(self.WINDOW_TITLE, f"エラーが発生しました:\n{e}")
            self.status_var.set("エラーが発生しました")
        
        finally:
            self._set_buttons_enabled(True)
            self.pause_btn.configure(state="disabled")
    
    def _show_results(self, label: str, results: dict) -> None:
        """タスク実行結果を表示"""
        elapsed = datetime.now() - self.task_start_time
        minutes = int(elapsed.total_seconds() // 60)
        seconds = int(elapsed.total_seconds() % 60)
        
        self._add_history(
            f"=== {label} 完了 (所要時間: {minutes:02d}:{seconds:02d}) ===",
            "success" if results['failed'] == 0 else "error"
        )
        self._add_history(
            f"結果: 成功={results['success']}, 失敗={results['failed']}, スキップ={results['skipped']}",
            "info"
        )
        
        message = (
            f"【{label}】の処理が完了しました。\n\n"
            f"✓ 成功: {results['success']} 件\n"
            f"✗ 失敗: {results['failed']} 件\n"
            f"⊘ スキップ: {results['skipped']} 件\n\n"
            f"⏱ 所要時間: {minutes}分{seconds}秒"
        )
        show_info(self.WINDOW_TITLE, message)
        
        # トースト通知
        notify_task_complete(
            results['success'], results['failed'], results['skipped'],
            f"{minutes}分{seconds}秒"
        )
        
        self.status_var.set("完了しました")
        self.detail_status_var.set("✓ 全タスク完了")
        self.progress_count_var.set("完了")
    
    def _on_pause_clicked(self) -> None:
        """『一時停止/再開』ボタンクリック時の処理"""
        # 現在の状態をチェック（ボタンのテキストで判断）
        current_text = self.pause_btn.cget("text")
        
        if "一時停止" in current_text:
            # 一時停止リクエスト
            self.task_runner.pause()
            self.pause_btn.configure(text="▶ 再開")
            self.detail_status_var.set("⏸ 一時停止リクエスト中... (完了後に停止します)")
        else:
            # 再開リクエスト
            self.task_runner.resume()
            self.pause_btn.configure(text="⏸ 一時停止")
            self.detail_status_var.set("▶ 再開します...")
    
    def run(self) -> None:
        """GUIメインループを開始"""
        logger.info("Co-worker Bot を起動しました")
        self.root.mainloop()
        logger.info("Co-worker Bot を終了しました")


def main():
    """エントリーポイント"""
    import argparse
    parser = argparse.ArgumentParser(description="Co-worker Bot")
    parser.add_argument("--env", choices=["production", "test"], default="production", help="実行環境 (production/test)")
    args = parser.parse_args()
    
    try:
        app = CoworkerBotGUI(env=args.env)
        app.run()
    except Exception as e:
        logger.error(f"致命的なエラー: {e}")
        show_error("Co-worker Bot", f"致命的なエラーが発生しました:\n{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()



