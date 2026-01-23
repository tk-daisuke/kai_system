# -*- coding: utf-8 -*-
"""
Co-worker Bot - メインエントリーポイント
TkinterによるGUI制御とタスクオーケストレーション
"""

import sys
import tkinter as tk
from tkinter import ttk, scrolledtext
from pathlib import Path
from typing import List
from datetime import datetime

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


class CoworkerBotGUI:
    """Co-worker Bot のメインGUIクラス"""
    
    WINDOW_TITLE = "Co-worker Bot"
    WINDOW_WIDTH = 550
    WINDOW_HEIGHT = 650
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(self.WINDOW_TITLE)
        self.root.geometry(f"{self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}")
        self.root.resizable(False, False)
        
        # 中央に配置
        self._center_window()
        
        # スタイル設定
        self._setup_styles()
        
        # コンポーネント初期化
        self.config_loader = ConfigLoader()
        self.task_runner = TaskRunner()
        self.task_runner.set_progress_callback(self._on_progress_update)
        self.groups: List[str] = []
        self.start_times: List = []  # StartTime一覧
        
        # 進捗履歴
        self.history_entries: List[dict] = []
        self.current_file_name: str = ""
        self.task_start_time: datetime = None
        
        # GUI構築
        self._build_ui()
        
        # セレクター読み込み
        self._load_selectors()
    
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
    
    def _build_ui(self) -> None:
        """UIを構築"""
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
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
        
        # StartTimeドロップダウン
        ttk.Label(retry_inner, text="開始時刻:", font=("Yu Gothic UI", 10)).pack(side=tk.LEFT, padx=(0, 5))
        
        self.start_time_var = tk.StringVar()
        self.start_time_combo = ttk.Combobox(
            retry_inner,
            textvariable=self.start_time_var,
            state="readonly",
            width=10,
            font=("Yu Gothic UI", 10)
        )
        self.start_time_combo.pack(side=tk.LEFT, padx=(0, 10))
        
        # 「ここから実行」ボタン
        self.retry_btn = ttk.Button(
            retry_inner,
            text="ここから実行 ▶",
            command=self._on_start_time_selected
        )
        self.retry_btn.pack(side=tk.LEFT, padx=5)
        
        # 「この時間のみ」ボタン
        self.only_btn = ttk.Button(
            retry_inner,
            text="この時間のみ",
            command=self._on_start_time_only
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
        
        # クリアボタン
        clear_btn = ttk.Button(
            history_frame,
            text="履歴クリア",
            command=self._clear_history
        )
        clear_btn.pack(anchor=tk.E, pady=(5, 0))
        
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
        
        self.history_text.configure(state=tk.NORMAL)
        self.history_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
        self.history_text.insert(tk.END, f"{message}\n", level)
        self.history_text.see(tk.END)  # 最下部にスクロール
        self.history_text.configure(state=tk.DISABLED)
        
        self.root.update()
    
    def _clear_history(self) -> None:
        """履歴をクリア"""
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
            self.start_times = self.config_loader.get_start_times()
            
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
            
            # StartTimeコンボボックスに値を設定
            time_labels = [t.strftime("%H:%M") for t in self.start_times]
            self.start_time_combo['values'] = time_labels
            if time_labels:
                self.start_time_combo.current(0)
            
            self.status_var.set(f"{len(self.groups)} グループ / {len(self.start_times)} 時間帯")
            self._add_history(f"起動完了: {len(self.groups)} グループ, {len(self.start_times)} 時間帯をロード", "info")
            logger.info(f"GUI起動完了: {len(self.groups)} グループ, {len(self.start_times)} StartTimes")
            
        except Exception as e:
            logger.error(f"データ読み込みエラー: {e}")
            show_error(self.WINDOW_TITLE, f"データの読み込みに失敗しました:\n{e}")
    
    def _on_group_selected(self, group_name: str) -> None:
        """グループボタンがクリックされた時の処理"""
        logger.info(f"グループ選択: {group_name}")
        self.status_var.set(f"実行中: {group_name}...")
        self._reset_progress()
        self._add_history(f"=== {group_name} 開始 ===", "info")
        self.root.update()
        
        # ボタンを無効化
        for widget in self.button_frame.winfo_children():
            widget.configure(state="disabled")
        
        try:
            # タスク取得
            tasks = self.config_loader.get_tasks_by_group(group_name)
            
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
    
    def _set_buttons_enabled(self, enabled: bool) -> None:
        """全ボタンの有効/無効を切り替え"""
        state = "normal" if enabled else "disabled"
        for widget in self.button_frame.winfo_children():
            widget.configure(state=state)
        self.retry_btn.configure(state=state)
        self.only_btn.configure(state=state)
        self.start_time_combo.configure(state="readonly" if enabled else "disabled")
    
    def _on_start_time_selected(self) -> None:
        """『ここから実行』ボタン - 選択したStartTime以降のタスクを実行"""
        selected_time_str = self.start_time_var.get()
        if not selected_time_str:
            show_warning(self.WINDOW_TITLE, "開始時刻を選択してください。")
            return
        
        # 文字列からtime型に変換
        parts = selected_time_str.split(":")
        from datetime import time
        selected_time = time(int(parts[0]), int(parts[1]))
        
        logger.info(f"StartTime選択（以降）: {selected_time_str}")
        self.status_var.set(f"実行中: {selected_time_str}以降...")
        self._reset_progress()
        self._add_history(f"=== {selected_time_str}以降 のタスクを開始 ===", "info")
        self.root.update()
        
        self._set_buttons_enabled(False)
        
        try:
            # 指定StartTime以降のタスクを取得
            tasks = self.config_loader.get_tasks_from_start_time(selected_time)
            
            if not tasks:
                show_warning(self.WINDOW_TITLE, f"'{selected_time_str}'以降にタスクがありません。")
                self._add_history(f"{selected_time_str}以降: タスクなし", "skip")
                return
            
            self._add_history(f"{len(tasks)} 件のタスクを実行します", "info")
            
            # タスク実行
            results = self.task_runner.run_group(tasks)
            
            # 結果表示
            self._show_results(f"{selected_time_str}以降", results)
            
        except Exception as e:
            logger.error(f"タスク実行エラー: {e}")
            self._add_history(f"エラー: {str(e)}", "error")
            show_error(self.WINDOW_TITLE, f"エラーが発生しました:\n{e}")
            self.status_var.set("エラーが発生しました")
        
        finally:
            self._set_buttons_enabled(True)
    
    def _on_start_time_only(self) -> None:
        """『この時間のみ』ボタン - 選択したStartTimeのタスクのみ実行"""
        selected_time_str = self.start_time_var.get()
        if not selected_time_str:
            show_warning(self.WINDOW_TITLE, "開始時刻を選択してください。")
            return
        
        # 文字列からtime型に変換
        parts = selected_time_str.split(":")
        from datetime import time
        selected_time = time(int(parts[0]), int(parts[1]))
        
        logger.info(f"StartTime選択（のみ）: {selected_time_str}")
        self.status_var.set(f"実行中: {selected_time_str}のみ...")
        self._reset_progress()
        self._add_history(f"=== {selected_time_str} のタスクを開始 ===", "info")
        self.root.update()
        
        self._set_buttons_enabled(False)
        
        try:
            # 指定StartTimeのタスクのみを取得
            tasks = self.config_loader.get_tasks_by_start_time(selected_time)
            
            if not tasks:
                show_warning(self.WINDOW_TITLE, f"'{selected_time_str}'のタスクがありません。")
                self._add_history(f"{selected_time_str}: タスクなし", "skip")
                return
            
            self._add_history(f"{len(tasks)} 件のタスクを実行します", "info")
            
            # タスク実行
            results = self.task_runner.run_group(tasks)
            
            # 結果表示
            self._show_results(f"{selected_time_str}", results)
            
        except Exception as e:
            logger.error(f"タスク実行エラー: {e}")
            self._add_history(f"エラー: {str(e)}", "error")
            show_error(self.WINDOW_TITLE, f"エラーが発生しました:\n{e}")
            self.status_var.set("エラーが発生しました")
        
        finally:
            self._set_buttons_enabled(True)
    
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
        
        self.status_var.set("完了しました")
        self.detail_status_var.set("✓ 全タスク完了")
        self.progress_count_var.set("完了")
    
    def run(self) -> None:
        """GUIメインループを開始"""
        logger.info("Co-worker Bot を起動しました")
        self.root.mainloop()
        logger.info("Co-worker Bot を終了しました")


def main():
    """エントリーポイント"""
    try:
        app = CoworkerBotGUI()
        app.run()
    except Exception as e:
        logger.error(f"致命的なエラー: {e}")
        show_error("Co-worker Bot", f"致命的なエラーが発生しました:\n{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()



