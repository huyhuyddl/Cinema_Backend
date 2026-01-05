from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Movie, Schedule

movie_bp = Blueprint('movie', __name__)

# Thêm phim (admin)
@movie_bp.route('/add', methods=['POST'])
@jwt_required()
def add_movie():
    identity = get_jwt_identity()
    if identity["role"] != "admin":
        return jsonify({"message": "Access denied"}), 403

    data = request.get_json()
    new_movie = Movie(
        name=data.get("name"),
        director=data.get("director"),
        casts=data.get("casts"),
        duration=data.get("duration"),
        release_date=data.get("release_date"),
        description=data.get("description"),
        status=data.get("status", "coming")
    )
    db.session.add(new_movie)
    db.session.commit()
    return jsonify({"message": "Movie added successfully!"}), 201


# Lấy danh sách phim
@movie_bp.route('/', methods=['GET'])
def get_movies():
    movies = Movie.query.all()
    return jsonify([{
        "id": m.id,
        "name": m.name,
        "status": m.status,
        "release_date": m.release_date.strftime("%Y-%m-%d") if m.release_date else None,
        "duration": m.duration,
        "director": m.director
    } for m in movies])

@movie_bp.route('/<int:movie_id>', methods=['GET'])
def get_movie_detail(movie_id):
    movie = Movie.query.get(movie_id)
    if not movie:
        return jsonify({"message": "Movie not found"}), 404

    # Định dạng dữ liệu trả về
    return jsonify({
        "id": movie.id,
        "name": movie.name,
        "director": movie.director,
        "casts": movie.casts,
        "duration": movie.duration,
        "release_date": movie.release_date.strftime("%Y-%m-%d") if movie.release_date else None,
        "description": movie.description,
        "status": movie.status,
        "poster": movie.poster if hasattr(movie, 'poster') else None 
        # Tùy thuộc vào Model Movie của bạn có cột 'poster' hay không
    })

# Cập nhật phim
@movie_bp.route('/<int:movie_id>', methods=['PUT'])
@jwt_required()
def update_movie(movie_id):
    identity = get_jwt_identity()
    if identity["role"] != "admin":
        return jsonify({"message": "Access denied"}), 403

    data = request.get_json()
    movie = Movie.query.get(movie_id)
    if not movie:
        return jsonify({"message": "Movie not found"}), 404

    for field in ["name", "director", "casts", "duration", "release_date", "description", "status"]:
        if field in data:
            setattr(movie, field, data[field])

    db.session.commit()
    return jsonify({"message": "Movie updated successfully"})


# Xóa phim
@movie_bp.route('/<int:movie_id>', methods=['DELETE'])
@jwt_required()
def delete_movie(movie_id):
    identity = get_jwt_identity()
    if identity["role"] != "admin":
        return jsonify({"message": "Access denied"}), 403

    movie = Movie.query.get(movie_id)
    if not movie:
        return jsonify({"message": "Movie not found"}), 404

    db.session.delete(movie)
    db.session.commit()
    return jsonify({"message": "Movie deleted successfully"})


# Thêm lịch chiếu
@movie_bp.route('/schedule/add', methods=['POST'])
@jwt_required()
def add_schedule():
    identity = get_jwt_identity()
    if identity["role"] != "admin":
        return jsonify({"message": "Access denied"}), 403

    data = request.get_json()
    new_schedule = Schedule(
        movie_id=data.get("movie_id"),
        show_time=data.get("show_time"),
        theater=data.get("theater")
    )
    db.session.add(new_schedule)
    db.session.commit()
    return jsonify({"message": "Schedule added successfully"}), 201


# Xem lịch chiếu
@movie_bp.route('/schedule', methods=['GET'])
def get_schedule():
    schedules = Schedule.query.all()
    result = []
    for s in schedules:
        result.append({
            "id": s.id,
            "movie_name": s.movie.name if s.movie else None,
            "show_time": s.show_time.strftime("%Y-%m-%d %H:%M:%S"),
            "theater": s.theater
        })
    return jsonify(result)

# Lấy tất cả lịch chiếu của một bộ phim (ví dụ: /api/movies/1/schedules)
@movie_bp.route('/<int:movie_id>/schedules', methods=['GET'])
def get_schedules_by_movie(movie_id):
    # Tìm tất cả Schedule liên quan đến movie_id này
    schedules = Schedule.query.filter_by(movie_id=movie_id).all()
    
    if not schedules:
        return jsonify({"message": "No schedules found for this movie"}), 404
        
    result = []
    for s in schedules:
        # Giả sử Model Schedule có các cột room_id, price_standard, price_vip
        result.append({
            "schedule_id": s.id,
            "show_time": s.show_time.strftime("%Y-%m-%d %H:%M:%S"),
            "room_id": s.room_id if hasattr(s, 'room_id') else None,
            "price_standard": s.price_standard if hasattr(s, 'price_standard') else None,
            "theater": s.theater if hasattr(s, 'theater') else None # Giữ lại 'theater' nếu cần
        })
        
    return jsonify(result), 200