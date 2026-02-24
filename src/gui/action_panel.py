# -*- coding: utf-8 -*-
"""
kai_system - アクションボタンパネル
グループごとにアクションボタンを表示・実行する
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, List, Optional

from core.config_manager import ActionConfig, GroupConfig


class ActionPanel(ttk.Frame):
    """グループ分けされたアクションボタンを表示するパネル"""

    def __init__(
        self,
        parent,
        on_action_click: Callable[[str], None],
        on_group_click: Callable[[str], None],
        **kwargs,
    ):
        super().__init__(parent, **kwargs)
        self.on_action_click = on_action_click
        self.on_group_click = on_group_click
        self._buttons: Dict[str, ttk.Button] = {}

    def render(
        self,
        groups: List[GroupConfig],
        grouped_actions: Dict[str, List[ActionConfig]],
        ungrouped: List[ActionConfig],
    ) -> None:
        """パネルを描画"""
        # 既存ウィジェットをクリア
        for widget in self.winfo_children():
            widget.destroy()
        self._buttons.clear()

        # グループごとにセクション作成
        for group in groups:
            actions = grouped_actions.get(group.name, [])
            if not actions:
                continue

            self._create_group_section(group, actions)

        # グループに属さないアクション
        if ungrouped:
            self._create_ungrouped_section(ungrouped)

    def _create_group_section(
        self, group: GroupConfig, actions: List[ActionConfig]
    ) -> None:
        """グループセクションを作成"""
        # グループフレーム
        group_frame = ttk.LabelFrame(
            self, text=f"{group.icon} {group.name}", padding=8
        )
        group_frame.pack(fill=tk.X, pady=(0, 8), padx=2)

        # グループ一括実行ボタン
        header_frame = ttk.Frame(group_frame)
        header_frame.pack(fill=tk.X, pady=(0, 5))

        run_all_btn = ttk.Button(
            header_frame,
            text=f"▶ {group.name} をすべて実行",
            command=lambda g=group.name: self.on_group_click(g),
            style="GroupRun.TButton",
        )
        run_all_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)

        count_label = ttk.Label(
            header_frame,
            text=f"({len(actions)}件)",
            font=("Yu Gothic UI", 9),
            foreground="#888888",
        )
        count_label.pack(side=tk.RIGHT, padx=(5, 0))

        # 個別アクションボタン
        for action in actions:
            btn = ttk.Button(
                group_frame,
                text=f"  {action.icon} {action.name}",
                command=lambda a=action.id: self.on_action_click(a),
                style="Action.TButton",
            )
            btn.pack(fill=tk.X, pady=1)
            self._buttons[action.id] = btn

    def _create_ungrouped_section(self, actions: List[ActionConfig]) -> None:
        """グループなしセクション"""
        frame = ttk.LabelFrame(self, text="📌 その他", padding=8)
        frame.pack(fill=tk.X, pady=(0, 8), padx=2)

        for action in actions:
            btn = ttk.Button(
                frame,
                text=f"  {action.icon} {action.name}",
                command=lambda a=action.id: self.on_action_click(a),
                style="Action.TButton",
            )
            btn.pack(fill=tk.X, pady=1)
            self._buttons[action.id] = btn

    def set_enabled(self, enabled: bool) -> None:
        """全ボタンの有効/無効を切り替え"""
        state = "normal" if enabled else "disabled"
        for btn in self._buttons.values():
            btn.configure(state=state)
        # グループボタンも
        for widget in self.winfo_children():
            if isinstance(widget, ttk.LabelFrame):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Frame):
                        for grandchild in child.winfo_children():
                            if isinstance(grandchild, ttk.Button):
                                grandchild.configure(state=state)

    def highlight_action(self, action_id: str) -> None:
        """実行中のアクションをハイライト"""
        # 全ボタンのスタイルをリセット
        for aid, btn in self._buttons.items():
            btn.configure(style="Action.TButton")
        # 対象をハイライト
        if action_id in self._buttons:
            self._buttons[action_id].configure(style="ActiveAction.TButton")
