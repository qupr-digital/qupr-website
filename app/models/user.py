from datetime import datetime, timezone
from bson import ObjectId
from app import get_db
import bcrypt


class User:
    """User model"""
    
    ROLE_OWNER = 'OWNER'
    ROLE_CLIENT = 'CLIENT'
    
    @staticmethod
    def create(name, email, password, role, client_id=None):
        """Create new user"""
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        user_data = {
            'name': name,
            'email': email.lower(),
            'password_hash': password_hash,
            'role': role,
            'client_id': ObjectId(client_id) if client_id else None,
            'is_active': True,
            'created_at': datetime.now(timezone.utc)
        }
        
        db = get_db()
        result = db.users.insert_one(user_data)
        return str(result.inserted_id)
    
    @staticmethod
    def get_by_id(user_id):
        """Get user by ID"""
        if not user_id:
            return None
        try:
            db = get_db()
            return db.users.find_one({'_id': ObjectId(user_id)})
        except:
            return None
    
    @staticmethod
    def get_by_email(email):
        """Get user by email"""
        db = get_db()
        return db.users.find_one({'email': email.lower()})
    
    @staticmethod
    def get_by_client_id(client_id):
        """Get user by client ID"""
        db = get_db()
        return db.users.find_one({'client_id': ObjectId(client_id)})
    
    @staticmethod
    def verify_password(user, password):
        """Verify user password"""
        if not user or not password:
            return False
        return bcrypt.checkpw(password.encode('utf-8'), user['password_hash'])
    
    @staticmethod
    def update_password(user_id, new_password):
        """Update user password"""
        password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        db = get_db()
        db.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {'password_hash': password_hash}}
        )
    
    @staticmethod
    def authenticate(email, password):
        """Authenticate user"""
        user = User.get_by_email(email)
        if user and user['is_active'] and User.verify_password(user, password):
            return user
        return None
    
    @staticmethod
    def deactivate(user_id):
        """Deactivate user"""
        db = get_db()
        db.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {'is_active': False}}
        )
    
    @staticmethod
    def is_owner(user):
        """Check if user is owner"""
        return user and user.get('role') == User.ROLE_OWNER
    
    @staticmethod
    def is_client(user):
        """Check if user is client"""
        return user and user.get('role') == User.ROLE_CLIENT
