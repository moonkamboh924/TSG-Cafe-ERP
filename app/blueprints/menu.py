from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from ..models import MenuItem, MenuCategory, InventoryItem, MenuRecipe
from ..extensions import db
from ..auth import require_permissions, log_audit

bp = Blueprint('menu', __name__)

@bp.route('/')
@login_required
@require_permissions('menu.view')
def index():
    return render_template('menu/index.html')

@bp.route('/api/categories')
@login_required
@require_permissions('menu.view')
def list_categories():
    # MULTI-TENANT: Filter by business_id
    categories = MenuCategory.query.filter_by(business_id=current_user.business_id).order_by(MenuCategory.order_index).all()
    return jsonify([{
        'id': cat.id,
        'name': cat.name,
        'order_index': cat.order_index,
        'is_active': cat.is_active,
        'item_count': len(cat.items)
    } for cat in categories])

@bp.route('/api/categories', methods=['POST'])
@login_required
@require_permissions('menu.create')
def create_category():
    data = request.get_json()
    
    try:
        # MULTI-TENANT: Add business_id
        category = MenuCategory(
            business_id=current_user.business_id,
            name=data['name'],
            order_index=data.get('order_index', 0),
            is_active=data.get('is_active', True)
        )
        
        db.session.add(category)
        db.session.commit()
        
        log_audit('create', 'menu_category', category.id, {'name': category.name})
        
        return jsonify({
            'success': True,
            'category': {
                'id': category.id,
                'name': category.name,
                'order_index': category.order_index,
                'is_active': category.is_active
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@bp.route('/api/items')
@login_required
@require_permissions('menu.view')
def list_items():
    category_id = request.args.get('category_id', type=int)
    q = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    # MULTI-TENANT: Filter by business_id
    query = MenuItem.query.filter_by(business_id=current_user.business_id)
    
    if category_id:
        query = query.filter(MenuItem.category_id == category_id)
    
    if q:
        search_pattern = f'%{q}%'
        query = query.filter(MenuItem.name.ilike(search_pattern))
    
    items = query.order_by(MenuItem.id.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'items': [item.to_dict() for item in items.items],
        'total': items.total,
        'pages': items.pages,
        'current_page': page
    })

@bp.route('/api/items', methods=['POST'])
@login_required
@require_permissions('menu.create')
def create_item():
    data = request.get_json()
    
    try:
        # Generate SKU if not provided
        sku = data.get('sku') or MenuItem.generate_next_sku()
        
        # MULTI-TENANT: Add business_id
        item = MenuItem(
            business_id=current_user.business_id,
            sku=sku,
            name=data['name'],
            category_id=data['category_id'],
            price=data['price'],
            tax_rate=data.get('tax_rate', 16) / 100,  # Convert percentage to decimal
            is_active=data.get('is_active', True)
        )
        
        db.session.add(item)
        db.session.flush()  # Get the item ID
        
        # Add recipe items if provided
        recipe_items = data.get('recipe_items', [])
        for recipe_data in recipe_items:
            recipe = MenuRecipe(
                menu_item_id=item.id,
                inventory_item_id=recipe_data['inventory_item_id'],
                quantity=recipe_data['quantity'],
                unit=recipe_data['unit']
            )
            db.session.add(recipe)
        
        db.session.commit()
        
        log_audit('create', 'menu_item', item.id, {
            'sku': item.sku,
            'name': item.name,
            'price': float(item.price),
            'recipe_items_count': len(recipe_items)
        })
        
        return jsonify({
            'success': True,
            'item': item.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@bp.route('/api/items/<int:item_id>', methods=['PUT'])
@login_required
@require_permissions('menu.edit')
def update_item(item_id):
    item = MenuItem.query.get_or_404(item_id)
    data = request.get_json()
    
    try:
        item.name = data.get('name', item.name)
        item.category_id = data.get('category_id', item.category_id)
        item.price = data.get('price', item.price)
        item.tax_rate = data.get('tax_rate', item.tax_rate * 100) / 100  # Handle percentage conversion
        item.is_active = data.get('is_active', item.is_active)
        
        # Update recipe items if provided
        if 'recipe_items' in data:
            # Remove existing recipe items
            MenuRecipe.query.filter_by(menu_item_id=item.id).delete()
            
            # Add new recipe items
            recipe_items = data.get('recipe_items', [])
            for recipe_data in recipe_items:
                recipe = MenuRecipe(
                    menu_item_id=item.id,
                    inventory_item_id=recipe_data['inventory_item_id'],
                    quantity=recipe_data['quantity'],
                    unit=recipe_data['unit']
                )
                db.session.add(recipe)
        
        db.session.commit()
        
        log_audit('update', 'menu_item', item.id, {
            'sku': item.sku,
            'name': item.name,
            'price': float(item.price)
        })
        
        return jsonify({
            'success': True,
            'item': item.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@bp.route('/api/items/<int:item_id>', methods=['DELETE'])
@login_required
@require_permissions('menu.edit')
def delete_item(item_id):
    item = MenuItem.query.get_or_404(item_id)
    
    try:
        # Soft delete - mark as inactive
        item.is_active = False
        db.session.commit()
        
        log_audit('delete', 'menu_item', item.id, {
            'sku': item.sku,
            'name': item.name
        })
        
        return jsonify({
            'success': True,
            'message': 'Menu item deactivated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@bp.route('/api/items/<int:item_id>')
@login_required
@require_permissions('menu.view')
def get_item(item_id):
    item = MenuItem.query.get_or_404(item_id)
    return jsonify({
        'success': True,
        'item': item.to_dict()
    })

@bp.route('/api/next-sku')
@login_required
@require_permissions('menu.view')
def get_next_sku():
    next_sku = MenuItem.generate_next_sku()
    return jsonify({'sku': next_sku})

# Inventory Items API for Recipe Builder
@bp.route('/api/inventory-items')
@login_required
@require_permissions('menu.view')
def list_inventory_items():
    q = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    
    query = InventoryItem.query.filter(InventoryItem.is_active == True)
    
    if q:
        search_pattern = f'%{q}%'
        query = query.filter(InventoryItem.name.ilike(search_pattern))
    
    if category:
        query = query.filter(InventoryItem.category == category)
    
    items = query.order_by(InventoryItem.name).all()
    
    return jsonify({
        'items': [item.to_dict() for item in items]
    })

@bp.route('/api/inventory-categories')
@login_required
@require_permissions('menu.view')
def list_inventory_categories():
    categories = db.session.query(InventoryItem.category).filter(
        InventoryItem.is_active == True
    ).distinct().all()
    
    return jsonify({
        'categories': [cat[0] for cat in categories if cat[0]]
    })

# Recipe Management
@bp.route('/api/items/<int:item_id>/recipe')
@login_required
@require_permissions('menu.view')
def get_item_recipe(item_id):
    item = MenuItem.query.get_or_404(item_id)
    return jsonify({
        'success': True,
        'recipe': [recipe.to_dict() for recipe in item.recipe_items]
    })

@bp.route('/api/items/<int:item_id>/recipe', methods=['POST'])
@login_required
@require_permissions('menu.edit')
def update_item_recipe(item_id):
    item = MenuItem.query.get_or_404(item_id)
    data = request.get_json()
    
    try:
        # Remove existing recipe items
        MenuRecipe.query.filter_by(menu_item_id=item.id).delete()
        
        # Add new recipe items
        recipe_items = data.get('recipe_items', [])
        for recipe_data in recipe_items:
            recipe = MenuRecipe(
                menu_item_id=item.id,
                inventory_item_id=recipe_data['inventory_item_id'],
                quantity=recipe_data['quantity'],
                unit=recipe_data['unit']
            )
            db.session.add(recipe)
        
        db.session.commit()
        
        log_audit('update', 'menu_recipe', item.id, {
            'menu_item': item.name,
            'recipe_items_count': len(recipe_items)
        })
        
        return jsonify({
            'success': True,
            'message': 'Recipe updated successfully',
            'recipe': [recipe.to_dict() for recipe in item.recipe_items]
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# Inventory Sync for Order Processing
def deduct_inventory_for_order(menu_item_id, quantity):
    """
    Deduct inventory based on menu item recipe and order quantity
    Returns True if successful, False if insufficient stock
    """
    try:
        item = MenuItem.query.get(menu_item_id)
        if not item or not item.recipe_items:
            return True  # No recipe to deduct from
        
        # Check if sufficient stock exists for all ingredients
        for recipe in item.recipe_items:
            required_qty = recipe.quantity * quantity
            if recipe.inventory_item.current_stock < required_qty:
                return False  # Insufficient stock
        
        # Deduct from inventory
        for recipe in item.recipe_items:
            required_qty = recipe.quantity * quantity
            recipe.inventory_item.current_stock -= required_qty
        
        db.session.commit()
        return True
        
    except Exception as e:
        db.session.rollback()
        return False
