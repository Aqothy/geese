from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import os
from dotenv import load_dotenv
from trading import buy_stock, get_stock_price, initialize_user, get_portfolio

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

    @app.route('/test/buy', methods=['POST'])
    def test_buy():
        """Test endpoint simulating stock purchase"""
        try:
            # Initialize user with test portfolio if not exists
            user = collection.find_one({'user_id': 1})
            if not user:
                initialize_user(user_id=1)
                # Set up initial portfolio matching test data
                collection.update_one(
                    {'user_id': 1},
                    {'$set': {
                        'portfolio': [
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
                        ],
                        'buying_power': 50000.00,
                        'total_value': 81255.00  # 50000 + 1755 + 14750 + 14750
                    }}
                )
            
            data = request.get_json()
            
            # Validate required fields
            if not data or 'symbol' not in data:
                return jsonify({
                    'success': False,
                    'error': 'Missing symbol'
                }), 400

            # Get amount or calculate from shares
            if 'amount' in data:
                amount = float(data['amount'])
            elif 'shares' in data:
                stock_price = get_stock_price(data['symbol'])
                amount = float(data['shares']) * stock_price
            else:
                return jsonify({
                    'success': False,
                    'error': 'Must provide either amount or shares'
                }), 400

            # Execute purchase
            result = buy_stock(1, data['symbol'], amount)
            
            if not result['success']:
                return jsonify(result), 400

            # Get updated portfolio
            portfolio = get_portfolio(1)
            
            return jsonify({
                'success': True,
                'transaction': result['transaction'],
                'portfolio': portfolio
            })

        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/test/sell', methods=['POST'])
    def test_sell():
        """Test endpoint simulating stock sale"""
        data = request.get_json()
        return jsonify({
            "success": True,
            "value": round(float(data['quantity']) * 175.50, 2),
            "price_per_share": 175.50
        })

    @app.route('/test/initialize', methods=['POST'])
    def test_initialize():
        """Test endpoint to reset user portfolio to initial test state"""
        try:
            # Delete existing user if exists
            collection.delete_one({'user_id': 1})
            
            # Initialize user
            initialize_user(user_id=1)
            
            # Set up test portfolio
            collection.update_one(
                {'user_id': 1},
                {'$set': {
                    'portfolio': [
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
                    ],
                    'buying_power': 50000.00,
                    'total_value': 81255.00
                }}
            )
            
            return jsonify({
                'success': True,
                'message': 'Portfolio initialized with test data'
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

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
