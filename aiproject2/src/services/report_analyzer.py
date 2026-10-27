
from pathlib import Path
import sys
import json

import pandas as pd


# ==========================================
# 1. 프로젝트 경로 설정
# ==========================================

BASE_DIR = Path(__file__).resolve().parents[2]

# 직접 실행할 때도 src 패키지를 불러올 수 있도록 설정
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.services.location_analyzer import analyze_location
from src.services.bus_analyzer import analyze_bus_access


SUBWAY_PATH = (
    BASE_DIR
    / "data"
    / "processed"
    / "dongseongro_subway.csv"
)

REPORT_PATH = (
    BASE_DIR
    / "data"
    / "processed"
    / "location_report.json"
)


# ==========================================
# 2. 최신 도시철도 승차인원 조회
# ==========================================

def get_subway_summary():

    if not SUBWAY_PATH.exists():
        return {
            "available": False,
            "message": "도시철도 데이터가 없습니다."
        }

    df = pd.read_csv(SUBWAY_PATH)

    if df.empty:
        return {
            "available": False,
            "message": "도시철도 데이터가 비어 있습니다."
        }

    # 최신 연월 선택
    df = df.sort_values(["년", "월"])
    latest = df.iloc[-1]

    return {
        "available": True,
        "year": int(latest["년"]),
        "month": int(latest["월"]),
        "jungangro": int(latest["중앙로"]),
        "banwoldang": int(latest["반월당역"]),
        "total": int(latest["인근역_승차인원_합계"]),
        "note": (
            "도시철도역 월별 승차인원입니다. "
            "후보지 앞 유동인구를 의미하지 않습니다."
        )
    }


# ==========================================
# 3. 통합 입지 분석
# ==========================================

def analyze_report(
    latitude,
    longitude,
    radius=200,
    location_name="동성로 후보지"
):
    """
    상가 경쟁 환경 + 버스 접근성 +
    동성로 인근 도시철도 승차인원 통합
    """

    # 상가 분석
    stores = analyze_location(
        latitude=latitude,
        longitude=longitude,
        radius=radius
    )

    # 버스 접근성
    buses = analyze_bus_access(
        latitude=latitude,
        longitude=longitude,
        radius=radius
    )

    # 도시철도 이용 규모
    subway = get_subway_summary()

    report = {
        "location_name": location_name,
        "coordinates": {
            "latitude": latitude,
            "longitude": longitude
        },
        "radius_m": radius,
        "commercial_analysis": {
            "total_stores": stores["total_stores"],
            "food_stores": stores["food_stores"],
            "cafes": stores["cafes"],
            "restaurants": stores["restaurants"],
            "pubs": stores["pubs"],
            "food_category_counts": (
                stores["food_category_counts"]
            ),
            "food_subcategory_counts": (
                stores["food_subcategory_counts"]
            )
        },
        "transport_analysis": {
            "bus": {
                "stop_count": buses["bus_stop_count"],
                "nearest_stop": buses["nearest_stop"],
                "nearest_distance_m": (
                    buses["nearest_distance"]
                ),
                "nearby_stops": buses["nearby_stops"],
                "data_scope": (
                    "전국 정류장 API의 일부 페이지에서 "
                    "수집한 대구 정류장 데이터"
                )
            },
            "subway": subway
        },
        "limitations": [
            "상가 및 정류장 거리는 직선거리 기준입니다.",
            "상가 데이터는 동성로 중심 반경 1km에서 "
            "수집되었으므로 경계 부근 후보지는 "
            "점포 수가 과소 집계될 수 있습니다.",
            "버스정류장 데이터는 일부 페이지 수집본으로 "
            "누락된 정류장이 있을 수 있습니다.",
            "도시철도 승차인원은 후보지별 "
            "실제 유동인구가 아닙니다.",
            "매출, 임대료, 실제 수익성은 분석하지 않습니다."
        ]
    }

    return report


# ==========================================
# 4. 테스트 및 JSON 저장
# ==========================================

if __name__ == "__main__":

    result = analyze_report(
        latitude=35.870,
        longitude=128.595,
        radius=200,
        location_name="동성로 중심 후보지"
    )

    REPORT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        REPORT_PATH,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            result,
            f,
            ensure_ascii=False,
            indent=2
        )

    print("\n===== SPOT CHECK 통합 분석 =====")

    print(f"분석 위치: {result['location_name']}")
    print(f"분석 반경: {result['radius_m']}m")

    commercial = result["commercial_analysis"]
    bus = result["transport_analysis"]["bus"]
    subway = result["transport_analysis"]["subway"]

    print("\n[상가 경쟁 환경]")
    print(f"전체 상가: {commercial['total_stores']}개")
    print(f"음식 업종: {commercial['food_stores']}개")
    print(f"카페: {commercial['cafes']}개")
    print(f"일반 식당: {commercial['restaurants']}개")
    print(f"주점: {commercial['pubs']}개")

    print("\n[버스 접근성]")
    print(f"주변 정류장: {bus['stop_count']}개")
    print(f"가장 가까운 정류장: {bus['nearest_stop']}")
    print(f"직선거리: {bus['nearest_distance_m']}m")

    print("\n[도시철도 이용 규모]")

    if subway["available"]:
        print(
            f"기준: {subway['year']}년 "
            f"{subway['month']}월"
        )
        print(
            f"중앙로역: {subway['jungangro']:,}명"
        )
        print(
            f"반월당역: {subway['banwoldang']:,}명"
        )
        print(
            f"두 역 합계: {subway['total']:,}명"
        )
    else:
        print(subway["message"])

    print(f"\n리포트 저장 완료: {REPORT_PATH}")
