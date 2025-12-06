from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timezone
from sqlalchemy import func
from ..models import MenuItem, InventoryLot, PurchaseOrder, PurchaseOrderLine, Supplier, InventoryItem
from ..extensions import db
from ..auth import require_permissions, log_audit
from ..utils.currency_utils import get_system_currency, get_currency_symbol

bp = Blueprint('inventory', __name__)

@bp.route('/')
@login_required
@require_permissions('inventory.view')
def index():
    currency_code = get_system_currency(current_user.business_id)
    currency_symbol = get_currency_symbol(currency_code)
    return render_template('inventory/index.html', currency_code=currency_code, currency_symbol=currency_symbol)

@bp.route('/api/items')
@login_required
@require_permissions('inventory.view')
def list_inventory():
    q = request.args.get('q', '').strip()
    low_stock = request.args.get('low_stock', type=bool)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    # MULTI-TENANT: Query inventory with stock levels filtered by business_id
    query = db.session.query(
        MenuItem.id,
        MenuItem.sku,
        MenuItem.name,
        func.coalesce(func.sum(InventoryLot.qty_on_hand), 0).label('stock_qty'),
        func.avg(InventoryLot.unit_cost).label('avg_cost')
    ).filter(
        MenuItem.business_id == current_user.business_id
    ).outerjoin(InventoryLot).group_by(MenuItem.id, MenuItem.sku, MenuItem.name)
    
    if q:
        search_pattern = f'%{q}%'
        query = query.filter(MenuItem.name.ilike(search_pattern))
    
    if low_stock:
        query = query.having(func.coalesce(func.sum(InventoryLot.qty_on_hand), 0) < 10)
    
    # Execute query with pagination
    items = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'items': [{
            'id': item.id,
            'sku': item.sku,
            'name': item.name,
            'stock_qty': float(item.stock_qty),
            'avg_cost': float(item.avg_cost) if item.avg_cost else 0,
            'is_low_stock': item.stock_qty < 10
        } for item in items.items],
        'total': items.total,
        'pages': items.pages,
        'current_page': page
    })

@bp.route('/api/items/<int:item_id>/stock', methods=['POST'])
@login_required
@require_permissions('inventory.edit')
def add_stock(item_id):
    # MULTI-TENANT: Verify item belongs to user's business
    item = MenuItem.query.filter_by(
        id=item_id,
        business_id=current_user.business_id
    ).first_or_404()
    data = request.get_json()
    
    try:
        lot = InventoryLot(
            business_id=current_user.business_id,
            item_id=item_id,
            qty_on_hand=data['qty'],
            unit_cost=data['unit_cost']
        )
        
        db.session.add(lot)
        db.session.commit()
        
        log_audit('stock_add', 'inventory_lot', lot.id, {
            'item_name': item.name,
            'qty': float(data['qty']),
            'unit_cost': float(data['unit_cost'])
        })
        
        return jsonify({'success': True}), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@bp.route('/api/purchase-orders')
@login_required
@require_permissions('inventory.view')
def list_purchase_orders():
    status = request.args.get('status', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # MULTI-TENANT: Filter by business_id
    query = PurchaseOrder.query.filter_by(business_id=current_user.business_id)
    
    if status:
        query = query.filter(PurchaseOrder.status == status)
    
    pos = query.order_by(PurchaseOrder.id.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'purchase_orders': [{
            'id': po.id,
            'po_number': po.po_number,
            'supplier_name': po.supplier.name,
            'date': po.date.isoformat(),
            'status': po.status,
            'total': float(po.total),
            'created_at': po.created_at.isoformat()
        } for po in pos.items],
        'total': pos.total,
        'pages': pos.pages,
        'current_page': page
    })

@bp.route('/api/suppliers')
@login_required
@require_permissions('inventory.view')
def list_suppliers():
    # MULTI-TENANT: Filter by business_id
    suppliers = Supplier.query.filter(
        Supplier.business_id == current_user.business_id,
        Supplier.is_active == True
    ).all()
    return jsonify([{
        'id': supplier.id,
        'name': supplier.name,
        'phone': supplier.phone,
        'email': supplier.email
    } for supplier in suppliers])

