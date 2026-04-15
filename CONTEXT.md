# CONTEXT.md — セッション引き継ぎメモ

作成日: 2026-04-14

このファイルは、MCPサーバー実装を別セッションで再開するための引き継ぎメモです。

---

## このプロジェクトの目的

個人でMCPサーバーを立ててみる実験として、JMA（気象庁）APIラッパーを
MCPサーバーとして実装する。Claude Code から自然言語で天気情報を取得できるようにする。

---

## 実装方針

- `mcp`（Anthropic公式Python SDK）を使って stdioベースのMCPサーバーを作る
- JMA APIへのHTTPリクエストは `requests` ライブラリで行う
- 既存の `../jma_weather_report/` のコードを参考・流用する

### 公開するツール

| ツール名 | 引数 | 説明 |
|---|---|---|
| `get_forecast` | `area_code: str` | 3日間短期天気予報を取得 |
| `get_weekly_forecast` | `area_code: str` | 週間天気予報を取得 |
| `get_overview` | `area_code: str` | 概況テキストを取得 |
| `search_area` | `name: str` | エリア名からエリアコードを検索 |
| `get_warning` | `area_code: str` | 警報・注意報発表状況を取得 |
| `get_early_warning` | `area_code: str` | 早期注意情報（警報級の可能性）を取得 |
| `get_mdrr_data` | `element, prefecture, top_n` | 全国観測値（気温・降水量・風速・積雪等）を取得 |
| `get_daily_ranking` | `date, element` | 全国観測値ランキングを取得 |
| `get_record_update` | `date` | 観測史上1位の値 更新状況を取得 |
| `get_forecaster_comment` | `area_code: str` | 気象台からのコメントを取得 |
| `get_information` | `area_code, info_type` | 気象情報（府県・地方・全般）を取得 |
| `get_twoweek_forecast` | `region_num: str` | 2週間気温予報を取得（確率CSV利用） |
| `get_monthly_forecast` | `region_num: str` | 1ヶ月予報を取得（確率CSV利用） |
| `get_3month_forecast` | なし | 3ヶ月予報解説資料のURL・概要を返す |
| `get_6month_forecast` | なし | 暖候期/寒候期予報のURL・概要を返す |

---

## JMA APIエンドポイント

```
天気予報（短期＋週間）:
  GET https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json

概況テキスト:
  GET https://www.jma.go.jp/bosai/forecast/data/overview_forecast/{area_code}.json

エリア一覧:
  GET https://www.jma.go.jp/bosai/common/const/area.json

2週間気温予報 確率CSV:
  GET https://www.data.jma.go.jp/risk/probability/guidance/download2w.php?2week_t_{num}.csv
  ※ num は地域番号 11〜34（LONGFCST_REGION_MAP 参照）
  ※ col[10] に気温平年差が 0.1℃単位の整数で格納（÷10 で℃変換）

1ヶ月予報 確率CSV:
  GET https://www.data.jma.go.jp/risk/probability/guidance/download.php?month1_t_{num}.csv
  ※ 2週間CSVと同じ列構造、気温範囲は -5.0〜+5.0℃

3ヶ月予報・暖候期/寒候期予報 解説資料（JavaScript SPA のため静的取得不可）:
  https://www.data.jma.go.jp/cpd/longfcst/kaisetsu/?term=P3M
  https://www.data.jma.go.jp/cpd/longfcst/kaisetsu/?term=P6M
  → URL と概要情報を返すツールを実装済み
```

User-Agent を必ず付けること（JMA利用規約対応）:
```
"User-Agent": "jma_mcp/1.0 (educational use)"
```

---

## 流用できる既存コード

### `../jma_weather_report/src/fetch_weather.py`
- `fetch_json(url)` — URL からJSONを取得する関数（headers付き）
- `fetch_area_data(area_code)` — forecast + overview を一括取得する関数

