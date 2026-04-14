"""
JMA MCP サーバー
気象庁APIをMCPツールとして公開するstdioベースのサーバー
"""
import asyncio
import sys
from datetime import datetime, timezone, timedelta

import requests
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from areas import AREA_CODE_MAP, search_area_by_name

# 日本標準時
JST = timezone(timedelta(hours=9))

# JMA API エンドポイント
FORECAST_URL     = "https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json"
OVERVIEW_URL     = "https://www.jma.go.jp/bosai/forecast/data/overview_forecast/{area_code}.json"
WARNING_URL      = "https://www.jma.go.jp/bosai/warning/data/warning/{area_code}.json"
PROBABILITY_URL  = "https://www.jma.go.jp/bosai/probability/data/probability/{area_code}.json"

# 警報・注意報コード → 名称マッピング（気象庁TELOPS準拠）
WARNING_CODE_MAP = {
    # 警報
    "02": "大雨警報",
    "03": "洪水警報",
    "10": "暴風警報",
    "12": "暴風雪警報",
    "13": "大雪警報",
    "14": "波浪警報",
    "15": "高潮警報",
    # 注意報
    "20": "波浪注意報",
    "21": "強風注意報",
    "22": "大雨注意報",
    "23": "洪水注意報",
    "24": "大雪注意報",
    "25": "高潮注意報",
    "26": "霜注意報",
    "27": "雷注意報",
    "28": "乾燥注意報",
    "29": "濃霧注意報",
    "30": "なだれ注意報",
    "31": "低温注意報",
    "32": "着氷注意報",
    "33": "着雪注意報",
    "34": "融雪注意報",
    # 特別警報
    "01": "大雨特別警報",
    "06": "暴風特別警報",
    "07": "高潮特別警報",
    "08": "波浪特別警報",
    "09": "大雪特別警報",
    "11": "暴風雪特別警報",
}

# 警報ステータスの優先度（表示順ソート用）
WARNING_STATUS_ORDER = {"発表": 0, "継続": 1, "更新": 2, "解除": 3}

# 警報・注意報エリアコード → 地域名（class10s / class15s）
WARNING_AREA_NAME_MAP = {
    # 沖縄本島地方
    "471010": "本島中南部", "471020": "本島北部", "471030": "久米島",
    # 大東島地方
    "472010": "南大東島", "472020": "北大東島",
    # 宮古島地方
    "473010": "宮古島", "473020": "多良間島",
    # 八重山地方
    "474010": "石垣島", "474020": "西表島・竹富島・小浜島・黒島・新城島・波照間島",
    "474030": "与那国島",
    # 北海道
    "011010": "石狩地方北部", "011020": "石狩地方南部",
    "012010": "渡島地方北部", "012020": "渡島地方南部",
    # 東北
    "040010": "宮城県北部", "040020": "宮城県南部・仙台",
    # 関東
    "130010": "東京地方", "130020": "伊豆諸島北部", "130030": "伊豆諸島南部",
    "130040": "小笠原諸島",
    # その他主要地方（class10s）
}

# HTTPリクエスト共通ヘッダー（JMA利用規約対応）
HEADERS = {"User-Agent": "jma_mcp/1.0 (educational use)"}

