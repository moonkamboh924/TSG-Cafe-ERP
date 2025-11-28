from flask import Blueprint, render_template, request, jsonify, session
from flask_login import login_required, current_user
from datetime import datetime, timezone
from sqlalchemy import and_
from ..models import MenuItem, MenuCategory, Sale, SaleLine, InventoryLot, CreditSale, InventoryItem, MenuRecipe
from ..extensions import db
from ..auth import require_permissions, log_audit
import uuid

bp = Blueprint('pos', __name__)

def validate_inventory_availability(menu_item_id, quantity):
    """
    Validate if sufficient inventory is available for a menu item order
    Returns True if sufficient stock, False otherwise
    """
    try:
        from flask_login import current_user
        # MULTI-TENANT: Verify item belongs to user's business
        item = MenuItem.query.filter_by(
            id=menu_item_id,
            business_id=current_user.business_id
        ).first()
        if not item or not item.recipe_items:
            return True  # No recipe to validate
        
        # Check if sufficient stock exists for all ingredients
        for recipe in item.recipe_items:
            required_qty = float(recipe.quantity) * quantity
            if float(recipe.inventory_item.current_stock) < required_qty:
                return False  # Insufficient stock
        
        return True
        
    except Exception as e:
        return False

def deduct_inventory_for_menu_item(menu_item_id, quantity):
    """
    Deduct inventory based on menu item recipe and order quantity
    Returns True if successful, False if insufficient stock or error
    """
    try:
        from flask_login import current_user
        # MULTI-TENANT: Verify item belongs to user's business
        item = MenuItem.query.filter_by(
            id=menu_item_id,
            business_id=current_user.business_id
        ).first()
        if not item or not item.recipe_items:
            return True  # No recipe to deduct from
        
        # Check if sufficient stock exists for all ingredients
        for recipe in item.recipe_items:
            required_qty = float(recipe.quantity) * quantity
            if float(recipe.inventory_item.current_stock) < required_qty:
                return False  # Insufficient stock
        
        # Deduct from inventory
        for recipe in item.recipe_items:
            required_qty = float(recipe.quantity) * quantity
            recipe.inventory_item.current_stock = float(recipe.inventory_item.current_stock) - required_qty
            
            # Log inventory deduction for audit
            log_audit('inventory_deduct', 'inventory_item', recipe.inventory_item.id, {
                'menu_item': item.name,
                'ingredient': recipe.inventory_item.name,
                'quantity_deducted': required_qty,
                'remaining_stock': float(recipe.inventory_item.current_stock)
            })
        
        return True
        
    except Exception as e:
        return False

@bp.route('/')
@login_required
@require_permissions('pos.view')
def index():
    return render_template('pos/index.html')

@bp.route('/api/menu')
@login_required
@require_permissions('pos.view')
def get_menu():
    category_id = request.args.get('category_id', type=int)
    search_query = request.args.get('q', '').strip()
    
    # MULTI-TENANT: Filter by business_id
    query = MenuItem.query.filter(
        MenuItem.business_id == current_user.business_id,
        MenuItem.is_active == True
    )
    
    if category_id:
        query = query.filter(MenuItem.category_id == category_id)
    
    if search_query:
        search_pattern = f'%{search_query}%'
        query = query.filter(MenuItem.name.ilike(search_pattern))
    
    items = query.join(MenuCategory).order_by(MenuCategory.order_index, MenuItem.name).all()
    
    return jsonify({
        'items': [item.to_dict() for item in items]
    })

@bp.route('/api/categories')
@login_required
@require_permissions('pos.view')
def get_categories():
    # MULTI-TENANT: Filter by business_id
    categories = MenuCategory.query.filter(
        MenuCategory.business_id == current_user.business_id,
        MenuCategory.is_active == True
    ).order_by(MenuCategory.order_index).all()
    
    return jsonify([{
        'id': cat.id,
        'name': cat.name,
        'order_index': cat.order_index
    } for cat in categories])

