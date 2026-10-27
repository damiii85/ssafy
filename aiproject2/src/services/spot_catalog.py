"""파일럿 스팟 설정과 실제 수집 상태. 중심점은 공식 상권 경계가 아니다."""

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]


def load_spots():
    return json.loads((BASE_DIR / "config/daegu_spots.json").read_text(encoding="utf-8"))


def get_spot(spot_id):
    for spot in load_spots():
        if spot["id"] == spot_id:
            return spot
        for component in spot.get('components', []):
            if component['id'] == spot_id:
                return dict(component, parent_id=spot['id'])
    raise ValueError("등록되지 않은 스팟입니다.")


def data_paths(spot_id):
    get_spot(spot_id)
    directory = BASE_DIR / "data/raw/spots" / spot_id
    csv_path, meta_path = directory / "stores.csv", directory / "metadata.json"
    if spot_id == "dongseongro" and not csv_path.exists():
        return BASE_DIR / "data/raw/dongseongro_stores.csv", BASE_DIR / "data/raw/collection_metadata.json"
    return csv_path, meta_path


def inventory():
    result = []
    for spot in load_spots():
        csv_path, meta_path = data_paths(spot["id"])
        metadata = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        result.append({"스팟": spot["name"], "지역": spot["district"],
                       "상가 데이터": "수집 완료" if csv_path.exists() and metadata else "미수집",
                       "점포 수": metadata.get("count", None),
                       "수집일": metadata.get("collected_at_utc", "")[:10],
                       "매출·유동인구·임대료": "반경 자료 미확보",
                       "상권 보고서": "사용자 제공 PDF" if (BASE_DIR / "data/reports/상권보고서.pdf").exists() else "미확보"})
    return result
