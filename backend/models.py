from typing import Optional
from pydantic import BaseModel, Field

class QRPayload(BaseModel):
    id: str = Field(..., description="Medicine ID encoded in QR")
    name: Optional[str] = Field(None, description="Name of the medicine")
    category: Optional[str] = Field(None, description="Category of the medicine")
    count: Optional[int] = Field(1, description="Count of the medicine, default is 1")
    
class AssignResult(BaseModel):
    medicine_id: str
    bin: str
    upserted: bool 
    total_stock: int
    
class StockUpdateResult(BaseModel):
    medicine_id: str
    current_stock: int
    updated: bool = Field(default=True, description="Indicates if the stock was updated successfully")