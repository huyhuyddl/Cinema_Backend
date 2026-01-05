import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # --- Cấu hình Database MySQL ---
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://root:Huy20055555@localhost/movieDB?charset=utf8mb4"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Cấu hình JWT ---
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "supersecretkey")
