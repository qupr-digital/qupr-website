from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from app.utils.auth import owner_required
from app.models.product import Product

products_bp = Blueprint('products', __name__)


@products_bp.route('/')
@owner_required
def list_products():
    """List all products"""
    search_query = request.args.get('q', '')
    
    if search_query:
        products = Product.search(search_query)
    else:
        products = Product.get_all()
    
    return render_template('products/list.html', products=products, search_query=search_query)


@products_bp.route('/<product_id>')
@owner_required
def view_product(product_id):
    """View product details"""
    product = Product.get_by_id(product_id)
    
    if not product:
        abort(404)
    
    return render_template('products/view.html', product=product)


@products_bp.route('/create', methods=['GET', 'POST'])
@owner_required
def create_product():
    """Create new product"""
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            hsn = request.form.get('hsn', '').strip()
            rate = request.form.get('rate', '').strip()
            tax_rate = request.form.get('tax_rate', '').strip()
            
            # Validation
            if not name:
                flash('Product name is required', 'error')
                return render_template('products/create.html')
            
            if not rate or not tax_rate:
                flash('Rate and tax rate are required', 'error')
                return render_template('products/create.html')
            
            try:
                rate = float(rate)
                tax_rate = float(tax_rate)
            except ValueError:
                flash('Rate and tax rate must be valid numbers', 'error')
                return render_template('products/create.html')
            
            # Create product
            product_id = Product.create(
                name=name,
                description=description,
                hsn=hsn,
                rate=rate,
                tax_rate=tax_rate
            )
            
            flash('Product created successfully', 'success')
            return redirect(url_for('products.view_product', product_id=product_id))
            
        except Exception as e:
            flash(f'Error creating product: {str(e)}', 'error')
    
    return render_template('products/create.html')


@products_bp.route('/<product_id>/edit', methods=['GET', 'POST'])
@owner_required
def edit_product(product_id):
    """Edit product details"""
    product = Product.get_by_id(product_id)
    
    if not product:
        abort(404)
    
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            hsn = request.form.get('hsn', '').strip()
            rate = request.form.get('rate', '').strip()
            tax_rate = request.form.get('tax_rate', '').strip()
            
            if not name:
                flash('Product name is required', 'error')
                return render_template('products/edit.html', product=product)
            
            try:
                rate = float(rate)
                tax_rate = float(tax_rate)
            except ValueError:
                flash('Rate and tax rate must be valid numbers', 'error')
                return render_template('products/edit.html', product=product)
            
            Product.update(
                product_id,
                name=name,
                description=description,
                hsn=hsn,
                rate=rate,
                tax_rate=tax_rate
            )
            
            flash('Product updated successfully', 'success')
            return redirect(url_for('products.view_product', product_id=product_id))
            
        except Exception as e:
            flash(f'Error updating product: {str(e)}', 'error')
    
    return render_template('products/edit.html', product=product)


@products_bp.route('/<product_id>/deactivate', methods=['POST'])
@owner_required
def deactivate_product(product_id):
    """Deactivate product"""
    try:
        Product.deactivate(product_id)
        flash('Product deactivated successfully', 'success')
        return redirect(url_for('products.list_products'))
        
    except Exception as e:
        flash(f'Error deactivating product: {str(e)}', 'error')
        return redirect(url_for('products.view_product', product_id=product_id))
