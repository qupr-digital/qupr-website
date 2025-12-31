from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify
from app.utils.auth import login_required, owner_required, get_current_user
from app.models.invoice import Invoice
from app.models.client import Client
from app.models.product import Product
from app.services.invoice_service import InvoiceService
from app.utils.permissions import can_view_invoice, can_edit_invoice, can_delete_invoice
from datetime import datetime

invoices_bp = Blueprint('invoices', __name__)


@invoices_bp.route('/')
@login_required
def list_invoices():
    """List all invoices"""
    user = get_current_user()
    
    # Get filters
    status = request.args.get('status')
    client_id = request.args.get('client_id')
    
    # Build query based on role
    from app.models.user import User
    if User.is_client(user):
        client_id = str(user['client_id'])
    
    invoices = Invoice.get_all(status=status, client_id=client_id)
    
    # Get clients for filter
    clients = Client.get_all() if User.is_owner(user) else []
    
    return render_template('invoices/list.html', 
                         invoices=invoices, 
                         clients=clients,
                         current_status=status,
                         current_client=client_id)


@invoices_bp.route('/<invoice_id>')
@login_required
def view_invoice(invoice_id):
    """View single invoice"""
    user = get_current_user()
    invoice = Invoice.get_by_id(invoice_id)
    
    if not invoice:
        abort(404)
    
    if not can_view_invoice(user, invoice):
        abort(403)
    
    # Get client details
    client = Client.get_by_id(str(invoice['client_id']))
    
    return render_template('invoices/view.html', 
                         invoice=invoice, 
                         client=client)


@invoices_bp.route('/create', methods=['GET', 'POST'])
@owner_required
def create_invoice():
    """Create new invoice"""
    if request.method == 'POST':
        try:
            client_id = request.form.get('client_id')
            
            # Get items from form
            items_data = []
            item_count = int(request.form.get('item_count', 0))
            
            for i in range(item_count):
                product_id = request.form.get(f'item_{i}_product_id')
                quantity = request.form.get(f'item_{i}_quantity')
                
                if product_id and quantity:
                    items_data.append({
                        'product_id': product_id,
                        'quantity': float(quantity)
                    })
            
            if not client_id:
                flash('Client is required', 'error')
                return redirect(url_for('invoices.create_invoice'))
            
            if not items_data:
                flash('At least one item is required', 'error')
                return redirect(url_for('invoices.create_invoice'))
            
            # Create draft invoice
            invoice_id = InvoiceService.create_draft_invoice(client_id, items_data)
            
            flash('Invoice created successfully', 'success')
            return redirect(url_for('invoices.view_invoice', invoice_id=invoice_id))
            
        except Exception as e:
            flash(f'Error creating invoice: {str(e)}', 'error')
            return redirect(url_for('invoices.create_invoice'))
    
    # GET request
    clients = Client.get_all()
    products = Product.get_all()
    
    return render_template('invoices/create.html', 
                         clients=clients, 
                         products=products)


@invoices_bp.route('/<invoice_id>/edit', methods=['GET', 'POST'])
@owner_required
def edit_invoice(invoice_id):
    """Edit draft invoice"""
    invoice = Invoice.get_by_id(invoice_id)
    user = get_current_user()
    
    if not invoice:
        abort(404)
    
    if not can_edit_invoice(user, invoice):
        flash('Cannot edit this invoice', 'error')
        return redirect(url_for('invoices.view_invoice', invoice_id=invoice_id))
    
    if request.method == 'POST':
        try:
            # Get items from form
            items_data = []
            item_count = int(request.form.get('item_count', 0))
            
            for i in range(item_count):
                product_id = request.form.get(f'item_{i}_product_id')
                quantity = request.form.get(f'item_{i}_quantity')
                
                if product_id and quantity:
                    items_data.append({
                        'product_id': product_id,
                        'quantity': float(quantity)
                    })
            
            if not items_data:
                flash('At least one item is required', 'error')
                return redirect(url_for('invoices.edit_invoice', invoice_id=invoice_id))
            
            # Update invoice
            InvoiceService.update_draft_invoice(invoice_id, items_data)
            
            flash('Invoice updated successfully', 'success')
            return redirect(url_for('invoices.view_invoice', invoice_id=invoice_id))
            
        except Exception as e:
            flash(f'Error updating invoice: {str(e)}', 'error')
    
    # GET request
    client = Client.get_by_id(str(invoice['client_id']))
    products = Product.get_all()
    
    return render_template('invoices/edit.html', 
                         invoice=invoice, 
                         client=client, 
                         products=products)