# 天気コード → テキストマッピング（気象庁TELOPS準拠）
WEATHER_CODE_MAP = {
    "100": "晴", "101": "晴時々曇", "102": "晴一時雨", "103": "晴時々雨",
    "104": "晴一時雪", "105": "晴時々雪", "106": "晴一時雨か雪",
    "107": "晴時々雨か雪", "108": "晴一時雨か雷雨", "110": "晴後時々曇",
    "111": "晴後曇", "112": "晴後一時雨", "113": "晴後時々雨", "114": "晴後雨",
    "115": "晴後一時雪", "116": "晴後時々雪", "117": "晴後雪",
    "118": "晴後雨か雪", "119": "晴後雨か雷雨", "120": "晴朝夕一時雨",
    "121": "晴朝の内一時雨", "122": "晴夕方一時雨", "123": "晴山沿い雷雨",
    "124": "晴山沿い雪", "125": "晴午後は雷雨", "126": "晴昼頃から雨",
    "127": "晴夕方から雨", "128": "晴夜は雨", "130": "朝の内霧後晴",
    "131": "晴明け方霧", "132": "晴朝夕曇", "140": "晴時々曇一時雨",
    "160": "晴一時雪か雨", "170": "晴時々雪か雨", "181": "晴後雪か雨",
    "200": "曇", "201": "曇時々晴", "202": "曇一時雨", "203": "曇時々雨",
    "204": "曇一時雪", "205": "曇時々雪", "206": "曇一時雨か雪",
    "207": "曇時々雨か雪", "208": "曇一時雨か雷雨", "209": "霧",
    "210": "曇後時々晴", "211": "曇後晴", "212": "曇後一時雨",
    "213": "曇後時々雨", "214": "曇後雨", "215": "曇後一時雪",
    "216": "曇後時々雪", "217": "曇後雪", "218": "曇後雨か雪",
    "219": "曇後雨か雷雨", "220": "曇朝夕一時雨", "221": "曇朝の内一時雨",
    "222": "曇夕方一時雨", "223": "曇山沿い雷雨", "224": "曇山沿い雪",
    "225": "曇午後は雷雨", "226": "曇昼頃から雨", "227": "曇夕方から雨",
    "228": "曇夜は雨", "229": "曇夜は雪", "230": "曇夜半後晴",
    "231": "曇海上海岸は霧か霧雨", "240": "曇時々曇一時雨", "250": "曇時々雪",
    "260": "曇一時雪か雨", "270": "曇時々雪か雨", "281": "曇後雪か雨",
    "300": "雨", "301": "雨時々晴", "302": "雨時々止む", "303": "雨時々雪",
    "304": "雨か雪", "306": "大雨", "308": "雨で暴風を伴う", "309": "雨一時雪",
    "311": "雨後時々晴", "313": "雨後時々曇", "314": "雨後時々雪",
    "315": "雨後雪", "316": "雨後晴", "317": "雨後曇", "320": "朝の内雨後晴",
    "321": "朝の内雨後曇", "322": "雨朝晩一時雪", "323": "雨昼頃から晴",
    "324": "雨夕方から晴", "325": "雨夜半から晴", "326": "雨夕方から雪",
    "327": "雨夜半から雪", "328": "雨一時強く降る", "329": "雨一時みぞれ",
    "340": "雪か雨", "350": "雨で雷を伴う", "361": "雪か雨後晴",
    "371": "雪か雨後曇", "400": "雪", "401": "雪時々晴", "402": "雪時々止む",
    "403": "雪時々雨", "405": "大雪", "406": "風雪強い", "407": "暴風雪",
    "409": "雪一時雨", "411": "雪後時々晴", "413": "雪後時々曇",
    "414": "雪後雨", "420": "朝の内雪後晴", "421": "朝の内雪後曇",
    "422": "雪昼頃から雨", "423": "雪夕方から雨", "424": "雪夜半から雨",
    "425": "雪一時強く降る", "426": "雪後みぞれ", "427": "雪一時みぞれ",
    "450": "雪で雷を伴う",
}

WEATHER_EMOJI_MAP = {"1": "☀️", "2": "☁️", "3": "🌧️", "4": "🌨️"}


def weather_code_to_text(code: str) -> str:
    """天気コードを説明テキストに変換"""
    return WEATHER_CODE_MAP.get(str(code), f"不明({code})")


def weather_code_to_emoji(code: str) -> str:
    """天気コードを絵文字に変換"""
    code_str = str(code)
    if not code_str:
        return "❓"
    return WEATHER_EMOJI_MAP.get(code_str[0], "🌤️")


def fetch_json(url: str) -> dict:
    """指定URLからJSONを取得する"""
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.json()