### `../jma_weather_report/src/utils.py`
- `WEATHER_CODE_MAP` — 天気コード→説明テキストの辞書（TELOPS完全マッピング）
- `WEATHER_EMOJI_MAP` — 天気コード先頭1文字→絵文字の辞書
- `weather_code_to_text(code)` — 天気コードをテキストに変換
- `weather_code_to_emoji(code)` — 天気コードを絵文字に変換
- `now_jst()` — 現在のJST日時を返す
- `format_date_jp(dt)` — 「4月14日(火)」形式に変換

---

## 主要エリアコード（沖縄中心）

| エリア名 | コード |
|---|---|
| 沖縄本島地方 | 471000 |
| 宮古島地方 | 474000 |
| 八重山地方 | 473000 |
| 奄美地方 | 460040 |
| 鹿児島県 | 460100 |
| 福岡県 | 400000 |
| 東京都 | 130000 |
| 大阪府 | 270000 |
| 北海道（札幌）| 016000 |

全エリアは `https://www.jma.go.jp/bosai/common/const/area.json` から取得可能
（ファイルサイズが大きいため、必要な地方だけ `areas.py` に定数として持つ方針）

---

## MCPサーバーの最小実装パターン

```python
from mcp.server import Server
from mcp.server.stdio import stdio_server
import asyncio

server = Server("jma-mcp")

@server.tool()
async def get_forecast(area_code: str) -> str:
    """エリアコードを指定して3日間の天気予報を取得する"""
    # JMA APIを叩いてテキスト整形して返す
    ...

async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Claude Code への登録方法（フェーズ2）

`~/.claude/settings.json` の `mcpServers` に追加:

```json
{
  "mcpServers": {
    "jma": {
      "command": "python3",
      "args": ["/Users/masahiro/projects/jma_mcp/server.py"]
    }
  }
}
```

登録後、`/mcp` コマンドで認識を確認する。

---

## 予定している変更

### WARNING_CODE_MAP のレベル付き名称への変更（2026年5月28日午後以降）

**2026年5月28日（水）午後**に気象庁コード表が改定され、大雨・高潮・土砂災害系の警報・注意報に
レベル番号付きの正式名称が導入される。それ以降に `server.py` の `WARNING_CODE_MAP` を修正すること。

| コード | 現在 | 変更後 |
|---|---|---|
| `10` | 大雨注意報 | レベル２大雨注意報 |
| `3` | 大雨警報 | レベル３大雨警報 |
| `43` | 大雨危険警報 | レベル４大雨危険警報 |
| `33` | 大雨特別警報 | レベル５大雨特別警報 |
| `19` | 高潮注意報 | レベル２高潮注意報 |
| `8` | 高潮警報 | レベル３高潮警報 |
| `48` | 高潮危険警報 | レベル４高潮危険警報 |
| `38` | 高潮特別警報 | レベル５高潮特別警報 |
| `29` | 土砂災害注意報 | レベル２土砂災害注意報 |
| `9` | 土砂災害警報 | レベル３土砂災害警報 |
| `49` | 土砂災害危険警報 | レベル４土砂災害危険警報 |
| `39` | 土砂災害特別警報 | レベル５土砂災害特別警報 |

---

## 作業ステータス

- [x] PLAN.md 作成
- [x] CONTEXT.md 作成（本ファイル）
- [x] `requirements.txt` 作成
- [x] `areas.py` 作成（エリアコードマスター）
- [x] `server.py` 作成（MCPサーバー本体）
- [x] mcp パッケージインストール確認・実行テスト
- [x] `.mcp.json` に登録（※ settings.json ではなく .mcp.json が正しい形式）
- [ ] 動作確認（Claude Code を再起動して /mcp で認識確認後、「沖縄の天気は？」等）

## 登録ファイル変更メモ

CONTEXT.md の「Claude Code への登録方法」では `settings.json` に `mcpServers` を追加すると書いていたが、
Claude Code の settings.json スキーマには `mcpServers` フィールドが存在しない。
正しくは `.mcp.json` ファイルをプロジェクトルートに置く方式。
