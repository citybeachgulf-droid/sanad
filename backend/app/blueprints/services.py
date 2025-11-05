from flask import Blueprint, render_template, request, redirect, url_for
from ..extensions import db
from ..models import Service

services_bp = Blueprint('services', __name__)

@services_bp.get('/')
def list_services():
    rows = Service.query.order_by(Service.id.desc()).all()
    return render_template('services/list.html', rows=rows)

@services_bp.get('/new')
def new_service():
    return render_template('services/form.html')

@services_bp.post('/new')
def create_service():
    s = Service(
        name=request.form['name'],
        gov_entity=request.form.get('gov_entity'),
        office_fee=request.form.get('office_fee', 0),
        gov_fee_type=request.form.get('gov_fee_type', 'fixed'),
        gov_fee_value=request.form.get('gov_fee_value', 0),
        vat_applicable=True if request.form.get('vat_applicable') else False,
    )
    db.session.add(s)
    db.session.commit()
    return redirect(url_for('services.list_services'))
