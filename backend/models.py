from typing import Optional, List
from pydantic import BaseModel, Field
from typing import List, Dict
from beanie import Document, Link
from bson import ObjectId

class QRPayload(BaseModel):
    id: str = Field(..., description="Medicine ID encoded in QR")
    name: Optional[str] = Field(None, description="Name of the medicine")
    category: Optional[str] = Field(None, description="Category of the medicine")
    count: Optional[int] = Field(1, description="Count of the medicine, default is 1")
    
class AssignResult(BaseModel):
    medicine_id: str
    medicine_name: str
    bin: str
    upserted: bool 
    total_stock: int
    
class StockUpdateResult(BaseModel):
    medicine_id: str
    current_stock: int
    updated: bool = Field(default=True, description="Indicates if the stock was updated successfully")


# ----- Bin -----
class Bin(BaseModel):
    bin_id: str          
    location: str      
    category: str       

class BinInDB(Bin):
    id: str

# ----- Medicine -----
class Medicine(BaseModel):
    medicine_id: str     # unique medicine identifier
    name: str
    bin_id: str          # reference to Bin.bin_id
    category: str        # category for quick filter (same as bin category or sub-category)
    quantity: int
    price: float

class MedicineInDB(Medicine):
    id: str

# ----- Order -----
class OrderItem(BaseModel):
    product_id: str
    quantity: int

class Order(BaseModel):
    items: List[OrderItem]

class OrderInDB(Order):
    id: str
