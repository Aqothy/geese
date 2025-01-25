from flask import Blueprint, request, jsonify

index = Blueprint('index', __name__)

@index.route('/')
def index_route():
    return jsonify({"msg": "hello world"})
