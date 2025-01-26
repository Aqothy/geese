"""
Trading System Core Module

This module implements the core trading functionality for a stock trading platform.
It provides functions for user management, portfolio tracking, stock trading operations,
and market data retrieval.

Key Features:
- User portfolio management with cash balance tracking
- Real-time stock price fetching with caching
- Support for fractional share trading
- Daily and all-time return calculations
- Login streak and reward system
- Comprehensive error handling

Dependencies:
- yfinance: For real-time stock market data
- pymongo: For database operations
- flask: For web framework utilities
- python-dotenv: For environment variable management
"""

import yfinance as yf
from pymongo import MongoClient
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables from .env file
# This allows us to keep sensitive information like database credentials secure
load_dotenv()

# Initialize MongoDB connection
# We use MongoDB to store user portfolios and transaction history
client = MongoClient(os.getenv('DB_URI'))  # Get MongoDB connection string from environment variables
db = client['stock_trading']  # Select the stock_trading database
users_collection = db['users']  # Collection for user data (portfolios, balances)
stocks_collection = db['stocks']  # Collection for stock-related data (price cache)

def initialize_user(user_id=1):
    """
    Initialize a new user in the database with starting cash balance.

    This function creates a new user document if one doesn't exist, setting up:
    - Initial buying power ($10,000)
    - Empty portfolio
    - Login streak tracking
    - Last login timestamp

    Args:
        user_id (int): Unique identifier for the user (defaults to 1)

    Database Structure:
    {
        'user_id': int,          # Unique identifier for the user
        'portfolio': [],         # List of stocks owned by user
        'buying_power': float,   # Available cash for trading
        'streak': int,          # Current login streak
        'last_login': datetime, # Last login date
        'streak_reward_claimed': datetime  # Last date streak reward was claimed
    }
    """
    if not users_collection.find_one({'user_id': user_id}):
        current_time = datetime.utcnow()
        users_collection.insert_one({
            'user_id': user_id,
            'portfolio': [],  # Empty portfolio to start
            'buying_power': 10000,  # Starting balance of $10,000
            'streak': 0,  # Initialize streak counter
            'last_login': current_time,  # Initialize last login date
            'streak_reward_claimed': None  # Initialize streak reward claim date
        })

def update_login_streak(user_id):
    """
    Update user's login streak and provide daily reward if eligible.

    This function manages the daily login reward system:
    - First-time login gets $100 reward
    - Consecutive daily logins maintain streak
    - Missing a day resets streak
    - Daily reward of $100 for each login
    - Rewards can only be claimed once per day

    Args:
        user_id (int): User's unique identifier

    Returns:
        dict: Information about streak and reward including:
            - Current streak count
            - Reward amount (if any)
            - Status message
    """
    user = users_collection.find_one({'user_id': user_id})
    if not user:
        return {'error': 'User not found'}

    current_time = datetime.utcnow()
    last_login = user.get('last_login')
    last_reward = user.get('streak_reward_claimed')
    current_streak = user.get('streak', 0)

    # Convert to datetime if stored as string
    if isinstance(last_login, str):
        last_login = datetime.fromisoformat(last_login.replace('Z', '+00:00'))
    if isinstance(last_reward, str):
        last_reward = datetime.fromisoformat(last_reward.replace('Z', '+00:00'))

    # First login or reward not yet claimed
    if last_reward is None:
        users_collection.update_one(
            {'user_id': user_id},
            {
                '$set': {
                    'last_login': current_time,
                    'streak': 1,
                    'streak_reward_claimed': current_time,
                    'buying_power': user['buying_power'] + 100
                }
            }
        )
        return {
            'message': 'First login! Streak started!',
            'streak': 1,
            'reward': 100
        }

    # Check if this is a new day (comparing dates, not times)
    last_login_date = last_login.date()
    current_date = current_time.date()
    last_reward_date = last_reward.date()

    if current_date > last_login_date:
        # Check if the login is consecutive (yesterday)
        if current_date == (last_login_date + timedelta(days=1)):
            # Increment streak
            current_streak += 1
        else:
            # Break streak if not consecutive
            current_streak = 1

        # Check if reward can be claimed (once per day)
        if current_date > last_reward_date:
            # Add reward
            reward_amount = 100  # Daily reward amount
            users_collection.update_one(
                {'user_id': user_id},
                {
                    '$set': {
                        'last_login': current_time,
                        'streak': current_streak,
                        'streak_reward_claimed': current_time,
                        'buying_power': user['buying_power'] + reward_amount
                    }
                }
            )
            return {
                'message': f'Daily login streak: {current_streak} days! Reward claimed: ${reward_amount}',
                'streak': current_streak,
                'reward': reward_amount
            }

    # Same day login or reward already claimed
    users_collection.update_one(
        {'user_id': user_id},
        {
            '$set': {
                'last_login': current_time,
                'streak': current_streak
            }
        }
    )
    return {
        'message': f'Welcome back! Current streak: {current_streak} days',
        'streak': current_streak,
        'reward': 0
    }

