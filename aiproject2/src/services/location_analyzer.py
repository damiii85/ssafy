
from pathlib import Path
from math import radians, sin, cos, sqrt, atan2

import pandas as pd


# ==========================================
# 1. 데이터 경로 설정
# ==========================================

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_PATH = (
    BASE_DIR / "data" / "raw" / "dongseongro_stores.csv"
)

DEFAULT_RADIUS = 200


# ==========================================
# 2. 두 좌표 사이의 거리 계산
# ==========================================

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    두 지점 사이의 직선거리 계산 (미터)
    Haversine 공식 사용
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
        + cos(lat1)
        * cos(lat2)
        * sin(dlon / 2) ** 2
    )

    c = 2 * atan2(
        sqrt(a),
        sqrt(max(0, 1 - a))
    )

    return R * c


# ==========================================
# 3. 입지 분석 함수
# ==========================================

def analyze_location(
    latitude,
    longitude,
    radius=DEFAULT_RADIUS
):
    """
    지정한 좌표 주변의 상가 데이터를 분석합니다.

    Parameters
    ----------
    latitude : float
        분석 기준 위도

    longitude : float
        분석 기준 경도

    radius : int
        분석 반경 (미터), 기본값 200m
    """

    if radius <= 0:
        raise ValueError("분석 반경은 0보다 커야 합니다.")

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"상가 데이터 파일이 없습니다: {DATA_PATH}"
        )

    # CSV 파일 불러오기
    df = pd.read_csv(DATA_PATH)

    # 위도 / 경도 숫자로 변환
    df["lat"] = pd.to_numeric(
        df["lat"],
        errors="coerce"
    )

    df["lon"] = pd.to_numeric(
        df["lon"],
        errors="coerce"
    )

    # 좌표가 없는 상가 제외
    df = df.dropna(subset=["lat", "lon"]).copy()

    # 각 상가와 기준점 사이 거리 계산
    df["distance"] = df.apply(
        lambda row: calculate_distance(
            latitude,
            longitude,
            row["lat"],
            row["lon"]
        ),
        axis=1
    )

    # 분석 반경 안에 있는 상가만 추출
    nearby = df[
        df["distance"] <= radius
    ].copy()

    # 음식 업종만 추출
    food = nearby[
        nearby["indsLclsNm"] == "음식"
    ].copy()

    # 카페
    cafes = food[
        food["indsSclsNm"] == "카페"
    ]

    # 일반 식당
    restaurant_categories = [
        "한식",
        "일식",
        "중식",
        "서양식",
        "동남아시아"
    ]

    restaurants = food[
        food["indsMclsNm"].isin(
            restaurant_categories
        )
    ]

    # 주점
    pubs = food[
        food["indsMclsNm"] == "주점"
    ]

    # 음식 업종 중분류별 점포 수
    food_category_counts = (
        food["indsMclsNm"]
        .value_counts()
        .to_dict()
    )

    # 음식 업종 소분류별 점포 수
    food_subcategory_counts = (
        food["indsSclsNm"]
        .value_counts()
        .to_dict()
    )

    # 분석 결과
    result = {
        "latitude": latitude,
        "longitude": longitude,
        "radius": radius,
        "total_stores": len(nearby),
        "food_stores": len(food),
        "cafes": len(cafes),
        "restaurants": len(restaurants),
        "pubs": len(pubs),
        "food_category_counts": food_category_counts,
        "food_subcategory_counts": food_subcategory_counts
    }

    return result


# ==========================================
# 4. 테스트 실행
# ==========================================

if __name__ == "__main__":

    # 기존 동성로 중심 좌표
    LATITUDE = 35.870
    LONGITUDE = 128.595

    # 비교할 분석 반경
    radii = [100, 200, 300, 500]

    print("\n===== SPOT CHECK 입지 분석 =====")
    print(
        f"기준 좌표: {LATITUDE}, {LONGITUDE}"
    )

    for radius in radii:

        result = analyze_location(
            latitude=LATITUDE,
            longitude=LONGITUDE,
            radius=radius
        )

        print(f"\n===== 반경 {radius}m =====")
        print(f"전체 상가: {result['total_stores']}개")
        print(f"음식 업종: {result['food_stores']}개")
        print(f"카페: {result['cafes']}개")
        print(f"일반 식당: {result['restaurants']}개")
        print(f"주점: {result['pubs']}개")

    print("\n분석 완료!")
