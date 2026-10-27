
from pathlib import Path
from math import radians, sin, cos, sqrt, atan2

import pandas as pd


# ==========================================
# 1. 데이터 경로 설정
# ==========================================

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_PATH = (
    BASE_DIR / "data" / "processed"
    / "daegu_bus_stops.csv"
)

DEFAULT_RADIUS = 200


# ==========================================
# 2. 거리 계산
# ==========================================

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Haversine 공식으로 두 좌표 사이의
    직선거리(미터)를 계산합니다.
    """

    R = 6371000

    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        sin(dlat / 2) ** 2
        + cos(lat1) * cos(lat2)
        * sin(dlon / 2) ** 2
    )

    c = 2 * atan2(
        sqrt(a),
        sqrt(max(0, 1 - a))
    )

    return R * c


# ==========================================
# 3. 버스 접근성 분석
# ==========================================

def analyze_bus_access(
    latitude,
    longitude,
    radius=DEFAULT_RADIUS
):
    """
    지정 좌표 주변 버스정류장 접근성 분석
    """

    if radius <= 0:
        raise ValueError(
            "분석 반경은 0보다 커야 합니다."
        )

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"버스정류장 데이터가 없습니다: {DATA_PATH}"
        )

    df = pd.read_csv(DATA_PATH)

    # 좌표 숫자형 변환
    df["lat"] = pd.to_numeric(
        df["lat"],
        errors="coerce"
    )

    df["lon"] = pd.to_numeric(
        df["lon"],
        errors="coerce"
    )

    # 좌표가 없는 데이터 제외
    df = df.dropna(
        subset=["lat", "lon"]
    ).copy()

    # 정류장 ID 기준 중복 제거
    df = df.drop_duplicates(
        subset=["stop_id"]
    )

    # 기준점과의 거리 계산
    df["distance"] = df.apply(
        lambda row: calculate_distance(
            latitude,
            longitude,
            row["lat"],
            row["lon"]
        ),
        axis=1
    )

    # 거리순 정렬
    df = df.sort_values("distance")

    # 지정 반경 안의 정류장
    nearby = df[
        df["distance"] <= radius
    ].copy()

    # 가장 가까운 정류장
    nearest = df.iloc[0] if not df.empty else None

    # 결과 정리
    result = {
        "latitude": latitude,
        "longitude": longitude,
        "radius": radius,
        "bus_stop_count": len(nearby),
        "nearest_stop": (
            nearest["stop_name"]
            if nearest is not None
            else None
        ),
        "nearest_distance": (
            round(float(nearest["distance"]), 1)
            if nearest is not None
            else None
        ),
        "nearby_stops": [
            {
                "name": row["stop_name"],
                "distance": round(
                    float(row["distance"]), 1
                )
            }
            for _, row in nearby.iterrows()
        ]
    }

    return result


# ==========================================
# 4. 실행 테스트
# ==========================================

if __name__ == "__main__":

    LATITUDE = 35.870
    LONGITUDE = 128.595

    print("\n===== SPOT CHECK 버스 접근성 분석 =====")

    for radius in [100, 200, 300]:

        result = analyze_bus_access(
            latitude=LATITUDE,
            longitude=LONGITUDE,
            radius=radius
        )

        print(f"\n===== 반경 {radius}m =====")
        print(
            f"주변 정류장 수: "
            f"{result['bus_stop_count']}개"
        )
        print(
            f"가장 가까운 정류장: "
            f"{result['nearest_stop']}"
        )
        print(
            f"직선거리: "
            f"{result['nearest_distance']}m"
        )

        print("주변 정류장 목록:")

        for stop in result["nearby_stops"][:5]:
            print(
                f"  - {stop['name']}: "
                f"{stop['distance']}m"
            )
