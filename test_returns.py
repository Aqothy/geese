import unittest
from trading import initialize_user, buy_stock, calculate_daily_return, calculate_all_time_return, get_portfolio
from pymongo import MongoClient
import os
from dotenv import load_dotenv

class TestReturns(unittest.TestCase):
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
    
    def test_daily_return_empty_portfolio(self):
        """Test daily return calculation with empty portfolio"""
        result = calculate_daily_return(1)
        self.assertEqual(result['daily_return'], 0)
        self.assertEqual(result['daily_return_percentage'], 0)
        self.assertEqual(result['portfolio_value_yesterday'], 10000)  # Initial cash balance
        self.assertEqual(result['portfolio_value_today'], 10000)  # Initial cash balance
        self.assertEqual(len(result['stock_returns']), 0)
    
    def test_daily_return_with_stocks(self):
        """Test daily return calculation with stocks in portfolio"""
        # Buy some test stocks
        buy_stock(1, 'AAPL', 1)
        
        result = calculate_daily_return(1)
        self.assertIn('daily_return', result)
        self.assertIn('daily_return_percentage', result)
        self.assertIn('stock_returns', result)
        self.assertTrue(len(result['stock_returns']) > 0)
        
        # Verify stock return structure
        stock_return = result['stock_returns'][0]
        self.assertIn('symbol', stock_return)
        self.assertIn('daily_return', stock_return)
        self.assertIn('daily_return_percentage', stock_return)
        self.assertIn('yesterday_price', stock_return)
        self.assertIn('today_price', stock_return)
    
    def test_all_time_return_empty_portfolio(self):
        """Test all-time return calculation with empty portfolio"""
        result = calculate_all_time_return(1)
        self.assertEqual(result['total_return'], 0)
        self.assertEqual(result['total_return_percentage'], 0)
        self.assertEqual(result['initial_investment'], 10000)
        self.assertEqual(result['current_value'], 10000)
        self.assertEqual(len(result['stock_performance']), 0)
    
    def test_all_time_return_with_stocks(self):
        """Test all-time return calculation with stocks in portfolio"""
        # Buy some test stocks
        buy_stock(1, 'AAPL', 1)
        
        result = calculate_all_time_return(1)
        self.assertIn('total_return', result)
        self.assertIn('total_return_percentage', result)
        self.assertIn('stock_performance', result)
        self.assertTrue(len(result['stock_performance']) > 0)
        
        # Verify stock performance structure
        stock_perf = result['stock_performance'][0]
        self.assertIn('symbol', stock_perf)
        self.assertIn('total_return', stock_perf)
        self.assertIn('return_percentage', stock_perf)
        self.assertIn('initial_value', stock_perf)
        self.assertIn('current_value', stock_perf)
        self.assertIn('quantity', stock_perf)
        self.assertIn('average_price', stock_perf)
        self.assertIn('current_price', stock_perf)
    
    def test_portfolio_includes_returns(self):
        """Test that get_portfolio includes return information"""
        # Buy some test stocks
        buy_stock(1, 'AAPL', 1)
        
        result = get_portfolio(1)
        self.assertIn('daily_returns', result)
        self.assertIn('all_time_returns', result)
        
        # Verify daily returns structure
        daily_returns = result['daily_returns']
        self.assertIn('daily_return', daily_returns)
        self.assertIn('daily_return_percentage', daily_returns)
        self.assertIn('stock_returns', daily_returns)
        
        # Verify all-time returns structure
        all_time_returns = result['all_time_returns']
        self.assertIn('total_return', all_time_returns)
        self.assertIn('total_return_percentage', all_time_returns)
        self.assertIn('stock_performance', all_time_returns)

if __name__ == '__main__':
    unittest.main() 