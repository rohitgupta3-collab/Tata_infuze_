from datetime import datetime, timedelta

DEFAULT_BIN_MAP = {
    "analgesic": "Bin-A1",
    "antibiotic": "Bin-B1",
    "vaccine": "Cold-Storage-1",
    "controlled": "Secure-Bin",
    "default": "Bin-General",
}

def choose_bin(payload: dict, bin_map: dict | None = None) -> tuple[str, str]:
    """
    Returns (bin_id, reason)
    """
    m = bin_map or DEFAULT_BIN_MAP
    
    cat = (payload.get("category") or "default").strip().lower()
    if cat and cat in m:
        return m[cat], f"Category: {cat}"
    return m["default"], "fallback"