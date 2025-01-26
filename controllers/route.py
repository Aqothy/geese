from flask import Blueprint, request, jsonify
import yfinance as yf
from app import collection
from utils import fetch_sp500_data
from trading import (
    initialize_user, buy_stock, sell_stock, get_portfolio,
    update_login_streak, get_stock_price, get_portfolio_with_streak
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
    per_page = 10  # Number of stocks per page
    data, total_pages = fetch_sp500_data(page=page, per_page=per_page)
    return jsonify({
        'data': data,
        'total_pages': total_pages,
        'current_page': page
    })

@index.route('/stock-data/<ticker>')
def stock_data(ticker):
    try:
        stock_info = yf.Ticker(ticker).info
        data = {
            'Name': stock_info.get('shortName'),
            'Bid': stock_info.get('bid'),
            'Ask': stock_info.get('ask'),
            'Open': stock_info.get('regularMarketOpen'),
            'High': stock_info.get('regularMarketDayHigh'),
            'Low': stock_info.get('regularMarketDayLow'),
            'Market Cap': stock_info.get('marketCap'),
            'P/E Ratio': stock_info.get('trailingPE'),
        }
        return jsonify({ticker: data})
    except Exception as e:
        return jsonify({'error': str(e)}), 404

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
    print('init user')
    initialize_user(user_id=1)
    result = get_portfolio(1)
    return jsonify(result)


#####
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
    data = request.get_json()

    if not data or 'symbol' not in data:
        return jsonify({
            'success': False,
            'error': 'Missing symbol'
        }), 400

    # If amount is provided, use it for dollar-based investing
    if 'amount' in data:
        result = buy_stock(1, data['symbol'], float(data['amount']))
    # Otherwise use shares if provided
    elif 'shares' in data:
        # Get current price to calculate amount
        try:
            current_price = get_stock_price(data['symbol'])
            amount = float(data['shares']) * current_price
            result = buy_stock(1, data['symbol'], amount)
        except ValueError as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 400
    else:
        return jsonify({
            'success': False,
            'error': 'Must provide either amount or shares'
        }), 400

    if 'error' in result:
        return jsonify({
            'success': False,
            'error': result['error']
        }), 400

    # Get updated portfolio after purchase
    portfolio = get_portfolio(1)

    return jsonify({
        'success': True,
        'transaction': result,
        'portfolio': portfolio
    })

@index.route('/portfolio/details')
def portfolio_details():
    return jsonify(get_portfolio(1))


@index.route('/sell', methods=['POST'])
def sell():
    data = request.get_json()
    return jsonify(sell_stock(1, data['symbol'], float(data['quantity'])))
#####

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
