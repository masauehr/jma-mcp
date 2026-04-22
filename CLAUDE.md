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
| 早期注意情報（警報級の可能性） | `get_early_warning` | `https://www.jma.go.jp/bosai/probability/#area_type=offices&area_code={area_code}&lang=ja` |
| 台風情報 | `get_information`（台風系） | `https://www.jma.go.jp/bosai/information/typhoon.html#` |
| その他気象情報 | `get_information` | `https://www.jma.go.jp/bosai/information/#area_type=offices&area_code={area_code}&format=table` |

### 早期注意情報と警報・注意報の区別

- 「早期注意情報」＝**警報級の可能性**（`/bosai/probability/`）
- 「警報・注意報」（`/bosai/warning/`）は別物。早期注意情報を聞かれたときに使わない。

### 📋 表示フォーマット（統一ルール）

#### 短期予報（今日・明日・明後日）
行＝項目、列＝日付 の縦横配置。

| 項目 | 今日（M/D(曜)） | 明日（M/D(曜)） | 明後日（M/D(曜)） |
|------|---------------|---------------|-----------------|
| 天気 | （天気） | （天気） | （天気） |
| 降水確率 | 0-6h:x% 6-12h:x% 12-18h:x% 18-24h:x% | 同左 | 同左 |
| 最高気温 | x℃ | x℃ | x℃ |
| 最低気温 | x℃ | x℃ | x℃ |

#### 週間予報（明後日〜7日後）
行＝日付、列＝項目 の横並び。

| 日付 | 天気 | 降水確率 | 最高気温 | 最低気温 | 信頼度 |
|------|------|---------|---------|---------|--------|
| M/D(曜) | （天気） | x% | x℃ | x℃ | A/B/C |

#### 早期注意情報（警報級の可能性）
行＝現象種別、列＝時間帯 の配置。値は「高」「中」「－」で統一。

| 現象 | 今夕まで | 今夜 | 明日昼 | 明日夜 | 明後日以降 |
|------|---------|------|--------|--------|-----------|
| 大雨 | 中 | － | － | － | － |
| 暴風 | － | － | － | － | － |
| 波浪 | － | － | － | － | － |
| 高潮 | － | － | － | － | － |
| 大雪 | － | － | － | － | － |

- 地域が複数ある場合は地域ごとに表を分けて表示する
- データなし・可能性なしは「－」で統一（空欄・「なし」は使わない）

#### 気象情報（府県気象情報等）
- **要約・省略せず全文をそのまま表示**すること
- XMLの `Body/Comment/Text` の内容を一字一句そのまま出力する

### 地域コードの参照

`~/projects/common/area.json` にローカルコピーあり。地域コード不明時はこちらを参照。

```python
import json
with open('/Users/masahiro/projects/common/area.json') as f:
    d = json.load(f)
for code, v in d['offices'].items():
    if 'キーワード' in v.get('name', ''):
        print(code, v)
```
