from fastapi import FastAPI, Depends, HTTPException, APIRouter
from typing import Any
from backend.models import QRPayload, AssignResult
from backend.db import get_db, init_indexes
from backend.bin_rules import choose_bin, DEFAULT_BIN_MAP
from bson import ObjectId
from backend.db import bins_collection, medicines_collection, orders_collection
from backend.models import Bin, BinInDB, Medicine, MedicineInDB, Order, OrderInDB


app = FastAPI(title = "smartbins")

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
                "$inc": {"count": count_to_add}
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
        upserted=upserted
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



# ---- Helpers ----
def bin_helper(b) -> dict:
    return {
        "id": str(b["_id"]),
        "bin_id": b["bin_id"],
        "location": b["location"],
        "category": b["category"]
    }

def medicine_helper(m) -> dict:
    return {
        "id": str(m["_id"]),
        "medicine_id": m["medicine_id"],
        "name": m["name"],
        "bin_id": m["bin_id"],
        "category": m["category"],
        "quantity": m["quantity"],
        "price": m["price"]
    }

def order_helper(order) -> dict:
    return {
        "id": str(order["_id"]),
        "items": order["items"]
    }

# ---- Root ----
@app.get("/")
def root():
    return {"message": "Welcome to Pharma Warehouse System with Bins"}

# ---- Bin Routes ----
@app.post("/bins", response_model=BinInDB)
def create_bin(bin: Bin):
    if bins_collection.find_one({"bin_id": bin.bin_id}):
        raise HTTPException(status_code=400, detail="Bin with this bin_id already exists")
    result = bins_collection.insert_one(bin.dict())
    return bin_helper(bins_collection.find_one({"_id": result.inserted_id}))

@app.get("/bins")
def get_bins():
    return [bin_helper(b) for b in bins_collection.find()]

# ---- Medicine Routes ----


@app.get("/medicines")
def get_medicines():
    return [medicine_helper(m) for m in medicines_collection.find()]

# ---- Order Routes ----
@app.post("/orders", response_model=OrderInDB)
def place_order(order: Order): # if med=0 then dont show and count as well
    # validate medicines
    for item in order.items:
        med = medicines_collection.find_one({"medicine_id": item.medicine_id})
        if not med:
            raise HTTPException(status_code=404, detail=f"Medicine {item.medicine_id} not found")
        if item.quantity > med["quantity"]:
            raise HTTPException(status_code=400, detail=f"Not enough stock for {item.medicine_id}")

    # reduce stock
    for item in order.items:
        medicines_collection.update_one(
            {"medicine_id": item.medicine_id},
            {"$inc": {"quantity": -item.quantity}}
        )

    result = orders_collection.insert_one(order.dict())
    return order_helper(orders_collection.find_one({"_id": result.inserted_id}))

@app.get("/orders")
def get_orders():
    return [order_helper(o) for o in orders_collection.find()]

# ---- Warehouse Dashboard ----
@app.get("/warehouse/orders")
def warehouse_view():
    """Shows medicines + bin info for each order"""
    dashboard = []
    orders = orders_collection.find()
    for order in orders:
        order_data = {
            "order_id": str(order["_id"]),
            "items": []
        }
        for item in order["items"]:
            med = medicines_collection.find_one({"medicine_id": item["medicine_id"]})
            bin_data = bins_collection.find_one({"bin_id": med["bin_id"]}) if med else None
            if med and bin_data:
                order_data["items"].append({
                    "medicine_id": med["medicine_id"],
                    "medicine_name": med["name"],
                    "quantity": item["quantity"],
                    "price": med["price"],
                    "bin_id": med["bin_id"],
                    "bin_location": bin_data["location"],
                    "category": med["category"]
                })
        dashboard.append(order_data)
    return dashboard


# Subtract medicine after order is taken from bins

