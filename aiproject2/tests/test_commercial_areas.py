import json
import tempfile
import unittest
from unittest.mock import Mock

from src.collectors.collect_commercial_areas import fetch_rows, save_rows


def response(data, total):
    return Mock(status_code=200, json=Mock(return_value={"data": data, "totalCount": total}))


class CommercialAreaTests(unittest.TestCase):
    def test_pagination_and_header_auth(self):
        session = Mock()
        session.get.side_effect = [response([{"구분": "대구", "2023년": 247}], 2),
                                   response([{"구분": "서울", "2023년": 849}], 2)]
        rows = fetch_rows("fake%2Bkey", per_page=1, session=session)
        self.assertEqual(len(rows), 2)
        self.assertEqual(session.get.call_args.kwargs["params"]["page"], 2)
        self.assertNotIn("serviceKey", session.get.call_args.kwargs["params"])
        self.assertEqual(session.get.call_args.kwargs["headers"]["Authorization"], "Infuser fake+key")
        with tempfile.TemporaryDirectory() as directory:
            path, csv_path = save_rows(rows, directory)
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["data"], rows)
            self.assertEqual(saved["row_count"], 2)
            self.assertNotIn("fake+key", path.read_text(encoding="utf-8"))
            self.assertTrue(csv_path.exists())

    def test_errors_do_not_leak_key(self):
        session = Mock()
        session.get.return_value = Mock(status_code=401)
        with self.assertRaises(ValueError) as caught:
            fetch_rows("secret-test-key", session=session)
        self.assertIn("401", str(caught.exception))
        self.assertNotIn("secret-test-key", str(caught.exception))
        session.get.side_effect = [response([{"구분": "대구"}], 2), response([], 2)]
        with self.assertRaises(ValueError):
            fetch_rows("test", session=session)


if __name__ == "__main__":
    unittest.main()
