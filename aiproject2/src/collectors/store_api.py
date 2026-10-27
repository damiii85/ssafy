"""Shared public store API response parser."""
URL = "https://apis.data.go.kr/B553077/api/open/sdsc2/storeListInRadius"

def unpack(payload):
    response = payload.get("response", payload)
    header = response.get("header", {})
    code = str(header.get("resultCode", "00"))
    if code not in ("00", "0"):
        raise RuntimeError(f"API 오류 ({code}): {header.get('resultMsg', '')}")
    body = response.get("body", {})
    items = body.get("items", [])
    if isinstance(items, dict):
        items = items.get("item", [])
    if isinstance(items, dict):
        items = [items]
    if not isinstance(items, list):
        raise ValueError(f"예상하지 못한 items 형식: {type(items).__name__}")
    return items, int(body.get("totalCount") or 0)

