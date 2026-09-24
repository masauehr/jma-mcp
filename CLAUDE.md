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

## 新体系（2026-05-28）と旧パスの禁止

2026-05-28 の防災気象情報の新体系への移行で、警報・早期注意情報・気象情報・台風情報の配信先が `data/r8/` 等に移った。**旧パスは 5/28（台風は 5/27）のまま更新されず古い内容が返る**ので、`server.py` の URL を旧パスに戻さないこと。
`r8` は将来変わりうる（`fetch_json_versioned` が 404 のとき自動探索する）。仕様・旧新対応表・コード表は [jma-mcp.md](jma-mcp.md)、全体の API 仕様は `../common/jma_api_spec.md`。
ツールは全23種（`get_warning_timeline`＝時系列情報、`get_typhoon`＝台風の実況・進路予報を追加）。**`server.py` を変更したら `jma_mcp_remote/server.py` にも同じ内容を反映**し（該当部分は同一）、`tests/` を実行する。

## テストの実行

`mcp` が導入された Python で実行する（`python3` が別の環境に解決される場合があるため絶対パスで）:
```bash
/opt/homebrew/bin/python3 -m unittest discover -s tests
```

## JMA情報の出力ルール

JMAツールの結果を回答に表示する際は、**必ず**出典リンクを末尾に付けること。
ツール結果に含まれるURLは不正確な場合があるため、以下の正しいURLを使うこと。

| 情報種別 | 使用ツール | 出典リンク |
|---|---|---|
| 短期天気予報 | `get_forecast` | `https://www.jma.go.jp/bosai/forecast/#area_type=offices&area_code={area_code}` |
| 週間天気予報 | `get_weekly_forecast` | `https://www.jma.go.jp/bosai/forecast/#area_type=offices&area_code={area_code}` |
| 警報・注意報（新体系: レベル付き） | `get_warning` | `https://www.jma.go.jp/bosai/map.html#contents=warning&areaCode={area_code}` |
| 時系列情報（警報等の見通し） | `get_warning_timeline` | `https://www.jma.go.jp/bosai/warning_timeline/` |
| 早期注意情報（警報級の可能性） | `get_early_warning` | `https://www.jma.go.jp/bosai/probability/#area_type=offices&area_code={area_code}&lang=ja` |
| 台風情報（実況・進路予報） | `get_typhoon` | `https://www.jma.go.jp/bosai/information/typhoon.html#` |
| その他気象情報 | `get_information` | `https://www.jma.go.jp/bosai/information/#area_type=offices&area_code={area_code}&format=table` |
| 潮位観測（現在値・推移） | `get_tide_observation` | `https://www.jma.go.jp/bosai/tidelevel/#area_type=class20s&area_code={area_code}&point_code={station_code}&filter=0&class30s={class30_code}` |
| 潮位観測所の検索 | `search_tide_stations` | `https://www.jma.go.jp/bosai/tidelevel/` |

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
新形式（2026-05-28〜）: 短期は**6時間ごと（明後日まで）**、週間は**日ごと**。行＝現象種別、列＝時間区分。値は「高」「中」「－」で統一。
列見出しは各区分の**開始時刻**（`M/D(曜)H時〜`）をそのまま使う（「今夕まで」「今夜」などの呼び替えはしない）。
`get_early_warning` の出力（地域ごとの表・全現象行・気象台コメント付き）は、この形式に合わせてある。

**短期（明後日まで・6時間ごと）** ※最後の2区分のみ12時間

| 現象 | 9/24(木)12時〜 | 9/24(木)18時〜 | 9/25(金)0時〜 | 9/25(金)6時〜 | 9/25(金)12時〜 | 9/25(金)18時〜 | 9/26(土)0時〜 | 9/26(土)12時〜 |
|------|------|------|------|------|------|------|------|------|
| 大雨 | 中 | － | － | － | － | － | － | － |
| 土砂災害 | － | － | － | － | － | － | － | － |
| 雪 | － | － | － | － | － | － | － | － |
| 風（風雪） | － | － | － | － | － | － | － | － |
| 波 | － | － | － | － | － | － | － | － |
| 潮位 | － | － | － | － | － | － | － | － |

**週間（明後日以降・日ごと）**

| 現象 | M/D(曜) | M/D(曜) | M/D(曜) | M/D(曜) |
|------|------|------|------|------|
| 雨 | － | － | － | － |
| 雪 | － | － | － | － |
| 風（風雪） | － | － | 中 | 中 |
| 波 | － | － | 中 | 中 |
| 潮位 | － | － | － | 中 |

- 現象名は気象庁の表記のまま（短期は「大雨」と「土砂災害」に分かれ、週間は「雨」）
- 地域が複数ある場合は地域ごとに表を分ける
- データなし・可能性なしは「－」で統一（空欄・「なし」は使わない。雪の「なし」も「－」）
- 発表時刻は時分まで表示。各地域の気象台コメントは、表の後に地域名を付けて省略せず表示
- 全期間が「－」の現象行も省略せず表示する（「可能性なし」であることを示すため）

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
