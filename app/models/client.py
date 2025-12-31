from datetime import datetime, timezone
from bson import ObjectId
from app import get_db


class Client:
    """Client model"""
    
    @staticmethod
    def create(company_name, gstin, billing_address, contact_person=None, 
               contact_email=None, contact_phone=None):
        """Create new client"""
        client_data = {
            'company_name': company_name,
            'gstin': gstin.upper() if gstin else None,
            'billing_address': billing_address,
            'contact_person': contact_person,
            'contact_email': contact_email.lower() if contact_email else None,
            'contact_phone': contact_phone,
            'is_active': True,
            'created_at': datetime.now(timezone.utc)
        }
        
        db = get_db()
        result = db.clients.insert_one(client_data)
        return str(result.inserted_id)
    
    @staticmethod
    def get_by_id(client_id):
        """Get client by ID"""
        if not client_id:
            return None
        try:
            db = get_db()
            return db.clients.find_one({'_id': ObjectId(client_id)})
        except:
            return None
    
    @staticmethod
    def get_all(active_only=True):
        """Get all clients"""
        db = get_db()
        query = {'is_active': True} if active_only else {}
        return list(db.clients.find(query).sort('company_name', 1))
    
    @staticmethod
    def update(client_id, **kwargs):
        """Update client"""
        update_data = {k: v for k, v in kwargs.items() if v is not None}
        if 'gstin' in update_data and update_data['gstin']:
            update_data['gstin'] = update_data['gstin'].upper()
        if 'contact_email' in update_data and update_data['contact_email']:
            update_data['contact_email'] = update_data['contact_email'].lower()
        
        db = get_db()
        db.clients.update_one(
            {'_id': ObjectId(client_id)},
            {'$set': update_data}
        )
    
    @staticmethod
    def deactivate(client_id):
        """Deactivate client"""
        db = get_db()
        db.clients.update_one(
            {'_id': ObjectId(client_id)},
            {'$set': {'is_active': False}}
        )
    
    @staticmethod
    def search(query):
        """Search clients by company name"""
        db = get_db()
        return list(db.clients.find({
            'company_name': {'$regex': query, '$options': 'i'},
            'is_active': True
        }).sort('company_name', 1))
