# PLAN.md — jma_mcp 実装計画

最終更新: 2026-04-14

## プロジェクト目標

気象庁（JMA）APIをMCP（Model Context Protocol）サーバーとして公開し、
Claude Code から自然言語で天気予報・概況情報を取得できるようにする。
既存の `jma_weather_report` プロジェクトのロジックを再利用する。

---

## フェーズ1：環境構築・基本サーバー実装（優先）

### タスク1-1: プロジェクト初期化
- [ ] ディレクトリ構成作成
- [ ] PLAN.md 作成
- [ ] `requirements.txt` 作成（mcp, requests）
- [ ] `.gitignore` 作成

### タスク1-2: MCPサーバー本体の実装
- [ ] `server.py` 実装
  - JMA APIエンドポイントへのHTTPリクエスト
  - MCPツールとして以下を公開:

| ツール名 | 説明 |
|---|---|
| `get_forecast` | エリアコードで3日間の短期天気予報を取得 |
| `get_weekly_forecast` | エリアコードで週間天気予報を取得 |
| `get_overview` | エリアコードで概況テキストを取得 |
| `search_area` | エリア名（都道府県・地方名）からエリアコードを検索 |

### タスク1-3: 主要エリアコードマスターの整備
- [ ] `areas.py` 実装
  - 主要地方・都市のエリアコード定数を定義
  - 検索用のリスト/辞書を提供

---

## フェーズ2：Claude Code への統合

### タスク2-1: Claude Code への設定追加
- [ ] `~/.claude/settings.json` の `mcpServers` セクションに本サーバーを追加
- [ ] `/mcp` コマンドで認識されることを確認

### タスク2-2: 動作確認
- [ ] 「沖縄の天気は？」などの自然言語クエリで正しく動作することを確認
- [ ] エラーハンドリング（エリアコード不正・API失敗）の確認

---

## フェーズ3：機能拡張（後回し）

- [ ] `get_amedas` — AMeDAS観測データ（気温・雨量・風速）の取得
- [ ] `get_warning` — 注意報・警報の取得
- [ ] `get_typhoon` — 台風情報の取得
- [ ] エリアコードの自動補完（area.json の全件ロード）

---

## ディレクトリ構成（予定）

```
jma_mcp/
├── PLAN.md           # 本ファイル
├── server.py         # MCPサーバー本体
├── areas.py          # エリアコードマスター
├── requirements.txt  # 依存パッケージ
└── .gitignore
```

---

## 技術スタック

| 項目 | 採用技術 | 理由 |
|---|---|---|
| 言語 | Python 3.x | 既存プロジェクトとの統一 |
| MCPフレームワーク | `mcp`（Anthropic公式SDK） | 標準・シンプル |
| HTTPクライアント | `requests` | 既存コードとの統一 |
| 通信方式 | stdio（標準入出力） | Claude Code ローカル連携の標準構成 |

---

## 参考: JMA APIエンドポイント

| API | URL |
|---|---|
| 天気予報（短期＋週間） | `https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json` |
| 概況テキスト | `https://www.jma.go.jp/bosai/forecast/data/overview_forecast/{area_code}.json` |
| エリア一覧 | `https://www.jma.go.jp/bosai/common/const/area.json` |

## 参考: 既存プロジェクト

| プロジェクト | 再利用箇所 |
|---|---|
| `jma_weather_report/src/fetch_weather.py` | JMA APIの取得ロジック |
| `jma_weather_report/src/utils.py` | 天気コードマッピング・JST変換 |