@bp.route('/api/check-inventory/<int:item_id>')
@login_required
@require_permissions('pos.view')
def check_inventory_availability(item_id):
    """Check inventory availability for a specific menu item"""
    quantity = request.args.get('quantity', 1, type=float)
    
    # MULTI-TENANT: Verify item belongs to user's business
    item = MenuItem.query.filter_by(
        id=item_id,
        business_id=current_user.business_id
    ).first_or_404()
    
    # Check if item has recipe
    if not item.recipe_items:
        return jsonify({
            'available': True,
            'message': 'No recipe defined - item available',
            'ingredients': []
        })
    
    # Check ingredient availability
    ingredients_status = []
    all_available = True
    
    for recipe in item.recipe_items:
        required_qty = float(recipe.quantity) * quantity
        current_stock = float(recipe.inventory_item.current_stock)
        is_available = current_stock >= required_qty
        
        if not is_available:
            all_available = False
        
        ingredients_status.append({
            'ingredient_name': recipe.inventory_item.name,
            'required_quantity': required_qty,
            'current_stock': current_stock,
            'unit': recipe.unit,
            'available': is_available
        })
    
    return jsonify({
        'available': all_available,
        'message': 'All ingredients available' if all_available else 'Insufficient stock for some ingredients',
        'ingredients': ingredients_status
    })

@bp.route('/api/cart', methods=['POST'])
@login_required
@require_permissions('pos.create')
def update_cart():
    data = request.get_json()
    
    if 'cart' not in session:
        session['cart'] = []
    
    session['cart'] = data.get('items', [])
    session.modified = True
    
    return jsonify({'success': True})

@bp.route('/api/cart', methods=['GET'])
@login_required
@require_permissions('pos.view')
def get_cart():
    return jsonify({
        'items': session.get('cart', [])
    })

