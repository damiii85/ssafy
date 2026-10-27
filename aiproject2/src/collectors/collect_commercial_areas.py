"""전국 상권 현황 API 수집. 전국 집계와 개별 상권 데이터를 구분한다."""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote

import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
API_URL = (
    "https://api.odcloud.kr/api/15143727/v1/"
    "uddi:ddbcfbd7-a6de-4f20-9a6e-b7d5d3493622"
)
SPEC_URL = "https://infuser.odcloud.kr/oas/docs?namespace=15143727/v1"


def fetch_rows(api_key, per_page=100, session=None):
    if not api_key or not api_key.strip():
        raise ValueError(".env에 COMMERCIAL_AREA_API_KEY를 설정해 주세요.")
    if not 1 <= per_page <= 1000:
        raise ValueError("페이지 크기는 1~1000이어야 합니다.")
    http = session or requests
    rows = []
    page = 1
    total = None
    while total is None or len(rows) < total:
        try:
            # 키를 URL 쿼리 문자열에 넣지 않는다. Encoding 키도 한 번 해제한다.
            response = http.get(
                API_URL, headers={"Authorization": "Infuser " + unquote(api_key.strip())},
                params={"page": page, "perPage": per_page, "returnType": "JSON"},
                timeout=(10, 30),
            )
            if response.status_code != 200:
                raise ValueError(f"상권 API 요청 실패(HTTP {response.status_code}). 인증·활용신청 상태를 확인해 주세요.")
            payload = response.json()
        except requests.RequestException:
            raise ValueError("상권 API 연결 실패. 네트워크 또는 서버 상태를 확인해 주세요.") from None
        except (json.JSONDecodeError, requests.exceptions.JSONDecodeError):
            raise ValueError("상권 API가 JSON 응답을 반환하지 않았습니다.") from None
        if not isinstance(payload, dict):
            raise ValueError("상권 API 응답 형식이 올바르지 않습니다.")
        batch = payload.get("data")
        reported_total = payload.get("totalCount")
        if (not isinstance(batch, list) or any(not isinstance(row, dict) for row in batch)
                or type(reported_total) is not int or reported_total < 0):
            raise ValueError("상권 API의 data 또는 totalCount 항목이 올바르지 않습니다.")
        if total is not None and total != reported_total:
            raise ValueError("수집 도중 총 건수가 변경됐습니다. 다시 실행해 주세요.")
        total = reported_total
        if not batch and len(rows) < total:
            raise ValueError("전체 건수를 받기 전에 빈 페이지가 반환됐습니다. 저장하지 않았습니다.")
        rows.extend(batch)
        if len(rows) > total:
            raise ValueError("응답 건수가 totalCount와 일치하지 않습니다.")
        page += 1
        if page > 10001:
            raise ValueError("페이지 제한을 초과했습니다.")
    return rows


def save_rows(rows, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    columns = list(dict.fromkeys(key for row in rows for key in row))
    metadata = {
        "source": "소상공인시장진흥공단 전국 상권 현황",
        "api_url": API_URL, "spec_url": SPEC_URL,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "data_reference_date": "2024-11-20", "statistic_year": "2023",
        "row_count": len(rows), "columns": columns,
        "limitation": "시도별 상권 현황 집계 자료. 동성로 매출·유동인구·경쟁 점포 수의 근거로 사용하지 않는다.",
        "data": rows,
    }
    json_path = output_dir / "national_commercial_areas.json"
    csv_path = output_dir / "national_commercial_areas.csv"
    json_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    return json_path, csv_path


def main():
    parser = argparse.ArgumentParser(description="전국 상권 현황 API 수집")
    parser.add_argument("--per-page", type=int, default=100)
    parser.add_argument("--output-dir", type=Path, default=BASE_DIR / "data/raw/commercial_areas")
    args = parser.parse_args()
    load_dotenv(BASE_DIR / ".env")
    try:
        rows = fetch_rows(os.getenv("COMMERCIAL_AREA_API_KEY"), args.per_page)
        paths = save_rows(rows, args.output_dir)
    except ValueError as error:
        print(f"오류: {error}", file=sys.stderr)
        return 1
    print(f"수집 완료: {len(rows)}건")
    print("응답 항목: " + ", ".join(dict.fromkeys(key for row in rows for key in row)))
    for row in rows[:10]:
        print(json.dumps(row, ensure_ascii=False))
    for path in paths:
        print(f"저장: {path}")
    print("주의: 전국 집계 자료이며 동성로의 개별 상권 현황을 의미하지 않습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
