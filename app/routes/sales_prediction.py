import logging
import json
import base64
import uuid
from flask import Blueprint, jsonify, request
from app.services.sales_prediction.prediction import prediction

sales_prediction = Blueprint('sales_prediction', __name__)

# logger = logging.getLogger(__name__)

@sales_prediction.route("/predict_sales", methods=['POST'])
def predict():
    request_data = request.get_json()
    data = prediction.get_sales(request_data)
    if not data:
        data = {
            "status":False,
            "message":"Something went wrong! We are working on it."
        }
    return jsonify(data)

