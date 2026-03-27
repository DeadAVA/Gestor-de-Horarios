from flask import jsonify


def success_response(message: str, data=None, status_code: int = 200):
    response = {
        "success": True,
        "message": message,
        "data": data,
        "errors": [],
    }
    return jsonify(response), status_code


def error_response(message: str, errors=None, status_code: int = 400):
    response = {
        "success": False,
        "message": message,
        "data": None,
        "errors": errors or [],
    }
    return jsonify(response), status_code