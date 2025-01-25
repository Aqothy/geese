from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy

def init_app():
    app = Flask(__name__)

    # init db here

    # import blueprints here and register route
    from controllers.route import index

    app.register_blueprint(index, url_prefix='/')

    return app