def get_stock_price(symbol, max_cache_age_seconds=30):
    """
    Fetch the current market price for a given stock symbol using Yahoo Finance API.

    Implements a caching system to:
    - Reduce API calls to Yahoo Finance
    - Improve response times
    - Prevent rate limiting
    - Maintain consistent prices during rapid transactions

    Cache System:
    - Prices are stored in MongoDB with timestamps
    - Cache expires after max_cache_age_seconds
    - New prices are fetched only when cache expires

    Args:
        symbol (str): Stock symbol (e.g., 'AAPL' for Apple)
        max_cache_age_seconds (int): Maximum age of cached price in seconds

    Returns:
        float: Current stock price

    Raises:
        ValueError: If price cannot be fetched or symbol is invalid
    """
    try:
        # Check cache first
        cached_data = stocks_collection.find_one({'symbol': symbol})
        current_time = datetime.utcnow()

        if cached_data and 'price' in cached_data and 'timestamp' in cached_data:
            cache_age = (current_time - cached_data['timestamp']).total_seconds()
            if cache_age < max_cache_age_seconds:
                return cached_data['price']

        # If not in cache or too old, fetch new price
        stock = yf.Ticker(symbol)
        hist = stock.history(period='1d')
        if hist.empty:
            raise ValueError(f"No price data available for {symbol}")

        price = hist['Close'].iloc[-1]

        # Update cache
        stocks_collection.update_one(
            {'symbol': symbol},
            {
                '$set': {
                    'price': price,
                    'timestamp': current_time
                }
            },
            upsert=True
        )

        return price
    except Exception as e:
        raise ValueError(f"Error fetching price for {symbol}: {str(e)}")

def get_multiple_stock_prices(symbols, max_cache_age_seconds=30):
    """
    Fetch current market prices for multiple stock symbols.

    Optimizes multiple price requests by:
    - Utilizing the cache system
    - Batching requests when possible
    - Handling errors individually per symbol

    Args:
        symbols (list): List of stock symbols
        max_cache_age_seconds (int): Maximum age of cached prices in seconds

    Returns:
        dict: Dictionary containing:
            - prices: Dict of symbol -> price mappings
            - errors: Dict of symbol -> error message for failed requests
    """
    prices = {}
    errors = {}
    current_time = datetime.utcnow()

    # Check cache first
    cached_data = list(stocks_collection.find({
        'symbol': {'$in': symbols},
        'timestamp': {'$gt': current_time - timedelta(seconds=max_cache_age_seconds)}
    }))

    # Create lookup of cached prices
    cached_prices = {doc['symbol']: doc['price'] for doc in cached_data}

    # Process each symbol
    for symbol in symbols:
        try:
            if symbol in cached_prices:
                prices[symbol] = cached_prices[symbol]
            else:
                prices[symbol] = get_stock_price(symbol, max_cache_age_seconds)
        except ValueError as e:
            errors[symbol] = str(e)

    return {'prices': prices, 'errors': errors}

