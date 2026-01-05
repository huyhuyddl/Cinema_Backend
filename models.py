# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'USER'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='user')  # admin / user
    bookings = db.relationship('Booking', backref='user', lazy=True)
    __table_args__ = {'mysql_engine': 'InnoDB'}

class Movie(db.Model):
    __tablename__ = 'MOVIE'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    director = db.Column(db.String(255))
    casts = db.Column(db.String(255))
    duration = db.Column(db.Integer)
    release_date = db.Column(db.Date)
    description = db.Column(db.Text)
    status = db.Column(db.String(50), default='coming')  # coming, showing, ended
    poster = db.Column(db.String(512))
    trailer = db.Column(db.String(512))
    schedules = db.relationship('Schedule', backref='movie', lazy=True)
    __table_args__ = {'mysql_engine': 'InnoDB'}

class Cinema(db.Model):
    __tablename__ = 'CINEMA'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    address = db.Column(db.String(512))
    rooms = db.relationship('Room', backref='cinema', lazy=True)
    __table_args__ = {'mysql_engine': 'InnoDB'}

class Room(db.Model):
    __tablename__ = 'ROOM'
    id = db.Column(db.Integer, primary_key=True)
    cinema_id = db.Column(db.Integer, db.ForeignKey('CINEMA.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    capacity = db.Column(db.Integer, default=0)
    seats = db.relationship('Seat', backref='room', lazy=True)
    schedules = db.relationship('Schedule', backref='room', lazy=True)
    __table_args__ = {'mysql_engine': 'InnoDB'}

class Seat(db.Model):
    __tablename__ = 'SEAT'
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('ROOM.id'), nullable=False)
    seat_code = db.Column(db.String(20), nullable=False)  # A1, A2...
    type = db.Column(db.String(50), default='standard')  # standard/vip/couple
    price = db.Column(db.Integer, default=0)

    __table_args__ = (db.UniqueConstraint('room_id', 'seat_code', name='_room_seat_uc'),)
    __table_args__ = {'mysql_engine': 'InnoDB'}

class Schedule(db.Model):  # suất chiếu
    __tablename__ = 'SCHEDULE'
    id = db.Column(db.Integer, primary_key=True)
    movie_id = db.Column(db.Integer, db.ForeignKey('MOVIE.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('ROOM.id'), nullable=False)
    show_time = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # price settings per schedule (optional override)
    price_standard = db.Column(db.Integer)
    price_vip = db.Column(db.Integer)

    schedule_seats = db.relationship('ScheduleSeat', backref='schedule', lazy=True)
    bookings = db.relationship('Booking', backref='schedule', lazy=True)
    __table_args__ = {'mysql_engine': 'InnoDB'}

class ScheduleSeat(db.Model):
    """
    Model để quản lý trạng thái ghế theo từng suất chiếu.
    status: 'available', 'locked', 'booked'
    locked_until: thời điểm khoá (timestamp). Nếu giờ hiện tại > locked_until -> tự coi là available.
    locked_by_booking_id: tham chiếu khi ghế đang được giữ tạm cho booking chưa thanh toán.
    """
    __tablename__ = 'SCHEDULE_SEAT'
    id = db.Column(db.Integer, primary_key=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey('SCHEDULE.id'), nullable=False)
    seat_id = db.Column(db.Integer, db.ForeignKey('SEAT.id'), nullable=False)
    status = db.Column(db.String(20), default='available')  # available / locked / booked
    lock_time = db.Column(db.DateTime, nullable=True)  # Thêm dòng này
    locked_until = db.Column(db.DateTime, nullable=True)
    locked_by_booking_id = db.Column(db.Integer, nullable=True)
    seat = db.relationship('Seat')

    __table_args__ = (db.UniqueConstraint('schedule_id', 'seat_id', name='_schedule_seat_uc'),)
    __table_args__ = {'mysql_engine': 'InnoDB'}

class Booking(db.Model):
    __tablename__ = 'BOOKING'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('USER.id'), nullable=False)
    schedule_id = db.Column(db.Integer, db.ForeignKey('SCHEDULE.id'), nullable=False)
    seats = db.Column(db.String(1000), nullable=False)  # lưu "A1,A2"
    total_price = db.Column(db.Integer, default=0)
    status = db.Column(db.String(50), default='pending')  # pending / paid / canceled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = {'mysql_engine': 'InnoDB'}

class Payment(db.Model):
    __tablename__ = 'PAYMENT'
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer)
    provider = db.Column(db.String(50))
    amount = db.Column(db.Integer)
    status = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = {'mysql_engine': 'InnoDB'}

# Helper: thời gian khóa ghế mặc định (phút)
LOCK_TIMEOUT_MINUTES = 5
def lock_expired(dt: datetime):
    if dt is None:
        return True
    return datetime.utcnow() > dt
