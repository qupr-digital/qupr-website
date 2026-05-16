from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.models.user import User
from app.models.magic_link import MagicLink
from app.models.client import Client
from app import get_db
from bson import ObjectId

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Register a new client account"""
    if 'user_id' in session:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        company_name = request.form.get('company_name', '').strip()
        gstin = request.form.get('gstin', '').strip()
        billing_address = request.form.get('billing_address', '').strip()
        contact_person = request.form.get('contact_person', '').strip()
        contact_email = request.form.get('contact_email', '').strip().lower()
        contact_phone = request.form.get('contact_phone', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not company_name:
            flash('Company name is required', 'error')
            return render_template('auth/register.html')

        if not contact_person:
            flash('Contact person name is required', 'error')
            return render_template('auth/register.html')

        if not contact_email:
            flash('Email address is required', 'error')
            return render_template('auth/register.html')

        if not billing_address:
            flash('Billing address is required', 'error')
            return render_template('auth/register.html')

        if not password:
            flash('Password is required', 'error')
            return render_template('auth/register.html')

        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('auth/register.html')

        if User.get_by_email(contact_email):
            flash('An account with this email already exists', 'error')
            return render_template('auth/register.html')

        db = get_db()
        if db.clients.find_one({'contact_email': contact_email}):
            flash('A client with this email already exists', 'error')
            return render_template('auth/register.html')

        client_id = None

        try:
            client_id = Client.create(
                company_name=company_name,
                gstin=gstin,
                billing_address=billing_address,
                contact_person=contact_person,
                contact_email=contact_email,
                contact_phone=contact_phone
            )

            user_id = User.create(
                name=contact_person,
                email=contact_email,
                password=password,
                role=User.ROLE_CLIENT,
                client_id=client_id
            )

            session['user_id'] = user_id
            session['user_role'] = User.ROLE_CLIENT
            session.permanent = True

            flash(f'Welcome, {contact_person}! Your account has been created.', 'success')
            return redirect(url_for('dashboard.index'))

        except Exception as e:
            if client_id:
                db.clients.delete_one({'_id': ObjectId(client_id)})
            flash(f'Error creating account: {str(e)}', 'error')
            return render_template('auth/register.html')

    return render_template('auth/register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if 'user_id' in session:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('Email and password are required', 'error')
            return render_template('auth/login.html')
        
        user = User.authenticate(email, password)
        if user:
            session['user_id'] = str(user['_id'])
            session['user_role'] = user['role']
            session.permanent = True
            
            flash(f'Welcome back, {user["name"]}!', 'success')
            return redirect(url_for('dashboard.index'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('auth/login.html')


@auth_bp.route('/logout')
def logout():
    """Logout"""
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('public.index'))


@auth_bp.route('/magic/<token>')
def magic_login(token):
    """Magic login link - passwordless login for clients"""
    # Don't allow if already logged in
    if 'user_id' in session:
        flash('You are already logged in', 'info')
        return redirect(url_for('dashboard.index'))
    
    # Validate the token
    validation = MagicLink.validate_token(token)
    
    if not validation['valid']:
        flash(validation['error'], 'error')
        return redirect(url_for('auth.login'))
    
    # Get the client
    client = Client.get_by_id(validation['client_id'])
    if not client:
        flash('Client account not found', 'error')
        return redirect(url_for('auth.login'))
    
    # Get the user account for this client
    user = User.get_by_client_id(validation['client_id'])
    if not user:
        flash('User account not found for this client', 'error')
        return redirect(url_for('auth.login'))
    
    # Mark the magic link as used
    ip_address = request.remote_addr
    MagicLink.mark_as_used(token, ip_address)
    
    # Log the user in
    session['user_id'] = str(user['_id'])
    session['user_role'] = user['role']
    session.permanent = True
    
    flash(f'Welcome, {user["name"]}! You have been logged in via magic link.', 'success')
    return redirect(url_for('dashboard.index'))

