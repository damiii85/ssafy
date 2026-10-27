
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_PATH = BASE_DIR / "data" / "raw" / "dongseongro_stores.csv"
OUTPUT_PATH = BASE_DIR / "data" / "processed" / "food_categories.csv"

df = pd.read_csv(DATA_PATH, dtype=str).fillna("")

food = df[df["indsLclsNm"] == "음식"].copy()

summary = (
    food.groupby(
        ["indsMclsCd", "indsMclsNm", "indsSclsCd", "indsSclsNm"]
    )
    .size()
    .reset_index(name="store_count")
    .sort_values("store_count", ascending=False)
)

print("\n===== 음식 업종 소분류 =====\n")

for _, row in summary.iterrows():
    print(
        f"{row['indsMclsNm']} > "
        f"{row['indsSclsNm']} : "
        f"{row['store_count']}개"
    )

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
summary.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

print(f"\n전체 음식 업종: {len(food)}개")
print(f"세부 업종 종류: {len(summary)}개")
print(f"파일 저장 완료: {OUTPUT_PATH}")
