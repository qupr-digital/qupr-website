from app.models.user import User
from flask import abort
from bson import ObjectId


def can_view_invoice(user, invoice):
    """Check if user can view invoice"""
    if User.is_owner(user):
        return True
    
    if User.is_client(user):
        # Client can only view their own invoices
        return str(invoice['client_id']) == str(user.get('client_id'))
    
    return False


def can_edit_invoice(user, invoice):
    """Check if user can edit invoice"""
    if not User.is_owner(user):
        return False
    
    # Can't edit issued or paid invoices
    if invoice['status'] in ['ISSUED', 'PAID']:
        return False
    
    return True


def can_delete_invoice(user, invoice):
    """Check if user can delete invoice"""
    if not User.is_owner(user):
        return False
    
    # Can only delete draft invoices
    return invoice['status'] == 'DRAFT'


def can_manage_clients(user):
    """Check if user can manage clients"""
    return User.is_owner(user)


def can_manage_products(user):
    """Check if user can manage products"""
    return User.is_owner(user)


def require_invoice_access(user, invoice, edit=False):
    """Require access to invoice or abort"""
    if edit:
        if not can_edit_invoice(user, invoice):
            abort(403)
    else:
        if not can_view_invoice(user, invoice):
            abort(403)


def filter_client_invoices(user, invoices):
    """Filter invoices based on user role"""
    if User.is_owner(user):
        return invoices
    
    if User.is_client(user):
        client_id = user.get('client_id')
        return [inv for inv in invoices if str(inv['client_id']) == str(client_id)]
    
    return []
