# cinema_routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Cinema

cinema_bp = Blueprint('cinema', __name__)

@cinema_bp.route('/', methods=['GET'])
def get_cinemas():
    cinemas = Cinema.query.all()
    return jsonify([{"id": c.id, "name": c.name, "address": c.address} for c in cinemas])

@cinema_bp.route('/<int:cinema_id>', methods=['GET'])
def get_cinema(cinema_id):
    c = Cinema.query.get(cinema_id)
    if not c:
        return jsonify({"message": "Cinema not found"}), 404
    return jsonify({"id": c.id, "name": c.name, "address": c.address})

@cinema_bp.route('/', methods=['POST'])
@jwt_required()
def create_cinema():
    identity = get_jwt_identity()
    if identity["role"] != "admin":
        return jsonify({"message": "Access denied"}), 403
    data = request.get_json()
    name = data.get("name")
    address = data.get("address")
    if not name:
        return jsonify({"message": "Name required"}), 400
    c = Cinema(name=name, address=address)
    db.session.add(c)
    db.session.commit()
    return jsonify({"message": "Cinema created", "id": c.id}), 201

@cinema_bp.route('/<int:cinema_id>', methods=['PUT'])
@jwt_required()
def update_cinema(cinema_id):
    identity = get_jwt_identity()
    if identity["role"] != "admin":
        return jsonify({"message": "Access denied"}), 403
    c = Cinema.query.get(cinema_id)
    if not c:
        return jsonify({"message": "Cinema not found"}), 404
    data = request.get_json()
    c.name = data.get("name", c.name)
    c.address = data.get("address", c.address)
    db.session.commit()
    return jsonify({"message": "Cinema updated"})

@cinema_bp.route('/<int:cinema_id>', methods=['DELETE'])
@jwt_required()
def delete_cinema(cinema_id):
    identity = get_jwt_identity()
    if identity["role"] != "admin":
        return jsonify({"message": "Access denied"}), 403
    c = Cinema.query.get(cinema_id)
    if not c:
        return jsonify({"message": "Cinema not found"}), 404
    db.session.delete(c)
    db.session.commit()
    return jsonify({"message": "Cinema deleted"})