# InventoryItem CRUD endpoints
@bp.route('/api/inventory-items')
@login_required
@require_permissions('inventory.view')
def get_inventory_items():
    """Get inventory items with pagination and filters"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    category = request.args.get('category', '').strip()
    status = request.args.get('status', '').strip()
    search = request.args.get('search', '').strip()
    
    # MULTI-TENANT: Filter by business_id
    query = InventoryItem.query.filter_by(business_id=current_user.business_id)
    
    # Apply filters
    if category:
        category_pattern = f'%{category}%'
        query = query.filter(InventoryItem.category.ilike(category_pattern))
    
    if status == 'active':
        query = query.filter(InventoryItem.is_active == True)
    elif status == 'inactive':
        query = query.filter(InventoryItem.is_active == False)
    
    if search:
        search_pattern = f'%{search}%'
        query = query.filter(
            InventoryItem.name.ilike(search_pattern) |
            InventoryItem.sku.ilike(search_pattern)
        )
    
    # Calculate statistics for all items (not just current page)
    all_items = query.all()
    total_stock_value = sum((item.current_stock or 0) * (item.unit_cost or 0) for item in all_items)
    total_items_count = len(all_items)
    
    
    # Get paginated results
    items = query.order_by(InventoryItem.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'success': True,
        'items': [item.to_dict() for item in items.items],
        'statistics': {
            'total_stock_value': total_stock_value,
            'total_items': total_items_count
        },
        'pagination': {
            'total': items.total,
            'pages': items.pages,
            'page': page,
            'per_page': per_page,
            'has_prev': items.has_prev,
            'has_next': items.has_next,
            'prev_num': items.prev_num,
            'next_num': items.next_num
        }
    })

@bp.route('/api/inventory-items', methods=['POST'])
@login_required
@require_permissions('inventory.edit')
def create_inventory_item():
    """Create a new inventory item"""
    try:
        data = request.get_json()
        
        # MULTI-TENANT: Generate SKU if not provided
        sku = data.get('sku') or InventoryItem.generate_next_sku(current_user.business_id)
        
        # MULTI-TENANT: Add business_id
        item = InventoryItem(
            business_id=current_user.business_id,
            sku=sku,
            name=data['name'],
            category=data['category'],
            unit=data['unit'],
            current_stock=data.get('current_stock', 0),
            min_stock_level=data.get('min_stock_level', 0),
            max_stock_level=data.get('max_stock_level', 0),
            unit_cost=data.get('unit_cost', 0),
            is_active=data.get('is_active', True)
        )
        
        db.session.add(item)
        db.session.commit()
        
        log_audit('create', 'inventory_item', item.id, {
            'name': item.name,
            'category': item.category,
            'sku': item.sku
        })
        
        return jsonify({
            'success': True,
            'message': 'Inventory item created successfully',
            'item': item.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@bp.route('/api/inventory-items/<int:item_id>')
@login_required
@require_permissions('inventory.view')
def get_inventory_item(item_id):
    """Get a specific inventory item"""
    # MULTI-TENANT: Verify item belongs to user's business
    if current_user.role == 'system_administrator':
        item = InventoryItem.query.get_or_404(item_id)
    else:
        item = InventoryItem.query.filter_by(
            id=item_id,
            business_id=current_user.business_id
        ).first_or_404()
    return jsonify({
        'success': True,
        'item': item.to_dict()
    })

@bp.route('/api/inventory-items/<int:item_id>', methods=['PUT'])
@login_required
@require_permissions('inventory.edit')
def update_inventory_item(item_id):
    """Update an inventory item"""
    try:
        # MULTI-TENANT: Verify item belongs to user's business
        if current_user.role == 'system_administrator':
            item = InventoryItem.query.get_or_404(item_id)
        else:
            item = InventoryItem.query.filter_by(
                id=item_id,
                business_id=current_user.business_id
            ).first_or_404()
        data = request.get_json()
        
        # Store old values for audit
        old_values = {
            'name': item.name,
            'category': item.category,
            'unit': item.unit,
            'current_stock': float(item.current_stock),
            'min_stock_level': float(item.min_stock_level),
            'max_stock_level': float(item.max_stock_level),
            'unit_cost': float(item.unit_cost)
        }
        
        # Update fields
        item.name = data.get('name', item.name)
        item.category = data.get('category', item.category)
        item.unit = data.get('unit', item.unit)
        item.current_stock = data.get('current_stock', item.current_stock)
        item.min_stock_level = data.get('min_stock_level', item.min_stock_level)
        item.max_stock_level = data.get('max_stock_level', item.max_stock_level)
        item.unit_cost = data.get('unit_cost', item.unit_cost)
        item.is_active = data.get('is_active', item.is_active)
        
        db.session.commit()
        
        log_audit('update', 'inventory_item', item.id, {
            'old_values': old_values,
            'new_values': item.to_dict()
        })
        
        return jsonify({
            'success': True,
            'message': 'Inventory item updated successfully',
            'item': item.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@bp.route('/api/inventory-items/<int:item_id>', methods=['DELETE'])
@login_required
@require_permissions('inventory.delete')
def delete_inventory_item(item_id):
    """Delete an inventory item (soft delete by setting is_active=False)"""
    try:
        # MULTI-TENANT: Verify item belongs to user's business
        if current_user.role == 'system_administrator':
            item = InventoryItem.query.get_or_404(item_id)
        else:
            item = InventoryItem.query.filter_by(
                id=item_id,
                business_id=current_user.business_id
            ).first_or_404()
        
        # Soft delete
        item.is_active = False
        db.session.commit()
        
        log_audit('delete', 'inventory_item', item.id, {
            'name': item.name,
            'sku': item.sku
        })
        
        return jsonify({'success': True, 'message': 'Inventory item deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@bp.route('/api/categories')
@bp.route('/api/inventory-categories')
@login_required
@require_permissions('inventory.view')
def get_inventory_categories():
    """Get all unique inventory categories - shared across all businesses"""
    # Predefined categories
    predefined_categories = [
        'Vegetables',
        'Fruits',
        'Meat & Poultry',
        'Seafood',
        'Dairy Products',
        'Bakery Items',
        'Beverages',
        'Spices & Seasonings',
        'Oils & Fats',
        'Grains & Cereals',
        'Canned Goods',
        'Frozen Foods',
        'Cleaning Supplies',
        'Paper Products',
        'Packaging Materials',
        'Kitchen Equipment',
        'Other'
    ]
    
    # Get ALL existing categories from ALL businesses (system-wide)
    existing_categories = db.session.query(InventoryItem.category).distinct().filter(
        InventoryItem.is_active == True
    ).all()
    
    # Combine predefined and existing categories
    all_categories = set(predefined_categories)
    all_categories.update([cat[0] for cat in existing_categories if cat[0]])
    
    return jsonify({
        'success': True,
        'categories': sorted(list(all_categories))
    })

@bp.route('/api/inventory-units')
@login_required
@require_permissions('inventory.view')
def get_inventory_units():
    """Get comprehensive inventory units for all types of measurements"""
    units = [
        # Weight Units
        {'value': 'kg', 'label': 'Kilograms (kg)'},
        {'value': 'g', 'label': 'Grams (g)'},
        {'value': 'mg', 'label': 'Milligrams (mg)'},
        {'value': 'lbs', 'label': 'Pounds (lbs)'},
        {'value': 'oz', 'label': 'Ounces (oz)'},
        {'value': 'ton', 'label': 'Tons (ton)'},
        {'value': 'quintal', 'label': 'Quintal (100kg)'},
        {'value': 'maund', 'label': 'Maund (37.32kg)'},
        
        # Volume Units
        {'value': 'l', 'label': 'Liters (l)'},
        {'value': 'ml', 'label': 'Milliliters (ml)'},
        {'value': 'gal', 'label': 'Gallons (gal)'},
        {'value': 'qt', 'label': 'Quarts (qt)'},
        {'value': 'pt', 'label': 'Pints (pt)'},
        {'value': 'fl_oz', 'label': 'Fluid Ounces (fl oz)'},
        
        # Count Units
        {'value': 'pcs', 'label': 'Pieces (pcs)'},
        {'value': 'dozen', 'label': 'Dozen (dozen)'},
        {'value': 'pack', 'label': 'Packs (pack)'},
        {'value': 'box', 'label': 'Boxes (box)'},
        {'value': 'case', 'label': 'Cases (case)'},
        {'value': 'bag', 'label': 'Bags (bag)'},
        {'value': 'bottle', 'label': 'Bottles (bottle)'},
        {'value': 'can', 'label': 'Cans (can)'},
        {'value': 'jar', 'label': 'Jars (jar)'},
        {'value': 'tube', 'label': 'Tubes (tube)'},
        
        # Cooking Units
        {'value': 'cups', 'label': 'Cups (cups)'},
        {'value': 'tbsp', 'label': 'Tablespoons (tbsp)'},
        {'value': 'tsp', 'label': 'Teaspoons (tsp)'},
        {'value': 'pinch', 'label': 'Pinch (pinch)'},
        {'value': 'dash', 'label': 'Dash (dash)'},
        
        # Length Units
        {'value': 'm', 'label': 'Meters (m)'},
        {'value': 'cm', 'label': 'Centimeters (cm)'},
        {'value': 'mm', 'label': 'Millimeters (mm)'},
        {'value': 'ft', 'label': 'Feet (ft)'},
        {'value': 'in', 'label': 'Inches (in)'},
        
        # Area Units
        {'value': 'sqm', 'label': 'Square Meters (sq m)'},
        {'value': 'sqft', 'label': 'Square Feet (sq ft)'},
        
        # Special Units
        {'value': 'roll', 'label': 'Rolls (roll)'},
        {'value': 'sheet', 'label': 'Sheets (sheet)'},
        {'value': 'slice', 'label': 'Slices (slice)'},
        {'value': 'portion', 'label': 'Portions (portion)'},
        {'value': 'serving', 'label': 'Servings (serving)'}
    ]
    
    return jsonify({
        'success': True,
        'units': units
    })

@bp.route('/api/next-inventory-sku')
@login_required
@require_permissions('inventory.view')
def get_next_inventory_sku():
    """Get the next available inventory SKU"""
    # MULTI-TENANT: Generate SKU for current business
    return jsonify({
        'success': True,
        'sku': InventoryItem.generate_next_sku(current_user.business_id)
    })
