from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify, current_app, session
from app.utils.auth import login_required, owner_required, get_current_user
from app.models.invoice import Invoice
from app.models.client import Client
from app.models.product import Product
from app.models.coupon import Coupon
from app.services.invoice_service import InvoiceService
from app.utils.permissions import can_view_invoice, can_edit_invoice, can_delete_invoice
from datetime import datetime, timezone
from app import get_db
from bson import ObjectId
import uuid

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
    if invoice['status'] in [Invoice.STATUS_ISSUED, Invoice.STATUS_PAID] and invoice.get('snapshot'):
        client = invoice['snapshot']['client']
        company_info = {
            'name': invoice['snapshot']['company_name'],
            'gstin': invoice['snapshot']['company_gstin'],
            'address': invoice['snapshot']['company_address'],
            'email': invoice['snapshot']['company_email'],
            'phone': invoice['snapshot']['company_phone']
        }
    else:
        # For draft invoices or merged invoices without snapshot
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


@invoices_bp.route('/payments/summary')
@login_required
def payment_summary():
    """Show payment summary with all pending invoices"""
    from app.models.user import User
    user = get_current_user()
    
    # Get pending invoices for client
    if User.is_client(user):
        client_id = str(user['client_id'])
        invoices = Invoice.get_all(status=Invoice.STATUS_ISSUED, client_id=client_id)
    else:
        # Owner can see all pending invoices
        invoices = Invoice.get_all(status=Invoice.STATUS_ISSUED)
    
    # Populate client data for each invoice
    for invoice in invoices:
        if 'client_id' in invoice:
            invoice['client'] = Client.get_by_id(str(invoice['client_id']))
    
    # Calculate totals
    total_amount = sum(inv.get('total', 0) for inv in invoices)
    
    return render_template('invoices/payment_summary.html',
                         invoices=invoices,
                         total_amount=total_amount)


@invoices_bp.route('/payments/validate-coupon', methods=['POST'])
@login_required
def validate_coupon():
    """Validate coupon code and return discount"""
    code = request.json.get('coupon_code', '').strip()
    amount = request.json.get('amount', 0)
    
    if not code:
        return jsonify({'valid': False, 'message': 'Coupon code required'})
    
    result = Coupon.validate_coupon(code, amount)
    
    # Format response for frontend
    if result['valid']:
        coupon = Coupon.get_by_code(code)
        discount_type = coupon['discount_type']
        discount_amount = result['discount']
        
        # Calculate percentage for display
        if discount_type == 'PERCENTAGE':
            discount_percentage = coupon['discount_value']
        else:
            discount_percentage = (discount_amount / amount * 100) if amount > 0 else 0
        
        return jsonify({
            'valid': True,
            'discount_type': discount_type,
            'discount_amount': discount_amount,
            'discount_percentage': discount_percentage,
            'discount_value': coupon['discount_value'],
            'final_amount': result['final_amount']
        })
    else:
        return jsonify({
            'valid': False,
            'message': result.get('error', 'Invalid coupon')
        })


