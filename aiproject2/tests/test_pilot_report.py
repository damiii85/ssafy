import json
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
from streamlit.testing.v1 import AppTest

from src.services.pilot_report import match_addresses, build_report, parse_request, load_spot_data
from src.services.spot_catalog import load_spots


def sample_frame():
    return pd.DataFrame([
        {"bizesId": "1", "bizesNm": "A", "rdnmAdr": "대구광역시 중구 테스트로 10", "lat": 35.870,
         "lon": 128.595, "indsLclsNm": "소매", "indsMclsNm": "의류", "indsSclsNm": "여성 의류 소매업"},
        {"bizesId": "2", "bizesNm": "B", "rdnmAdr": "대구광역시 중구 테스트로 100", "lat": 35.8701,
         "lon": 128.595, "indsLclsNm": "음식", "indsMclsNm": "비알코올", "indsSclsNm": "카페"},
        {"bizesId": "3", "bizesNm": "C", "rdnmAdr": "대구광역시 중구 테스트로 12", "lat": 35.879,
         "lon": 128.595, "indsLclsNm": "소매", "indsMclsNm": "의류", "indsSclsNm": "여성 의류 소매업"},
    ])


class PilotTests(unittest.TestCase):
    def test_exact_building_number_and_unknown(self):
        df = sample_frame()
        self.assertEqual(match_addresses("테스트로 10", df), ["대구광역시 중구 테스트로 10"])
        self.assertEqual(match_addresses("테스트로 1", df), [])
        self.assertEqual(match_addresses("서울 테스트로 10", df), [])

    def test_full_csv_count_and_union_no_double_count(self):
        df = sample_frame()
        meta = {"center_lat": 35.87, "center_lon": 128.595, "radius_m": 1000,
                "collected_at_utc": "2026-10-21", "source": "test"}
        categories = [{"level": "middle", "name": "의류"}, {"level": "small", "name": "여성 의류 소매업"}]
        report = build_report("dongseongro", df, meta, df.iloc[0].rdnmAdr, categories)
        self.assertEqual(report["total_stores"], 2)
        self.assertEqual(report["competitor_count"], 1)
        self.assertTrue(report["coverage_complete"])
        report = build_report("dongseongro", df, meta, "경계", categories, coordinates=(35.878, 128.595))
        self.assertFalse(report["coverage_complete"])
        with self.assertRaises(ValueError):
            build_report("dongseongro", df, meta, "다른 지역", categories, coordinates=(35.94, 128.56))

    def test_parse_rejects_hallucinated_category_or_address(self):
        llm = Mock()
        llm.invoke.return_value = SimpleNamespace(content=json.dumps({
            "address": "테스트로 10", "categories": [{"level": "small", "name": "여성 의류 소매업"}]}))
        result = parse_request("테스트로 10에서 옷가게", sample_frame(), llm=llm)
        self.assertEqual(result["address"], "")
        self.assertEqual(result['intent'], 'spot_overview')
        llm.invoke.return_value = SimpleNamespace(content=json.dumps({
            "address": "", "categories": [{"level": "small", "name": "없는 업종"}]}))
        with self.assertRaises(ValueError):
            parse_request("창업", sample_frame(), llm=llm)

    def test_real_spot_datasets(self):
        for spot in load_spots():
            with self.subTest(spot=spot["id"]):
                df, meta = load_spot_data(spot["id"])
                self.assertEqual(len(df), meta["count"])
                self.assertEqual(df.bizesId.nunique(), len(df))
                self.assertEqual(meta["center_lat"], spot["latitude"])
                self.assertEqual(meta["center_lon"], spot["longitude"])
                self.assertEqual(meta["radius_m"], 1000)
                if spot.get("anchor_stop_id"):
                    self.assertEqual(meta["anchor_stop_id"], spot["anchor_stop_id"])
                    self.assertEqual(meta["api_total"], len(df))

    def test_ui_spot_switch_chat_and_history(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=20).run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.chat_input), 0)
        app.button(key="start").click().run()
        self.assertEqual(len([b for b in app.button if b.key and b.key.startswith("select_")]), 5)
        app.button(key="select_daegu_downtown").click().run()
        self.assertEqual(len(app.chat_input), 1)
        df, _ = load_spot_data("dongseongro")
        address = "대구광역시 중구 중앙대로 412-21"
        request = {"address": address, "categories": [{"level": "small", "name": "카페"}], "clarification": ""}
        with patch("src.services.pilot_report.parse_request", return_value=request):
            app.chat_input[0].set_value(address + " 카페").run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.session_state["spot_sessions"]["daegu_downtown"]["reports"]), 1)
        app.selectbox(key='chat_spot_selector').set_value('suseongmot').run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["spot_sessions"]["suseongmot"]["messages"], [])
        app.selectbox(key='chat_spot_selector').set_value('daegu_downtown').run()
        self.assertEqual(len(app.session_state["spot_sessions"]["daegu_downtown"]["reports"]), 1)


if __name__ == "__main__":
    unittest.main()
