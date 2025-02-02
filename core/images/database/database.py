import pymongo
import motor.motor_asyncio
import os

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

async def retrieve_items():
    items = []
    async for item in collection.find():
        items.append(item_helper(item))
    return items

#client.drop_database("Distributed_DB")