@invoices_bp.route('/payments/process', methods=['POST'])
@login_required
def process_payment():
    """Process payment - create payment request and redirect to confirmation"""
    from app.models.user import User
    from bson import ObjectId
    import uuid
    
    user = get_current_user()
    
    invoice_ids = request.json.get('invoice_ids', [])
    coupon_code = request.json.get('coupon_code', '').strip()
    payment_type = request.json.get('payment_type', 'selected')  # 'selected' or 'total'
    amount = float(request.json.get('amount', 0))
    
    try:
        # Get client info
        if User.is_client(user):
            client_id = str(user['client_id'])
            client = Client.get_by_id(client_id)
        else:
            return jsonify({'success': False, 'message': 'Only clients can make payments'}), 403
        
        if not client:
            return jsonify({'success': False, 'message': 'Client not found'}), 404
        
        # Get invoices
        if payment_type == 'selected' and invoice_ids:
            invoices = [Invoice.get_by_id(inv_id) for inv_id in invoice_ids]
            invoices = [inv for inv in invoices if inv and inv.get('status') == Invoice.STATUS_ISSUED and str(inv.get('client_id')) == client_id]
        else:
            # All pending invoices
            invoices = Invoice.get_all(status=Invoice.STATUS_ISSUED, client_id=client_id)
        
        if not invoices:
            return jsonify({'success': False, 'message': 'No invoices to pay'}), 400
        
        # Validate coupon if provided
        coupon_discount = 0
        coupon_id = None
        if coupon_code:
            result = Coupon.validate_coupon(coupon_code, amount)
            if result['valid']:
                coupon_discount = result['discount']
                coupon = Coupon.get_by_code(coupon_code)
                coupon_id = str(coupon['_id'])
            else:
                return jsonify({'success': False, 'message': result.get('error', 'Invalid coupon')}), 400
        
        final_amount = max(0, amount - coupon_discount)
        
        # Store payment request in session
        payment_id = str(uuid.uuid4())
        session[f'payment_{payment_id}'] = {
            'client_id': client_id,
            'client_name': client.get('company_name', client.get('name', 'Client')),
            'invoice_ids': [str(inv['_id']) for inv in invoices],
            'subtotal': amount,
            'coupon_code': coupon_code,
            'coupon_discount': coupon_discount,
            'coupon_id': coupon_id,
            'final_amount': final_amount,
            'created_at': datetime.now(),
            'owner_phone': current_app.config.get('COMPANY_PHONE', '9876543210')
        }
        session.modified = True
        
        return jsonify({
            'success': True,
            'payment_id': payment_id,
            'redirect_url': url_for('invoices.payment_confirmation', payment_id=payment_id)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@invoices_bp.route('/payments/confirm/<payment_id>')
@login_required
def payment_confirmation(payment_id):
    """Show payment confirmation with UPI QR code"""
    payment_data = session.get(f'payment_{payment_id}')
    
    if not payment_data:
        flash('Payment request not found or expired', 'error')
        return redirect(url_for('invoices.list_invoices'))
    
    # Get company details for UPI
    company_name = current_app.config.get('COMPANY_NAME', 'Qupr Digital')
    company_upi = current_app.config.get('COMPANY_UPI', 'jpshashank200@oksbi')
    company_phone = payment_data.get('owner_phone')
    
    # Build UPI string with dynamic amount
    final_amount = payment_data['final_amount']
    upi_string = f"upi://pay?pa={company_upi}&pn={company_name}&am={final_amount}&tn=Invoice%20Payment"
    
    return render_template('invoices/payment_confirmation.html',
                         payment_id=payment_id,
                         payment_data=payment_data,
                         upi_string=upi_string,
                         company_name=company_name,
                         company_phone=company_phone)


@invoices_bp.route('/payments/success')
@login_required
def payment_success():
    """Show payment success page (when owner marks as paid)"""
    payment_id = request.args.get('payment_id')
    payment_data = session.get(f'payment_{payment_id}')
    
    if not payment_data:
        flash('Payment request not found', 'error')
        return redirect(url_for('invoices.list_invoices'))
    
    # Mark invoices as paid
    for invoice_id in payment_data.get('invoice_ids', []):
        Invoice.update(invoice_id, status=Invoice.STATUS_PAID, paid_at=datetime.now(timezone.utc))
    
    # Increment coupon usage if applied
    if payment_data.get('coupon_id'):
        Coupon.increment_use(payment_data['coupon_id'])
    
    # Clear from session
    session.pop(f'payment_{payment_id}', None)
    session.modified = True
    
    return render_template('invoices/payment_success.html', payment_data=payment_data)


@invoices_bp.route('/merge', methods=['GET', 'POST'])
@owner_required
def merge_invoices():
    """Merge two invoices with custom amount and coupon support"""
    from app.models.user import User
    
    if request.method == 'POST':
        try:
            invoice_id_1 = request.form.get('invoice_id_1')
            invoice_id_2 = request.form.get('invoice_id_2')
            custom_amount = request.form.get('custom_amount')
            coupon_code = request.form.get('coupon_code', '').strip()
            
            if not invoice_id_1 or not invoice_id_2:
                flash('Please select two invoices to merge', 'error')
                return redirect(url_for('invoices.merge_invoices'))
            
            if invoice_id_1 == invoice_id_2:
                flash('Please select two different invoices', 'error')
                return redirect(url_for('invoices.merge_invoices'))
            
            # Get invoices
            invoice_1 = Invoice.get_by_id(invoice_id_1)
            invoice_2 = Invoice.get_by_id(invoice_id_2)
            
            if not invoice_1 or not invoice_2:
                flash('One or both invoices not found', 'error')
                return redirect(url_for('invoices.merge_invoices'))
            
            # Verify both invoices are issued
            if invoice_1.get('status') != Invoice.STATUS_ISSUED or invoice_2.get('status') != Invoice.STATUS_ISSUED:
                flash('Both invoices must have "ISSUED" status to merge', 'error')
                return redirect(url_for('invoices.merge_invoices'))
            
            # Get client (both invoices should be for same client)
            client_id_1 = str(invoice_1['client_id'])
            client_id_2 = str(invoice_2['client_id'])
            
            if client_id_1 != client_id_2:
                flash('Both invoices must belong to the same client', 'error')
                return redirect(url_for('invoices.merge_invoices'))
            
            client = Client.get_by_id(client_id_1)
            
            # Calculate merged amount
            if custom_amount:
                merged_amount = float(custom_amount)
            else:
                merged_amount = invoice_1.get('total', 0) + invoice_2.get('total', 0)
            
            # Apply coupon if provided
            coupon_discount = 0
            coupon_id = None
            discount_type = None
            discount_value = 0
            
            if coupon_code:
                coupon_result = Coupon.validate_coupon(coupon_code, merged_amount)
                if coupon_result['valid']:
                    coupon_discount = coupon_result['discount']
                    coupon = Coupon.get_by_code(coupon_code)
                    coupon_id = str(coupon['_id'])
                    discount_type = coupon['discount_type']
                    discount_value = coupon['discount_value']
                else:
                    flash(f'Invalid coupon: {coupon_result.get("error", "Unknown error")}', 'error')
                    return redirect(url_for('invoices.merge_invoices'))
            
            final_amount = max(0, merged_amount - coupon_discount)
            
            # Generate new invoice number for merged invoice
            new_invoice_number = Invoice.get_next_invoice_no('INV')
            
            # Create merged invoice
            merged_invoice = {
                'invoice_no': new_invoice_number,
                'client_id': ObjectId(client_id_1),
                'status': Invoice.STATUS_ISSUED,
                'issue_date': datetime.now(timezone.utc),
                'due_date': None,
                'items': [
                    {
                        'description': f"Merged from Invoice #{invoice_1.get('invoice_no')}",
                        'quantity': 1,
                        'unit_price': invoice_1.get('total', 0),
                        'amount': invoice_1.get('total', 0)
                    },
                    {
                        'description': f"Merged from Invoice #{invoice_2.get('invoice_no')}",
                        'quantity': 1,
                        'unit_price': invoice_2.get('total', 0),
                        'amount': invoice_2.get('total', 0)
                    }
                ],
                'subtotal': merged_amount,
                'tax': 0,
                'tax_breakup': {},
                'total': final_amount,
                'coupon_applied': coupon_code if coupon_code else None,
                'coupon_discount': coupon_discount,
                'coupon_type': discount_type,
                'coupon_value': discount_value,
                'merged_from': [invoice_id_1, invoice_id_2],
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            }
            
            # Insert merged invoice
            db = get_db()
            result = db.invoices.insert_one(merged_invoice)
            merged_invoice_id = str(result.inserted_id)
            
            # Mark original invoices as paid (since they're merged)
            Invoice.update(invoice_id_1, status=Invoice.STATUS_PAID, paid_at=datetime.now(timezone.utc))
            Invoice.update(invoice_id_2, status=Invoice.STATUS_PAID, paid_at=datetime.now(timezone.utc))
            
            # Increment coupon usage if applied
            if coupon_id:
                Coupon.increment_use(coupon_id)
            
            flash(f'Invoices merged successfully! New invoice #{new_invoice_number} created with combined amount ₹{final_amount:.2f}', 'success')
            return redirect(url_for('invoices.view_invoice', invoice_id=merged_invoice_id))
        
        except Exception as e:
            flash(f'Error merging invoices: {str(e)}', 'error')
            return redirect(url_for('invoices.merge_invoices'))
    
    # GET request - show merge form
    # Get all issued invoices
    issued_invoices = Invoice.get_all(status=Invoice.STATUS_ISSUED)
    
    # Group by client
    invoices_by_client = {}
    for inv in issued_invoices:
        client_id = str(inv['client_id'])
        client = Client.get_by_id(client_id)
        if client_id not in invoices_by_client:
            invoices_by_client[client_id] = {
                'client': client,
                'invoices': []
            }
        invoices_by_client[client_id]['invoices'].append(inv)
    
    return render_template('invoices/merge.html', invoices_by_client=invoices_by_client)
