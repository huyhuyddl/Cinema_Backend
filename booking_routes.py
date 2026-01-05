# booking_routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Booking, Schedule, ScheduleSeat, Seat, LOCK_TIMEOUT_MINUTES
from datetime import datetime, timedelta

booking_bp = Blueprint('booking', __name__)

LOCK_MINUTES = LOCK_TIMEOUT_MINUTES

def free_expired_locks(schedule_id=None):
    """
    Giải phóng các khóa đã hết hạn (status == 'locked' và locked_until < now).
    Nếu schedule_id được truyền, chỉ dọn cho schedule đó.
    """
    now = datetime.utcnow()
    q = ScheduleSeat.query.filter(ScheduleSeat.status == 'locked')
    if schedule_id:
        q = q.filter(ScheduleSeat.schedule_id == schedule_id)
    expired = q.filter(ScheduleSeat.locked_until != None, ScheduleSeat.locked_until < now).all()
    for ss in expired:
        ss.status = 'available'
        ss.locked_until = None
        ss.locked_by_booking_id = None
    if expired:
        db.session.commit()

@booking_bp.route('/showtimes/<int:sid>/seats', methods=['GET'])
def get_seats_for_showtime(sid):
    schedule = Schedule.query.get(sid)
    if not schedule:
        return jsonify({"message": "Showtime not found"}), 404
    # dọn khóa hết hạn
    free_expired_locks(schedule_id=sid)
    seats = []
    ss_list = ScheduleSeat.query.filter_by(schedule_id=sid).all()
    for ss in ss_list:
        s = ss.seat
        seats.append({
            "schedule_seat_id": ss.id,
            "seat_id": s.id,
            "seat_code": s.seat_code,
            "type": s.type,
            "price": s.price if s.type != 'vip' else (schedule.price_vip or s.price),
            "status": ss.status  # available / locked / booked
        })
    return jsonify({"showtime_id": sid, "seats": seats})

@booking_bp.route('/', methods=['POST'])
@jwt_required()
def create_booking():
    """
    Payload:
    {
      "schedule_id": 1,
      "seat_codes": ["A1","A2"]
    }
    """
    identity = get_jwt_identity()
    user = identity

    data = request.get_json()
    schedule_id = data.get("schedule_id")
    seat_codes = data.get("seat_codes", [])

    if not schedule_id or not seat_codes:
        return jsonify({"message": "schedule_id and seat_codes required"}), 400

    schedule = Schedule.query.get(schedule_id)
    if not schedule:
        return jsonify({"message": "Showtime not found"}), 404

    # dọn khóa hết hạn trước khi kiểm tra
    free_expired_locks(schedule_id=schedule_id)

    # tìm tất cả seat objects theo seat_code + room
    seats = Seat.query.filter(Seat.room_id == schedule.room_id, Seat.seat_code.in_(seat_codes)).all()
    if len(seats) != len(seat_codes):
        return jsonify({"message": "One or more seats not found"}), 404

    # kiểm tra ScheduleSeat cho mỗi seat
    ss_list = []
    for seat in seats:
        ss = ScheduleSeat.query.filter_by(schedule_id=schedule_id, seat_id=seat.id).with_for_update().first()
        if not ss:
            return jsonify({"message": f"Seat {seat.seat_code} is not available for this showtime"}), 400
        if ss.status == 'booked':
            return jsonify({"message": f"Seat {seat.seat_code} already booked"}), 409
        if ss.status == 'locked' and ss.locked_until and ss.locked_until > datetime.utcnow():
            return jsonify({"message": f"Seat {seat.seat_code} currently locked"}), 409
        ss_list.append((ss, seat))

    # Tính tổng giá (lấy từ seat.price hoặc override từ schedule)
    total = 0
    for ss, seat in ss_list:
        if seat.type == 'vip':
            price = schedule.price_vip or seat.price
        else:
            price = schedule.price_standard or seat.price
        total += price

    # Tạo booking và khóa ghế cho booking (pending)
    booking = Booking(user_id=None, schedule_id=schedule_id, seats=",".join(seat_codes),
                      total_price=total, status='pending')
    # tìm user id:
    from models import User
    user_obj = User.query.filter_by(username=user).first()
    if not user_obj:
        return jsonify({"message": "User not found"}), 404
    booking.user_id = user_obj.id

    db.session.add(booking)
    db.session.flush()  # để có booking.id

    # khóa từng ss
    now = datetime.utcnow()
    lock_until = now + timedelta(minutes=LOCK_MINUTES)
    for ss, seat in ss_list:
        ss.status = 'locked'
        ss.locked_until = lock_until
        ss.locked_by_booking_id = booking.id
        db.session.add(ss)

    db.session.commit()
    return jsonify({"message": "Booking created (pending). Please confirm payment within {} minutes".format(LOCK_MINUTES),
                    "booking_id": booking.id, "total_price": total}), 201

