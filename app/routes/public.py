from flask import Blueprint, render_template
from app.models.product import Product

public_bp = Blueprint('public', __name__)


@public_bp.route('/')
def index():
    """Public landing page"""
    products = Product.get_all()
    # print(products)
    return render_template('public/index.html', products=products)


@public_bp.route('/about')
def about():
    """About page"""
    return render_template('public/about.html')


@public_bp.route('/free-invoice-maker')
@public_bp.route('/invoice-maker')
def free_invoice_maker():
    """Free invoice maker page"""
    return render_template('public/free_invoice_maker.html')


@public_bp.route('/contactus')
def contact():
    """Contact page"""
    return render_template('public/contact.html')


@public_bp.route('/careers')
@public_bp.route('/carrers')
def careers():
    """Careers page"""
    return render_template('public/careers.html')