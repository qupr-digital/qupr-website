from datetime import datetime, timezone, timedelta
from bson import ObjectId
from app import get_db
import secrets
import string


class MagicLink:
    """Magic login link model for passwordless client access"""
    
    @staticmethod
    def generate_token():
        """Generate a secure random token"""
        # Generate a 32-character URL-safe token
        return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
    
    @staticmethod
    def create(client_id, expires_in_hours=24, created_by=None):
        """
        Create a new magic login link
        
        Args:
            client_id: The client ID this link is for
            expires_in_hours: How many hours until the link expires (default 24)
            created_by: User ID of who created the link (owner)
        
        Returns:
            dict: The created magic link document with token
        """
        token = MagicLink.generate_token()
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=expires_in_hours)
        
        magic_link_data = {
            'token': token,
            'client_id': str(client_id),
            'created_by': created_by,
            'created_at': now,
            'expires_at': expires_at,
            'used': False,
            'used_at': None,
            'ip_address': None
        }
        
        db = get_db()
        result = db.magic_links.insert_one(magic_link_data)
        magic_link_data['_id'] = result.inserted_id
        
        return magic_link_data
    
    @staticmethod
    def get_by_token(token):
        """Get magic link by token"""
        db = get_db()
        return db.magic_links.find_one({'token': token})
    
    @staticmethod
    def validate_token(token):
        """
        Validate a magic link token
        
        Returns:
            dict: {'valid': bool, 'client_id': str, 'error': str}
        """
        magic_link = MagicLink.get_by_token(token)
        
        if not magic_link:
            return {'valid': False, 'error': 'Invalid or expired link'}
        
        # Check if already used
        if magic_link.get('used'):
            return {'valid': False, 'error': 'This link has already been used'}
        
        # Check if expired
        now = datetime.now(timezone.utc)
        expires_at = magic_link['expires_at']
        
        # Make timezone-aware if needed
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        
        if now > expires_at:
            return {'valid': False, 'error': 'This link has expired'}
        
        return {
            'valid': True,
            'client_id': magic_link['client_id'],
            'magic_link_id': str(magic_link['_id'])
        }
    
    @staticmethod
    def mark_as_used(token, ip_address=None):
        """Mark a magic link as used"""
        db = get_db()
        result = db.magic_links.update_one(
            {'token': token},
            {
                '$set': {
                    'used': True,
                    'used_at': datetime.now(timezone.utc),
                    'ip_address': ip_address
                }
            }
        )
        return result.modified_count > 0
    
    @staticmethod
    def get_all_for_client(client_id):
        """Get all magic links for a client (for audit trail)"""
        db = get_db()
        return list(db.magic_links.find({'client_id': str(client_id)}).sort('created_at', -1))
    
    @staticmethod
    def delete_expired():
        """Delete expired magic links (cleanup task)"""
        db = get_db()
        now = datetime.now(timezone.utc)
        result = db.magic_links.delete_many({'expires_at': {'$lt': now}})
        return result.deleted_count
    
    @staticmethod
    def revoke(token):
        """Revoke a magic link before it expires"""
        db = get_db()
        result = db.magic_links.update_one(
            {'token': token},
            {
                '$set': {
                    'used': True,
                    'used_at': datetime.now(timezone.utc)
                }
            }
        )
        return result.modified_count > 0
