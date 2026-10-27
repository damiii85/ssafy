
from pathlib import Path
import pandas as pd


# 프로젝트 경로
BASE_DIR = Path(__file__).resolve().parents[2]

RAW_PATH = (
    BASE_DIR / "data" / "raw"
    / "daegu_subway_ridership.csv"
)

OUTPUT_PATH = (
    BASE_DIR / "data" / "processed"
    / "dongseongro_subway.csv"
)


def analyze_subway():

    # 1. 원본 CSV 불러오기
    df = pd.read_csv(
        RAW_PATH,
        encoding="cp949"
    )

    # 2. 필요한 컬럼만 선택
    subway = df[
        ["년", "월", "중앙로", "반월당1", "반월당2"]
    ].copy()

    # 3. 숫자형으로 변환
    for col in ["중앙로", "반월당1", "반월당2"]:
        subway[col] = pd.to_numeric(
            subway[col],
            errors="coerce"
        )

    # 4. 반월당역 1·2호선 합산
    subway["반월당역"] = (
        subway["반월당1"] + subway["반월당2"]
    )

    # 5. 두 역의 승차인원 합계
    subway["인근역_승차인원_합계"] = (
        subway["중앙로"] + subway["반월당역"]
    )

    # 6. 연월 정렬
    subway = subway.sort_values(
        ["년", "월"]
    ).reset_index(drop=True)

    # 7. 필요한 컬럼만 저장
    result = subway[
        ["년", "월", "중앙로", "반월당역",
         "인근역_승차인원_합계"]
    ].copy()

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    result.to_csv(
        OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig"
    )

    # 8. 최신 월 출력
    latest = result.iloc[-1]

    print("\n===== SPOT CHECK 교통 분석 =====")
    print(
        f"최신 데이터: "
        f"{int(latest['년'])}년 "
        f"{int(latest['월'])}월"
    )

    print(
        f"중앙로역: "
        f"{int(latest['중앙로']):,}명"
    )

    print(
        f"반월당역: "
        f"{int(latest['반월당역']):,}명"
    )

    print(
        f"인근역 승차인원 합계: "
        f"{int(latest['인근역_승차인원_합계']):,}명"
    )

    print(f"\n저장 완료: {OUTPUT_PATH}")

    return result


if __name__ == "__main__":
    analyze_subway()
