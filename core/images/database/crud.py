from fastapi import APIRouter, Query, HTTPException
from models import Item, UpdateItem
from database import collection, retrieve_items
from bson import ObjectId
from typing import Optional, Dict, Any
import json

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

@router.get("/items/{collection}")
async def get_items_by_collection(
    collection: str, 
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    filter: Optional[str] = Query(None)
):
    """
    Retrieve items from a specified collection with optional filtering, pagination, and sorting.
    
    - `collection`: Name of the MongoDB collection to query
    - `skip`: Number of documents to skip (for pagination)
    - `limit`: Maximum number of documents to return
    - `filter`: Optional dictionary of query filters
    
    Example queries:
    - Basic: `/items/users`
    - With filter: `/items/products?filter={"category":"electronics"}`
    - With pagination: `/items/orders?skip=10&limit=20`
    """
    try:
        query_filter = {}
        if filter:
            try:
                # Parse the filter string directly
                filter_str = filter.replace("'", '"')
                query_filter = json.loads(filter_str)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid filter format")
        
        # Retrieve items from the specified collection
        items = await retrieve_items(
            collection_name=collection, 
            query_filter=query_filter,
            skip=skip,
            limit=limit
        )
        
        return items
    
    except Exception as e:
        # Handle potential errors (e.g., collection not found, invalid filter)
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/videos/{video_id}")
async def get_item_by_video_id(video_id: str):
    """
    Retrieve an item by its video_id field
    """
    item = await collection.find_one({"video_id": video_id})
    if not item:
        raise HTTPException(status_code=404, detail="Video not found")
    return item_helper(item)

@router.delete("/videos/{video_id}")
async def delete_item_by_video_id(video_id: str):
    """
    Delete an item by its video_id field
    """
    result = await collection.delete_one({"video_id": video_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Video not found")
    return {"message": "Video deleted successfully"}

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
    result = await collection.update_one({"video_id": ObjectId(item_id)}, {"$set": update_data})
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

