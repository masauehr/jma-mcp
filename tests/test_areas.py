"""areas.py（エリアコードマスター）のテスト

実行:
  /opt/homebrew/bin/python3 -m unittest discover -s tests -v
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from areas import AREA_CODE_MAP, search_area_by_name  # noqa: E402

AREA_JSON = Path(__file__).resolve().parents[2] / "common" / "area.json"


class TestAreas(unittest.TestCase):
    @unittest.skipUnless(AREA_JSON.exists(), "common/area.json が無い")
    def test_気象庁のofficesと全件一致(self):
        offices = json.loads(AREA_JSON.read_text(encoding="utf-8"))["offices"]
        self.assertEqual(AREA_CODE_MAP, {c: v["name"] for c, v in offices.items()})

    def test_北海道の予報区(self):
        self.assertEqual(AREA_CODE_MAP["014100"], "釧路・根室地方")
        self.assertEqual(AREA_CODE_MAP["017000"], "渡島・檜山地方")
        self.assertEqual(AREA_CODE_MAP["014030"], "十勝地方")
        self.assertNotIn("018000", AREA_CODE_MAP)
        self.assertNotIn("019000", AREA_CODE_MAP)

    def test_気象台名や地方名で検索できる(self):
        self.assertEqual([r["code"] for r in search_area_by_name("函館")], ["017000"])
        self.assertEqual([r["code"] for r in search_area_by_name("網走")], ["013000"])
        self.assertEqual(len(search_area_by_name("北海道")), 8)


if __name__ == "__main__":
    unittest.main()
