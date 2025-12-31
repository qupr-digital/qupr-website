from datetime import datetime, timedelta
from flask import current_app
from app.models.invoice import Invoice
from app.models.client import Client
from app.models.product import Product
from app.services.tax_service import TaxService
from app.services.snapshot_service import SnapshotService


class InvoiceService:
    """Service for invoice management"""
    
    @staticmethod
    def create_draft_invoice(client_id, items_data):
        """Create draft invoice from items data
        
        items_data format: [{'product_id': 'xxx', 'quantity': 2}, ...]
        """
        # Get client
        client = Client.get_by_id(client_id)
        if not client:
            raise ValueError('Client not found')
        
        # Build items with product snapshots
        items = []
        for item_data in items_data:
            product = Product.get_by_id(item_data['product_id'])
            if not product:
                raise ValueError(f"Product {item_data['product_id']} not found")
            
            item_snapshot = SnapshotService.create_item_snapshot(
                product, 
                item_data['quantity']
            )
            items.append(item_snapshot)
        
        # Calculate totals
        totals = TaxService.calculate_invoice_totals(items)
        
        # Generate invoice number
        invoice_no = Invoice.get_next_invoice_no(
            current_app.config['INVOICE_PREFIX']
        )
        
        # Create draft invoice
        invoice_id = Invoice.create(
            invoice_no=invoice_no,
            client_id=client_id,
            items=items,
            subtotal=totals['subtotal'],
            tax_breakup=totals['tax_breakup'],
            total=totals['total'],
            status=Invoice.STATUS_DRAFT
        )
        
        return invoice_id
    
    @staticmethod
    def issue_invoice(invoice_id, issue_date=None, due_date=None):
        """Issue a draft invoice"""
        invoice = Invoice.get_by_id(invoice_id)
        if not invoice:
            raise ValueError('Invoice not found')
        
        if invoice['status'] != Invoice.STATUS_DRAFT:
            raise ValueError('Only draft invoices can be issued')
        
        # Create snapshot
        snapshot = SnapshotService.create_snapshot()
        
        # Get client snapshot
        client = Client.get_by_id(str(invoice['client_id']))
        snapshot['client'] = SnapshotService.create_client_snapshot(client)
        
        # Set dates
        if not issue_date:
            issue_date = datetime.utcnow()
        if not due_date:
            due_date = issue_date + timedelta(days=30)
        
        # Update invoice
        Invoice.update(
            invoice_id,
            status=Invoice.STATUS_ISSUED,
            snapshot=snapshot,
            issue_date=issue_date,
            due_date=due_date
        )
        
        return invoice_id
    
    @staticmethod
    def mark_as_paid(invoice_id, paid_on=None):
        """Mark invoice as paid"""
        invoice = Invoice.get_by_id(invoice_id)
        if not invoice:
            raise ValueError('Invoice not found')
        
        if invoice['status'] != Invoice.STATUS_ISSUED:
            raise ValueError('Only issued invoices can be marked as paid')
        
        if not paid_on:
            paid_on = datetime.utcnow()
        
        Invoice.update_status(invoice_id, Invoice.STATUS_PAID, paid_on)
        return invoice_id
    
    @staticmethod
    def update_draft_invoice(invoice_id, items_data):
        """Update draft invoice items"""
        invoice = Invoice.get_by_id(invoice_id)
        if not invoice:
            raise ValueError('Invoice not found')
        
        if invoice['status'] != Invoice.STATUS_DRAFT:
            raise ValueError('Only draft invoices can be updated')
        
        # Build items with product snapshots
        items = []
        for item_data in items_data:
            product = Product.get_by_id(item_data['product_id'])
            if not product:
                raise ValueError(f"Product {item_data['product_id']} not found")
            
            item_snapshot = SnapshotService.create_item_snapshot(
                product, 
                item_data['quantity']
            )
            items.append(item_snapshot)
        
        # Calculate totals
        totals = TaxService.calculate_invoice_totals(items)
        
        # Update invoice
        Invoice.update(
            invoice_id,
            items=items,
            subtotal=totals['subtotal'],
            tax_breakup=totals['tax_breakup'],
            total=totals['total']
        )
        
        return invoice_id
    
    @staticmethod
    def delete_draft_invoice(invoice_id):
        """Delete draft invoice"""
        invoice = Invoice.get_by_id(invoice_id)
        if not invoice:
            raise ValueError('Invoice not found')
        
        if invoice['status'] != Invoice.STATUS_DRAFT:
            raise ValueError('Only draft invoices can be deleted')
        
        Invoice.delete(invoice_id)
        return True