def format_date_jp(iso_str: str) -> str:
    """ISO 8601文字列を日本語日付に変換（例: 4月14日(月)）"""
    weekdays = ["月", "火", "水", "木", "金", "土", "日"]
    dt = datetime.fromisoformat(iso_str).astimezone(JST)
    wd = weekdays[dt.weekday()]
    return f"{dt.month}月{dt.day}日({wd})"


# MCPサーバーのインスタンス作成
server = Server("jma-mcp")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """利用可能なツール一覧を返す"""
    return [
        Tool(
            name="get_forecast",
            description="エリアコードを指定して3日間の短期天気予報を取得する",
            inputSchema={
                "type": "object",
                "properties": {
                    "area_code": {
                        "type": "string",
                        "description": "気象庁エリアコード（例: '471000' = 沖縄本島地方）",
                    }
                },
                "required": ["area_code"],
            },
        ),
        Tool(
            name="get_weekly_forecast",
            description="エリアコードを指定して週間天気予報を取得する",
            inputSchema={
                "type": "object",
                "properties": {
                    "area_code": {
                        "type": "string",
                        "description": "気象庁エリアコード（例: '471000' = 沖縄本島地方）",
                    }
                },
                "required": ["area_code"],
            },
        ),
        Tool(
            name="get_overview",
            description="エリアコードを指定して天気概況テキストを取得する",
            inputSchema={
                "type": "object",
                "properties": {
                    "area_code": {
                        "type": "string",
                        "description": "気象庁エリアコード（例: '471000' = 沖縄本島地方）",
                    }
                },
                "required": ["area_code"],
            },
        ),
        Tool(
            name="search_area",
            description="エリア名（部分一致）からエリアコードを検索する",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "検索キーワード（例: '沖縄', '東京', '福岡'）",
                    }
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="get_warning",
            description="エリアコードを指定して警報・注意報の発表状況を取得する",
            inputSchema={
                "type": "object",
                "properties": {
                    "area_code": {
                        "type": "string",
                        "description": "気象庁エリアコード（例: '471000' = 沖縄本島地方）",
                    }
                },
                "required": ["area_code"],
            },
        ),
        Tool(
            name="get_early_warning",
            description="エリアコードを指定して早期注意情報（警報級の可能性）を取得する。今日・明日・明後日以降の大雨・暴風・大雪・波浪・高潮などの警報級現象の可能性（高・中・なし）を確認できる",
            inputSchema={
                "type": "object",
                "properties": {
                    "area_code": {
                        "type": "string",
                        "description": "気象庁エリアコード（例: '471000' = 沖縄本島地方）",
                    }
                },
                "required": ["area_code"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """ツール呼び出しのディスパッチャー"""
    if name == "get_forecast":
        result = await _get_forecast(arguments["area_code"])
    elif name == "get_weekly_forecast":
        result = await _get_weekly_forecast(arguments["area_code"])
    elif name == "get_overview":
        result = await _get_overview(arguments["area_code"])
    elif name == "search_area":
        result = await _search_area(arguments["name"])
    elif name == "get_warning":
        result = await _get_warning(arguments["area_code"])
    elif name == "get_early_warning":
        result = await _get_early_warning(arguments["area_code"])
    else:
        result = f"エラー: 未知のツール '{name}'"

    return [TextContent(type="text", text=result)]


async def _get_forecast(area_code: str) -> str:
    """3日間短期天気予報を取得して整形する"""
    area_name = AREA_CODE_MAP.get(area_code, area_code)
    url = FORECAST_URL.format(area_code=area_code)

    try:
        data = fetch_json(url)
    except requests.exceptions.RequestException as e:
        return f"エラー: 予報データの取得に失敗しました。\n詳細: {e}"

    # 短期予報（data[0]）を使用
    if not data or len(data) == 0:
        return "エラー: 予報データが空です。"

    short_term = data[0]
    lines = [f"【{area_name} 短期天気予報】", ""]

    for time_series in short_term.get("timeSeries", []):
        time_defines = time_series.get("timeDefines", [])
        areas = time_series.get("areas", [])
        if not areas:
            continue

        area = areas[0]

        # 天気情報
        if "weathers" in area:
            lines.append("■ 天気")
            for i, weather in enumerate(area["weathers"]):
                if i < len(time_defines):
                    date_str = format_date_jp(time_defines[i])
                    lines.append(f"  {date_str}: {weather}")
            lines.append("")

        # 降水確率
        if "pops" in area:
            lines.append("■ 降水確率")
            for i, pop in enumerate(area["pops"]):
                if i < len(time_defines):
                    date_str = format_date_jp(time_defines[i])
                    lines.append(f"  {date_str}: {pop}%")
            lines.append("")

        # 気温
        if "temps" in area:
            lines.append("■ 気温")
            for i, temp in enumerate(area["temps"]):
                if i < len(time_defines) and temp:
                    date_str = format_date_jp(time_defines[i])
                    lines.append(f"  {date_str}: {temp}°C")
            lines.append("")

    return "\n".join(lines).rstrip()


async def _get_weekly_forecast(area_code: str) -> str:
    """週間天気予報を取得して整形する"""
    area_name = AREA_CODE_MAP.get(area_code, area_code)
    url = FORECAST_URL.format(area_code=area_code)

    try:
        data = fetch_json(url)
    except requests.exceptions.RequestException as e:
        return f"エラー: 予報データの取得に失敗しました。\n詳細: {e}"

    # 週間予報（data[1]）を使用
    if not data or len(data) < 2:
        return "エラー: 週間予報データがありません。"

    weekly = data[1]
    lines = [f"【{area_name} 週間天気予報】", ""]

    for time_series in weekly.get("timeSeries", []):
        time_defines = time_series.get("timeDefines", [])
        areas = time_series.get("areas", [])
        if not areas:
            continue

        area = areas[0]

        # 天気コード → テキスト変換
        if "weatherCodes" in area:
            lines.append("■ 天気")
            for i, code in enumerate(area["weatherCodes"]):
                if i < len(time_defines):
                    date_str = format_date_jp(time_defines[i])
                    emoji = weather_code_to_emoji(code)
                    text = weather_code_to_text(code)
                    lines.append(f"  {date_str}: {emoji} {text}")
            lines.append("")

        # 降水確率
        if "pops" in area:
            lines.append("■ 降水確率")
            for i, pop in enumerate(area["pops"]):
                if i < len(time_defines) and pop:
                    date_str = format_date_jp(time_defines[i])
                    lines.append(f"  {date_str}: {pop}%")
            lines.append("")

        # 最高・最低気温
        if "tempsMin" in area or "tempsMax" in area:
            lines.append("■ 気温（最低 / 最高）")
            temps_min = area.get("tempsMin", [])
            temps_max = area.get("tempsMax", [])
            for i in range(max(len(temps_min), len(temps_max))):
                if i < len(time_defines):
                    date_str = format_date_jp(time_defines[i])
                    t_min = temps_min[i] if i < len(temps_min) and temps_min[i] else "—"
                    t_max = temps_max[i] if i < len(temps_max) and temps_max[i] else "—"
                    lines.append(f"  {date_str}: {t_min}°C / {t_max}°C")
            lines.append("")

    return "\n".join(lines).rstrip()


async def _get_overview(area_code: str) -> str:
    """天気概況テキストを取得する"""
    area_name = AREA_CODE_MAP.get(area_code, area_code)
    url = OVERVIEW_URL.format(area_code=area_code)

    try:
        data = fetch_json(url)
    except requests.exceptions.RequestException as e:
        return f"エラー: 概況データの取得に失敗しました。\n詳細: {e}"

    lines = [f"【{area_name} 天気概況】", ""]

    # 発表時刻
    published_at = data.get("publishingOffice", "")
    report_datetime = data.get("reportDatetime", "")
    if report_datetime:
        lines.append(f"発表: {format_date_jp(report_datetime)}")
    if published_at:
        lines.append(f"発表機関: {published_at}")
    lines.append("")

    # 概況テキスト
    text = data.get("text", "")
    if text:
        lines.append(text)
    else:
        lines.append("概況テキストがありません。")

    return "\n".join(lines)


async def _get_warning(area_code: str) -> str:
    """警報・注意報の発表状況を取得して整形する"""
    area_name = AREA_CODE_MAP.get(area_code, area_code)
    url = WARNING_URL.format(area_code=area_code)

    try:
        data = fetch_json(url)
    except requests.exceptions.RequestException as e:
        return f"エラー: 警報データの取得に失敗しました。\n詳細: {e}"

    report_datetime = data.get("reportDatetime", "")
    publishing_office = data.get("publishingOffice", "")
    headline = data.get("headlineText", "")

    lines = [f"【{area_name} 警報・注意報】", ""]
    if report_datetime:
        lines.append(f"発表: {format_date_jp(report_datetime)}")
    if publishing_office:
        lines.append(f"発表機関: {publishing_office}")
    if headline:
        lines.append(f"見出し: {headline}")
    lines.append("")

    # areaTypes[0]: 地域区分（class10）レベルで集計
    area_types = data.get("areaTypes", [])
    if not area_types:
        lines.append("警報・注意報データがありません。")
        return "\n".join(lines)

    # 発表中・解除以外を先に、解除を後にまとめる
    active_entries = []
    cleared_entries = []

    for area_info in area_types[0].get("areas", []):
        code = area_info.get("code", "")
        name_str = WARNING_AREA_NAME_MAP.get(code, code)
        warnings = area_info.get("warnings", [])

        active_warnings = []
        cleared_warnings = []

        for w in warnings:
            w_code = str(w.get("code", ""))
            status = w.get("status", "")
            w_name = WARNING_CODE_MAP.get(w_code, f"不明({w_code})")
            if status == "解除":
                cleared_warnings.append(f"{w_name}（{status}）")
            elif status:
                active_warnings.append(f"{w_name}（{status}）")

        if active_warnings:
            active_entries.append((name_str, active_warnings))
        if cleared_warnings:
            cleared_entries.append((name_str, cleared_warnings))

    if active_entries:
        lines.append("■ 発表中")
        for name_str, ws in active_entries:
            lines.append(f"  {name_str}: {' / '.join(ws)}")
        lines.append("")

    if cleared_entries:
        lines.append("■ 解除")
        for name_str, ws in cleared_entries:
            lines.append(f"  {name_str}: {' / '.join(ws)}")
        lines.append("")

    if not active_entries and not cleared_entries:
        lines.append("現在、発表中の警報・注意報はありません。")

    return "\n".join(lines).rstrip()


async def _get_early_warning(area_code: str) -> str:
    """早期注意情報（警報級の可能性）を取得して整形する"""
    area_name = AREA_CODE_MAP.get(area_code, area_code)
    url = PROBABILITY_URL.format(area_code=area_code)

    try:
        data = fetch_json(url)
    except requests.exceptions.RequestException as e:
        return f"エラー: 早期注意情報の取得に失敗しました。\n詳細: {e}"

    if not data:
        return "エラー: 早期注意情報データが空です。"

    # 可能性ラベルの表示変換（空文字は「低い」または「情報なし」）
    def fmt_prob(val: str) -> str:
        if val in ("高", "中"):
            return val
        if val == "なし":
            return "なし"
        return "—"

    # 警報級の可能性を持つプロパティのみ抽出するヘルパー
    EARLY_TYPES = {
        "雨の警報級の可能性",
        "雪の警報級の可能性",
        "風（風雪）の警報級の可能性",
        "波の警報級の可能性",
        "潮位の警報級の可能性",
    }

    lines = [f"【{area_name} 早期注意情報（警報級の可能性）】", ""]

    # 発表情報（data[0] から取得）
    first = data[0]
    report_datetime = first.get("reportDatetime", "")
    publishing_office = first.get("publishingOffice", "")
    if report_datetime:
        lines.append(f"発表: {format_date_jp(report_datetime)}")
    if publishing_office:
        lines.append(f"発表機関: {publishing_office}")
    lines.append("")

    # 短期（今日夜・明日）の警報級の可能性 — data[0] の timeSeries から抽出
    short_ts = first.get("timeSeries", [])
    short_early_ts = None
    for ts in short_ts:
        areas = ts.get("areas", [])
        if areas and "properties" in areas[0]:
            props = areas[0]["properties"]
            if any(p.get("type") in EARLY_TYPES for p in props):
                short_early_ts = ts
                break

    if short_early_ts:
        time_defines = short_early_ts.get("timeDefines", [])
        # 時刻ラベルを作成（例: 15日夜、16日昼）
        time_labels = []
        for td in time_defines:
            dt = datetime.fromisoformat(td).astimezone(JST)
            hour = dt.hour
            period = "夜" if hour >= 18 or hour < 6 else "昼前後"
            time_labels.append(f"{dt.month}/{dt.day}({['月','火','水','木','金','土','日'][dt.weekday()]}){period}")

        lines.append("■ 短期（今日夜～明日）")
        header = "  地域" + "".join(f"  {lbl}" for lbl in time_labels)
        lines.append(header)

        for area_info in short_early_ts.get("areas", []):
            code = area_info.get("code", "")
            area_label = WARNING_AREA_NAME_MAP.get(code, code)
            text = area_info.get("text", "")
            props = area_info.get("properties", [])

            # 警報級の可能性プロパティのみ表示
            printed_props = []
            for prop in props:
                ptype = prop.get("type", "")
                if ptype not in EARLY_TYPES:
                    continue
                probs = prop.get("probabilities", [])
                prob_strs = [fmt_prob(p) for p in probs]
                # 全て「—」なら省略
                if all(p == "—" for p in prob_strs):
                    continue
                printed_props.append(f"  [{area_label}] {ptype}: {' / '.join(prob_strs)}")

            if printed_props:
                lines.extend(printed_props)
                if text:
                    lines.append(f"    → {text}")
        lines.append("")

    # 週間（明後日以降）の警報級の可能性 — data[1]
    if len(data) > 1:
        weekly = data[1]
        weekly_ts = weekly.get("timeSeries", [])
        for ts in weekly_ts:
            time_defines = ts.get("timeDefines", [])
            areas = ts.get("areas", [])
            if not areas:
                continue
            props_sample = areas[0].get("properties", [])
            if not any(p.get("type") in EARLY_TYPES for p in props_sample):
                continue

            time_labels = [
                f"{datetime.fromisoformat(td).astimezone(JST).strftime('%m/%d')}"
                for td in time_defines
            ]

            lines.append("■ 週間（明後日以降）")
            lines.append("  地域: " + " / ".join(time_labels))

            for area_info in areas:
                code = area_info.get("code", "")
                area_label = WARNING_AREA_NAME_MAP.get(code, AREA_CODE_MAP.get(code, code))
                for prop in area_info.get("properties", []):
                    ptype = prop.get("type", "")
                    if ptype not in EARLY_TYPES:
                        continue
                    probs = prop.get("probabilities", [])
                    prob_strs = [fmt_prob(p) for p in probs]
                    if all(p == "—" for p in prob_strs):
                        continue
                    lines.append(f"  [{area_label}] {ptype}: {' / '.join(prob_strs)}")
            lines.append("")

    # 短期・週間ともに出力なし
    if len(lines) <= 4:
        lines.append("現在、警報級の可能性が高い・中程度の現象はありません。")

    return "\n".join(lines).rstrip()


async def _search_area(name: str) -> str:
    """エリア名の部分一致でエリアコードを検索する"""
    results = search_area_by_name(name)

    if not results:
        return f"「{name}」に一致するエリアが見つかりませんでした。"

    lines = [f"「{name}」の検索結果 ({len(results)}件)", ""]
    for item in results:
        lines.append(f"  {item['name']}: {item['code']}")

    return "\n".join(lines)


async def main():
    """MCPサーバーをstdioモードで起動する"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
