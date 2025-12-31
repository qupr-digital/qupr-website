from datetime import datetime, timezone
from bson import ObjectId
from app import get_db


class Invoice:
    """Invoice model"""
    
    STATUS_DRAFT = 'DRAFT'
    STATUS_ISSUED = 'ISSUED'
    STATUS_PAID = 'PAID'
    
    @staticmethod
    def create(invoice_no, client_id, items, subtotal, tax_breakup, 
               total, status=STATUS_DRAFT, snapshot=None, issue_date=None, 
               due_date=None):
        """Create new invoice"""
        invoice_data = {
            'invoice_no': invoice_no,
            'client_id': ObjectId(client_id),
            'items': items,
            'subtotal': float(subtotal),
            'tax_breakup': tax_breakup,
            'total': float(total),
            'status': status,
            'snapshot': snapshot,
            'issue_date': issue_date,
            'due_date': due_date,
            'paid_on': None,
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc)
        }
        
        db = get_db()
        result = db.invoices.insert_one(invoice_data)
        return str(result.inserted_id)
    
    @staticmethod
    def get_by_id(invoice_id):
        """Get invoice by ID"""
        if not invoice_id:
            return None
        try:
            db = get_db()
            return db.invoices.find_one({'_id': ObjectId(invoice_id)})
        except:
            return None
    
    @staticmethod
    def get_by_invoice_no(invoice_no):
        """Get invoice by invoice number"""
        db = get_db()
        return db.invoices.find_one({'invoice_no': invoice_no})
    
    @staticmethod
    def get_all(status=None, client_id=None):
        """Get all invoices with optional filters"""
        db = get_db()
        query = {}
        if status:
            query['status'] = status
        if client_id:
            query['client_id'] = ObjectId(client_id)
        
        return list(db.invoices.find(query).sort('created_at', -1))
    
    @staticmethod
    def update(invoice_id, **kwargs):
        """Update invoice"""
        update_data = {k: v for k, v in kwargs.items() if k != '_id'}
        update_data['updated_at'] = datetime.now(timezone.utc)
        
        # Convert numeric fields
        if 'subtotal' in update_data:
            update_data['subtotal'] = float(update_data['subtotal'])
        if 'total' in update_data:
            update_data['total'] = float(update_data['total'])
        
        db = get_db()
        db.invoices.update_one(
            {'_id': ObjectId(invoice_id)},
            {'$set': update_data}
        )
    
    @staticmethod
    def update_status(invoice_id, status, paid_on=None):
        """Update invoice status"""
        update_data = {
            'status': status,
            'updated_at': datetime.now(timezone.utc)
        }
        if status == Invoice.STATUS_PAID and paid_on:
            update_data['paid_on'] = paid_on
        
        db = get_db()
        db.invoices.update_one(
            {'_id': ObjectId(invoice_id)},
            {'$set': update_data}
        )
    
    @staticmethod
    def delete(invoice_id):
        """Delete invoice (only if draft)"""
        db = get_db()
        db.invoices.delete_one({
            '_id': ObjectId(invoice_id),
            'status': Invoice.STATUS_DRAFT
        })
    
    @staticmethod
    def get_next_invoice_no(prefix='INV'):
        """Generate next invoice number"""
        db = get_db()
        last_invoice = db.invoices.find_one(
            {'invoice_no': {'$regex': f'^{prefix}'}},
            sort=[('invoice_no', -1)]
        )
        
        if last_invoice:
            last_no = last_invoice['invoice_no'].replace(prefix, '')
            try:
                next_no = int(last_no) + 1
            except:
                next_no = 1
        else:
            next_no = 1
        
        return f"{prefix}{next_no:05d}"
