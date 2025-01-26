import unittest
from trading import initialize_user, buy_stock, sell_stock, get_portfolio, get_stock_price
from pymongo import MongoClient
import os
from dotenv import load_dotenv
from app import create_app
from datetime import datetime, timedelta

class TestTrading(unittest.TestCase):
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
        
        # Set up Flask test client
        cls.app = create_app(testing=True)
        cls.client = cls.app.test_client()
    
    def setUp(self):
        # Initialize test user before each test
        initialize_user(user_id=1)
    
    def tearDown(self):
        # Clean up after each test
        self.users_collection.delete_one({'user_id': 1})
    
    def test_initialize_user(self):
        """Test user initialization"""
        user = self.users_collection.find_one({'user_id': 1})
        self.assertIsNotNone(user)
        self.assertEqual(user['buying_power'], 10000)
        self.assertEqual(len(user['portfolio']), 0)
    
    def test_buy_stock_success(self):
        """Test buying stocks successfully with dollar amount"""
        result = buy_stock(1, 'AAPL', 1000)  # Buy $1000 worth of stock
        self.assertTrue(result['success'])
        self.assertIn('shares_bought', result)
        
        user = self.users_collection.find_one({'user_id': 1})
        self.assertEqual(len(user['portfolio']), 1)
        self.assertAlmostEqual(user['buying_power'], 9000, delta=5)  # Allow $5 variance
    
    def test_buy_stock_insufficient_funds(self):
        """Test buying stocks with insufficient funds"""
        # Try to buy more than available funds
        result = buy_stock(1, 'AAPL', 15000)
        self.assertIn('error', result)
        self.assertEqual(result['error'], 'Insufficient funds')
    
    def test_buy_stock_small_amount(self):
        """Test buying with amount too small for minimum shares"""
        result = buy_stock(1, 'AAPL', 0.01)  # Try to buy 1 cent worth
        self.assertIn('error', result)
        self.assertEqual(result['error'], 'Dollar amount too small to buy minimum share quantity (0.01)')
    
    def test_sell_stock_success(self):
        """Test selling stocks successfully"""
        # First buy some stock
        buy_result = buy_stock(1, 'AAPL', 1000)
        initial_shares = buy_result['shares_bought']
        
        # Sell half of the shares
        sell_result = sell_stock(1, 'AAPL', initial_shares / 2)
        self.assertTrue(sell_result['success'])
        
        user = self.users_collection.find_one({'user_id': 1})
        self.assertEqual(len(user['portfolio']), 1)
        self.assertAlmostEqual(user['portfolio'][0]['quantity'], initial_shares / 2, places=2)
    
    def test_sell_stock_insufficient_shares(self):
        """Test selling more shares than owned"""
        # First buy $500 worth of stock
        buy_result = buy_stock(1, 'AAPL', 500)
        shares_owned = buy_result['shares_bought']
        
        # Try to sell more than owned
        result = sell_stock(1, 'AAPL', shares_owned + 1)
        self.assertIn('error', result)
        self.assertIn('Insufficient shares', result['error'])
    
    def test_get_portfolio(self):
        """Test getting user portfolio"""
        # Buy some stocks first
        buy_stock(1, 'AAPL', 1000)
        buy_stock(1, 'GOOGL', 1000)
        
        portfolio = get_portfolio(1)
        self.assertIn('portfolio', portfolio)
        self.assertEqual(len(portfolio['portfolio']), 2)
        self.assertIn('buying_power', portfolio)
        self.assertAlmostEqual(portfolio['buying_power'], 8000, delta=5)  # Allow $5 variance
    
    def test_buy_multiple_times(self):
        """Test buying the same stock multiple times with dollar amounts"""
        # Buy $500 worth first
        first_buy = buy_stock(1, 'AAPL', 500)
        first_shares = first_buy['shares_bought']
        
        # Buy another $500 worth
        second_buy = buy_stock(1, 'AAPL', 500)
        second_shares = second_buy['shares_bought']
        
        user = self.users_collection.find_one({'user_id': 1})
        self.assertEqual(len(user['portfolio']), 1)
        self.assertAlmostEqual(user['portfolio'][0]['quantity'], first_shares + second_shares, places=2)
        self.assertAlmostEqual(user['buying_power'], 9000, delta=5)  # Allow $5 variance
    
    def test_get_stock_price_success(self):
        """Test getting stock price for a valid symbol"""
        response = self.client.get('/stock-price/AAPL')
        data = response.get_json()
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertEqual(data['symbol'], 'AAPL')
        self.assertIsInstance(data['price'], float)
        self.assertGreater(data['price'], 0)
    
    def test_get_stock_price_invalid_symbol(self):
        """Test getting stock price for an invalid symbol"""
        response = self.client.get('/stock-price/INVALID')
        data = response.get_json()
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', data)
    
    def test_stock_price_caching(self):
        """Test that stock prices are properly cached"""
        # First request should cache the price
        response1 = self.client.get('/stock-price/AAPL')
        data1 = response1.get_json()
        self.assertEqual(response1.status_code, 200)
        self.assertTrue(data1['success'])
        price1 = data1['price']
        
        # Second request within cache time should return same price
        response2 = self.client.get('/stock-price/AAPL')
        data2 = response2.get_json()
        self.assertEqual(response2.status_code, 200)
        self.assertTrue(data2['success'])
        price2 = data2['price']
        
        # Prices should be identical due to caching
        self.assertEqual(price1, price2)
        
        # Verify cache entry in database
        cache_entry = self.db['stocks'].find_one({'symbol': 'AAPL'})
        self.assertIsNotNone(cache_entry)
        self.assertEqual(cache_entry['price'], price1)
    
    def test_batch_stock_prices(self):
        """Test getting prices for multiple stocks"""
        response = self.client.post('/stock-prices', 
                                  json={'symbols': ['AAPL', 'GOOGL']})
        data = response.get_json()
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('prices', data)
        self.assertIn('AAPL', data['prices'])
        self.assertIn('GOOGL', data['prices'])
        self.assertIsInstance(data['prices']['AAPL'], float)
        self.assertIsInstance(data['prices']['GOOGL'], float)
    
    def test_batch_price_caching(self):
        """Test that batch stock price requests use caching"""
        # First batch request
        response1 = self.client.post('/stock-prices', 
                                   json={'symbols': ['AAPL', 'GOOGL']})
        data1 = response1.get_json()
        self.assertIn('prices', data1)
        
        # Second batch request should use cache
        response2 = self.client.post('/stock-prices', 
                                   json={'symbols': ['AAPL', 'GOOGL']})
        data2 = response2.get_json()
        self.assertIn('prices', data2)
        
        # Prices should be identical due to caching
        self.assertEqual(
            data1['prices']['AAPL'],
            data2['prices']['AAPL']
        )
        self.assertEqual(
            data1['prices']['GOOGL'],
            data2['prices']['GOOGL']
        )
        
        # Verify cache entries
        cache_entries = list(self.db['stocks'].find(
            {'symbol': {'$in': ['AAPL', 'GOOGL']}}
        ))
        self.assertEqual(len(cache_entries), 2)

if __name__ == '__main__':
    unittest.main() 