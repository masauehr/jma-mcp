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

### 公開するツール（予定）

| ツール名 | 引数 | 説明 |
|---|---|---|
| `get_forecast` | `area_code: str` | 3日間短期天気予報を取得 |
| `get_weekly_forecast` | `area_code: str` | 週間天気予報を取得 |
| `get_overview` | `area_code: str` | 概況テキストを取得 |
| `search_area` | `name: str` | エリア名からエリアコードを検索 |

---

## JMA APIエンドポイント

```
天気予報（短期＋週間）:
  GET https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json

概況テキスト:
  GET https://www.jma.go.jp/bosai/forecast/data/overview_forecast/{area_code}.json

エリア一覧:
  GET https://www.jma.go.jp/bosai/common/const/area.json
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
