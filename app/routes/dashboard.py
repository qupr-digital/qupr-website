from flask import Blueprint, render_template, session, request, redirect, url_for, flash
from app.utils.auth import login_required, get_current_user, owner_required
from app.models.user import User
from app.models.invoice import Invoice
from app.models.coupon import Coupon
from app.utils.permissions import filter_client_invoices
from flask import current_app
from datetime import datetime

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard')
@login_required
def index():
    """Role-based dashboard"""
    user = get_current_user()
    
    if User.is_owner(user):
        return render_owner_dashboard(user)
    elif User.is_client(user):
        return render_client_dashboard(user)
    else:
        return 'Invalid role', 403


def render_owner_dashboard(user):
    """Render owner dashboard"""
    db = current_app.db
    total_clients = db.clients.count_documents({'is_active': True})
    total_products = db.products.count_documents({'is_active': True})
    total_invoices = db.invoices.count_documents({})
    draft_invoices = db.invoices.count_documents({'status': Invoice.STATUS_DRAFT})
    issued_invoices = db.invoices.count_documents({'status': Invoice.STATUS_ISSUED})
    paid_invoices = db.invoices.count_documents({'status': Invoice.STATUS_PAID})

    recent_invoices = Invoice.get_all()[:10]

    pipeline = [
        {'$match': {'status': Invoice.STATUS_PAID}},
        {'$group': {'_id': None, 'total': {'$sum': '$total'}}}
    ]
    revenue_result = list(db.invoices.aggregate(pipeline))
    total_revenue = revenue_result[0]['total'] if revenue_result else 0
    
    # Calculate pending amount (issued invoices)
    pending_pipeline = [
        {'$match': {'status': Invoice.STATUS_ISSUED}},
        {'$group': {'_id': None, 'total': {'$sum': '$total'}}}
    ]
    pending_result = list(db.invoices.aggregate(pending_pipeline))
    pending_amount = pending_result[0]['total'] if pending_result else 0
    
    return render_template('dashboard/owner.html',
                         total_clients=total_clients,
                         total_products=total_products,
                         total_invoices=total_invoices,
                         draft_invoices=draft_invoices,
                         issued_invoices=issued_invoices,
                         paid_invoices=paid_invoices,
                         total_revenue=total_revenue,
                         pending_amount=pending_amount,
                         recent_invoices=recent_invoices)


def render_client_dashboard(user):
    """Render client dashboard"""
    client_id = user.get('client_id')
    
    # Get client's invoices
    invoices = Invoice.get_all(client_id=str(client_id))
    
    # Calculate statistics
    total_invoices = len(invoices)
    issued_invoices = len([inv for inv in invoices if inv['status'] == Invoice.STATUS_ISSUED])
    paid_invoices = len([inv for inv in invoices if inv['status'] == Invoice.STATUS_PAID])
    
    total_amount = sum(inv['total'] for inv in invoices if inv['status'] in [Invoice.STATUS_ISSUED, Invoice.STATUS_PAID])
    pending_amount = sum(inv['total'] for inv in invoices if inv['status'] == Invoice.STATUS_ISSUED)
    
    return render_template('dashboard/client.html',
                         total_invoices=total_invoices,
                         issued_invoices=issued_invoices,
                         paid_invoices=paid_invoices,
                         total_amount=total_amount,
                         pending_amount=pending_amount,
                         invoices=invoices)


# Coupon Management Routes
@dashboard_bp.route('/coupons')
@owner_required
def list_coupons():
    """List all coupons"""
    coupons = Coupon.get_all()
    return render_template('dashboard/coupons/list.html', coupons=coupons)


