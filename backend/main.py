from fastapi import FastAPI, Depends, HTTPException
from typing import Any
from backend.models import QRPayload, AssignResult
from backend.db import get_db, init_indexes
from backend.bin_rules import choose_bin, DEFAULT_BIN_MAP

app = FastAPI(title = "Warehouse Management API")

@app.on_event("startup")
async def _startup() -> None:
    db = await get_db()
    await db.command("ping")  # Check if the database is reachable
    await init_indexes(db)
    
@app.post("/assign-bin", response_model=AssignResult)
@app.post("/choose-bin", response_model=AssignResult)
async def assign_bin(qr: QRPayload, db: Any = Depends(get_db)) -> AssignResult:
    bin_id, _reason = choose_bin(qr.model_dump(), DEFAULT_BIN_MAP)
    count_to_add = qr.count or 1
    
    # Check if medicine already exists
    existing = await db.medicines.find_one({"id": qr.id})
    
    if existing:
        result = await db.medicines.update_one(
            {"id": qr.id},
            {
                
                "$set": {
                    "name": qr.name,
                    "category": qr.category,
                    "bin": bin_id,
                },
                "$inc": {"stock": count_to_add}
            }
        )
        updated_doc = await db.medicines.find_one({"id": qr.id})
        total_stock = updated_doc['stock']
        upserted = False
    else: 
        #New Medicine - create with initial stock
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
        bin=bin_id,
        upserted=upserted,
        total_stock=total_stock
    )
    
@app.get("/get-medicine-location/{medicine_id}")
async def get_medicine_location(medicine_id: str, db: Any = Depends(get_db)):
    '''
    Fetch the medicine location by ID
    '''
    medicine = await db.medicines.find_one({"id": medicine_id})
    if not medicine:
        raise HTTPException(status_code=404, detail="Medicine not found")
    
    medicine.pop("_id", None)  # Remove MongoDB's ObjectId field
    return medicine