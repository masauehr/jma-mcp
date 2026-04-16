# CLAUDE.md — jma_mcp

## このプロジェクトについて

JMA（気象庁）APIをMCPサーバーとして公開するプロジェクト。
Claude Code から自然言語で天気予報・概況情報を取得できるようにする。

## 作業の続き方

**CONTEXT.md を最初に読むこと。** セッション引き継ぎ情報（実装方針・流用コード・APIエンドポイント等）がまとめてある。

## 実装の優先順位

1. `requirements.txt` の作成
2. `areas.py` の作成（エリアコードマスター）
3. `server.py` の作成（MCPサーバー本体）
4. 動作確認・Claude Code への登録

## 参照すべき既存コード

- `../jma_weather_report/src/fetch_weather.py` — JMA APIの取得ロジック
- `../jma_weather_report/src/utils.py` — 天気コードマッピング

## 技術スタック

- Python 3.x
- `mcp`（Anthropic公式SDK）— stdioベースのMCPサーバー
- `requests` — HTTP通信

## JMA情報の出力ルール

JMAツールの結果を回答に表示する際は、**必ず**出典リンクを末尾に付けること。
ツール結果に含まれるURLは不正確な場合があるため、以下の正しいURLを使うこと。

| 情報種別 | 使用ツール | 出典リンク |
|---|---|---|
| 短期天気予報 | `get_forecast` | `https://www.jma.go.jp/bosai/forecast/#area_type=offices&area_code={area_code}` |
| 週間天気予報 | `get_weekly_forecast` | `https://www.jma.go.jp/bosai/forecast/#area_type=offices&area_code={area_code}` |
| 早期注意情報 | `get_early_warning` | `https://www.jma.go.jp/bosai/map.html#contents=probability&areaCode={area_code}` |
| 台風情報 | `get_information`（台風系） | `https://www.jma.go.jp/bosai/information/typhoon.html#` |
| その他気象情報 | `get_information` | `https://www.jma.go.jp/bosai/information/` |
