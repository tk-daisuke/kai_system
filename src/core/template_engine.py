# -*- coding: utf-8 -*-
"""
kai_system - URL/文字列テンプレート変数の展開ユーティリティ
期間指定 (from / to) とタイムゾーン (JST / UTC) をサポート
"""

import calendar
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional


# タイムゾーン定義
TZ_JST = timezone(timedelta(hours=9))
TZ_UTC = timezone.utc


def _weeknum_sunday(d: datetime) -> int:
    """
    Excel WEEKNUM 互換（日曜始まり）
    1/1 が属する週を第1週とし、日曜日で区切る。
    """
    jan1 = d.replace(month=1, day=1)
    # 日曜=0, 月曜=1 ... 土曜=6
    jan1_dow = (jan1.weekday() + 1) % 7
    day_of_year = d.timetuple().tm_yday
    return (day_of_year + jan1_dow - 1) // 7 + 1


def get_template_variables(
    dt_from: Optional[datetime] = None,
    dt_to: Optional[datetime] = None,
    tz_mode: str = "jst",
) -> Dict[str, str]:
    """
    テンプレート変数の辞書を返す

    Args:
        dt_from:  期間開始日時（省略時: 前日 00:00 JST）
        dt_to:    期間終了日時（省略時: 本日 00:00 JST）
        tz_mode:  'jst' or 'utc'。汎用変数 {from},{to} の解決先

    週番号変数:
        {week}          → WEEKNUM互換 日曜始まり (1-54)
        {week_iso}      → ISO 8601 月曜始まり (1-53)
        {week02}        → ゼロ埋め2桁 (01-54)
        {week_iso02}    → ISO ゼロ埋め2桁

    汎用変数（tz_mode に連動）:
        {from}           → ISO形式
        {from_short}     → 2026-02-23 00:00
        {from_date}      → 日付のみ (2026-02-23)
        {from_date_jp}   → 20260223
        {to}, {to_short}, {to_date}, {to_date_jp} → 同上

    明示変数（常に利用可能）:
        {from_jst}, {from_utc}, {to_jst}, {to_utc} 等
        {from_epoch}, {to_epoch}

    互換変数:
        {today}, {today_jp}, {yesterday}, {yesterday_jp}
        {year}, {month}, {day}
        {first_day}, {last_day} 等
    """
    now_jst = datetime.now(TZ_JST)

    if dt_to is None:
        dt_to = now_jst.replace(hour=0, minute=0, second=0, microsecond=0)
    elif dt_to.tzinfo is None:
        dt_to = dt_to.replace(tzinfo=TZ_JST)

    if dt_from is None:
        dt_from = dt_to - timedelta(days=1)
    elif dt_from.tzinfo is None:
        dt_from = dt_from.replace(tzinfo=TZ_JST)

    # 基準日（to の日付ベース）
    base = dt_to
    yesterday = base - timedelta(days=1)
    last_day_num = calendar.monthrange(base.year, base.month)[1]
    first_day = base.replace(day=1)
    last_day = base.replace(day=last_day_num)

    # TZ 変換
    from_jst = dt_from.astimezone(TZ_JST)
    from_utc = dt_from.astimezone(TZ_UTC)
    to_jst = dt_to.astimezone(TZ_JST)
    to_utc = dt_to.astimezone(TZ_UTC)

    # 週番号（to 基準）
    wn = _weeknum_sunday(base)
    wn_iso = base.isocalendar()[1]
    # from 基準の週番号
    from_wn = _weeknum_sunday(from_jst)
    from_wn_iso = from_jst.isocalendar()[1]

    vars = {
        # 互換
        "today": base.strftime("%Y-%m-%d"),
        "today_jp": base.strftime("%Y%m%d"),
        "yesterday": yesterday.strftime("%Y-%m-%d"),
        "yesterday_jp": yesterday.strftime("%Y%m%d"),
        "year": base.strftime("%Y"),
        "month": base.strftime("%m"),
        "day": base.strftime("%d"),
        "first_day": first_day.strftime("%Y-%m-%d"),
        "first_day_jp": first_day.strftime("%Y%m%d"),
        "last_day": last_day.strftime("%Y-%m-%d"),
        "last_day_jp": last_day.strftime("%Y%m%d"),

        # 週番号（to 基準）
        "week": str(wn),
        "week02": f"{wn:02d}",
        "week_iso": str(wn_iso),
        "week_iso02": f"{wn_iso:02d}",
        # 週番号（from 基準）
        "from_week": str(from_wn),
        "from_week02": f"{from_wn:02d}",
        "from_week_iso": str(from_wn_iso),
        "from_week_iso02": f"{from_wn_iso:02d}",

        # from (JST)
        "from_jst": from_jst.strftime("%Y-%m-%dT%H:%M:%S+09:00"),
        "from_jst_short": from_jst.strftime("%Y-%m-%d %H:%M"),
        "from_jst_date": from_jst.strftime("%Y-%m-%d"),
        "from_jst_jp": from_jst.strftime("%Y%m%d"),
        "from_jst_time": from_jst.strftime("%H:%M"),
        # from (UTC)
        "from_utc": from_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "from_utc_short": from_utc.strftime("%Y-%m-%d %H:%M"),
        "from_utc_date": from_utc.strftime("%Y-%m-%d"),
        "from_utc_jp": from_utc.strftime("%Y%m%d"),
        "from_utc_time": from_utc.strftime("%H:%M"),
        # to (JST)
        "to_jst": to_jst.strftime("%Y-%m-%dT%H:%M:%S+09:00"),
        "to_jst_short": to_jst.strftime("%Y-%m-%d %H:%M"),
        "to_jst_date": to_jst.strftime("%Y-%m-%d"),
        "to_jst_jp": to_jst.strftime("%Y%m%d"),
        "to_jst_time": to_jst.strftime("%H:%M"),
        # to (UTC)
        "to_utc": to_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "to_utc_short": to_utc.strftime("%Y-%m-%d %H:%M"),
        "to_utc_date": to_utc.strftime("%Y-%m-%d"),
        "to_utc_jp": to_utc.strftime("%Y%m%d"),
        "to_utc_time": to_utc.strftime("%H:%M"),
        # epoch
        "from_epoch": str(int(dt_from.timestamp())),
        "to_epoch": str(int(dt_to.timestamp())),
    }

    # 汎用エイリアス（tz_mode に連動）
    if tz_mode == "utc":
        vars["from"] = vars["from_utc"]
        vars["from_short"] = vars["from_utc_short"]
        vars["from_date"] = vars["from_utc_date"]
        vars["from_date_jp"] = vars["from_utc_jp"]
        vars["to"] = vars["to_utc"]
        vars["to_short"] = vars["to_utc_short"]
        vars["to_date"] = vars["to_utc_date"]
        vars["to_date_jp"] = vars["to_utc_jp"]
    else:
        vars["from"] = vars["from_jst"]
        vars["from_short"] = vars["from_jst_short"]
        vars["from_date"] = vars["from_jst_date"]
        vars["from_date_jp"] = vars["from_jst_jp"]
        vars["to"] = vars["to_jst"]
        vars["to_short"] = vars["to_jst_short"]
        vars["to_date"] = vars["to_jst_date"]
        vars["to_date_jp"] = vars["to_jst_jp"]

    return vars


