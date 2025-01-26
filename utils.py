import time
import requests
import bs4 as bs
import yfinance as yf

_cache = {}
CACHE_TTL = 300  # 5 minutes

def get_500():
    print("Getting 500")
    """Web scrape top 500 and write to file (only needed if you want to auto-update that file)."""
    resp = requests.get('http://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
    soup = bs.BeautifulSoup(resp.text, 'lxml')
    table = soup.find('table', {'id': 'constituents'})
    tickers = []
    for row in table.findAll('tr')[1:]:
        ticker = row.findAll('td')[0].text
        # Clean up newlines
        ticker = ticker.strip()
        tickers.append(ticker)

    # Write tickers to a file
    with open('tickers.txt', 'w') as f:
        for t in tickers:
            f.write(f"{t}\n")


def read_tickers_from_file(filename='tickers.txt'):
    """Read tickers from file (existing code)."""
    with open(filename, 'r') as f:
        return [line.strip() for line in f.readlines()]

def fetch_sp500_data(page=1, per_page=15):
    """Fetch data for a paginated chunk of S&P 500 stocks with caching."""
    tickers = read_tickers_from_file()
    total_pages = (503 + per_page - 1) // per_page

    # Validate page number
    if page < 1 or page > total_pages:
        return {}, 0  # Return empty data and invalid total_pages

    # Check cache for existing valid data
    if page in _cache:
        cached = _cache[page]
        if time.time() - cached['timestamp'] < CACHE_TTL:
            return cached['data'], total_pages

    # Calculate tickers for the current page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    current_tickers = tickers[start_idx:end_idx]

    # Fetch data for current tickers
    data = {}
    for ticker in current_tickers:
        try:
            info = yf.Ticker(ticker).info
            data[ticker] = {
                'Bid': info.get('bid'),
                'Ask': info.get('ask'),
                'Open': info.get('regularMarketOpen'),
                'High': info.get('regularMarketDayHigh'),
                'Low': info.get('regularMarketDayLow'),
                'Market Cap': info.get('marketCap'),
                'P/E Ratio': info.get('trailingPE'),
            }
        except Exception as e:
            print(f"Error fetching {ticker}: {e}")
            data[ticker] = None

    # Update cache
    _cache[page] = {
        'data': data,
        'timestamp': time.time()
    }

    return data, total_pages
