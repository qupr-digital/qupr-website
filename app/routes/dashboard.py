from flask import Blueprint, render_template, session
from app.utils.auth import login_required, get_current_user
from app.models.user import User
from app.models.invoice import Invoice
from app.utils.permissions import filter_client_invoices
from flask import current_app

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
