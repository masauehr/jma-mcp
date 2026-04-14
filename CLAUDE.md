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
