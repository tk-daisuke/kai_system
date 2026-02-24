# -*- coding: utf-8 -*-
"""
kai_system - メインウィンドウ
アクション駆動型GUIのメインウィンドウ
"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime
from pathlib import Path
from typing import Optional
import threading

from core.config_manager import ConfigManager
from core.action_manager import ActionManager
from core.group_manager import GroupManager
from gui.action_panel import ActionPanel
from gui.history_panel import HistoryPanel
from infra.logger import logger


class MainWindow:
    """kai_system メインウィンドウ"""

    WINDOW_TITLE = "kai_system"
    WINDOW_WIDTH = 600
    WINDOW_HEIGHT = 700

    def __init__(self, config_dir: Optional[Path] = None):
        self.root = tk.Tk()
        self.root.title(self.WINDOW_TITLE)
        self.root.geometry(f"{self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}")
        self.root.resizable(True, True)
        self.root.minsize(500, 500)

        # コンポーネント初期化
        self.config = ConfigManager(config_dir=config_dir)
        self.config.load()

        self.action_manager = ActionManager(self.config)
        self.action_manager.set_progress_callback(self._on_progress)

        self.group_manager = GroupManager(self.config)

        # 状態
        self.dark_mode = False
        self.running = False
        self.task_start_time: Optional[datetime] = None

        # スタイル設定
        self._setup_styles()

        # ウィンドウを中央配置
        self._center_window()

        # UI構築
        self._build_ui()

        # データ読み込み
        self._load_data()

    def _center_window(self):
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - self.WINDOW_WIDTH) // 2
        y = (sh - self.WINDOW_HEIGHT) // 2
        self.root.geometry(f"{self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}+{x}+{y}")

    def _setup_styles(self):
        style = ttk.Style()
        style.configure("Title.TLabel", font=("Yu Gothic UI", 14, "bold"), padding=10)
        style.configure("Status.TLabel", font=("Yu Gothic UI", 9), foreground="gray")
        style.configure(
            "GroupRun.TButton", font=("Yu Gothic UI", 10, "bold"), padding=6
        )
        style.configure("Action.TButton", font=("Yu Gothic UI", 10), padding=4)
        style.configure(
            "ActiveAction.TButton",
            font=("Yu Gothic UI", 10, "bold"),
            foreground="#0066cc",
        )
        style.configure("Current.TLabel", font=("Yu Gothic UI", 10, "bold"), foreground="#0066cc")

    def _build_ui(self):
        # メニューバー
        self._create_menu()

        # メインフレーム（スクロール対応）
        outer = ttk.Frame(self.root, padding=10)
        outer.pack(fill=tk.BOTH, expand=True)

        # タイトル
        ttk.Label(outer, text="どのアクションを実行しますか？", style="Title.TLabel").pack(
            pady=(0, 5)
        )

        # スクロール可能なアクションパネル
        canvas = tk.Canvas(outer, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        self.scroll_frame = ttk.Frame(canvas)

        self.scroll_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # マウスホイール対応
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        # macOS
        canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas = canvas

        # アクションパネル
        self.action_panel = ActionPanel(
            self.scroll_frame,
            on_action_click=self._on_action_click,
            on_group_click=self._on_group_click,
        )
        self.action_panel.pack(fill=tk.X, expand=True)

        # 現在の進捗
        progress_frame = ttk.LabelFrame(
            self.root, text="📍 現在の処理", padding=10
        )
        progress_frame.pack(fill=tk.X, padx=10, pady=(0, 5))

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            progress_frame, variable=self.progress_var, maximum=100, length=500
        )
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))

        info_frame = ttk.Frame(progress_frame)
        info_frame.pack(fill=tk.X)

        self.status_detail_var = tk.StringVar(value="待機中")
        ttk.Label(
            info_frame,
            textvariable=self.status_detail_var,
            style="Current.TLabel",
        ).pack(side=tk.LEFT)

        self.elapsed_var = tk.StringVar(value="")
        ttk.Label(
            info_frame,
            textvariable=self.elapsed_var,
            font=("Yu Gothic UI", 9),
            foreground="#666",
        ).pack(side=tk.RIGHT)

        # 中断ボタン
        self.stop_btn = ttk.Button(
            progress_frame,
            text="⏹ 中断",
            command=self._on_stop,
            state="disabled",
        )
        self.stop_btn.pack(fill=tk.X, pady=(5, 0))

        # 履歴パネル
        self.history = HistoryPanel(self.root)
        self.history.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 5))

        # ステータスバー
        self.status_var = tk.StringVar(value="準備完了")
        ttk.Label(
            self.root,
            textvariable=self.status_var,
            style="Status.TLabel",
        ).pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=3)

    def _create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # ファイルメニュー
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ファイル", menu=file_menu)
        file_menu.add_command(label="設定を再読み込み", command=self._reload_config)
        file_menu.add_separator()
        file_menu.add_command(label="終了", command=self.root.quit)

        # 表示メニュー
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="表示", menu=view_menu)
        self.dark_mode_var = tk.BooleanVar(value=False)
        view_menu.add_checkbutton(
            label="ダークモード",
            variable=self.dark_mode_var,
            command=self._toggle_dark_mode,
        )

    def _load_data(self):
        """設定を読み込んでUIに反映"""
        try:
            groups = self.group_manager.get_groups()
            grouped = self.group_manager.get_grouped_actions()
            ungrouped = self.config.get_ungrouped_actions()

            self.action_panel.render(groups, grouped, ungrouped)

            total_actions = len(self.config.get_all_actions())
            total_groups = len(groups)
            self.status_var.set(f"{total_groups} グループ / {total_actions} アクション")
            self.history.add(
                f"起動完了: {total_groups} グループ, {total_actions} アクションをロード",
                "info",
            )
            logger.info(f"GUI起動完了: {total_groups} グループ, {total_actions} アクション")

            # バリデーション
            issues = self.config.validate()
            if issues:
                self.history.add(f"設定警告: {len(issues)} 件のアクションに問題あり", "skip")

        except Exception as e:
            logger.error(f"データ読み込みエラー: {e}")
            self.history.add(f"エラー: {e}", "error")

    def _reload_config(self):
        """設定を再読み込み"""
        self.config.reload()
        self._load_data()
        self.history.add("設定を再読み込みしました", "info")

    def _on_action_click(self, action_id: str):
        """単一アクション実行"""
        if self.running:
            return

        action = self.config.get_action_by_id(action_id)
        if not action:
            return

        self._start_run()
        self.history.add(f"=== {action.name} 開始 ===", "info")

        def run():
            try:
                result = self.action_manager.run_action(action)
                self.root.after(0, lambda: self._on_action_done(action.name, result))
            except Exception as e:
                self.root.after(0, lambda: self._on_run_error(str(e)))

        threading.Thread(target=run, daemon=True).start()

    def _on_group_click(self, group_name: str):
        """グループ一括実行"""
        if self.running:
            return

        self._start_run()
        self.history.add(f"=== {group_name} グループ実行開始 ===", "info")

        def run():
            try:
                results = self.action_manager.run_group(group_name)
                self.root.after(0, lambda: self._on_group_done(group_name, results))
            except Exception as e:
                self.root.after(0, lambda: self._on_run_error(str(e)))

        threading.Thread(target=run, daemon=True).start()

    def _start_run(self):
        """実行開始の共通処理"""
        self.running = True
        self.task_start_time = datetime.now()
        self.progress_var.set(0)
        self.action_panel.set_enabled(False)
        self.stop_btn.configure(state="normal")
        self._update_elapsed()

    def _finish_run(self):
        """実行完了の共通処理"""
        self.running = False
        self.action_panel.set_enabled(True)
        self.stop_btn.configure(state="disabled")
        self.action_panel.highlight_action("")

    def _on_action_done(self, name, result):
        """単一アクション完了"""
        if result.success:
            self.history.add(f"{name}: 完了 ({result.elapsed_str})", "success")
        else:
            self.history.add(f"{name}: 失敗 - {result.error}", "error")

        self.status_detail_var.set("完了" if result.success else "エラー")
        self.progress_var.set(100)
        self._finish_run()

    def _on_group_done(self, group_name, results):
        """グループ完了"""
        elapsed = datetime.now() - self.task_start_time
        minutes = int(elapsed.total_seconds() // 60)
        seconds = int(elapsed.total_seconds() % 60)

        self.history.add(
            f"=== {group_name} 完了 ({minutes:02d}:{seconds:02d}) ===",
            "success" if results["failed"] == 0 else "error",
        )
        self.history.add(
            f"結果: 成功={results['success']}, 失敗={results['failed']}, "
            f"スキップ={results['skipped']}",
            "info",
        )

        self.status_detail_var.set("全アクション完了")
        self.progress_var.set(100)
        self._finish_run()

    def _on_run_error(self, error_msg):
        """実行エラー"""
        self.history.add(f"エラー: {error_msg}", "error")
        self.status_detail_var.set(f"エラー: {error_msg[:50]}")
        self._finish_run()

    def _on_stop(self):
        """中断"""
        self.action_manager.request_stop()
        self.history.add("中断をリクエストしました", "skip")

    def _on_progress(self, current: int, total: int, message: str):
        """進捗コールバック（アクションマネージャから呼ばれる）"""
        def update():
            if total > 0:
                pct = (current / total) * 100
                self.progress_var.set(pct)
            self.status_detail_var.set(f"▶ {message}")

            # 履歴に重要なメッセージを追加
            if any(k in message for k in ["完了", "エラー", "失敗", "スキップ"]):
                if "完了" in message:
                    self.history.add(message, "success")
                elif "エラー" in message or "失敗" in message:
                    self.history.add(message, "error")
                elif "スキップ" in message:
                    self.history.add(message, "skip")

        self.root.after(0, update)

    def _update_elapsed(self):
        """経過時間を更新"""
        if self.running and self.task_start_time:
            elapsed = datetime.now() - self.task_start_time
            minutes = int(elapsed.total_seconds() // 60)
            seconds = int(elapsed.total_seconds() % 60)
            self.elapsed_var.set(f"⏱ {minutes:02d}:{seconds:02d}")
            self.root.after(1000, self._update_elapsed)
        else:
            self.elapsed_var.set("")

    def _toggle_dark_mode(self):
        self.dark_mode = self.dark_mode_var.get()
        if self.dark_mode:
            self.root.configure(bg="#2b2b2b")
            style = ttk.Style()
            style.configure("TFrame", background="#2b2b2b")
            style.configure("TLabel", background="#2b2b2b", foreground="#fff")
            style.configure("TLabelframe", background="#2b2b2b", foreground="#fff")
            style.configure("TLabelframe.Label", background="#2b2b2b", foreground="#fff")
        else:
            self.root.configure(bg="#f0f0f0")
            style = ttk.Style()
            style.configure("TFrame", background="#f0f0f0")
            style.configure("TLabel", background="#f0f0f0", foreground="#000")
            style.configure("TLabelframe", background="#f0f0f0", foreground="#000")
            style.configure("TLabelframe.Label", background="#f0f0f0", foreground="#000")

        self.history.apply_dark_mode(self.dark_mode)

    def run(self):
        """GUIメインループを開始"""
        logger.info("kai_system GUI を起動します")
        self.root.mainloop()
