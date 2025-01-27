from fastapi import APIRouter, HTTPException
from database.models import Item, UpdateItem
from database.database import collection, retrieve_items
from bson import ObjectId

router = APIRouter()

# Helper function to convert BSON to JSON
def item_helper(item) -> dict:
    item["_id"] = str(item["_id"])
    return item

# Create an item
@router.post("/items/", status_code=201)
async def create_item(item: Item):
    new_item = item.dict()
    result = await collection.insert_one(new_item)
    return {"id": str(result.inserted_id)}

# Read all items
@router.get("/items/")
async def get_items():
    items = await retrieve_items()
    #items = [item_helper(item) for item in collection.find()]
    return items

# Read an item by ID
@router.get("/items/{item_id}")
async def get_item(item_id: str):
    item = await collection.find_one({"_id": ObjectId(item_id)})
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item_helper(item)

# Update an item
@router.put("/items/{item_id}")
async def update_item(item_id: str, item: UpdateItem):
    update_data = {k: v for k, v in item.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No data provided to update")
    result = await collection.update_one({"_id": ObjectId(item_id)}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Item updated successfully"}

# Delete an item
@router.delete("/items/{item_id}")
async def delete_item(item_id: str):
    result = await collection.delete_one({"_id": ObjectId(item_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Item deleted successfully"}

