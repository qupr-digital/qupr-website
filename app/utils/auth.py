from functools import wraps
from flask import session, redirect, url_for, flash, abort
from app.models.user import User


def login_required(f):
    """Require user to be logged in"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page', 'warning')
            return redirect(url_for('auth.login'))
        
        user = User.get_by_id(session['user_id'])
        if not user or not user.get('is_active'):
            session.clear()
            flash('Your account is not active', 'error')
            return redirect(url_for('auth.login'))
        
        return f(*args, **kwargs)
    return decorated_function


def owner_required(f):
    """Require user to be owner"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page', 'warning')
            return redirect(url_for('auth.login'))
        
        user = User.get_by_id(session['user_id'])
        if not user or not user.get('is_active'):
            session.clear()
            flash('Your account is not active', 'error')
            return redirect(url_for('auth.login'))
        
        if not User.is_owner(user):
            abort(403)
        
        return f(*args, **kwargs)
    return decorated_function


def client_or_owner_required(f):
    """Require user to be client or owner"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page', 'warning')
            return redirect(url_for('auth.login'))
        
        user = User.get_by_id(session['user_id'])
        if not user or not user.get('is_active'):
            session.clear()
            flash('Your account is not active', 'error')
            return redirect(url_for('auth.login'))
        
        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    """Get current logged in user"""
    user_id = session.get('user_id')
    if user_id:
        return User.get_by_id(user_id)
    return None


def is_authenticated():
    """Check if user is authenticated"""
    return 'user_id' in session
