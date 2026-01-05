# room_routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Room, Cinema, Seat

room_bp = Blueprint('room', __name__)

@room_bp.route('/', methods=['GET'])
def list_rooms():
    cinema_id = request.args.get('cinemaId', type=int)
    if cinema_id:
        rooms = Room.query.filter_by(cinema_id=cinema_id).all()
    else:
        rooms = Room.query.all()
    return jsonify([{
        "id": r.id, "name": r.name, "cinema_id": r.cinema_id, "capacity": r.capacity
    } for r in rooms])

@room_bp.route('/<int:room_id>', methods=['GET'])
def get_room(room_id):
    r = Room.query.get(room_id)
    if not r:
        return jsonify({"message": "Room not found"}), 404
    seats = [{"id": s.id, "seat_code": s.seat_code, "type": s.type, "price": s.price} for s in r.seats]
    return jsonify({"id": r.id, "name": r.name, "cinema_id": r.cinema_id, "capacity": r.capacity, "seats": seats})

@room_bp.route('/', methods=['POST'])
@jwt_required()
def create_room():
    identity = get_jwt_identity()
    if identity["role"] != "admin":
        return jsonify({"message": "Access denied"}), 403

    data = request.get_json()
    cinema_id = data.get("cinema_id")
    name = data.get("name")
    seats = data.get("seats", [])  # list of {"seat_code":"A1","type":"standard","price":100}
    if not cinema_id or not name:
        return jsonify({"message": "cinema_id and name required"}), 400
    if not Cinema.query.get(cinema_id):
        return jsonify({"message": "Cinema not found"}), 404

    room = Room(cinema_id=cinema_id, name=name, capacity=len(seats))
    db.session.add(room)
    db.session.flush()  # để có room.id

    for s in seats:
        seat_code = s.get("seat_code")
        seat_type = s.get("type", "standard")
        price = s.get("price", 0)
        seat = Seat(room_id=room.id, seat_code=seat_code, type=seat_type, price=price)
        db.session.add(seat)

    db.session.commit()
    return jsonify({"message": "Room created", "id": room.id}), 201

@room_bp.route('/<int:room_id>', methods=['PUT'])
@jwt_required()
def update_room(room_id):
    identity = get_jwt_identity()
    if identity["role"] != "admin":
        return jsonify({"message": "Access denied"}), 403
    r = Room.query.get(room_id)
    if not r:
        return jsonify({"message": "Room not found"}), 404
    data = request.get_json()
    r.name = data.get("name", r.name)
    db.session.commit()
    return jsonify({"message": "Room updated"})

@room_bp.route('/<int:room_id>', methods=['DELETE'])
@jwt_required()
def delete_room(room_id):
    identity = get_jwt_identity()
    if identity["role"] != "admin":
        return jsonify({"message": "Access denied"}), 403
    r = Room.query.get(room_id)
    if not r:
        return jsonify({"message": "Room not found"}), 404
    db.session.delete(r)
    db.session.commit()
    return jsonify({"message": "Room deleted"})

