import requests
from datetime import datetime
#from models import Item

url = "http://localhost:8000/api/v1/items/"

itemIds = []

def test_create_item():
    
    data = {
    "url": "http://example.com",
    "status": "active",
    "videoTitle": "Sample Video"
    }
    postResponse = requests.post(url, json=data)
    if postResponse.status_code == 201:
        print("Item created successfully!")
        print(f"Created item ID: {postResponse.json()['id']}")
    else:
        print(f"Failed to create item: {postResponse.status_code}")
        print(postResponse.text)

def test_get_items():
    getResponse = requests.get(url)

    # Check if the request was successful
    if getResponse.status_code == 200:
        items = getResponse.json()  # Parse the JSON response
        print("Items fetched successfully:")
        for item in items:
            itemIds.append(item["_id"])
            print(item)
    else:
        print(f"Failed to fetch items: {getResponse.status_code}")
        print(getResponse.text)

def test_get_item():
    getResponse = requests.get(f"{url}{itemIds[0]}")

    # Check if the request was successful
    if getResponse.status_code == 200:
        item = getResponse.json()  # Parse the JSON response
        print(f"Item fetched successfully: {item}")
    else:
        print(f"Failed to fetch item: {getResponse.status_code}")
        print(getResponse.text)

def test_update_item():
    data = {
        "url": "http://example-updated.com",
        "status": "inactive",
        "videoTitle": "Updated Video",
        "time_updated": str(datetime.now())  # Can leave this as None or specify a datetime string
    }

    putResponse = requests.put(f"{url}{itemIds[0]}", json=data)

    # Check if the request was successful
    if putResponse.status_code == 200:
        print(f"Item {itemIds[0]} updated successfully!")
    else:
        print(f"Failed to update item {itemIds[0]}: {putResponse.status_code}")
        print(putResponse.text)
    
    getResponse = requests.get(f"{url}{itemIds[0]}")
    if getResponse.status_code == 200:
        item = getResponse.json()  # Parse the JSON response
        print(f"Updated Item: {item}")
    else:
        print(f"Failed to fetch updated item: {getResponse.status_code}")
        print(getResponse.text)


def test_delete_item():
    deleteResponse = requests.delete(f"{url}{itemIds[0]}")

    # Check if the request was successful
    if deleteResponse.status_code == 200:
        print(f"Item {itemIds[0]} deleted successfully!")
    else:
        print(f"Failed to delete item {itemIds[0]}: {deleteResponse.status_code}")
        print(deleteResponse.text)
    
    getResponse = requests.get(url)
    if getResponse.status_code == 200:
        items = getResponse.json()  # Parse the JSON response
        print(f"Items after delete: {items}")
    else:
        print(f"Failed to fetch items: {getResponse.status_code}")
        print(getResponse.text)

if __name__ == "__main__":
    test_create_item()
    test_get_items()
    test_get_item()
    test_update_item()
    test_delete_item()