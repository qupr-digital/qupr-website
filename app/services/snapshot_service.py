from datetime import datetime
from flask import current_app


class SnapshotService:
    """Service for creating immutable invoice snapshots"""
    
    @staticmethod
    def create_snapshot():
        """Create snapshot of current company info and template version"""
        return {
            'company_name': current_app.config['COMPANY_NAME'],
            'company_gstin': current_app.config['COMPANY_GSTIN'],
            'company_address': current_app.config['COMPANY_ADDRESS'],
            'company_email': current_app.config['COMPANY_EMAIL'],
            'company_phone': current_app.config['COMPANY_PHONE'],
            'template_version': current_app.config['INVOICE_TEMPLATE_VERSION'],
            'snapshot_at': datetime.utcnow()
        }
    
    @staticmethod
    def create_item_snapshot(product, quantity):
        """Create snapshot of product data for invoice item"""
        return {
            'product_id': str(product['_id']),
            'name': product['name'],
            'description': product['description'],
            'hsn': product['hsn'],
            'rate': float(product['rate']),
            'tax_rate': float(product['tax_rate']),
            'quantity': float(quantity)
        }
    
    @staticmethod
    def create_client_snapshot(client):
        """Create snapshot of client data for invoice"""
        return {
            'client_id': str(client['_id']),
            'company_name': client['company_name'],
            'gstin': client.get('gstin'),
            'billing_address': client['billing_address'],
            'contact_person': client.get('contact_person'),
            'contact_email': client.get('contact_email'),
            'contact_phone': client.get('contact_phone')
        }
