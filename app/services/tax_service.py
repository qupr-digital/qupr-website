from datetime import datetime
from flask import current_app


class TaxService:
    """Tax calculation service"""
    
    @staticmethod
    def calculate_item_tax(rate, quantity, tax_rate):
        """Calculate tax for a single item"""
        subtotal = float(rate) * float(quantity)
        tax_amount = subtotal * (float(tax_rate) / 100)
        total = subtotal + tax_amount
        
        return {
            'subtotal': round(subtotal, 2),
            'tax_amount': round(tax_amount, 2),
            'total': round(total, 2)
        }
    
    @staticmethod
    def calculate_invoice_totals(items):
        """Calculate invoice totals with tax breakup"""
        subtotal = 0
        tax_breakup = {}  # {tax_rate: amount}
        
        for item in items:
            item_subtotal = float(item['rate']) * float(item['quantity'])
            subtotal += item_subtotal
            
            tax_rate = float(item.get('tax_rate', 0))
            if tax_rate > 0:
                tax_amount = item_subtotal * (tax_rate / 100)
                if tax_rate not in tax_breakup:
                    tax_breakup[tax_rate] = 0
                tax_breakup[tax_rate] += tax_amount
        
        total_tax = sum(tax_breakup.values())
        total = subtotal + total_tax
        
        # Round all values
        subtotal = round(subtotal, 2)
        tax_breakup = {k: round(v, 2) for k, v in tax_breakup.items()}
        total = round(total, 2)
        
        return {
            'subtotal': subtotal,
            'tax_breakup': tax_breakup,
            'total_tax': round(total_tax, 2),
            'total': total
        }
    
    @staticmethod
    def split_gst(tax_rate, tax_amount):
        """Split GST into CGST and SGST"""
        half_rate = tax_rate / 2
        half_amount = tax_amount / 2
        
        return {
            'cgst_rate': round(half_rate, 2),
            'cgst_amount': round(half_amount, 2),
            'sgst_rate': round(half_rate, 2),
            'sgst_amount': round(half_amount, 2)
        }