@invoices_bp.route('/<invoice_id>/issue', methods=['POST'])
@owner_required
def issue_invoice(invoice_id):
    """Issue a draft invoice"""
    try:
        issue_date_str = request.form.get('issue_date')
        due_date_str = request.form.get('due_date')
        
        issue_date = datetime.fromisoformat(issue_date_str) if issue_date_str else None
        due_date = datetime.fromisoformat(due_date_str) if due_date_str else None
        
        InvoiceService.issue_invoice(invoice_id, issue_date, due_date)
        
        flash('Invoice issued successfully', 'success')
    except Exception as e:
        flash(f'Error issuing invoice: {str(e)}', 'error')
    
    return redirect(url_for('invoices.view_invoice', invoice_id=invoice_id))


@invoices_bp.route('/<invoice_id>/mark-paid', methods=['POST'])
@owner_required
def mark_paid(invoice_id):
    """Mark invoice as paid"""
    try:
        paid_on_str = request.form.get('paid_on')
        paid_on = datetime.fromisoformat(paid_on_str) if paid_on_str else None
        
        InvoiceService.mark_as_paid(invoice_id, paid_on)
        
        flash('Invoice marked as paid', 'success')
    except Exception as e:
        flash(f'Error marking invoice as paid: {str(e)}', 'error')
    
    return redirect(url_for('invoices.view_invoice', invoice_id=invoice_id))


@invoices_bp.route('/<invoice_id>/delete', methods=['POST'])
@owner_required
def delete_invoice(invoice_id):
    """Delete draft invoice"""
    user = get_current_user()
    invoice = Invoice.get_by_id(invoice_id)
    
    if not invoice:
        abort(404)
    
    if not can_delete_invoice(user, invoice):
        flash('Cannot delete this invoice', 'error')
        return redirect(url_for('invoices.view_invoice', invoice_id=invoice_id))
    
    try:
        InvoiceService.delete_draft_invoice(invoice_id)
        flash('Invoice deleted successfully', 'success')
        return redirect(url_for('invoices.list_invoices'))
    except Exception as e:
        flash(f'Error deleting invoice: {str(e)}', 'error')
        return redirect(url_for('invoices.view_invoice', invoice_id=invoice_id))


@invoices_bp.route('/<invoice_id>/print')
@login_required
def print_invoice(invoice_id):
    """Print invoice (HTML view)"""
    user = get_current_user()
    invoice = Invoice.get_by_id(invoice_id)
    
    if not invoice:
        abort(404)
    
    if not can_view_invoice(user, invoice):
        abort(403)
    
    # Get client from snapshot if issued, otherwise get current
    if invoice['status'] in [Invoice.STATUS_ISSUED, Invoice.STATUS_PAID]:
        client = invoice['snapshot']['client']
        company_info = {
            'name': invoice['snapshot']['company_name'],
            'gstin': invoice['snapshot']['company_gstin'],
            'address': invoice['snapshot']['company_address'],
            'email': invoice['snapshot']['company_email'],
            'phone': invoice['snapshot']['company_phone']
        }
    else:
        client = Client.get_by_id(str(invoice['client_id']))
        from flask import current_app
        company_info = {
            'name': current_app.config['COMPANY_NAME'],
            'gstin': current_app.config['COMPANY_GSTIN'],
            'address': current_app.config['COMPANY_ADDRESS'],
            'email': current_app.config['COMPANY_EMAIL'],
            'phone': current_app.config['COMPANY_PHONE']
        }
    
    return render_template('invoices/invoice_v1.html', 
                         invoice=invoice, 
                         client=client,
                         company_info=company_info)
