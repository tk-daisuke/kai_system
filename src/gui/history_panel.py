# -*- coding: utf-8 -*-
"""
kai_system - 処理履歴パネル
実行ログのフィルタリング表示を提供する
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
from datetime import datetime
from typing import List


class HistoryPanel(ttk.LabelFrame):
    """処理履歴を表示するパネル"""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, text="📋 処理履歴", padding=10, **kwargs)

        self.entries: List[dict] = []
        self._build()

    def _build(self):
        # テキストエリア
        self.text = scrolledtext.ScrolledText(
            self,
            height=10,
            font=("Consolas", 9),
            wrap=tk.WORD,
            state=tk.DISABLED,
            background="#f8f8f8",
        )
        self.text.pack(fill=tk.BOTH, expand=True)

        # タグ設定（色分け）
        self.text.tag_configure("timestamp", foreground="#888888")
        self.text.tag_configure("success", foreground="#28a745")
        self.text.tag_configure("error", foreground="#dc3545")
        self.text.tag_configure("info", foreground="#0066cc")
        self.text.tag_configure("skip", foreground="#ffc107")

        # フィルターフレーム
        filter_frame = ttk.Frame(self)
        filter_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Label(filter_frame, text="フィルタ:", font=("Yu Gothic UI", 9)).pack(
            side=tk.LEFT
        )

        self.filter_var = tk.StringVar(value="all")
        filters = [
            ("全て", "all"),
            ("成功", "success"),
            ("失敗", "error"),
            ("スキップ", "skip"),
        ]
        for text, value in filters:
            rb = ttk.Radiobutton(
                filter_frame,
                text=text,
                value=value,
                variable=self.filter_var,
                command=self._apply_filter,
            )
            rb.pack(side=tk.LEFT, padx=3)

        # クリアボタン
        ttk.Button(filter_frame, text="履歴クリア", command=self.clear).pack(
            side=tk.RIGHT
        )

    def add(self, message: str, level: str = "info") -> None:
        """履歴エントリを追加"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.entries.append(
            {"timestamp": timestamp, "message": message, "level": level}
        )

        # フィルタチェック
        current_filter = self.filter_var.get()
        if current_filter != "all" and current_filter != level:
            return

        self.text.configure(state=tk.NORMAL)
        self.text.insert(tk.END, f"[{timestamp}] ", "timestamp")
        self.text.insert(tk.END, f"{message}\n", level)
        self.text.see(tk.END)
        self.text.configure(state=tk.DISABLED)

    def _apply_filter(self) -> None:
        """フィルタを適用して再表示"""
        selected = self.filter_var.get()
        self.text.configure(state=tk.NORMAL)
        self.text.delete(1.0, tk.END)

        for entry in self.entries:
            if selected == "all" or entry["level"] == selected:
                self.text.insert(tk.END, f"[{entry['timestamp']}] ", "timestamp")
                self.text.insert(tk.END, f"{entry['message']}\n", entry["level"])

        self.text.see(tk.END)
        self.text.configure(state=tk.DISABLED)

    def clear(self) -> None:
        """履歴をクリア"""
        self.entries = []
        self.text.configure(state=tk.NORMAL)
        self.text.delete(1.0, tk.END)
        self.text.configure(state=tk.DISABLED)

    def apply_dark_mode(self, dark: bool) -> None:
        """ダークモード切り替え"""
        if dark:
            self.text.configure(bg="#1e1e1e", fg="#d4d4d4")
        else:
            self.text.configure(bg="#f8f8f8", fg="#000000")
