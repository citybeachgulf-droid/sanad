from app import create_app, db
from app.models import User
import sqlite3
from pathlib import Path
import sys

# ===============================
# إعدادات المستخدم الافتراضية
# ===============================
DEFAULT_USERNAME = "admin"
DEFAULT_EMAIL = "admin@example.com"
DEFAULT_PASSWORD = "123"
DEFAULT_ROLE = "admin"

# ===============================
# مسار قاعدة البيانات
# ===============================
DB_FILE = Path("sandak.db")

# ===============================
# دالة إعادة إنشاء قاعدة البيانات
# ===============================
def reset_database(username, email, password, role):
    # محاولة حذف قاعدة البيانات القديمة
    if DB_FILE.exists():
        try:
            DB_FILE.unlink()
            print(f"Deleted old database: {DB_FILE}")
        except PermissionError:
            print(f"Cannot delete {DB_FILE}. Make sure no process is using it.")
            print("Exiting script.")
            sys.exit(1)

    # إنشاء قاعدة بيانات جديدة
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # مثال: إنشاء جدول مستخدمين
    cursor.execute("""
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        email TEXT NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    )
    """)

    # إدخال المستخدم الافتراضي
    cursor.execute("""
    INSERT INTO users (username, email, password, role)
    VALUES (?, ?, ?, ?)
    """, (username, email, password, role))

    conn.commit()
    conn.close()

    print(f"Database reset successfully. Default user: {username} ({role})")


# ===============================
# تشغيل السكريبت
# ===============================
if __name__ == "__main__":
    # يمكنك تعديل القيم هنا أو تمريرها من args
    reset_database(DEFAULT_USERNAME, DEFAULT_EMAIL, DEFAULT_PASSWORD, DEFAULT_ROLE)
