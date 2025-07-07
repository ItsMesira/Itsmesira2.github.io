import requests
import json
from datetime import datetime, timedelta
import time
import unittest
import uuid

# Use local backend URL for testing
BACKEND_URL = "http://localhost:8001"
API_URL = f"{BACKEND_URL}/api"

class FinancialGoalAPITest(unittest.TestCase):
    def setUp(self):
        # Create a unique test goal name to avoid conflicts
        self.test_goal_name = f"Test Goal {uuid.uuid4()}"
        self.test_goal_amount = 1000.0
        
        # Create a test goal for use in tests
        self.test_goal = self.create_test_goal()
    
    def tearDown(self):
        # Clean up by deleting the test goal if it exists
        if hasattr(self, 'test_goal') and 'id' in self.test_goal:
            try:
                requests.delete(f"{API_URL}/goals/{self.test_goal['id']}")
            except:
                pass
    
    def create_test_goal(self):
        """Helper method to create a test goal"""
        goal_data = {
            "name": self.test_goal_name,
            "target_amount": self.test_goal_amount
        }
        response = requests.post(f"{API_URL}/goals", json=goal_data)
        self.assertEqual(response.status_code, 200, f"Failed to create test goal: {response.text}")
        return response.json()
    
    def add_transaction(self, goal_id, amount, description="Test transaction"):
        """Helper method to add a transaction to a goal"""
        transaction_data = {
            "goal_id": goal_id,
            "amount": amount,
            "description": description
        }
        response = requests.post(f"{API_URL}/transactions", json=transaction_data)
        self.assertEqual(response.status_code, 200, f"Failed to add transaction: {response.text}")
        return response.json()
    
    def test_api_root(self):
        """Test the API root endpoint"""
        response = requests.get(f"{API_URL}/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("message", data)
        self.assertEqual(data["message"], "Financial Goal Tracker API")
    
    def test_create_goal(self):
        """Test creating a new goal"""
        # Goal was already created in setUp, verify it has the correct properties
        self.assertEqual(self.test_goal["name"], self.test_goal_name)
        self.assertEqual(self.test_goal["target_amount"], self.test_goal_amount)
        self.assertEqual(self.test_goal["current_amount"], 0.0)
        self.assertEqual(self.test_goal["completed"], False)
        self.assertIsNotNone(self.test_goal["id"])
        self.assertIsNotNone(self.test_goal["created_date"])
    
    def test_get_goals(self):
        """Test retrieving all goals"""
        response = requests.get(f"{API_URL}/goals")
        self.assertEqual(response.status_code, 200)
        goals = response.json()
        self.assertIsInstance(goals, list)
        
        # Find our test goal in the list
        found = False
        for goal in goals:
            if goal["id"] == self.test_goal["id"]:
                found = True
                break
        
        self.assertTrue(found, "Test goal not found in goals list")
    
    def test_get_goal_by_id(self):
        """Test retrieving a specific goal by ID"""
        response = requests.get(f"{API_URL}/goals/{self.test_goal['id']}")
        self.assertEqual(response.status_code, 200)
        goal = response.json()
        self.assertEqual(goal["id"], self.test_goal["id"])
        self.assertEqual(goal["name"], self.test_goal_name)
        self.assertEqual(goal["target_amount"], self.test_goal_amount)
    
    def test_get_nonexistent_goal(self):
        """Test retrieving a goal that doesn't exist"""
        fake_id = str(uuid.uuid4())
        response = requests.get(f"{API_URL}/goals/{fake_id}")
        self.assertEqual(response.status_code, 404)
    
    def test_add_transaction(self):
        """Test adding a transaction to a goal"""
        # Add a transaction
        amount = 100.0
        transaction = self.add_transaction(self.test_goal["id"], amount)
        
        # Verify transaction properties
        self.assertEqual(transaction["goal_id"], self.test_goal["id"])
        self.assertEqual(transaction["amount"], amount)
        self.assertIsNotNone(transaction["id"])
        self.assertIsNotNone(transaction["transaction_date"])
        
        # Verify goal was updated
        response = requests.get(f"{API_URL}/goals/{self.test_goal['id']}")
        self.assertEqual(response.status_code, 200)
        updated_goal = response.json()
        self.assertEqual(updated_goal["current_amount"], amount)
    
    def test_get_transactions(self):
        """Test retrieving transactions for a goal"""
        # Add a couple of transactions
        amount1 = 100.0
        amount2 = 200.0
        self.add_transaction(self.test_goal["id"], amount1, "First transaction")
        self.add_transaction(self.test_goal["id"], amount2, "Second transaction")
        
        # Get transactions
        response = requests.get(f"{API_URL}/transactions/{self.test_goal['id']}")
        self.assertEqual(response.status_code, 200)
        transactions = response.json()
        
        # Verify we have at least 2 transactions
        self.assertGreaterEqual(len(transactions), 2)
        
        # Verify transactions belong to our goal
        for transaction in transactions:
            self.assertEqual(transaction["goal_id"], self.test_goal["id"])
    
    def test_goal_completion(self):
        """Test that a goal is marked as completed when target amount is reached"""
        # Add a transaction that completes the goal
        self.add_transaction(self.test_goal["id"], self.test_goal_amount)
        
        # Verify goal is marked as completed
        response = requests.get(f"{API_URL}/goals/{self.test_goal['id']}")
        self.assertEqual(response.status_code, 200)
        updated_goal = response.json()
        self.assertTrue(updated_goal["completed"])
        self.assertIsNotNone(updated_goal["completion_date"])
    
    def test_goal_progress_no_transactions(self):
        """Test goal progress calculation with no transactions"""
        response = requests.get(f"{API_URL}/goals/{self.test_goal['id']}/progress")
        self.assertEqual(response.status_code, 200)
        progress = response.json()
        
        # Verify progress data
        self.assertEqual(progress["progress_percentage"], 0.0)
        self.assertEqual(progress["remaining_amount"], self.test_goal_amount)
        self.assertIsNone(progress["estimated_days_to_completion"])
        self.assertIsNone(progress["estimated_completion_date"])
        self.assertIsNone(progress["average_daily_savings"])
    
    def test_goal_progress_with_transactions(self):
        """Test goal progress calculation with transactions"""
        # Add a transaction
        amount = self.test_goal_amount / 2  # 50% of the goal
        self.add_transaction(self.test_goal["id"], amount)
        
        # Get progress
        response = requests.get(f"{API_URL}/goals/{self.test_goal['id']}/progress")
        self.assertEqual(response.status_code, 200)
        progress = response.json()
        
        # Verify progress data
        self.assertAlmostEqual(progress["progress_percentage"], 50.0)
        self.assertAlmostEqual(progress["remaining_amount"], self.test_goal_amount - amount)
        self.assertIsNotNone(progress["estimated_days_to_completion"])
        self.assertIsNotNone(progress["estimated_completion_date"])
        self.assertIsNotNone(progress["average_daily_savings"])
    
    def test_estimation_algorithm_same_day_transactions(self):
        """Test estimation algorithm with multiple transactions on the same day"""
        # Add multiple transactions on the same day
        self.add_transaction(self.test_goal["id"], 100.0, "First transaction")
        self.add_transaction(self.test_goal["id"], 150.0, "Second transaction")
        
        # Get progress
        response = requests.get(f"{API_URL}/goals/{self.test_goal['id']}/progress")
        self.assertEqual(response.status_code, 200)
        progress = response.json()
        
        # Verify estimation data
        self.assertIsNotNone(progress["estimated_days_to_completion"])
        self.assertIsNotNone(progress["estimated_completion_date"])
        self.assertIsNotNone(progress["average_daily_savings"])
        
        # For same-day transactions, average_daily_savings should be the sum of today's transactions
        self.assertAlmostEqual(progress["average_daily_savings"], 250.0)
    
    def test_estimation_algorithm_multiple_days(self):
        """Test estimation algorithm with transactions across multiple days"""
        # This test is more complex as we can't easily simulate transactions on different days
        # We'll add transactions and check that the estimation logic works in general
        
        # Add a transaction for 25% of the goal
        amount1 = self.test_goal_amount * 0.25
        self.add_transaction(self.test_goal["id"], amount1)
        
        # Get progress after first transaction
        response = requests.get(f"{API_URL}/goals/{self.test_goal['id']}/progress")
        self.assertEqual(response.status_code, 200)
        progress1 = response.json()
        
        # Add another transaction for 25% of the goal
        amount2 = self.test_goal_amount * 0.25
        self.add_transaction(self.test_goal["id"], amount2)
        
        # Get progress after second transaction
        response = requests.get(f"{API_URL}/goals/{self.test_goal['id']}/progress")
        self.assertEqual(response.status_code, 200)
        progress2 = response.json()
        
        # Verify that the estimated days to completion decreased after the second transaction
        # This is because we've added more money, so it should take less time to reach the goal
        self.assertLess(progress2["estimated_days_to_completion"], progress1["estimated_days_to_completion"])
    
    def test_delete_goal(self):
        """Test deleting a goal and its transactions"""
        # Add a transaction to the goal
        self.add_transaction(self.test_goal["id"], 100.0)
        
        # Verify transactions exist
        response = requests.get(f"{API_URL}/transactions/{self.test_goal['id']}")
        self.assertEqual(response.status_code, 200)
        transactions_before = response.json()
        self.assertGreater(len(transactions_before), 0)
        
        # Delete the goal
        response = requests.delete(f"{API_URL}/goals/{self.test_goal['id']}")
        self.assertEqual(response.status_code, 200)
        
        # Verify goal no longer exists
        response = requests.get(f"{API_URL}/goals/{self.test_goal['id']}")
        self.assertEqual(response.status_code, 404)
        
        # Verify transactions were also deleted
        response = requests.get(f"{API_URL}/transactions/{self.test_goal['id']}")
        self.assertEqual(response.status_code, 200)
        transactions_after = response.json()
        self.assertEqual(len(transactions_after), 0)
        
        # Reset test_goal so tearDown doesn't try to delete it again
        delattr(self, 'test_goal')

if __name__ == "__main__":
    print(f"Testing against API URL: {API_URL}")
    unittest.main()