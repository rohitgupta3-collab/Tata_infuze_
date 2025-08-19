from datetime import datetime, timedelta

DEFAULT_BIN_MAP = {
    "paracetamol": "Bin-A1",
    "acetaminophen": "Bin-B1", 
    "aspirin": "Cold-Storage-1",
    "azithromycin": "Secure-Bin",
    "covaxin": "Bin-C1",
    "covishield": "Bin-D1",
    "metformin": "Bin-R1",
    "salbutamol": "Bin-V1",
    "chlorhexidine": "Bin-AS1",
    "vitamin b12": "Bin-General",
    "default": "Bin-Default"
}

def choose_bin(payload: dict, bin_map: dict | None = None) -> tuple[str, str]:
    """
    Returns (bin_id, reason) on medicine name
    """
    m = bin_map or DEFAULT_BIN_MAP
    
    medicine_name = payload.get("name", "").strip().lower()
    
    if not medicine_name:
        return m["default"], "No medicine name provided"
    
    if medicine_name in m:
        return m[medicine_name], f"Medicine: {medicine_name}"
    
    for key in m:
        if key != "default" and key in medicine_name:
            return m[key], f"Medicine: {medicine_name} (matched: {key})"
        
    return m["default"], f"Unknown medicine: {medicine_name}"