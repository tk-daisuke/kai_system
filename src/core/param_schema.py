# -*- coding: utf-8 -*-
"""
kai_system - アクションタイプ別パラメータスキーマ定義
エディタUIがタイプに応じた動的フォームを生成するために使用する
"""

from typing import Any, Dict, List


PARAM_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "csv_download": {
        "label": "CSVダウンロード + Excel転記",
        "description": "WebサイトからCSVをダウンロードし、指定Excelファイルのシートに転記する",
        "fields": [
            {
                "key": "url",
                "label": "ダウンロードURL",
                "type": "url",
                "required": True,
                "placeholder": "https://example.com/csv?from={from_date}&to={to_date}",
                "help": "テンプレート変数 ({from_date} 等) を使用できます",
            },
            {
                "key": "excel_path",
                "label": "Excelファイルパス",
                "type": "path",
                "required": True,
                "placeholder": "C:/Reports/売上.xlsx",
            },
            {
                "key": "target_sheet",
                "label": "転記先シート名",
                "type": "text",
                "required": True,
                "placeholder": "Data",
            },
            {
                "key": "macro_name",
                "label": "マクロ名（任意）",
                "type": "text",
                "required": False,
                "placeholder": "Module1.SendMailReport",
                "help": "転記後にExcelマクロを実行する場合に指定",
            },
            {
                "key": "action_after",
                "label": "完了後の動作",
                "type": "select",
                "options": [
                    {"value": "save", "label": "保存"},
                    {"value": "pause", "label": "一時停止（手動作業を待つ）"},
                ],
                "default": "save",
            },
            {
                "key": "close_after",
                "label": "完了後にファイルを閉じる",
                "type": "bool",
                "default": False,
            },
            {
                "key": "skip_download",
                "label": "ダウンロードをスキップ",
                "type": "bool",
                "default": False,
                "help": "既にCSVがある場合、マクロ実行のみ行う",
            },
        ],
    },
    "scraper": {
        "label": "Webスクレーピング",
        "description": "ブラウザを操作してCSVをダウンロードする",
        "fields": [
            {
                "key": "url",
                "label": "対象URL",
                "type": "url",
                "required": True,
                "placeholder": "https://analytics.example.com/login",
                "help": "テンプレート変数を使用できます",
            },
            {
                "key": "cdp_url",
                "label": "Chrome DevTools URL",
                "type": "url",
                "required": False,
                "default": "http://localhost:9222",
                "help": "Chrome を --remote-debugging-port=9222 で起動済みであること",
            },
            {
                "key": "form_fills",
                "label": "フォーム操作ステップ",
                "type": "form_fills",
                "required": False,
                "help": "ページ上のフォーム入力・ボタンクリック等を順番に定義します",
                "item_fields": [
                    {
                        "key": "selector",
                        "label": "CSSセレクタ",
                        "type": "text",
                        "placeholder": "input#date_from",
                    },
                    {
                        "key": "action",
                        "label": "操作",
                        "type": "select",
                        "options": [
                            {"value": "fill", "label": "入力 (fill)"},
                            {"value": "clear_and_fill", "label": "クリア後入力"},
                            {"value": "select", "label": "プルダウン選択"},
                            {"value": "click", "label": "クリック"},
                            {"value": "type", "label": "1文字ずつ入力（日付ピッカー等）"},
                        ],
                        "default": "fill",
                    },
                    {
                        "key": "value",
                        "label": "値",
                        "type": "text",
                        "placeholder": "{from_date_jp}",
                        "help": "テンプレート変数も使用可能",
                    },
                    {
                        "key": "wait_after",
                        "label": "操作後の待機(ms)",
                        "type": "number",
                        "default": 500,
                    },
                ],
            },
            {
                "key": "download_button",
                "label": "ダウンロードボタン",
                "type": "text",
                "required": True,
                "placeholder": "button#csv_export, a.download-link",
                "help": "CSVダウンロードをトリガーするボタンのCSSセレクタ",
            },
            {
                "key": "download_dir",
                "label": "ダウンロード先",
                "type": "path",
                "required": False,
                "placeholder": "~/Downloads",
                "help": "空欄の場合はユーザーのDownloadsフォルダ",
            },
            {
                "key": "download_timeout",
                "label": "ダウンロード待機（秒）",
                "type": "number",
                "default": 60,
            },
        ],
    },
    "shell_cmd": {
        "label": "シェルコマンド実行",
        "description": "任意のシェルコマンドを実行する",
        "fields": [
            {
                "key": "command",
                "label": "コマンド",
                "type": "textarea",
                "required": True,
                "placeholder": 'curl -o export.json "https://api.example.com/v2/data?from={from_epoch}&to={to_epoch}"',
                "help": "テンプレート変数を使用できます",
            },
            {
                "key": "cwd",
                "label": "作業ディレクトリ",
                "type": "path",
                "required": False,
                "placeholder": "/home/user/scripts",
            },
            {
                "key": "timeout",
                "label": "タイムアウト（秒）",
                "type": "number",
                "required": False,
                "default": 300,
            },
            {
                "key": "encoding",
                "label": "エンコーディング",
                "type": "text",
                "required": False,
                "default": "utf-8",
            },
        ],
    },
}


def get_action_types() -> List[Dict[str, str]]:
    """利用可能なアクションタイプ一覧を返す"""
    return [
        {"type": k, "label": v["label"], "description": v.get("description", "")}
        for k, v in PARAM_SCHEMAS.items()
    ]


def get_param_schema(action_type: str) -> Dict[str, Any]:
    """指定タイプのパラメータスキーマを返す"""
    return PARAM_SCHEMAS.get(action_type, {"label": action_type, "fields": []})
