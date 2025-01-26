import unittest
from trading import initialize_user, update_login_streak
from pymongo import MongoClient
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

class TestStreak(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Load environment variables
        load_dotenv()
        
        # Connect to MongoDB
        cls.client = MongoClient(os.getenv('DB_URI'))
        cls.db = cls.client['stock_trading']
        cls.users_collection = cls.db['users']
        
        # Clear test user if exists
        cls.users_collection.delete_one({'user_id': 1})
    
    def setUp(self):
        # Initialize test user before each test
        initialize_user(user_id=1)
    
    def tearDown(self):
        # Clean up after each test
        self.users_collection.delete_one({'user_id': 1})
    
    def test_first_login(self):
        """Test first time login streak initialization"""
        result = update_login_streak(1)
        self.assertEqual(result['streak'], 1)
        self.assertEqual(result['reward'], 100)
        
        user = self.users_collection.find_one({'user_id': 1})
        self.assertEqual(user['cash_balance'], 10100)  # Initial 10000 + 100 reward
    
    def test_same_day_login(self):
        """Test multiple logins in the same day"""
        # First login
        update_login_streak(1)
        initial_balance = self.users_collection.find_one({'user_id': 1})['cash_balance']
        
        # Second login same day
        result = update_login_streak(1)
        self.assertEqual(result['streak'], 1)
        self.assertEqual(result['reward'], 0)
        
        # Verify balance hasn't changed
        current_balance = self.users_collection.find_one({'user_id': 1})['cash_balance']
        self.assertEqual(current_balance, initial_balance)
    
    def test_consecutive_days(self):
        """Test login streak for consecutive days"""
        # First day login
        update_login_streak(1)
        
        # Simulate next day login
        yesterday = datetime.utcnow() - timedelta(days=1)
        self.users_collection.update_one(
            {'user_id': 1},
            {'$set': {'last_login': yesterday, 'streak_reward_claimed': yesterday}}
        )
        
        # Login next day
        result = update_login_streak(1)
        self.assertEqual(result['streak'], 2)
        self.assertEqual(result['reward'], 100)
        
        user = self.users_collection.find_one({'user_id': 1})
        self.assertEqual(user['cash_balance'], 10200)  # Initial 10000 + 2 * 100 rewards
    
    def test_broken_streak(self):
        """Test streak reset when missing a day"""
        # First day login
        update_login_streak(1)
        
        # Simulate login from 2 days ago
        two_days_ago = datetime.utcnow() - timedelta(days=2)
        self.users_collection.update_one(
            {'user_id': 1},
            {'$set': {'last_login': two_days_ago, 'streak_reward_claimed': two_days_ago}}
        )
        
        # Login today
        result = update_login_streak(1)
        self.assertEqual(result['streak'], 1)  # Streak should reset
        self.assertEqual(result['reward'], 100)

if __name__ == '__main__':
    unittest.main() 