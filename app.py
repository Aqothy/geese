from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

try:
    # Initialize MongoDB connection
    uri = os.getenv('DB_URI')
    if uri is None:
        raise Exception('DB_URI is not set')

    client = MongoClient(uri)
    db = client['stock_trading']
    collection = db['users']

except Exception as e:
    raise e

def init_app():
    """Initialize and configure Flask application"""
    app = Flask(__name__)
    
    # Configure CORS for development
    CORS(app, resources={r"/*": {"origins": "*"}})

    @app.route('/test/portfolio')
    def test_portfolio():
        """Test endpoint that returns mock portfolio data"""
        return jsonify({
            "total_value": 100000.00,
            "cash_balance": 50000.00,
            "stocks_value": 50000.00,
            "streak_info": {
                "current_streak": 5,
                "last_login": "2025-01-26T12:00:00Z"
            }
        })

    # Import blueprints here and register routes
    from controllers.route import index
    app.register_blueprint(index, url_prefix='/api')  # Changed to /api prefix

    # Test endpoints for frontend development
    @app.route('/test/portfolio/details')
    def test_portfolio_details():
        """Test endpoint returning detailed mock portfolio data"""
        portfolio = [
            {
                "symbol": "AAPL",
                "quantity": 10,
                "average_price": 150.00,
                "current_price": 175.50,
                "current_value": 1755.00
            },
            {
                "symbol": "GOOGL",
                "quantity": 5,
                "average_price": 2800.00,
                "current_price": 2950.00,
                "current_value": 14750.00
            },
            {
                "symbol": "MSFT",
                "quantity": 5,
                "average_price": 2800.00,
                "current_price": 2950.00,
                "current_value": 14750.00
            }
        ]
        buying_power = 50000.00
        
        # Calculate total value by summing up all stock values and buying power
        stocks_value = sum(stock["current_value"] for stock in portfolio)
        total_value = stocks_value + buying_power

        return jsonify({
            "portfolio": portfolio,
            "buying_power": buying_power,
            "total_value": total_value,
            "daily_returns": {
                "daily_return": 505.00,
                "daily_return_percentage": 0.76,
                "stock_returns": [
                    {
                        "symbol": "AAPL",
                        "daily_return": 205.00,
                        "daily_return_percentage": 1.2
                    },
                    {
                        "symbol": "GOOGL",
                        "daily_return": 300.00,
                        "daily_return_percentage": 0.5
                    }
                ]
            },
            "all_time_returns": {
                "total_return": 6505.00,
                "total_return_percentage": 10.84,
                "current_value": total_value
            },
            "streak_info": {
                "current_streak": 5,
                "last_login": "2025-01-26T12:00:00Z"
            }
        })

    @app.route('/test/stock-price/<symbol>')
    def test_stock_price(symbol):
        """Test endpoint returning mock stock price data"""
        mock_prices = {
            "AAPL": 175.50,
            "GOOGL": 2950.00,
            "MSFT": 380.25,
            "AMZN": 3450.75
        }
        price = mock_prices.get(symbol, 100.00)  # Default price for unknown symbols
        return jsonify({
            "success": True,
            "symbol": symbol,
            "price": price
        })

    @app.route('/test/buy', methods=['POST'])
    def test_buy():
        """Test endpoint simulating stock purchase"""
        data = request.get_json()
        return jsonify({
            "success": True,
            "shares_bought": round(float(data['amount']) / 175.50, 2),  # Using AAPL price as example
            "cost": float(data['amount']),
            "price_per_share": 175.50
        })

    @app.route('/test/sell', methods=['POST'])
    def test_sell():
        """Test endpoint simulating stock sale"""
        data = request.get_json()
        return jsonify({
            "success": True,
            "value": round(float(data['quantity']) * 175.50, 2),
            "price_per_share": 175.50
        })

    return app

def create_app(testing=False):
    """Create Flask application with optional testing configuration"""
    app = init_app()
    
    if testing:
        app.config['TESTING'] = True
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=8000)
