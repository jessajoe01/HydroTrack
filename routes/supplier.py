from flask import Blueprint, jsonify
from flask_login import login_required
from models import Supplier

supplier_bp = Blueprint('supplier', __name__)

@supplier_bp.route('/api/suppliers', methods=['GET'])
@login_required
def get_suppliers():
    suppliers = Supplier.query.filter_by(is_available=1).all()
    return jsonify([{
        'id'                : s.id,
        'name'              : s.name,
        'contact'           : s.contact,
        'area'              : s.area,
        'price_per_litre'   : s.price_per_litre,
        'min_order_litres'  : s.min_order_litres,
        'avg_delivery_days' : s.avg_delivery_days
    } for s in suppliers]), 200