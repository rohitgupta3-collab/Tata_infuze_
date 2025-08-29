from fastapi import FastAPI, Depends, HTTPException
from typing import Any, List
from backend.models import CollectMedicineRequest, Order, QRPayload, AssignResult
from backend.db import get_db, init_indexes
from backend.bin_rules import choose_bin, DEFAULT_BIN_MAP
from fastapi.middleware.cors import CORSMiddleware
from arduino.basic import arduino_service

active_picker_colors = set()
app = FastAPI(title = "Warehouse Management API")


#CORS For React dev
origins = [
    "*"  
]

def get_available_picker_color():
    picker_colors = ["BLUE", "GREEN", "YELLOW"]
    for color in picker_colors:
        if color not in active_picker_colors:
            return color
        
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
    
    medicine.pop("_id", None)  # Remove MongoDB's ObjectId field
    return medicine


@app.post("/receive-order")
async def receive_order(order_items: List[dict], db: Any = Depends(get_db)):
    global active_picker_colors
    results = []
    picker_color = get_available_picker_color()
    # if not picker_color:
    #     print('All pickers are busy. Please wait.')
    active_picker_colors.add(picker_color)
    for item in order_items:
        name = item.get("name", "").strip()
        qty = item.get("quantity", 0)
        med = await db.medicines.find_one({"name": {"$regex": f"^{name}$", "$options": "i"}})
        if not med:
            results.append({"name": name, "status": "not_found"})
        elif med.get("stock", 0) < qty:
            results.append({"name": name, "status": "insufficient_stock", "available": med.get("stock", 0)})
        else:
            bin_id = med.get("bin", "Bin-Default")
            arduino_service.led_on(bin_id, picker_color)
            # Store picker_color in the medicine document
            await db.medicines.update_one(
                {"name": {"$regex": f"^{name}$", "$options": "i"}},
                {"$set": {"current_picker_color": picker_color}}
            )
            results.append({"name": name, "status": "ok", "bin": bin_id, "picker": picker_color})
    return {"results": results, "picker_color": picker_color}

@app.post("/collect-medicine")
async def collect_medicine(request: CollectMedicineRequest, db: Any = Depends(get_db)):
    med = await db.medicines.find_one({"name": {"$regex": f"^{request.medicine_name.strip()}$", "$options": "i"}})
    if not med:
        raise HTTPException(status_code=404, detail="Medicine not found")
    if med.get("stock", 0) < request.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")
    
    picker_color = med.get("current_picker_color") 
    
    await db.medicines.update_one(
        {"name": {"$regex": f"^{request.medicine_name.strip()}$", "$options": "i"}},
        {
            "$inc": {"stock": -request.quantity},
            "$unset": {"current_picker_color": ""}  # Remove picker color after collection
        }
    )
    # Turn OFF LED for this bin and picker color
    bin_id = med.get("bin", "Bin-Default")
    arduino_service.led_off(bin_id, request.picker_color)
    
    active_picker_colors.discard(picker_color)
    return {"name": request.medicine_name, "collected": request.quantity, "picker_color": picker_color}

#API To show what all orders have been recieved, to show in the ui of warehouse Laptop

@app.get("/medicines")
async def get_medicines(db: Any = Depends(get_db)):
    """
    Get list of all medicines in the warehouse.
    """
    cursor = db.medicines.find({})
    medicines = []
    async for med in cursor:
        med.pop("_id", None)
        medicines.append(med)
    return {"medicines": medicines}


@app.post("/orders")
async def create_order(order: Order, db: Any = Depends(get_db)):
    """
    Place a new order.
    """
    order_dict = order.dict()
    result = await db.orders.insert_one(order_dict)
    order_dict["_id"] = str(result.inserted_id)
    return order_dict


@app.get("/orders")
async def get_orders(db: Any = Depends(get_db)):
    """
    Get all placed orders (for warehouse UI).
    """
    cursor = db.orders.find({})
    orders = []
    async for order in cursor:
        order["_id"] = str(order["_id"])
        orders.append(order)
    return {"orders": orders}

from bson import ObjectId

@app.delete("/orders/{order_id}")
async def delete_order(order_id: str, db: Any = Depends(get_db)):
    """
    Delete an order from the orders collection by its ID.
    """
    global active_picker_colors
    order = await db.orders.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    picker_colors = ["BLUE", "GREEN", "YELLOW"]
    for idx, item in enumerate(order.get("items", [])):
        name = item.get("name", "").strip()
        med = await db.medicines.find_one({"name": {"$regex": f"^{name}$", "$options": "i"}})
        if med:
            bin_id = med.get("bin", "Bin-Default")
            picker_color = picker_colors[idx % 3]
            arduino_service.led_off(bin_id, picker_color)  # Turn OFF LED
    result = await db.orders.delete_one({"_id": ObjectId(order_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"message": "Order deleted successfully", "order_id": order_id}


#it currently fails when I click on the process order(colour assigned) and goes back(if more than 3, then it is null)
