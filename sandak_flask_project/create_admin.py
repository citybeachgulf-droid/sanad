from app import create_app, db
from app.models import User

app = create_app()
with app.app_context():
    # إنشاء admin جديد إذا لم يكن موجودًا
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', email='admin@example.com', role='admin')
        admin.set_password('123')  # كلمة السر الجديدة
        db.session.add(admin)
        db.session.commit()
        print("Admin user created successfully!")
        print("Username: admin")
        print("Password: admin123")
    else:
        print("Admin user already exists.")