def expand_template(
    text: str,
    dt_from: Optional[datetime] = None,
    dt_to: Optional[datetime] = None,
    tz_mode: str = "jst",
) -> str:
    """テンプレート変数を展開した文字列を返す"""
    if not text or "{" not in text:
        return text
    variables = get_template_variables(dt_from=dt_from, dt_to=dt_to, tz_mode=tz_mode)
    result = text
    for key, value in variables.items():
        result = result.replace(f"{{{key}}}", value)
    return result


def expand_params(
    params: Dict[str, Any],
    dt_from: Optional[datetime] = None,
    dt_to: Optional[datetime] = None,
    tz_mode: str = "jst",
) -> Dict[str, Any]:
    """パラメータ辞書内の全文字列値に対してテンプレート展開を行う"""
    return _expand_recursive(params, dt_from, dt_to, tz_mode)


def _expand_recursive(
    obj: Any,
    dt_from: Optional[datetime] = None,
    dt_to: Optional[datetime] = None,
    tz_mode: str = "jst",
) -> Any:
    """再帰的にテンプレート展開"""
    if isinstance(obj, str):
        return expand_template(obj, dt_from=dt_from, dt_to=dt_to, tz_mode=tz_mode)
    elif isinstance(obj, dict):
        return {k: _expand_recursive(v, dt_from, dt_to, tz_mode) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_expand_recursive(item, dt_from, dt_to, tz_mode) for item in obj]
    else:
        return obj
