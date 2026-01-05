# showtime_routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Movie, Schedule, Room, Seat, ScheduleSeat, LOCK_TIMEOUT_MINUTES
from datetime import datetime, timedelta

showtime_bp = Blueprint('showtime', __name__)

def parse_show_time(val):
    # chấp nhận "YYYY-mm-dd HH:MM:SS" hoặc ISO
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    try:
        return datetime.strptime(val, "%Y-%m-%d %H:%M:%S")
    except Exception:
        try:
            return datetime.fromisoformat(val)
        except Exception:
            return None

@showtime_bp.route('/', methods=['GET'])
def list_showtimes():
    movie_id = request.args.get('movieId', type=int)
    date = request.args.get('date')  # "2025-11-20"
    q = Schedule.query
    if movie_id:
        q = q.filter_by(movie_id=movie_id)
    if date:
        try:
            d = datetime.strptime(date, "%Y-%m-%d").date()
            start = datetime.combine(d, datetime.min.time())
            end = datetime.combine(d, datetime.max.time())
            q = q.filter(Schedule.show_time >= start, Schedule.show_time <= end)
        except:
            pass
    sts = q.all()
    def tojson(s):
        return {
            "id": s.id,
            "movie_id": s.movie_id,
            "movie_name": s.movie.name if s.movie else None,
            "room_id": s.room_id,
            "show_time": s.show_time.strftime("%Y-%m-%d %H:%M:%S"),
            "price_standard": s.price_standard,
            "price_vip": s.price_vip
        }
    return jsonify([tojson(s) for s in sts])

@showtime_bp.route('/<int:sid>', methods=['GET'])
def get_showtime(sid):
    s = Schedule.query.get(sid)
    if not s:
        return jsonify({"message": "Showtime not found"}), 404
    return jsonify({
        "id": s.id,
        "movie_id": s.movie_id,
        "movie_name": s.movie.name if s.movie else None,
        "room_id": s.room_id,
        "show_time": s.show_time.strftime("%Y-%m-%d %H:%M:%S"),
        "price_standard": s.price_standard,
        "price_vip": s.price_vip
    })

# Trong showtime_routes.py, thêm đoạn mã này sau hàm get_showtime(sid)

@showtime_bp.route('/<int:sid>/seats', methods=['GET'])
def list_schedule_seats(sid):
    """
    Trả về danh sách tất cả các ghế và trạng thái của chúng
    trong một suất chiếu (schedule) cụ thể.
    """
    schedule = Schedule.query.get(sid)
    if not schedule:
        return jsonify({"message": "Showtime not found"}), 404

    schedule_seats = ScheduleSeat.query.filter_by(schedule_id=sid).all()
    
    now = datetime.now()
    seats_data = []
    
    for ss in schedule_seats:
        current_status = ss.status
        
        if ss.status == 'locked':
            if ss.lock_time and (now - ss.lock_time) > timedelta(minutes=LOCK_TIMEOUT_MINUTES):
                ss.status = 'available'
                ss.lock_time = None
                db.session.add(ss)
                current_status = 'available'
            
        seats_data.append({
            "seat_id": ss.seat_id,
            "seat_code": ss.seat.seat_code,
            "type": ss.seat.type,
            "status": current_status,
            "price_standard": schedule.price_standard if ss.seat.type == 'standard' else None,
            "price_vip": schedule.price_vip if ss.seat.type == 'vip' else None
        })

    db.session.commit()
    
    return jsonify(seats_data)

@showtime_bp.route('/', methods=['POST'])
@jwt_required()
def create_showtime():
    identity = get_jwt_identity()
    if identity["role"] != "admin":
        return jsonify({"message": "Access denied"}), 403

    data = request.get_json()
    movie_id = data.get("movie_id")
    room_id = data.get("room_id")
    show_time_raw = data.get("show_time")
    price_standard = data.get("price_standard")
    price_vip = data.get("price_vip")

    if not (movie_id and room_id and show_time_raw):
        return jsonify({"message": "movie_id, room_id, show_time required"}), 400

    show_time = parse_show_time(show_time_raw)
    if not show_time:
        return jsonify({"message": "Invalid show_time format. Use 'YYYY-mm-dd HH:MM:SS'"}), 400

    if not Movie.query.get(movie_id):
        return jsonify({"message": "Movie not found"}), 404
    room = Room.query.get(room_id)
    if not room:
        return jsonify({"message": "Room not found"}), 404

    s = Schedule(movie_id=movie_id, room_id=room_id, show_time=show_time,
                 price_standard=price_standard, price_vip=price_vip)
    db.session.add(s)
    db.session.flush()

    # Tạo ScheduleSeat từ tất cả Seat trong Room
    seats = Seat.query.filter_by(room_id=room_id).all()
    for seat in seats:
        ss = ScheduleSeat(schedule_id=s.id, seat_id=seat.id, status='available')
        db.session.add(ss)

    db.session.commit()
    return jsonify({"message": "Showtime created", "id": s.id}), 201

@showtime_bp.route('/<int:sid>', methods=['PUT'])
@jwt_required()
def update_showtime(sid):
    identity = get_jwt_identity()
    if identity["role"] != "admin":
        return jsonify({"message": "Access denied"}), 403
    s = Schedule.query.get(sid)
    if not s:
        return jsonify({"message": "Showtime not found"}), 404
    data = request.get_json()
    if data.get("show_time"):
        st = parse_show_time(data.get("show_time"))
        if not st:
            return jsonify({"message": "Invalid show_time"}), 400
        s.show_time = st
    s.price_standard = data.get("price_standard", s.price_standard)
    s.price_vip = data.get("price_vip", s.price_vip)
    db.session.commit()
    return jsonify({"message": "Showtime updated"})

@showtime_bp.route('/<int:sid>', methods=['DELETE'])
@jwt_required()
def delete_showtime(sid):
    identity = get_jwt_identity()
    if identity["role"] != "admin":
        return jsonify({"message": "Access denied"}), 403
    s = Schedule.query.get(sid)
    if not s:
        return jsonify({"message": "Showtime not found"}), 404
    # Xoá ScheduleSeat trước
    from models import ScheduleSeat
    ScheduleSeat.query.filter_by(schedule_id=s.id).delete()
    db.session.delete(s)
    db.session.commit()
    return jsonify({"message": "Showtime deleted"})
