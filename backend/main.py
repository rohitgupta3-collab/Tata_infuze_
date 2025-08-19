from fastapi import FastAPI, Depends, HTTPException
from typing import Any
from backend.models import QRPayload, AssignResult
from backend.db import get_db, init_indexes
from backend.bin_rules import choose_bin, DEFAULT_BIN_MAP
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title = "Warehouse Management API")

#CORS For React dev
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",  
]

app.add_middleware(
    CORSMiddleware,
    allow_origins = origins,
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"],
)

@app.on_event("startup")
async def _startup() -> None:
    db = await get_db()
    await db.command("ping")  # Check if the database is reachable
    await init_indexes(db)
    
@app.post("/assign-bin", response_model=AssignResult)
async def assign_bin(qr: QRPayload, db: Any = Depends(get_db)) -> AssignResult:
    bin_id, _reason = choose_bin(qr.model_dump(), DEFAULT_BIN_MAP)
    count_to_add = qr.count or 1
    
    if not qr.name or not qr.name.strip():
        raise HTTPException(status_code=400, detail="Medicine name is required")
    # Check if medicine already exists
    existing = await db.medicines.find_one({"name": {"$regex": f"^{qr.name.strip()}$", "$options": "i"}})

    
    if existing:
        result = await db.medicines.update_one(
            {"name": {"$regex": f"^{qr.name.strip()}$", "$options": "i"}},
            {
                "$set": {
                    "category": qr.category,
                    "bin": bin_id,
                },
                "$inc": {"stock": count_to_add}
            }
        )
        updated_doc = await db.medicines.find_one({"name": {"$regex": f"^{qr.name.strip()}$", "$options": "i"}})
        total_stock = updated_doc['stock']
        upserted = False
    else: 
        # New Medicine - create with initial stock
        doc = {
            "id": qr.id,
            "name": qr.name,
            "category": qr.category,
            "bin": bin_id,
            "stock": count_to_add
        }
        result = await db.medicines.insert_one(doc)
        total_stock = count_to_add
        upserted = True
    
    return AssignResult(
        medicine_id=qr.id,
        medicine_name = qr.name,
        bin=bin_id,
        upserted=upserted,
        total_stock=total_stock
    )
    
    
    
@app.get("/get-medicine-location/{medicine_name}")
async def get_medicine_location(medicine_name: str, db: Any = Depends(get_db)):
    '''
    Fetch the medicine location by name (case-insensitive)
    '''
    medicine = await db.medicines.find_one({"name": {"$regex": f"^{medicine_name.strip()}$", "$options": "i"}})
    if not medicine:
        raise HTTPException(status_code=404, detail="Medicine not found")
    
   #medicine.pop("_id", None)  # Remove MongoDB's ObjectId field
    return medicine