@dashboard_bp.route('/coupons/create', methods=['GET', 'POST'])
@owner_required
def create_coupon():
    """Create new coupon"""
    if request.method == 'POST':
        try:
            code = request.form.get('code', '').strip()
            description = request.form.get('description', '').strip()
            discount_value = request.form.get('discount_value', '0')
            discount_type = request.form.get('discount_type', Coupon.TYPE_PERCENTAGE)
            max_uses = request.form.get('max_uses', '')
            is_active = request.form.get('is_active') == 'on'
            valid_from = request.form.get('valid_from')
            valid_until = request.form.get('valid_until')
            min_amount = request.form.get('min_amount', '')
            
            if not code or not description:
                flash('Code and description are required', 'error')
                return redirect(url_for('dashboard.create_coupon'))
            
            # Check if code already exists
            existing = Coupon.get_by_code(code)
            if existing:
                flash('Coupon code already exists', 'error')
                return redirect(url_for('dashboard.create_coupon'))
            
            # Parse dates if provided
            valid_from_dt = None
            valid_until_dt = None
            
            if valid_from:
                valid_from_dt = datetime.fromisoformat(valid_from)
            if valid_until:
                valid_until_dt = datetime.fromisoformat(valid_until)
            
            max_uses_int = int(max_uses) if max_uses else None
            min_amount_float = float(min_amount) if min_amount else None
            
            Coupon.create(
                code=code,
                description=description,
                discount_value=discount_value,
                discount_type=discount_type,
                max_uses=max_uses_int,
                is_active=is_active,
                valid_from=valid_from_dt,
                valid_until=valid_until_dt,
                min_amount=min_amount_float
            )
            
            flash('Coupon created successfully', 'success')
            return redirect(url_for('dashboard.list_coupons'))
        
        except Exception as e:
            flash(f'Error creating coupon: {str(e)}', 'error')
            return redirect(url_for('dashboard.create_coupon'))
    
    return render_template('dashboard/coupons/create.html')


@dashboard_bp.route('/coupons/<coupon_id>/edit', methods=['GET', 'POST'])
@owner_required
def edit_coupon(coupon_id):
    """Edit coupon"""
    coupon = Coupon.get_by_id(coupon_id)
    
    if not coupon:
        flash('Coupon not found', 'error')
        return redirect(url_for('dashboard.list_coupons'))
    
    if request.method == 'POST':
        try:
            description = request.form.get('description', '').strip()
            discount_value = request.form.get('discount_value', '0')
            discount_type = request.form.get('discount_type', Coupon.TYPE_PERCENTAGE)
            max_uses = request.form.get('max_uses', '')
            is_active = request.form.get('is_active') == 'on'
            valid_from = request.form.get('valid_from')
            valid_until = request.form.get('valid_until')
            min_amount = request.form.get('min_amount', '')
            
            # Parse dates if provided
            valid_from_dt = None
            valid_until_dt = None
            
            if valid_from:
                valid_from_dt = datetime.fromisoformat(valid_from)
            if valid_until:
                valid_until_dt = datetime.fromisoformat(valid_until)
            
            max_uses_int = int(max_uses) if max_uses else None
            min_amount_float = float(min_amount) if min_amount else None
            
            Coupon.update(coupon_id,
                description=description,
                discount_value=float(discount_value),
                discount_type=discount_type,
                max_uses=max_uses_int,
                is_active=is_active,
                valid_from=valid_from_dt,
                valid_until=valid_until_dt,
                min_amount=min_amount_float
            )
            
            flash('Coupon updated successfully', 'success')
            return redirect(url_for('dashboard.list_coupons'))
        
        except Exception as e:
            flash(f'Error updating coupon: {str(e)}', 'error')
    
    return render_template('dashboard/coupons/edit.html', coupon=coupon)


@dashboard_bp.route('/coupons/<coupon_id>/delete', methods=['POST'])
@owner_required
def delete_coupon(coupon_id):
    """Delete coupon"""
    try:
        Coupon.delete(coupon_id)
        flash('Coupon deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting coupon: {str(e)}', 'error')
    
    return redirect(url_for('dashboard.list_coupons'))
