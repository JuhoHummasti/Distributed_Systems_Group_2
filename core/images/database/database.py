import pymongo
import motor.motor_asyncio
import os
from typing import Optional, Dict, Any

MONGO_URI = os.getenv("MONGODB_URL", "mongodb://mongodb:27017/?directConnection=true")
DATABASE_NAME = "Distributed_DB"        
COLLECTION_NAME = "videos"              

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = client[DATABASE_NAME]
collection = db[COLLECTION_NAME]

"""client = pymongo.MongoClient(MONGO_URI)
db = client[DATABASE_NAME]
collection = db[COLLECTION_NAME]"""

def item_helper(item) -> dict:
    item["_id"] = str(item["_id"])
    return item

async def retrieve_items(
    collection_name: Optional[str] = None, 
    query_filter: Dict[str, Any] = {},
    skip: int = 0, 
    limit: int = 100
):
    """
    Retrieve items from a collection or all collections if no collection is specified.
    
    :param collection_name: Optional name of the collection. If None, retrieves from all collections.
    :param query_filter: Dictionary of query filters
    :param skip: Number of documents to skip
    :param limit: Maximum number of documents to return
    :return: List of items
    """
    try:
        # If no collection specified, retrieve from all collections
        if collection_name is None:
            # Get list of all collection names
            collection_names = await db.list_collection_names()
            
            # Aggregate items from all collections
            all_items = []
            for name in collection_names:
                collection = db[name]
                
                # Find items matching the filter
                cursor = collection.find(query_filter).skip(skip).limit(limit)
                items = await cursor.to_list(length=limit)
                
                # Add collection name to each item for context
                for item in items:
                    item['_collection'] = name
                
                all_items.extend(items)
            
            # Optional: Apply item helper function
            processed_items = [item_helper(item) for item in all_items]
            
            # Limit total results if necessary
            return processed_items[:limit]
        
        # If a specific collection is specified
        collection = db[collection_name]
        
        # Perform the query
        cursor = collection.find(query_filter).skip(skip).limit(limit)
        
        # Convert cursor to list and process items
        items = await cursor.to_list(length=limit)
        
        # Optional: Apply item helper function if needed
        processed_items = [item_helper(item) for item in items]
        
        return processed_items
    
    except Exception as e:
        raise ValueError(f"Error retrieving items: {str(e)}")

#client.drop_database("Distributed_DB")