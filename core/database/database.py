import pymongo
import motor.motor_asyncio

MONGO_URI = "mongodb://localhost:27017" 
DATABASE_NAME = "Distributed_DB"        
COLLECTION_NAME = "urls"              

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