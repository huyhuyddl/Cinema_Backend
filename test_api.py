import requests

BASE = "http://127.0.0.1:5000/api"

print("---- Đăng ký tài khoản ----")
r = requests.post(f"{BASE}/auth/register", json={"username": "admin1", "password": "admin"})
print(r.json())

r = requests.post(f"{BASE}/auth/register", json={"username": "user1", "password": "123"})
print(r.json())

print("---- Đăng nhập ----")
admin_login = requests.post(f"{BASE}/auth/login", json={"username": "admin1", "password": "admin"})
admin_token = admin_login.json().get("access_token")
print("Admin Token:", admin_token)

user_login = requests.post(f"{BASE}/auth/login", json={"username": "user1", "password": "123"})
user_token = user_login.json().get("access_token")
print("User Token:", user_token)

print("---- Thêm phim ----")
headers = {"Authorization": f"Bearer {admin_token}"}
r = requests.post(f"{BASE}/movies/add", json={
    "name": "Avengers: Endgame",
    "director": "Anthony Russo",
    "duration": 180,
    "release_date": "2019-04-26",
    "status": "showing"
}, headers=headers)
print(r.json())

print("---- Lấy danh sách phim ----")
r = requests.get(f"{BASE}/movies/")
print(r.json())

print("---- Thêm lịch chiếu ----")
r = requests.post(f"{BASE}/movies/schedule/add", json={
    "movie_id": 1,
    "show_time": "2025-11-15 19:30:00",
    "theater": "CGV Aeon Mall"
}, headers=headers)
print(r.json())

print("---- Xem lịch chiếu ----")
r = requests.get(f"{BASE}/movies/schedule")
print(r.json())
