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
    CORS(app)  # Enable CORS for all routes

    # Import blueprints here and register routes
    from controllers.route import index
    app.register_blueprint(index, url_prefix='/')

    return app

def create_app(testing=False):
    """Create Flask application with optional testing configuration"""
    app = init_app()
    
    if testing:
        app.config['TESTING'] = True
    
    return app
