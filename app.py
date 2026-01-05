
from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from models import db
from config import Config
from auth_routes import auth_bp
from movie_routes import movie_bp
from cinema_routes import cinema_bp
from room_routes import room_bp
from showtime_routes import showtime_bp
from booking_routes import booking_bp
# Thêm các imports này
from models import db, User, Movie, Cinema, Room, Schedule, Seat, ScheduleSeat
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta 
# Note: Cần thêm 'db' vào import list nếu chưa có.

app = Flask(__name__)
app.config.from_object(Config)

# Khởi tạo DB và JWT
db.init_app(app)
jwt = JWTManager(app)

# Đăng ký blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(movie_bp, url_prefix='/api/movies')
app.register_blueprint(cinema_bp, url_prefix='/api/cinemas')
app.register_blueprint(room_bp, url_prefix='/api/rooms')
app.register_blueprint(showtime_bp, url_prefix='/api/showtimes')
app.register_blueprint(booking_bp, url_prefix='/api/bookings')

# ... phần khác giữ nguyên


# --- Route test đơn giản ---
@app.route('/')
def home():
    return jsonify({"message": "Cinema API is running!"})

# --- Lệnh CLI tạo DB ---
@app.cli.command('create_db')
def create_db():
    db.create_all()
    print("✅ Database created successfully!")


@app.cli.command("drop_db")
def drop_db():
    """Xóa tất cả các bảng trong database hiện tại."""
    
    with app.app_context():
        db.session.execute(db.text("SET FOREIGN_KEY_CHECKS = 0;"))
        db.session.commit()
    
    db.drop_all()
    print("🗑️ All database tables dropped successfully!")

    with app.app_context():
        db.session.execute(db.text("SET FOREIGN_KEY_CHECKS = 1;"))
        db.session.commit()

# Test

@app.cli.command("seed_db")
def seed_db():
    """Thêm dữ liệu mẫu vào database."""
    print("🌱 Seeding database...")
    
    with app.app_context():
        # --- 1. USERS ---
        admin_user = User(
            username='admin1', 
            password_hash=generate_password_hash('password123'), 
            role='admin'
        )
        test_user = User(
            username='testuser01', 
            password_hash=generate_password_hash('password123'), 
            role='user'
        )
        db.session.add_all([admin_user, test_user])
        db.session.commit()
        
        # --- 2. CINEMA & ROOM ---
        cinema = Cinema(name='CGV Vincom', address='Quận 1, TPHCM')
        db.session.add(cinema)
        db.session.commit()
        
        room = Room(cinema_id=cinema.id, name='Phòng 01', capacity=50)
        db.session.add(room)
        db.session.commit()
        
        # --- 3. SEATS for Room 01 ---
        seat_list = []
        rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J'] # 10 hàng
        cols = range(1, 6) # 5 cột
        for r_index, row in enumerate(rows):
            for col in cols:
                seat_code = f'{row}{col}'
                seat_type = 'standard'
                if r_index >= 8:
                    seat_type = 'vip'
                
                new_seat = Seat(
                    room_id=room.id, 
                    seat_code=seat_code, 
                    type=seat_type, 
                    price=0 
                )
                seat_list.append(new_seat)
        db.session.add_all(seat_list)
        db.session.commit()

        # --- 4. MOVIE ---
        movie = Movie(
            name='Phim Hay Nhất', 
            director='Đạo Diễn A', 
            duration=120, 
            release_date=datetime.now().date(),
            status='showing',
            poster='/img/poster.jpg'
        )
        db.session.add(movie)
        db.session.commit()
        
        # --- 5. SCHEDULE (Suất Chiếu) ---
        showtime_dt = datetime.now() + timedelta(days=1, hours=2) 
        schedule = Schedule(
            movie_id=movie.id,
            room_id=room.id,
            show_time=showtime_dt,
            price_standard=80000,
            price_vip=120000
        )
        db.session.add(schedule)
        db.session.commit()
        
        # --- 6. SCHEDULE SEATS (Tạo trạng thái cho từng ghế) ---
        schedule_seats_list = []
        for seat in seat_list:
            schedule_seat = ScheduleSeat(
                schedule_id=schedule.id,
                seat_id=seat.id,
                status='available'
            )
            schedule_seats_list.append(schedule_seat)
            
        db.session.add_all(schedule_seats_list)
        db.session.commit()

    print("🌱 Database seeded successfully with sample data!")
if __name__ == '__main__':
    app.run(debug=True)
