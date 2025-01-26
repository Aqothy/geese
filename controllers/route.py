from flask import Blueprint, request, jsonify
from app import collection, db
import yfinance as yf
from utils import fetch_sp500_data

index = Blueprint('index', __name__)

@index.route('/sp500-data')
def index_route():
    """Retrieves paginated S&P 500 data from Yahoo Finance."""
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
