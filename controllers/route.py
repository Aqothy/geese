"""
Trading Platform API Routes

This module defines the REST API endpoints for the trading platform.
It handles HTTP requests and responses, input validation, and
coordinates with the trading module for business logic.

API Structure:
- User Management: Initialize user, login
- Trading Operations: Buy/sell stocks
- Portfolio Management: View portfolio, get stock prices
- Market Data: S&P 500 data, batch price requests

All endpoints return JSON responses with appropriate HTTP status codes.
Error handling is implemented consistently across all routes.
"""

from flask import Blueprint, request, jsonify
from app import collection, db
import yfinance as yf
from utils import fetch_sp500_data
from trading import (
    initialize_user, buy_stock, sell_stock, get_portfolio, 
    update_login_streak, get_stock_price, get_multiple_stock_prices, get_portfolio_with_streak
)

# Create a Blueprint for all trading routes
index = Blueprint('index', __name__)

@index.route('/sp500-data')
def index_route():
    """
    Retrieves paginated S&P 500 data from Yahoo Finance.
    
    Provides a paginated list of S&P 500 stocks with:
    - Basic company information
    - Current market data
    - Trading metrics
    
    Query Parameters:
        page (int): Page number for pagination (default: 1)
        per_page (int): Number of stocks per page (fixed: 15)
    
    Returns:
        JSON response containing:
        - List of stock data
        - Total number of pages
        - Current page number
    
    Status Codes:
        200: Successful request
    """
    page = request.args.get('page', default=1, type=int)
    per_page = 15  # Number of stocks per page
    data, total_pages = fetch_sp500_data(page=page, per_page=per_page)
    return jsonify({
        'data': data,
        'total_pages': total_pages,
        'current_page': page
    })

@index.route('/initialize-user', methods=['POST'])
def init_user():
    """
    Initialize a new user and get initial portfolio.
    
    Creates a new user account with:
    - Starting balance of $10,000
    - Empty portfolio
    - Login streak tracking
    
    Returns:
        JSON response containing:
        - Initial portfolio state
        - Starting buying power
        - Success/error status
    
    Status Codes:
        200: User initialized successfully
    """
    initialize_user(user_id=1)
    result = get_portfolio(1)
    return jsonify(result)

@index.route('/login', methods=['POST'])
def login():
    """
    Update login streak and get portfolio.
    
    Processes daily login:
    - Updates login streak
    - Awards daily reward if eligible
    - Retrieves current portfolio state
    
    Returns:
        JSON response containing:
        - Updated portfolio
        - Streak information
        - Reward details
    
    Status Codes:
        200: Login processed successfully
    """
    result = get_portfolio_with_streak(1)
    return jsonify(result)

@index.route('/buy', methods=['POST'])
def buy():
    """
    Buy stocks and get updated portfolio.
    
    Processes stock purchase:
    - Validates input parameters
    - Checks sufficient funds
    - Executes trade
    - Updates portfolio
    
    Request Body:
        {
            "symbol": str,  # Stock symbol (e.g., "AAPL")
            "amount": float # Dollar amount to invest
        }
    
    Returns:
        JSON response containing:
        - Transaction details
        - Updated position
        - Success/error status
    
    Status Codes:
        200: Purchase successful
        400: Invalid request (missing/invalid parameters)
    """
    data = request.get_json()
    if not data or 'symbol' not in data or 'amount' not in data:
        return jsonify({
            'error': 'Missing symbol or amount'
        }), 400
    
    result = buy_stock(1, data['symbol'], float(data['amount']))
    if 'error' in result:
        return jsonify(result), 400
    
    return jsonify(result)

@index.route('/sell', methods=['POST'])
def sell():
    """
    Sell stocks and get updated portfolio.
    
    Processes stock sale:
    - Validates input parameters
    - Checks sufficient shares
    - Executes trade
    - Updates portfolio
    
    Request Body:
        {
            "symbol": str,    # Stock symbol (e.g., "AAPL")
            "quantity": float # Number of shares to sell
        }
    
    Returns:
        JSON response containing:
        - Transaction details
        - Updated position
        - Success/error status
    
    Status Codes:
        200: Sale successful
        400: Invalid request (missing/invalid parameters)
    """
    data = request.get_json()
    if not data or 'symbol' not in data or 'quantity' not in data:
        return jsonify({
            'error': 'Missing symbol or quantity'
        }), 400
    
    result = sell_stock(1, data['symbol'], float(data['quantity']))
    if 'error' in result:
        return jsonify(result), 400
    
    return jsonify(result)

@index.route('/portfolio', methods=['GET'])
def portfolio():
    """
    Get portfolio and streak information.
    
    Retrieves comprehensive portfolio data:
    - Current positions
    - Cash balance
    - Total value
    - Performance metrics
    
    Returns:
        JSON response containing:
        - Complete portfolio details
        - Performance calculations
        - Success/error status
    
    Status Codes:
        200: Portfolio retrieved successfully
    """
    result = get_portfolio(1)
    return jsonify(result)

@index.route('/stock-price/<symbol>', methods=['GET'])
def stock_price(symbol):
    """
    Get current price for a stock symbol.
    
    Fetches real-time price data:
    - Uses caching system
    - Validates symbol
    - Handles errors
    
    URL Parameters:
        symbol (str): Stock symbol to look up
    
    Returns:
        JSON response containing:
        - Current price
        - Symbol details
        - Success/error status
    
    Status Codes:
        200: Price retrieved successfully
        400: Invalid symbol or fetch error
    """
    try:
        price = get_stock_price(symbol)
        return jsonify({
            'success': True,
            'symbol': symbol,
            'price': price
        })
    except ValueError as e:
        return jsonify({
            'error': str(e)
        }), 400

@index.route('/stock-prices', methods=['POST'])
def batch_stock_prices():
    """
    Get current prices for multiple stock symbols.
    
    Processes batch price requests:
    - Validates input
    - Uses caching system
    - Handles multiple symbols efficiently
    
    Request Body:
        {
            "symbols": list[str]  # List of stock symbols
        }
    
    Returns:
        JSON response containing:
        - Price data for each symbol
        - Any errors encountered
        - Success/error status
    
    Status Codes:
        200: Prices retrieved successfully
        400: Invalid request format
    """
    data = request.get_json()
    if not data or 'symbols' not in data:
        return jsonify({
            'error': 'Missing symbols list'
        }), 400
    
    symbols = data['symbols']
    if not isinstance(symbols, list):
        return jsonify({
            'error': 'Symbols must be a list'
        }), 400
    
    result = get_multiple_stock_prices(symbols)
    return jsonify(result)

@index.route('/')
def home():
    """
    API documentation endpoint.
    
    Provides:
    - List of available endpoints
    - Basic usage information
    - API status
    
    Returns:
        JSON response containing:
        - API status message
        - Endpoint documentation
    
    Status Codes:
        200: Documentation retrieved successfully
    """
    return jsonify({
        'message': 'Trading API is running',
        'endpoints': {
            'POST /initialize-user': 'Initialize a new user',
            'POST /login': 'Update login streak and get daily reward',
            'POST /buy': 'Buy stocks (requires symbol and amount)',
            'POST /sell': 'Sell stocks (requires symbol and quantity)',
            'GET /portfolio': 'Get user portfolio',
            'GET /stock-price/<symbol>': 'Get current price for a stock'
        }
    })
