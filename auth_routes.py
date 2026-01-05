from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt

from models import db, User

auth_bp = Blueprint('auth', __name__)

# --- Đăng ký ---
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if User.query.filter_by(username=username).first():
        return jsonify({"message": "Username already exists"}), 400

    hashed_pw = generate_password_hash(password)
    new_user = User(username=username, password_hash=hashed_pw)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully"}), 201


# --- Đăng nhập ---
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"message": "Invalid credentials"}), 401

    additional_claims = {"role": user.role}
    token = create_access_token(
        identity=user.username, 
        additional_claims=additional_claims # Thêm vai trò vào claims
    )
       
    return jsonify({
        "access_token": token,
        "username": user.username,
        "role": user.role 
    }), 200


# --- Đăng xuất (JWT client xoá token) ---
@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    return jsonify({"message": "Logged out successfully"}), 200


# --- Kiểm tra quyền admin ---
@auth_bp.route('/admin-only', methods=['GET'])
@jwt_required()
def admin_only():
    claims = get_jwt()
    if claims.get("role") != "admin": 
        return jsonify({"message": "Access denied"}), 403
    return jsonify({"message": "Welcome, admin!"}), 200

# Lấy danh sách người dùng (Chỉ Admin)
@auth_bp.route('/users', methods=['GET'])
@jwt_required()
def list_users():
    claims = get_jwt() # Lấy toàn bộ claims/dictionary từ Token
    current_username = get_jwt_identity() # Lấy username (là string)
    
    # Kiểm tra quyền Admin bằng claims["role"]
    if claims.get("role") != "admin": 
        return jsonify({"message": "Access denied"}), 403

    # Dùng username string để query DB
    current_user = User.query.filter_by(username=current_username).first()

    users = User.query.all()

    return jsonify([{
        "id": u.id, 
        "username": u.username, 
        "role": u.role,
        "created_at": u.created_at.strftime("%Y-%m-%d %H:%M:%S") if hasattr(u, 'created_at') else None
    } for u in users])

# Quản lý người dùng theo ID (Xóa, Cập nhật Role - Chỉ Admin)
@auth_bp.route('/users/<int:user_id>', methods=['DELETE', 'PUT'])
@jwt_required()
def manage_user(user_id):
    claims = get_jwt() # Lấy claims/dictionary
    current_username = get_jwt_identity() # Lấy username (là string)

    # Bắt buộc phải là Admin
    if claims.get("role") != "admin":
        return jsonify({"message": "Access denied"}), 403

    current_user = User.query.filter_by(username=current_username).first()

    user_to_manage = User.query.get(user_id)
    if not user_to_manage:
        return jsonify({"message": "User not found"}), 404
        
    # Không cho phép Admin tự xóa hoặc thay đổi vai trò của chính mình (tùy chọn)
    if user_to_manage.id == current_user.id:
        return jsonify({"message": "Cannot manage your own account via this endpoint"}), 403

    if request.method == 'DELETE':
        db.session.delete(user_to_manage)
        db.session.commit()
        return jsonify({"message": "User deleted successfully"}), 200

    elif request.method == 'PUT':
        data = request.get_json()
        if 'role' in data:
            user_to_manage.role = data['role']
        db.session.commit()
        return jsonify({"message": "User updated successfully"}), 200