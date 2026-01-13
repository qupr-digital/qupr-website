from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.models.user import User
from app.models.magic_link import MagicLink
from app.models.client import Client

auth_bp = Blueprint('auth', __name__)


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

