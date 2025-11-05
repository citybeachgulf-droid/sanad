from flask import Blueprint, render_template, request, redirect, url_for
from ..extensions import db
from ..models import Customer

customers_bp = Blueprint('customers', __name__)

@customers_bp.get('/')
def list_customers():
    q = request.args.get('q')
    query = Customer.query
    if q:
        query = query.filter(Customer.full_name.ilike(f"%{q}%"))
    rows = query.order_by(Customer.id.desc()).all()
    return render_template('customers/list.html', rows=rows)

@customers_bp.get('/new')
def new_customer():
    return render_template('customers/form.html')

@customers_bp.post('/new')
def create_customer():
    c = Customer(full_name=request.form['full_name'],
                 phone=request.form.get('phone'),
                 email=request.form.get('email'),
                 national_id=request.form.get('national_id'))
    db.session.add(c)
    db.session.commit()
    return redirect(url_for('customers.list_customers'))
