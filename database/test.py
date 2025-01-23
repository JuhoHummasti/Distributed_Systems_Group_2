import requests
import unittest
from datetime import datetime

class TestItemsAPI(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Runs once before all tests."""
        cls.base_url = "http://localhost:8000/api/v1/items/"
        cls.test_item_ids = []
    
    def setUp(self):
        """Runs before every individual test."""
        self.item_id = None  # Reset item ID for each test
    
    def test_create_item(self):

        print("-------Create Item Test-------")

        data = {
            "url": "http://example.com",
            "status": "active",
            "videoTitle": "Sample Video"
        }
        
        postResponse = requests.post(self.base_url, json=data)
        self.test_item_ids.append(postResponse.json()["id"])
        self.assertEqual(postResponse.status_code, 201, "Failed to create item")
        
        item_id = postResponse.json().get('id')
        
        print(f"POST response data: {postResponse.json()}")  # Debugging log
        self.assertIsNotNone(item_id, "Item ID should not be None")
        
        print(f"Item created successfully! Created item ID: {item_id}")

    def test_get_items(self):

        print("-------Get Items Test-------")

        data = {
            "url": "http://example.com",
            "status": "active",
            "videoTitle": "Sample Video"
        }
        postResponse = requests.post(self.base_url, json=data)
        self.test_item_ids.append(postResponse.json()["id"])  # Access the 'id' field

        postResponse = requests.post(self.base_url, json=data)
        self.test_item_ids.append(postResponse.json()["id"])  # Access the 'id' field

        postResponse = requests.post(self.base_url, json=data)
        self.test_item_ids.append(postResponse.json()["id"])  # Access the 'id' field

        getResponse = requests.get(self.base_url)
        self.assertEqual(getResponse.status_code, 200, "Failed to fetch items")
        
        items = getResponse.json()
        self.assertGreater(len(items), 0, "No items returned")
        
        print(f"Items fetched successfully: {items}")
        

    def test_get_item(self):

        print("-------Get Item Test-------")

        data = {
            "url": "http://example.com",
            "status": "active",
            "videoTitle": "Sample Video"
        }
        postResponse = requests.post(self.base_url, json=data)
        if postResponse.status_code == 201:
            response_data = postResponse.json()  # Parse the JSON response
            item_id = response_data.get("id")  # Access the 'id' field
            self.test_item_ids.append(postResponse.json()["id"])
        
        getResponse = requests.get(f"{self.base_url}{item_id}")
        self.assertEqual(getResponse.status_code, 200, "Failed to fetch item")
        
        item = getResponse.json()
        print(f"Item fetched successfully: {item}")

    def test_update_item(self):
        
        print("-------Update Item Test-------")

        data = {
            "url": "http://example.com",
            "status": "active",
            "videoTitle": "Sample Video"
        }
        postResponse = requests.post(self.base_url, json=data)
        if postResponse.status_code == 201:
            response_data = postResponse.json()  # Parse the JSON response
            item_id = response_data.get("id")  # Access the 'id' field
            self.test_item_ids.append(postResponse.json()["id"])
        
        
        # Verify item existence
        getResponse = requests.get(f"{self.base_url}{item_id}")
        self.assertEqual(getResponse.status_code, 200, f"Item {item_id} does not exist before update.")
        
        data = {
            "url": "http://example-updated.com",
            "status": "inactive",
            "videoTitle": "Updated Video",
            "time_updated": str(datetime.now())
        }
        
        putResponse = requests.put(f"{self.base_url}{item_id}", json=data)
        self.assertEqual(putResponse.status_code, 200, f"Failed to update item {item_id}")
        
        getResponse = requests.get(f"{self.base_url}{item_id}")
        self.assertEqual(getResponse.status_code, 200, "Failed to fetch updated item")
        
        item = getResponse.json()
        print(f"Updated Item: {item}")
    
    def test_delete_item(self):

        print("-------Delete Item Test-------")

        data = {
            "url": "http://example.com",
            "status": "active",
            "videoTitle": "Sample Video"
        }
        postResponse = requests.post(self.base_url, json=data)
        if postResponse.status_code == 201:
            response_data = postResponse.json()  # Parse the JSON response
            item_id = response_data["id"]  # Access the 'id' field
            self.test_item_ids.append(postResponse.json()["id"])
            
        deleteResponse = requests.delete(f"{self.base_url}{item_id}")
        self.assertEqual(deleteResponse.status_code, 200, f"Failed to delete item {item_id}")
        
        getResponse = requests.get(self.base_url)
        self.assertEqual(getResponse.status_code, 200, "Failed to fetch items")
        
        self.test_item_ids.remove(postResponse.json()["id"])
        print(f"Deleted item: {postResponse.json()["id"]}")
        items = getResponse.json()
        
        print(f"Items after delete: {items}")

    @classmethod
    def tearDownClass(cls):
        """Runs once after all tests,
            Deletes test data"""
        
        print("-------Test Items cleanup-------")
        for id in cls.test_item_ids:
            requests.delete(f"{cls.base_url}{id}")
        print("Cleaned up test items.")

if __name__ == "__main__":
    unittest.main()