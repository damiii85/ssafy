
from pathlib import Path
import os
import json
import time

import pandas as pd
import requests
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

API_KEY = os.getenv("BUS_API_KEY")

API_URL = (
    "https://api.odcloud.kr/api/15067528/v1/"
    "uddi:f74b9799-9db1-4754-a5d0-b66e2ae705f3"
)

RAW_PATH = BASE_DIR / "data/raw/daegu_bus_stops.json"
CSV_PATH = BASE_DIR / "data/processed/daegu_bus_stops.csv"

# 우선 대구 데이터가 많이 발견된 구간
START_PAGE = 35
END_PAGE = 45
PER_PAGE = 1000


def save_data(stops):
    RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(RAW_PATH, "w", encoding="utf-8") as f:
        json.dump(stops, f, ensure_ascii=False, indent=2)

    df = pd.DataFrame(stops)

    if df.empty:
        return

    df = df.rename(columns={
        "정류장번호": "stop_id",
        "정류장명": "stop_name",
        "위도": "lat",
        "경도": "lon",
        "도시명": "city",
        "관리도시명": "managed_city",
    })

    if "lat" in df.columns and "lon" in df.columns:
        df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
        df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
        df = df.dropna(subset=["lat", "lon"])

    df = df.drop_duplicates()

    df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")


def collect_bus_stops():
    if not API_KEY:
        raise ValueError(".env에 BUS_API_KEY가 없습니다.")

    # 기존에 저장한 데이터가 있다면 이어서 사용
    if RAW_PATH.exists():
        with open(RAW_PATH, "r", encoding="utf-8") as f:
            all_stops = json.load(f)
    else:
        all_stops = []

    for page in range(START_PAGE, END_PAGE + 1):
        for attempt in range(3):
            try:
                response = requests.get(
                    API_URL,
                    params={
                        "serviceKey": API_KEY,
                        "page": page,
                        "perPage": PER_PAGE,
                        "returnType": "JSON",
                    },
                    timeout=30,
                )
                response.raise_for_status()
                result = response.json()
                break
            except requests.RequestException:
                if attempt == 2:
                    raise
                time.sleep(2)

        data = result.get("data", [])

        daegu_stops = [
            stop for stop in data
            if (
                "대구" in str(stop.get("도시명", ""))
                or "대구" in str(stop.get("관리도시명", ""))
            )
        ]

        all_stops.extend(daegu_stops)

        # 중간에 중단되어도 결과가 남도록 매 페이지 저장
        save_data(all_stops)

        print(
            f"{page}페이지 완료 / "
            f"대구 누적 {len(all_stops)}건"
        )

        time.sleep(0.2)

    print("\n===== 수집 완료 =====")
    print(f"저장 위치: {CSV_PATH}")


if __name__ == "__main__":
    collect_bus_stops()