@booking_bp.route('/<int:booking_id>/confirm', methods=['POST'])
@jwt_required()
def confirm_booking(booking_id):
    """
    Xác nhận thanh toán (giả lập) -> chuyển trạng thái seat -> booked
    """
    identity = get_jwt_identity()
    user = identity["username"]
    # tìm booking
    b = Booking.query.get(booking_id)
    if not b:
        return jsonify({"message": "Booking not found"}), 404
    # kiểm tra chủ sở hữu
    from models import User
    user_obj = User.query.filter_by(username=user).first()
    if b.user_id != user_obj.id:
        return jsonify({"message": "Not your booking"}), 403
    if b.status != 'pending':
        return jsonify({"message": f"Cannot confirm booking with status {b.status}"}), 400

    # dọn khóa hết hạn trước
    free_expired_locks(schedule_id=b.schedule_id)

    # lấy schedule seats thuộc booking
    seat_codes = b.seats.split(",")
    seats = Seat.query.filter(Seat.room_id == b.schedule.room_id, Seat.seat_code.in_(seat_codes)).all()
    ss_list = []
    for seat in seats:
        ss = ScheduleSeat.query.filter_by(schedule_id=b.schedule_id, seat_id=seat.id).first()
        if not ss:
            return jsonify({"message": f"Seat {seat.seat_code} not available"}), 400
        if ss.status == 'booked':
            return jsonify({"message": f"Seat {seat.seat_code} already booked"}), 409
        if ss.status == 'locked' and ss.locked_by_booking_id != b.id:
            return jsonify({"message": f"Seat {seat.seat_code} locked by another booking"}), 409
        ss_list.append(ss)

    # mark all as booked
    for ss in ss_list:
        ss.status = 'booked'
        ss.locked_until = None
        ss.locked_by_booking_id = None
        db.session.add(ss)

    b.status = 'paid'
    db.session.commit()
    return jsonify({"message": "Booking confirmed/paid", "booking_id": b.id})

@booking_bp.route('/<int:booking_id>/cancel', methods=['POST'])
@jwt_required()
def cancel_booking(booking_id):
    identity = get_jwt_identity()
    user = identity["username"]
    b = Booking.query.get(booking_id)
    if not b:
        return jsonify({"message": "Booking not found"}), 404
    from models import User
    user_obj = User.query.filter_by(username=user).first()
    if b.user_id != user_obj.id and identity.get("role") != "admin":
        return jsonify({"message": "Not allowed"}), 403

    # nếu đã paid -> cần logic refund (bỏ qua)
    # giải phóng schedule seats
    seat_codes = b.seats.split(",")
    seats = Seat.query.filter(Seat.room_id == b.schedule.room_id, Seat.seat_code.in_(seat_codes)).all()
    for seat in seats:
        ss = ScheduleSeat.query.filter_by(schedule_id=b.schedule_id, seat_id=seat.id).first()
        if ss:
            ss.status = 'available'
            ss.locked_until = None
            ss.locked_by_booking_id = None
            db.session.add(ss)
    b.status = 'canceled'
    db.session.commit()
    return jsonify({"message": "Booking canceled"})

@booking_bp.route('/history', methods=['GET'])
@jwt_required()
def booking_history():
    identity = get_jwt_identity()
    username = identity["username"]
    from models import User
    user_obj = User.query.filter_by(username=username).first()
    if not user_obj:
        return jsonify({"message": "User not found"}), 404
    bookings = Booking.query.filter_by(user_id=user_obj.id).order_by(Booking.created_at.desc()).all()
    res = []
    for b in bookings:
        res.append({
            "id": b.id,
            "schedule_id": b.schedule_id,
            "seats": b.seats.split(","),
            "total_price": b.total_price,
            "status": b.status,
            "created_at": b.created_at.strftime("%Y-%m-%d %H:%M:%S")
        })
    return jsonify(res)

