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
FORECAST_URL = "https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json"
OVERVIEW_URL = "https://www.jma.go.jp/bosai/forecast/data/overview_forecast/{area_code}.json"

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