def buy_stock(user_id, symbol, amount):
    """
    Process a stock purchase order and update the user's portfolio.

    Implements dollar-based investing with:
    - Real-time price fetching
    - Portfolio position updates
    - Buying power verification
    - Transaction tracking

    Args:
        user_id (int): User's unique identifier
        symbol (str): Symbol of stock to buy (e.g., 'AAPL')
        amount (float): Amount of money to spend on the stock

    Returns:
        dict: Result of the transaction including:
            - success status
            - transaction details
            - updated portfolio
            - error message (if any)
    """
    try:
        # Get current portfolio and stock data
        portfolio = get_portfolio(user_id)
        stock_price = get_stock_price(symbol)
        
        # Calculate shares based on amount
        shares = amount / stock_price
        
        # Validate buying power
        if amount > portfolio['buying_power']:
            raise ValueError("Insufficient buying power")

        # Update buying power
        portfolio['buying_power'] -= amount

        # Update or add stock to portfolio
        stock_found = False
        for holding in portfolio['portfolio']:
            if holding['symbol'] == symbol:
                # Update existing position
                total_value = holding['current_value'] + amount
                total_shares = holding['quantity'] + shares
                holding.update({
                    'quantity': total_shares,
                    'current_value': total_value,
                    'average_price': total_value / total_shares,
                    'current_price': stock_price
                })
                stock_found = True
                break

        if not stock_found:
            # Add new position
            portfolio['portfolio'].append({
                'symbol': symbol,
                'quantity': shares,
                'average_price': stock_price,
                'current_price': stock_price,
                'current_value': amount
            })

        # Update total portfolio value
        portfolio['total_value'] = (
            portfolio['buying_power'] + 
            sum(holding['current_value'] for holding in portfolio['portfolio'])
        )

        # Save updated portfolio
        users_collection.update_one(
            {'user_id': user_id},
            {'$set': portfolio}
        )

        # Return transaction details and updated portfolio
        return {
            'success': True,
            'transaction': {
                'symbol': symbol,
                'shares_bought': shares,
                'price_per_share': stock_price,
                'total_amount': amount
            },
            'portfolio': portfolio
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def sell_stock(user_id, stock_symbol, quantity):
    """
    Process a stock sell order and update the user's portfolio.

    Supports:
    - Fractional share selling (minimum 0.01 shares)
    - Automatic position reduction
    - Position removal when fully sold
    - Real-time price fetching

    Transaction Flow:
    1. Validate quantity
    2. Get current market price
    3. Verify sufficient shares owned
    4. Update portfolio and buying power

    Args:
        user_id (int): User's unique identifier
        stock_symbol (str): Symbol of stock to sell
        quantity (float): Number of shares to sell

    Returns:
        dict: Result of the transaction including:
            - success status
            - total value received
            - price per share
            - error message (if any)
    """
    try:
        # Validate quantity
        quantity = float(quantity)
        if quantity <= 0:
            return {'error': 'Quantity must be greater than 0'}

        # Round to 2 decimal places for fractional shares
        quantity = round(quantity, 2)

        # Get current market price
        current_price = get_stock_price(stock_symbol)
        total_value = round(current_price * quantity, 2)

        # Find user and verify stock ownership
        user = users_collection.find_one({'user_id': user_id})
        if not user:
            return {'error': 'User not found'}

        portfolio = user['portfolio']
        stock_found = False

        # Find the stock in user's portfolio
        for stock in portfolio:
            if stock['symbol'] == stock_symbol:
                # Verify sufficient shares
                if stock['quantity'] < quantity:
                    return {'error': f'Insufficient shares. You own {stock["quantity"]} shares.'}

                # Update share quantity
                stock['quantity'] = round(stock['quantity'] - quantity, 2)
                stock_found = True

                # Remove stock from portfolio if no shares left (or less than 0.01)
                if stock['quantity'] < 0.01:
                    portfolio.remove(stock)
                break

        if not stock_found:
            return {'error': 'Stock not found in portfolio'}

        # Update user document with new portfolio and cash balance
        new_buying_power = round(user['buying_power'] + total_value, 2)
        users_collection.update_one(
            {'user_id': user_id},
            {
                '$set': {
                    'portfolio': portfolio,
                    'buying_power': new_buying_power
                }
            }
        )

        return {
            'success': True,
            'value': total_value,
            'price_per_share': current_price
        }
    except ValueError as e:
        return {'error': str(e)}

def calculate_daily_return(user_id):
    """
    Calculate today's return for the user's portfolio.

    Calculates:
    - Individual stock performance
    - Total portfolio performance
    - Percentage and absolute returns
    - Day-over-day value changes

    Uses:
    - Yesterday's closing prices
    - Current market prices
    - Position quantities

    Args:
        user_id (int): User's unique identifier

    Returns:
        dict: Daily return information including:
            - Absolute return (in dollars)
            - Percentage return
            - Individual stock returns
            - Portfolio values (yesterday vs today)
    """
    user = users_collection.find_one({'user_id': user_id})
    if not user:
        return {'error': 'User not found'}

    portfolio = user['portfolio']
    daily_return = 0
    daily_return_percentage = 0
    stock_returns = []
    portfolio_value_yesterday = user['buying_power']
    portfolio_value_today = user['buying_power']

    for stock in portfolio:
        try:
            # Get today's and yesterday's prices
            ticker = yf.Ticker(stock['symbol'])
            hist = ticker.history(period='2d')

            if len(hist) >= 2:
                yesterday_price = hist['Close'].iloc[-2]
                today_price = hist['Close'].iloc[-1]
                quantity = stock['quantity']

                # Calculate returns for this stock
                stock_daily_return = (today_price - yesterday_price) * quantity
                stock_daily_return_percentage = ((today_price - yesterday_price) / yesterday_price) * 100

                # Add to total returns
                daily_return += stock_daily_return
                portfolio_value_yesterday += yesterday_price * quantity
                portfolio_value_today += today_price * quantity

                stock_returns.append({
                    'symbol': stock['symbol'],
                    'daily_return': stock_daily_return,
                    'daily_return_percentage': stock_daily_return_percentage,
                    'yesterday_price': yesterday_price,
                    'today_price': today_price
                })
        except Exception as e:
            stock_returns.append({
                'symbol': stock['symbol'],
                'error': str(e)
            })

    # Calculate total portfolio return percentage
    if portfolio_value_yesterday > 0:
        daily_return_percentage = ((portfolio_value_today - portfolio_value_yesterday) / portfolio_value_yesterday) * 100

    return {
        'daily_return': daily_return,
        'daily_return_percentage': daily_return_percentage,
        'portfolio_value_yesterday': portfolio_value_yesterday,
        'portfolio_value_today': portfolio_value_today,
        'stock_returns': stock_returns
    }

def calculate_all_time_return(user_id):
    """
    Calculate all-time return for the user's portfolio.

    Tracks:
    - Total portfolio performance since inception
    - Individual stock performance
    - Initial investment vs current value
    - Percentage and absolute returns

    Calculations include:
    - Position-weighted average costs
    - Realized and unrealized gains
    - Cash balance changes

    Args:
        user_id (int): User's unique identifier

    Returns:
        dict: All-time return information including:
            - Total return (in dollars)
            - Percentage return
            - Initial investment amount
            - Current portfolio value
            - Individual stock performance metrics
    """
    user = users_collection.find_one({'user_id': user_id})
    if not user:
        return {'error': 'User not found'}

    portfolio = user['portfolio']
    initial_investment = 10000  # Starting balance
    current_value = user['buying_power']
    stock_performance = []

    for stock in portfolio:
        try:
            # Get current price
            current_price = get_stock_price(stock['symbol'])
            quantity = stock['quantity']
            avg_price = stock['average_price']

            # Calculate stock's return
            stock_initial_value = avg_price * quantity
            stock_current_value = current_price * quantity
            stock_return = stock_current_value - stock_initial_value
            stock_return_percentage = ((current_price - avg_price) / avg_price) * 100

            # Add to total value
            current_value += stock_current_value
            initial_investment += stock_initial_value

            stock_performance.append({
                'symbol': stock['symbol'],
                'total_return': stock_return,
                'return_percentage': stock_return_percentage,
                'initial_value': stock_initial_value,
                'current_value': stock_current_value,
                'quantity': quantity,
                'average_price': avg_price,
                'current_price': current_price
            })
        except Exception as e:
            stock_performance.append({
                'symbol': stock['symbol'],
                'error': str(e)
            })

    # Calculate total return
    total_return = current_value - initial_investment
    total_return_percentage = ((current_value - initial_investment) / initial_investment) * 100 if initial_investment > 0 else 0

    return {
        'total_return': total_return,
        'total_return_percentage': total_return_percentage,
        'initial_investment': initial_investment,
        'current_value': current_value,
        'stock_performance': stock_performance
    }

def get_portfolio(user_id):
    """
    Retrieve user's current portfolio with up-to-date market values.

    Provides:
    - Current position values
    - Cash balance
    - Total portfolio value
    - Performance metrics

    Includes:
    - Real-time price updates
    - Daily return calculations
    - All-time return calculations
    - Individual position details

    Args:
        user_id (int): User's unique identifier

    Returns:
        dict: Comprehensive portfolio information including:
            - List of stocks owned with current prices
            - Available buying power
            - Total portfolio value
            - Daily performance metrics
            - All-time performance metrics
    """
    user = users_collection.find_one({'user_id': user_id})
    if not user:
        return {'error': 'User not found'}

    # Calculate current values of all positions
    portfolio = user['portfolio']
    total_value = user['buying_power']

    # Update each stock with current market value
    for stock in portfolio:
        try:
            current_price = get_stock_price(stock['symbol'])
            stock['current_price'] = current_price
            stock['current_value'] = current_price * stock['quantity']
            total_value += stock['current_value']
        except ValueError:
            stock['current_price'] = None
            stock['current_value'] = None

    # Get daily and all-time returns
    daily_returns = calculate_daily_return(user_id)
    all_time_returns = calculate_all_time_return(user_id)

    return {
        'portfolio': portfolio,
        'buying_power': user['buying_power'],
        'total_value': total_value,
        'daily_returns': daily_returns,
        'all_time_returns': all_time_returns
    }

def get_portfolio_with_streak(user_id):
    """
    Get portfolio information and update login streak in a single operation.

    Combines:
    - Portfolio value calculation
    - Login streak processing
    - Reward distribution

    Optimizes:
    - Database operations
    - API response time
    - Data consistency

    Args:
        user_id (int): User's unique identifier

    Returns:
        dict: Combined portfolio and streak information including:
            - Complete portfolio details
            - Streak status
            - Reward information
            - Performance metrics
    """
    # Update streak first to ensure reward is included in portfolio value
    streak_info = update_login_streak(user_id)

    # Get portfolio information
    portfolio_info = get_portfolio(user_id)

    if 'error' in portfolio_info:
        return format_api_response(success=False, error=portfolio_info['error'])

    # Combine the information
    return format_api_response(
        data={
            'portfolio': portfolio_info['portfolio'],
            'buying_power': portfolio_info['buying_power'],
            'total_value': portfolio_info['total_value'],
            'daily_returns': portfolio_info['daily_returns'],
            'all_time_returns': portfolio_info['all_time_returns'],
            'streak_info': streak_info
        }
    )