@bp.route('/api/checkout', methods=['POST'])
@login_required
@require_permissions('pos.create')
def checkout():
    data = request.get_json()
    
    items = data.get('items', [])
    customer_name = data.get('customer_name', 'Walk-in Customer')
    customer_phone = data.get('customer_phone', '')
    table_number = data.get('table_number', '')
    payment_method = data.get('payment_method', 'cash')
    
    if not items:
        return jsonify({'error': 'No items in cart'}), 400
    
    try:
        # Generate unique invoice number in format YYMMDD-NN
        from app.utils.timezone_utils import get_current_time
        current_time = get_current_time()
        
        # Format: YYMMDD (Year-Year-Month-Month-Day-Day)
        date_part = current_time.strftime('%y%m%d')
        
        # Generate unique invoice number with proper sequential numbering
        max_attempts = 100
        invoice_no = None
        
        # MULTI-TENANT: Get the highest invoice number for today from current business
        existing_invoices = Sale.query.filter(
            Sale.business_id == current_user.business_id,
            Sale.invoice_no.like(f'{date_part}-%')
        ).order_by(Sale.invoice_no.desc()).all()
        
        # Find the next available number
        next_number = 1
        if existing_invoices:
            # Extract the highest number from existing invoices
            for sale in existing_invoices:
                try:
                    number_part = int(sale.invoice_no.split('-')[1])
                    if number_part >= next_number:
                        next_number = number_part + 1
                except (IndexError, ValueError):
                    continue
        
        # Try to find a unique invoice number
        for attempt in range(max_attempts):
            test_invoice_no = f'{date_part}-{next_number:02d}'
            
            # MULTI-TENANT: Check if this invoice number already exists in current business
            existing_sale = Sale.query.filter_by(business_id=current_user.business_id, invoice_no=test_invoice_no).first()
            if not existing_sale:
                invoice_no = test_invoice_no
                break
            
            # If it exists, try the next number
            next_number += 1
        
        if not invoice_no:
            return jsonify({'error': 'Unable to generate unique invoice number'}), 500
        
        # Calculate totals
        subtotal = 0
        sale_lines = []
        
        for item_data in items:
            item = MenuItem.query.get(item_data['item_id'])
            if not item:
                return jsonify({'error': f'Item not found: {item_data["item_id"]}'}), 400
            
            qty = float(item_data['qty'])
            unit_price = float(item.price)
            line_total = qty * unit_price
            
            subtotal += line_total
            
            sale_lines.append({
                'item_id': item.id,
                'qty': qty,
                'unit_price': unit_price,
                'line_total': line_total
            })
        
        # Get tax rate from global settings
        from app.models import SystemSetting
        tax_rate = float(SystemSetting.get_setting('tax_rate', 16)) / 100
        tax = subtotal * tax_rate
        total = subtotal + tax
        
        # Create sale record with timezone-aware timestamp
        from app.utils.timezone_utils import convert_local_to_utc
        utc_time = convert_local_to_utc(current_time)
        
        # MULTI-TENANT: Add business_id
        sale = Sale(
            business_id=current_user.business_id,
            invoice_no=invoice_no,
            customer_name=customer_name,
            customer_phone=customer_phone,
            table_number=table_number,
            subtotal=subtotal,
            tax=tax,
            total=total,
            payment_method=payment_method,
            user_id=current_user.id,
            created_at=utc_time.replace(tzinfo=None)  # Store as naive UTC in database
        )
        
        db.session.add(sale)
        db.session.flush()  # Get the sale ID
        
        # Validate inventory availability before processing
        for item_data in items:
            if not validate_inventory_availability(item_data['item_id'], float(item_data['qty'])):
                item = MenuItem.query.get(item_data['item_id'])
                return jsonify({'error': f'Insufficient inventory for {item.name if item else "item"}'}), 400
        
        # Create sale lines and update inventory
        for line_data in sale_lines:
            # MULTI-TENANT: Add business_id
            sale_line = SaleLine(
                business_id=current_user.business_id,
                sale_id=sale.id,
                item_id=line_data['item_id'],
                qty=line_data['qty'],
                unit_price=line_data['unit_price'],
                line_total=line_data['line_total']
            )
            db.session.add(sale_line)
            
            # Check if item has recipe - use recipe-based deduction, otherwise use legacy FIFO
            item = MenuItem.query.get(line_data['item_id'])
            if item and item.recipe_items:
                # Recipe-based inventory deduction
                if not deduct_inventory_for_menu_item(line_data['item_id'], line_data['qty']):
                    db.session.rollback()
                    return jsonify({'error': f'Failed to deduct inventory for {item.name if item else "item"}'}), 500
            else:
                # Legacy inventory deduction for items without recipes (FIFO)
                remaining_qty = line_data['qty']
                lots = InventoryLot.query.filter(
                    and_(
                        InventoryLot.item_id == line_data['item_id'],
                        InventoryLot.qty_on_hand > 0
                    )
                ).order_by(InventoryLot.received_at).all()
                
                for lot in lots:
                    if remaining_qty <= 0:
                        break
                    
                    if float(lot.qty_on_hand) >= remaining_qty:
                        lot.qty_on_hand = float(lot.qty_on_hand) - remaining_qty
                        remaining_qty = 0
                    else:
                        remaining_qty -= float(lot.qty_on_hand)
                        lot.qty_on_hand = 0
                
                # Update inventory item current stock for legacy items only
                inventory_item = InventoryItem.query.get(line_data['item_id'])
                if inventory_item:
                    inventory_item.current_stock = max(0, float(inventory_item.current_stock) - float(line_data['qty']))
        
        db.session.commit()
        
        # Handle credit orders
        if payment_method == 'credit':
            # Create credit sale record
            credit_sale = CreditSale(
                sale_id=sale.id,
                customer_name=customer_name,
                customer_phone=customer_phone,
                credit_amount=total,
                remaining_amount=total,
                created_by=current_user.id,
                notes=f"Credit order for table {table_number}" if table_number else "Credit order"
            )
            db.session.add(credit_sale)
            db.session.commit()
            
            # Log credit sale audit
            log_audit('create', 'credit_sale', credit_sale.id, {
                'invoice_no': invoice_no,
                'credit_amount': float(total),
                'customer': customer_name
            })
        
        # Clear cart
        session.pop('cart', None)
        
        # Log audit
        log_audit('create', 'sale', sale.id, {
            'invoice_no': invoice_no,
            'total': float(total),
            'customer': customer_name,
            'payment_method': payment_method
        })
        
        return jsonify({
            'success': True,
            'sale': sale.to_dict(),
            'is_credit': payment_method == 'credit'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/sales')
@login_required
@require_permissions('pos.view')
def get_sales():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    search = request.args.get('search', '').strip()
    
    # MULTI-TENANT: Filter by business_id and exclude credit payment sale records
    query = Sale.query.filter(
        Sale.business_id == current_user.business_id,
        ~Sale.invoice_no.like('%-PAY-%')
    )
    
    if date_from:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            query = query.filter(Sale.created_at >= date_from)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            query = query.filter(Sale.created_at <= date_to)
        except ValueError:
            pass
    
    if search:
        search_pattern = f'%{search}%'
        query = query.filter(
            Sale.invoice_no.ilike(search_pattern) |
            Sale.customer_name.ilike(search_pattern) |
            Sale.customer_phone.ilike(search_pattern)
        )
    
    sales = query.order_by(Sale.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'success': True,
        'sales': [sale.to_dict() for sale in sales.items],
        'pagination': {
            'total': sales.total,
            'pages': sales.pages,
            'page': page,
            'per_page': per_page,
            'has_prev': sales.has_prev,
            'has_next': sales.has_next,
            'prev_num': sales.prev_num,
            'next_num': sales.next_num
        }
    })

@bp.route('/api/sales/<int:sale_id>')
@login_required
@require_permissions('pos.view')
def get_sale(sale_id):
    # MULTI-TENANT: Verify sale belongs to user's business
    if current_user.role == 'system_administrator':
        sale = Sale.query.get_or_404(sale_id)
    else:
        sale = Sale.query.filter_by(
            id=sale_id,
            business_id=current_user.business_id
        ).first_or_404()
    return jsonify({
        'success': True,
        'sale': sale.to_dict()
    })

@bp.route('/api/sales/<int:sale_id>', methods=['PUT'])
@login_required
@require_permissions('pos.view')
def update_sale(sale_id):
    # MULTI-TENANT: Verify sale belongs to user's business
    if current_user.role == 'system_administrator':
        sale = Sale.query.get_or_404(sale_id)
    else:
        sale = Sale.query.filter_by(
            id=sale_id,
            business_id=current_user.business_id
        ).first_or_404()
    data = request.get_json()
    
    try:
        # Update sale details
        sale.customer_name = data.get('customer_name', sale.customer_name)
        sale.customer_phone = data.get('customer_phone', sale.customer_phone)
        sale.table_number = data.get('table_number', sale.table_number)
        sale.payment_method = data.get('payment_method', sale.payment_method)
        
        # Update items if provided
        if 'items' in data:
            # Remove existing sale lines
            SaleLine.query.filter_by(sale_id=sale.id).delete()
            
            # Recalculate totals
            subtotal = 0
            
            for item_data in data['items']:
                item = MenuItem.query.get(item_data['item_id'])
                if not item:
                    return jsonify({'error': f'Item not found: {item_data["item_id"]}'}), 400
                
                qty = float(item_data['qty'])
                unit_price = float(item.price)
                line_total = qty * unit_price
                
                subtotal += line_total
                
                sale_line = SaleLine(
                    sale_id=sale.id,
                    item_id=item.id,
                    qty=qty,
                    unit_price=unit_price,
                    line_total=line_total
                )
                db.session.add(sale_line)
            
            # Get tax rate from global settings
            from app.models import SystemSetting
            tax_rate = float(SystemSetting.get_setting('tax_rate', 16)) / 100
            tax = subtotal * tax_rate
            total = subtotal + tax
            
            sale.subtotal = subtotal
            sale.tax = tax
            sale.total = total
        
        db.session.commit()
        
        log_audit('update', 'sale', sale.id, {
            'invoice_no': sale.invoice_no,
            'total': float(sale.total)
        })
        
        return jsonify({
            'success': True,
            'sale': sale.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/sales/<int:sale_id>', methods=['DELETE'])
@login_required
@require_permissions('pos.delete')
def delete_sale(sale_id):
    # MULTI-TENANT: Verify sale belongs to user's business
    if current_user.role == 'system_administrator':
        sale = Sale.query.get_or_404(sale_id)
    else:
        sale = Sale.query.filter_by(
            id=sale_id,
            business_id=current_user.business_id
        ).first_or_404()
    
    try:
        # Delete sale lines first
        SaleLine.query.filter_by(sale_id=sale.id).delete()
        
        # Delete the sale
        db.session.delete(sale)
        db.session.commit()
        
        log_audit('delete', 'sale', sale.id, {
            'invoice_no': sale.invoice_no,
            'total': float(sale.total)
        })
        
        return jsonify({
            'success': True,
            'message': 'Sale deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/sales/<int:sale_id>/print')
@login_required
@require_permissions('pos.view')
def print_sale_bill(sale_id):
    """Print bill for a specific sale using bill template settings"""
    try:
        sale = Sale.query.get_or_404(sale_id)
        
        # Get bill template settings
        from app.models import BillTemplate
        template = BillTemplate.get_template('receipt')
        
        # Map font size to actual pixel values
        font_size_map = {
            'small': 10,
            'medium': 12,
            'large': 14,
            'extra-large': 16
        }
        
        font_size = font_size_map.get(template.font_size, 12)
        
        template_data = {
            'sale': sale,
            'header_name': template.header_name,
            'header_tagline': template.header_tagline,
            'logo_filename': template.logo_filename,
            'show_logo': template.show_logo,
            'show_order_number': template.show_order_number,
            'show_date_time': template.show_date_time,
            'show_cashier': template.show_cashier,
            'show_table': template.show_table,
            'show_tax': template.show_tax,
            'footer_message': template.footer_message,
            'show_qr_code': template.show_qr_code,
            'paper_size': template.paper_size,
            'font_size': font_size,
            'auto_cut': template.auto_cut
        }
        
        return render_template('pos/bill_print.html', **template_data)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/print-bill/<int:sale_id>')
@login_required
@require_permissions('pos.view')
def print_bill(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    
    # Get bill template settings and business name from global settings
    from ..models import BillTemplate, SystemSetting
    template = BillTemplate.query.filter_by(template_type='receipt').first()
    business_name = SystemSetting.get_setting('restaurant_name', 'My Business')
    
    template_data = {
        'sale': sale.to_dict(),
        'template_type': 'receipt',
        'header_name': template.header_name if template else business_name,
        'show_logo': template.show_logo if template else False,
        'logo_path': template.logo_path if template and template.logo_path else None,
        'footer_text': template.footer_text if template else 'Thank you for your visit!',
        'paper_size': template.paper_size if template else 'A4',
        'font_size': template.font_size if template else 12,
        'show_tax_details': template.show_tax_details if template else True,
        'show_customer_info': template.show_customer_info if template else True
    }
    
    return render_template('pos/bill_print.html', **template_data)

# Credit Sales Management
@bp.route('/api/credit-sales')
@login_required
@require_permissions('pos.view')
def get_credit_sales():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status', '')
    search = request.args.get('search', '').strip()
    
    # MULTI-TENANT: Filter by business_id
    query = CreditSale.query.filter_by(business_id=current_user.business_id)
    
    if status:
        query = query.filter(CreditSale.status == status)
    
    if search:
        search_pattern = f'%{search}%'
        query = query.filter(
            CreditSale.customer_name.ilike(search_pattern) |
            CreditSale.customer_phone.ilike(search_pattern)
        )
    
    credit_sales = query.order_by(CreditSale.credit_date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'success': True,
        'credit_sales': [cs.to_dict() for cs in credit_sales.items],
        'pagination': {
            'total': credit_sales.total,
            'pages': credit_sales.pages,
            'page': page,
            'per_page': per_page,
            'has_prev': credit_sales.has_prev,
            'has_next': credit_sales.has_next,
            'prev_num': credit_sales.prev_num,
            'next_num': credit_sales.next_num
        }
    })

@bp.route('/api/credit-sales/<int:credit_sale_id>')
@login_required
@require_permissions('pos.view')
def get_credit_sale(credit_sale_id):
    """Get individual credit sale details"""
    # MULTI-TENANT: Verify credit sale belongs to user's business
    if current_user.role == 'system_administrator':
        credit_sale = CreditSale.query.get_or_404(credit_sale_id)
    else:
        credit_sale = CreditSale.query.filter_by(
            id=credit_sale_id,
            business_id=current_user.business_id
        ).first_or_404()
    return jsonify({
        'success': True,
        'credit_sale': credit_sale.to_dict()
    })

@bp.route('/api/credit-sales/<int:credit_sale_id>', methods=['PUT'])
@login_required
@require_permissions('pos.edit')
def update_credit_sale(credit_sale_id):
    """Update credit sale details"""
    # MULTI-TENANT: Verify credit sale belongs to user's business
    if current_user.role == 'system_administrator':
        credit_sale = CreditSale.query.get_or_404(credit_sale_id)
    else:
        credit_sale = CreditSale.query.filter_by(
            id=credit_sale_id,
            business_id=current_user.business_id
        ).first_or_404()
    data = request.get_json()
    
    try:
        # Update credit sale details
        credit_sale.customer_name = data.get('customer_name', credit_sale.customer_name)
        credit_sale.customer_phone = data.get('customer_phone', credit_sale.customer_phone)
        credit_sale.notes = data.get('notes', credit_sale.notes)
        
        # Update credit amount if provided and no payments have been made
        if 'credit_amount' in data and credit_sale.paid_amount == 0:
            new_credit_amount = float(data['credit_amount'])
            credit_sale.credit_amount = new_credit_amount
            credit_sale.remaining_amount = new_credit_amount
        
        db.session.commit()
        
        log_audit('update', 'credit_sale', credit_sale.id, {
            'customer_name': credit_sale.customer_name,
            'credit_amount': float(credit_sale.credit_amount)
        })
        
        return jsonify({
            'success': True,
            'credit_sale': credit_sale.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/credit-sales/<int:credit_sale_id>', methods=['DELETE'])
@login_required
@require_permissions('pos.delete')
def delete_credit_sale(credit_sale_id):
    """Delete credit sale with optional force parameter"""
    # MULTI-TENANT: Verify credit sale belongs to user's business
    if current_user.role == 'system_administrator':
        credit_sale = CreditSale.query.get_or_404(credit_sale_id)
    else:
        credit_sale = CreditSale.query.filter_by(
            id=credit_sale_id,
            business_id=current_user.business_id
        ).first_or_404()
    force_delete = request.args.get('force', 'false').lower() == 'true'
    
    # Check if any payments have been made (unless force delete)
    if not force_delete and credit_sale.paid_amount > 0:
        return jsonify({'error': 'Cannot delete credit sale with existing payments. Use force delete if needed.'}), 400
    
    try:
        from ..models import CreditPayment
        
        # Get the associated sale
        sale = credit_sale.sale
        
        # If force delete, also remove all associated payments
        if force_delete:
            CreditPayment.query.filter_by(credit_sale_id=credit_sale.id).delete()
        
        # Delete credit sale first
        db.session.delete(credit_sale)
        
        # Delete associated sale and sale lines
        if sale:
            SaleLine.query.filter_by(sale_id=sale.id).delete()
            db.session.delete(sale)
        
        db.session.commit()
        
        log_audit('delete', 'credit_sale', credit_sale_id, {
            'customer_name': credit_sale.customer_name,
            'credit_amount': float(credit_sale.credit_amount),
            'force_delete': force_delete,
            'had_payments': credit_sale.paid_amount > 0
        })
        
        return jsonify({
            'success': True,
            'message': 'Credit sale deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/credit-sales/bulk-delete', methods=['POST'])
@login_required
@require_permissions('pos.delete')
def bulk_delete_credit_sales():
    """Bulk delete multiple credit sales"""
    data = request.get_json()
    credit_sale_ids = data.get('credit_sale_ids', [])
    force_delete = data.get('force', False)
    
    if not credit_sale_ids:
        return jsonify({'error': 'No credit sale IDs provided'}), 400
    
    try:
        from ..models import CreditPayment
        deleted_count = 0
        skipped_count = 0
        
        for credit_sale_id in credit_sale_ids:
            credit_sale = CreditSale.query.get(credit_sale_id)
            if not credit_sale:
                continue
                
            # Skip if has payments and not force delete
            if not force_delete and credit_sale.paid_amount > 0:
                skipped_count += 1
                continue
            
            # Get the associated sale
            sale = credit_sale.sale
            
            # If force delete, also remove all associated payments
            if force_delete:
                CreditPayment.query.filter_by(credit_sale_id=credit_sale.id).delete()
            
            # Delete credit sale
            db.session.delete(credit_sale)
            
            # Delete associated sale and sale lines
            if sale:
                SaleLine.query.filter_by(sale_id=sale.id).delete()
                db.session.delete(sale)
            
            deleted_count += 1
            
            log_audit('delete', 'credit_sale', credit_sale_id, {
                'customer_name': credit_sale.customer_name,
                'credit_amount': float(credit_sale.credit_amount),
                'bulk_delete': True,
                'force_delete': force_delete
            })
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Deleted {deleted_count} credit sales. Skipped {skipped_count} with payments.',
            'deleted_count': deleted_count,
            'skipped_count': skipped_count
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/credit-sales/<int:credit_sale_id>/pay', methods=['POST'])
@login_required
@require_permissions('pos.create')
def pay_credit_sale(credit_sale_id):
    from ..models import CreditPayment
    
    try:
        credit_sale = CreditSale.query.get_or_404(credit_sale_id)
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        payment_amount = float(data.get('payment_amount', 0))
        payment_method = data.get('payment_method', 'cash')
        notes = data.get('notes', '')
        
        if payment_amount <= 0:
            return jsonify({'error': 'Payment amount must be greater than 0'}), 400
        
        if payment_amount > float(credit_sale.remaining_amount):
            return jsonify({'error': 'Payment amount cannot exceed remaining amount'}), 400
    
    except Exception as e:
        return jsonify({'error': f'Validation error: {str(e)}'}), 400
    
    try:
        # Create payment record with business_id for multi-tenant tracking
        payment = CreditPayment(
            business_id=current_user.business_id,
            credit_sale_id=credit_sale.id,
            payment_amount=payment_amount,
            payment_method=payment_method,
            notes=notes,
            received_by=current_user.id
        )
        db.session.add(payment)
        db.session.flush()  # Get the payment ID
        
        # Update credit sale amounts and status
        credit_sale.paid_amount = float(credit_sale.paid_amount) + payment_amount
        credit_sale.remaining_amount = float(credit_sale.remaining_amount) - payment_amount
        
        if credit_sale.remaining_amount <= 0:
            credit_sale.status = 'paid'
        elif credit_sale.paid_amount > 0:
            credit_sale.status = 'partial'
        
        # Create a new sale record for the payment (for financial tracking)
        from app.utils.timezone_utils import get_current_time
        current_time = get_current_time()
        date_part = current_time.strftime('%y%m%d')
        
        # Generate unique payment invoice number using timestamp to ensure uniqueness
        import time
        timestamp = int(time.time() * 1000) % 100000  # Last 5 digits of timestamp
        payment_invoice_no = f'{date_part}-PAY-{credit_sale.id}-{timestamp}'
        
        # Ensure uniqueness by checking if it exists
        counter = 1
        original_invoice_no = payment_invoice_no
        while db.session.query(Sale).filter(Sale.invoice_no == payment_invoice_no).first():
            payment_invoice_no = f'{original_invoice_no}-{counter}'
            counter += 1
        
        # Get tax rate from system settings
        from app.models import SystemSetting
        tax_rate = float(SystemSetting.get_setting('tax_rate', 16)) / 100
        tax_multiplier = 1 + tax_rate
        
        # MULTI-TENANT: Add business_id to payment sale
        payment_sale = Sale(
            business_id=current_user.business_id,
            invoice_no=payment_invoice_no,
            customer_name=credit_sale.customer_name,
            customer_phone=credit_sale.customer_phone,
            table_number='',
            subtotal=payment_amount / tax_multiplier,
            tax=payment_amount - (payment_amount / tax_multiplier),
            total=payment_amount,
            payment_method=payment_method,
            user_id=current_user.id,
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(payment_sale)
        
        db.session.commit()
        
        # Log audit
        log_audit('create', 'credit_payment', payment.id, {
            'credit_sale_id': credit_sale.id,
            'payment_amount': payment_amount,
            'payment_method': payment_method,
            'customer': credit_sale.customer_name
        })
        
        return jsonify({
            'success': True,
            'payment': payment.to_dict(),
            'credit_sale': credit_sale.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
