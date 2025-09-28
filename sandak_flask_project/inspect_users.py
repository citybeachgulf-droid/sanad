# inspect_users.py
from app import create_app, db
from app.models import User

app = create_app()
with app.app_context():
    # طباعة مسار DB ووجود الملف
    print("DB URI:", app.config.get("SQLALCHEMY_DATABASE_URI"))
    users = User.query.all()
    if not users:
        print("No users found in the users table.")
    else:
        print(f"Found {len(users)} user(s):")
        for u in users:
            print(f"- id={u.id} username='{u.username}' email='{u.email}' role='{u.role}' password_hash={'SET' if u.password_hash else 'EMPTY'}")
