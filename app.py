from flask import Flask, request, jsonify
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

try:
    # init db here
    uri = os.getenv('DB_URI')

    client = MongoClient(os.getenv('DB_URI'))

    db = client['test']

    collection = db['users']

except Exception as e:
    raise e


def init_app():
    try:
        app = Flask(__name__)


        if uri is None:
            raise Exception('DB_URI is not set')

        # import blueprints here and register route
        from controllers.route import index

        app.register_blueprint(index, url_prefix='/')

        return app

    except Exception as e:
        print(e)
