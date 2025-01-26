from app import init_app
from flask_cors import CORS

app = init_app()

if __name__ == '__main__':
    print("runnning app")
    # enable cors for all origins
    CORS(app, resources={r"/*": {"origins": "*"}})
    app.run(port=8080, debug=True)
