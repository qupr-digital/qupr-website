from datetime import datetime, timezone
from bson import ObjectId
from app import get_db


class Coupon:
    """Coupon model for payment discounts"""
    
    TYPE_PERCENTAGE = 'PERCENTAGE'
    TYPE_FIXED = 'FIXED'
    
    @staticmethod
    def create(code, description, discount_value, discount_type=TYPE_PERCENTAGE, 
               max_uses=None, used_count=0, is_active=True, valid_from=None, 
               valid_until=None, min_amount=None):
        """Create new coupon"""
        coupon_data = {
            'code': code.upper(),
            'description': description,
            'discount_value': float(discount_value),
            'discount_type': discount_type,
            'max_uses': max_uses,
            'used_count': used_count,
            'is_active': is_active,
            'valid_from': valid_from,
            'valid_until': valid_until,
            'min_amount': float(min_amount) if min_amount else None,
            'used_by': [],
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc)
        }
        
        db = get_db()
        result = db.coupons.insert_one(coupon_data)
        return str(result.inserted_id)
    
    @staticmethod
    def get_by_id(coupon_id):
        """Get coupon by ID"""
        if not coupon_id:
            return None
        try:
            db = get_db()
            return db.coupons.find_one({'_id': ObjectId(coupon_id)})
        except:
            return None
    
    @staticmethod
    def get_by_code(code):
        """Get coupon by code"""
        db = get_db()
        return db.coupons.find_one({'code': code.upper(), 'is_active': True})
    
    @staticmethod
    def get_all():
        """Get all coupons"""
        db = get_db()
        return list(db.coupons.find().sort('created_at', -1))
    
    @staticmethod
    def validate_coupon(code, amount, user_id=None):
        """Validate coupon and return discount details"""
        coupon = Coupon.get_by_code(code)
        
        if not coupon:
            return {'valid': False, 'error': 'Coupon code not found'}
        
        if not coupon.get('is_active'):
            return {'valid': False, 'error': 'Coupon is inactive'}
        
        # Check if user has already used this coupon (one-time use per user)
        if user_id and user_id in coupon.get('used_by', []):
            return {'valid': False, 'error': 'You have already used this coupon code'}
        
        # Check max uses
        if coupon.get('max_uses') and coupon.get('times_used', 0) >= coupon.get('max_uses'):
            return {'valid': False, 'error': 'Coupon usage limit exceeded'}
        
        # Check valid dates (only if dates are explicitly set)
        now = datetime.now(timezone.utc)
        
        if coupon.get('valid_from'):
            valid_from = coupon['valid_from']
            # Make datetimes comparable by adding timezone if needed
            if valid_from.tzinfo is None:
                valid_from = valid_from.replace(tzinfo=timezone.utc)
            if now < valid_from:
                return {'valid': False, 'error': f'Coupon will be valid from {valid_from.strftime("%d %b %Y")}'}
        
        if coupon.get('valid_until'):
            valid_until = coupon['valid_until']
            # Make datetimes comparable by adding timezone if needed
            if valid_until.tzinfo is None:
                valid_until = valid_until.replace(tzinfo=timezone.utc)
            if now > valid_until:
                return {'valid': False, 'error': f'Coupon expired on {valid_until.strftime("%d %b %Y")}'}
        
        # Check minimum amount
        if coupon.get('min_amount') and amount < coupon['min_amount']:
            return {'valid': False, 'error': f'Minimum purchase amount: ₹{coupon["min_amount"]}'}
        
        # Calculate discount
        if coupon['discount_type'] == Coupon.TYPE_PERCENTAGE:
            discount = (amount * coupon['discount_value']) / 100
        else:
            discount = coupon['discount_value']
        
        # Don't discount more than the amount
        discount = min(discount, amount)
        
        return {
            'valid': True,
            'code': coupon['code'],
            'discount': discount,
            'final_amount': amount - discount,
            'coupon_id': str(coupon['_id'])
        }
    
    @staticmethod
    def update(coupon_id, **kwargs):
        """Update coupon"""
        db = get_db()
        kwargs['updated_at'] = datetime.now(timezone.utc)
        
        result = db.coupons.update_one(
            {'_id': ObjectId(coupon_id)},
            {'$set': kwargs}
        )
        return result.modified_count > 0
    
    @staticmethod
    def increment_use(coupon_id, user_id=None):
        """Increment coupon usage count and track user"""
        db = get_db()
        update_data = {'$inc': {'used_count': 1}, '$set': {'updated_at': datetime.now(timezone.utc)}}
        
        # Add user to used_by list if user_id is provided
        if user_id:
            update_data['$addToSet'] = {'used_by': user_id}
        
        result = db.coupons.update_one(
            {'_id': ObjectId(coupon_id)},
            update_data
        )
        return result.modified_count > 0
    
    @staticmethod
    def delete(coupon_id):
        """Delete coupon"""
        db = get_db()
        result = db.coupons.delete_one({'_id': ObjectId(coupon_id)})
        return result.deleted_count > 0
