from typing import Optional, List
from pydantic import BaseModel, Field

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
    
class CollectMedicineRequest(BaseModel):
    medicine_name: str = Field(..., description="Name of the medicine to collect")
    quantity: int = Field(..., description="Quantity to collect", gt=0)
    
    
class Order(BaseModel):
    customer_name: str = Field(..., description="Name of the customer")
    items: List[dict] = Field(..., description="List of medicines and quantities")
    status: str = Field(default="pending", description="Order status")
