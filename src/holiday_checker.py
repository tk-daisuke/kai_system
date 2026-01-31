# -*- coding: utf-8 -*-
"""
Co-worker Bot - 祝日チェックモジュール
日本の祝日判定とスキップ処理
"""

from datetime import date, datetime
from typing import Optional

from utils import logger


def is_japanese_holiday(check_date: Optional[date] = None) -> bool:
    """
    指定日が日本の祝日かどうかを判定する
    
    Args:
        check_date: チェックする日付（Noneの場合は今日）
        
    Returns:
        祝日ならTrue
    """
    if check_date is None:
        check_date = date.today()
    
    try:
        import jpholiday
        return jpholiday.is_holiday(check_date)
    except ImportError:
        logger.warning("jpholidayがインストールされていません。祝日チェックをスキップします。")
        logger.warning("インストール: pip install jpholiday")
        return False


def get_holiday_name(check_date: Optional[date] = None) -> Optional[str]:
    """
    指定日の祝日名を取得する
    
    Args:
        check_date: チェックする日付（Noneの場合は今日）
        
    Returns:
        祝日名（祝日でなければNone）
    """
    if check_date is None:
        check_date = date.today()
    
    try:
        import jpholiday
        return jpholiday.is_holiday_name(check_date)
    except ImportError:
        return None


def check_weekday_condition(weekdays_str: str) -> bool:
    """
    曜日条件をチェックする
    
    Args:
        weekdays_str: 実行する曜日（1=月〜7=日、カンマ区切り）
                      例: "1,2,3,4,5" = 平日のみ
                      空文字 = 毎日実行
        
    Returns:
        今日が実行対象曜日ならTrue
    """
    if not weekdays_str or weekdays_str.strip() == "":
        return True  # 条件なし = 毎日実行
    
    try:
        # 今日の曜日を取得（1=月曜〜7=日曜）
        today_weekday = datetime.now().isoweekday()
        
        # カンマ区切りでパース
        allowed_days = [int(d.strip()) for d in weekdays_str.split(",") if d.strip()]
        
        return today_weekday in allowed_days
    except ValueError as e:
        logger.warning(f"曜日条件のパースに失敗: {weekdays_str} - {e}")
        return True  # パース失敗時は実行する


def check_date_condition(date_condition_str: str) -> bool:
    """
    日付条件をチェックする
    
    Args:
        date_condition_str: 実行する日（カンマ区切り）
                            例: "1,15" = 毎月1日と15日
                            例: "L" = 月末
                            空文字 = 毎日実行
        
    Returns:
        今日が実行対象日ならTrue
    """
    if not date_condition_str or date_condition_str.strip() == "":
        return True  # 条件なし = 毎日実行
    
    try:
        today = datetime.now()
        today_day = today.day
        
        # 月末判定用
        import calendar
        last_day = calendar.monthrange(today.year, today.month)[1]
        
        conditions = [c.strip().upper() for c in date_condition_str.split(",")]
        
        for cond in conditions:
            if cond == "L":  # 月末
                if today_day == last_day:
                    return True
            elif cond.isdigit():
                if today_day == int(cond):
                    return True
        
        return False
    except ValueError as e:
        logger.warning(f"日付条件のパースに失敗: {date_condition_str} - {e}")
        return True  # パース失敗時は実行する


def should_skip_task(weekdays: str, skip_holiday: bool, date_condition: str) -> tuple[bool, str]:
    """
    タスクをスキップすべきか総合判定する
    
    Args:
        weekdays: 曜日条件
        skip_holiday: 祝日スキップフラグ
        date_condition: 日付条件
        
    Returns:
        (スキップするか, 理由)
    """
    # 曜日チェック
    if not check_weekday_condition(weekdays):
        today_weekday = datetime.now().isoweekday()
        weekday_names = ["", "月", "火", "水", "木", "金", "土", "日"]
        return True, f"曜日条件外 (今日: {weekday_names[today_weekday]}曜日)"
    
    # 祝日チェック
    if skip_holiday and is_japanese_holiday():
        holiday_name = get_holiday_name() or "祝日"
        return True, f"祝日スキップ ({holiday_name})"
    
    # 日付条件チェック
    if not check_date_condition(date_condition):
        return True, f"日付条件外 (今日: {datetime.now().day}日)"
    
    return False, ""
