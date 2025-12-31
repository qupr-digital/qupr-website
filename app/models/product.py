from datetime import datetime, timezone
from bson import ObjectId
from app import get_db


class Product:
    """Product model"""
    
    @staticmethod
    def create(name, description, hsn, rate, tax_rate):
        """Create new product"""
        product_data = {
            'name': name,
            'description': description,
            'hsn': hsn,
            'rate': float(rate),
            'tax_rate': float(tax_rate),
            'is_active': True,
            'created_at': datetime.now(timezone.utc)
        }
        
        db = get_db()
        result = db.products.insert_one(product_data)
        return str(result.inserted_id)
    
    @staticmethod
    def get_by_id(product_id):
        """Get product by ID"""
        if not product_id:
            return None
        try:
            db = get_db()
            return db.products.find_one({'_id': ObjectId(product_id)})
        except:
            return None
    
    @staticmethod
    def get_all(active_only=True):
        """Get all products"""
        db = get_db()
        query = {'is_active': True} if active_only else {}
        return list(db.products.find(query).sort('name', 1))
    
    @staticmethod
    def update(product_id, **kwargs):
        """Update product"""
        update_data = {}
        if 'name' in kwargs:
            update_data['name'] = kwargs['name']
        if 'description' in kwargs:
            update_data['description'] = kwargs['description']
        if 'hsn' in kwargs:
            update_data['hsn'] = kwargs['hsn']
        if 'rate' in kwargs:
            update_data['rate'] = float(kwargs['rate'])
        if 'tax_rate' in kwargs:
            update_data['tax_rate'] = float(kwargs['tax_rate'])
        
        if update_data:
            db = get_db()
            db.products.update_one(
                {'_id': ObjectId(product_id)},
                {'$set': update_data}
            )
    
    @staticmethod
    def deactivate(product_id):
        """Deactivate product"""
        db = get_db()
        db.products.update_one(
            {'_id': ObjectId(product_id)},
            {'$set': {'is_active': False}}
        )
    
    @staticmethod
    def search(query):
        """Search products by name"""
        db = get_db()
        return list(db.products.find({
            'name': {'$regex': query, '$options': 'i'},
            'is_active': True
        }).sort('name', 1))
