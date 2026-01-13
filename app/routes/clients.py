from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from app.utils.auth import owner_required, get_current_user
from app.models.client import Client
from app.services.client_service import ClientService
from app.models.magic_link import MagicLink

clients_bp = Blueprint('clients', __name__)


@clients_bp.route('/')
@owner_required
def list_clients():
    """List all clients"""
    search_query = request.args.get('q', '')
    
    if search_query:
        clients = Client.search(search_query)
    else:
        clients = Client.get_all()
    
    return render_template('clients/list.html', clients=clients, search_query=search_query)


@clients_bp.route('/<client_id>')
@owner_required
def view_client(client_id):
    """View client details"""
    client = Client.get_by_id(client_id)
    
    if not client:
        abort(404)
    
    # Get client's user account
    user = ClientService.get_client_user(client_id)
    
    # Get client's invoices
    from app.models.invoice import Invoice
    invoices = Invoice.get_all(client_id=client_id)
    
    return render_template('clients/view.html', 
                         client=client, 
                         user=user, 
                         invoices=invoices)


@clients_bp.route('/create', methods=['GET', 'POST'])
@owner_required
def create_client():
    """Create new client with user account"""
    if request.method == 'POST':
        try:
            company_name = request.form.get('company_name', '').strip()
            gstin = request.form.get('gstin', '').strip()
            billing_address = request.form.get('billing_address', '').strip()
            contact_person = request.form.get('contact_person', '').strip()
            contact_email = request.form.get('contact_email', '').strip()
            contact_phone = request.form.get('contact_phone', '').strip()
            
            # Validation
            if not company_name:
                flash('Company name is required', 'error')
                return render_template('clients/create.html')
            
            if not billing_address:
                flash('Billing address is required', 'error')
                return render_template('clients/create.html')
            
            if not contact_email:
                flash('Contact email is required', 'error')
                return render_template('clients/create.html')
            
            # Create client with user
            result = ClientService.create_client_with_user(
                company_name=company_name,
                gstin=gstin,
                billing_address=billing_address,
                contact_person=contact_person,
                contact_email=contact_email,
                contact_phone=contact_phone
            )
            
            # Show credentials on dedicated page
            return render_template('clients/credentials.html',
                                 client_id=result['client_id'],
                                 email=result['email'],
                                 password=result['password'])
            
        except Exception as e:
            flash(f'Error creating client: {str(e)}', 'error')
    
    return render_template('clients/create.html')


@clients_bp.route('/<client_id>/edit', methods=['GET', 'POST'])
@owner_required
def edit_client(client_id):
    """Edit client details"""
    client = Client.get_by_id(client_id)
    
    if not client:
        abort(404)
    
    if request.method == 'POST':
        try:
            Client.update(
                client_id,
                company_name=request.form.get('company_name', '').strip(),
                gstin=request.form.get('gstin', '').strip(),
                billing_address=request.form.get('billing_address', '').strip(),
                contact_person=request.form.get('contact_person', '').strip(),
                contact_email=request.form.get('contact_email', '').strip(),
                contact_phone=request.form.get('contact_phone', '').strip()
            )
            
            flash('Client updated successfully', 'success')
            return redirect(url_for('clients.view_client', client_id=client_id))
            
        except Exception as e:
            flash(f'Error updating client: {str(e)}', 'error')
    
    return render_template('clients/edit.html', client=client)


@clients_bp.route('/<client_id>/reset-password', methods=['POST'])
@owner_required
def reset_password(client_id):
    """Reset client user password"""
    try:
        result = ClientService.reset_client_password(client_id)
        
        if result:
            # Show new credentials on dedicated page
            return render_template('clients/credentials.html',
                                 client_id=client_id,
                                 email=result['email'],
                                 password=result['password'],
                                 is_reset=True)
        else:
            flash('No user account found for this client', 'error')
            return redirect(url_for('clients.view_client', client_id=client_id))
            
    except Exception as e:
        flash(f'Error resetting password: {str(e)}', 'error')
        return redirect(url_for('clients.view_client', client_id=client_id))


@clients_bp.route('/<client_id>/deactivate', methods=['POST'])
@owner_required
def deactivate_client(client_id):
    """Deactivate client"""
    try:
        Client.deactivate(client_id)
        
        # Also deactivate user
        user = ClientService.get_client_user(client_id)
        if user:
            from app.models.user import User
            User.deactivate(str(user['_id']))
        
        flash('Client deactivated successfully', 'success')
        return redirect(url_for('clients.list_clients'))
        
    except Exception as e:
        flash(f'Error deactivating client: {str(e)}', 'error')
        return redirect(url_for('clients.view_client', client_id=client_id))


@clients_bp.route('/<client_id>/generate-magic-link', methods=['POST'])
@owner_required
def generate_magic_link(client_id):
    """Generate a magic login link for a client"""
    try:
        client = Client.get_by_id(client_id)
        if not client:
            flash('Client not found', 'error')
            return redirect(url_for('clients.list_clients'))
        
        # Check if client has a user account
        user = ClientService.get_client_user(client_id)
        if not user:
            flash('This client does not have a user account', 'error')
            return redirect(url_for('clients.view_client', client_id=client_id))
        
        # Get expiry hours from form (default 24)
        expires_in_hours = int(request.form.get('expires_in_hours', 24))
        
        # Get current user (owner) who is generating the link
        current_user = get_current_user()
        
        # Create magic link
        magic_link = MagicLink.create(
            client_id=client_id,
            expires_in_hours=expires_in_hours,
            created_by=str(current_user['_id'])
        )
        
        # Build the full URL
        magic_url = url_for('auth.magic_login', token=magic_link['token'], _external=True)
        
        # Return to a page showing the magic link
        return render_template('clients/magic_link.html',
                             client=client,
                             magic_url=magic_url,
                             expires_at=magic_link['expires_at'])
        
    except Exception as e:
        flash(f'Error generating magic link: {str(e)}', 'error')
        return redirect(url_for('clients.view_client', client_id=client_id))

