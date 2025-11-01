from flask import Blueprint, render_template, request, jsonify, make_response
from flask_login import login_required
from datetime import datetime, timedelta, timezone
from sqlalchemy import func, and_
from ..models import Sale, SaleLine, MenuItem, MenuCategory, Expense
from ..extensions import db
from ..auth import require_permissions
import csv
import io

bp = Blueprint('reports', __name__)

@bp.route('/')
@login_required
@require_permissions('reports.view')
def index():
    return render_template('reports/index.html')

@bp.route('/api/sales')
@login_required
@require_permissions('reports.view')
def sales_report():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    group_by = request.args.get('group_by', 'day')  # day, week, month
    
    # Sales report: Revenue = Cash+Online+Account sales + Credit payments received
    # Order count includes all order types (Cash+Online+Account+Credit) excluding payment tracking
    
    # MULTI-TENANT: Get cash/online/account sales by date
    from flask_login import current_user
    sales_query = db.session.query(
        func.date(Sale.created_at).label('date'),
        func.count(Sale.id).label('order_count'),
        func.sum(Sale.total).label('sales_total')
    ).filter(
        Sale.business_id == current_user.business_id,
        ~Sale.invoice_no.like('%-PAY-%'),
        Sale.payment_method.in_(['cash', 'online', 'account'])
    )
    
    # MULTI-TENANT: Get all orders count (including credit) by date for accurate order counting
    all_orders_query = db.session.query(
        func.date(Sale.created_at).label('date'),
        func.count(Sale.id).label('total_order_count')
    ).filter(
        Sale.business_id == current_user.business_id,
        ~Sale.invoice_no.like('%-PAY-%')
    )
    
    if start_date:
        sales_query = sales_query.filter(func.date(Sale.created_at) >= start_date)
        all_orders_query = all_orders_query.filter(func.date(Sale.created_at) >= start_date)
    
    if end_date:
        sales_query = sales_query.filter(func.date(Sale.created_at) <= end_date)
        all_orders_query = all_orders_query.filter(func.date(Sale.created_at) <= end_date)
    
    if group_by == 'day':
        sales_query = sales_query.group_by(func.date(Sale.created_at))
        all_orders_query = all_orders_query.group_by(func.date(Sale.created_at))
    elif group_by == 'week':
        sales_query = sales_query.group_by(func.strftime('%Y-%W', Sale.created_at))
        all_orders_query = all_orders_query.group_by(func.strftime('%Y-%W', Sale.created_at))
    elif group_by == 'month':
        sales_query = sales_query.group_by(func.strftime('%Y-%m', Sale.created_at))
        all_orders_query = all_orders_query.group_by(func.strftime('%Y-%m', Sale.created_at))
    
    sales_results = sales_query.order_by('date').all()
    orders_results = all_orders_query.order_by('date').all()
    
    # MULTI-TENANT: Get credit payments by date
    from ..models import CreditPayment
    credit_payments_query = db.session.query(
        func.date(CreditPayment.payment_date).label('date'),
        func.sum(CreditPayment.payment_amount).label('credit_payments')
    ).filter(
        CreditPayment.business_id == current_user.business_id
    )
    
    if start_date:
        credit_payments_query = credit_payments_query.filter(func.date(CreditPayment.payment_date) >= start_date)
    
    if end_date:
        credit_payments_query = credit_payments_query.filter(func.date(CreditPayment.payment_date) <= end_date)
    
    if group_by == 'day':
        credit_payments_query = credit_payments_query.group_by(func.date(CreditPayment.payment_date))
    elif group_by == 'week':
        credit_payments_query = credit_payments_query.group_by(func.strftime('%Y-%W', CreditPayment.payment_date))
    elif group_by == 'month':
        credit_payments_query = credit_payments_query.group_by(func.strftime('%Y-%m', CreditPayment.payment_date))
    
    credit_results = credit_payments_query.order_by('date').all()
    
    # MULTI-TENANT: Get total order value (all orders including credit) by date
    total_orders_query = db.session.query(
        func.date(Sale.created_at).label('date'),
        func.sum(Sale.total).label('total_order_value')
    ).filter(
        Sale.business_id == current_user.business_id,
        ~Sale.invoice_no.like('%-PAY-%')
    )
    
    if start_date:
        total_orders_query = total_orders_query.filter(func.date(Sale.created_at) >= start_date)
    
    if end_date:
        total_orders_query = total_orders_query.filter(func.date(Sale.created_at) <= end_date)
    
    if group_by == 'day':
        total_orders_query = total_orders_query.group_by(func.date(Sale.created_at))
    elif group_by == 'week':
        total_orders_query = total_orders_query.group_by(func.strftime('%Y-%W', Sale.created_at))
    elif group_by == 'month':
        total_orders_query = total_orders_query.group_by(func.strftime('%Y-%m', Sale.created_at))
    
    total_orders_results = total_orders_query.order_by('date').all()
    
    # Combine results by date
    data = {}
    
    # Add sales data
    for row in sales_results:
        date_str = str(row.date)
        data[date_str] = {
            'date': date_str,
            'order_count': 0,
            'total_sales': float(row.sales_total or 0),
            'total_order_value': 0,
            'avg_order_value': 0
        }
    
    # Add order counts
    for row in orders_results:
        date_str = str(row.date)
        if date_str not in data:
            data[date_str] = {
                'date': date_str,
                'order_count': 0,
                'total_sales': 0,
                'total_order_value': 0,
                'avg_order_value': 0
            }
        data[date_str]['order_count'] = row.total_order_count
        if row.total_order_count > 0:
            data[date_str]['avg_order_value'] = data[date_str]['total_sales'] / row.total_order_count
    
    # Add total order values
    for row in total_orders_results:
        date_str = str(row.date)
        if date_str not in data:
            data[date_str] = {
                'date': date_str,
                'order_count': 0,
                'total_sales': 0,
                'total_order_value': 0,
                'avg_order_value': 0
            }
        data[date_str]['total_order_value'] = float(row.total_order_value or 0)
    
    # Add credit payments to revenue
    for row in credit_results:
        date_str = str(row.date)
        if date_str not in data:
            data[date_str] = {
                'date': date_str,
                'order_count': 0,
                'total_sales': 0,
                'total_order_value': 0,
                'avg_order_value': 0
            }
        data[date_str]['total_sales'] += float(row.credit_payments or 0)
        # Recalculate avg order value with updated revenue
        if data[date_str]['order_count'] > 0:
            data[date_str]['avg_order_value'] = data[date_str]['total_sales'] / data[date_str]['order_count']
    
    return jsonify({
        'success': True,
        'data': list(data.values())
    })

@bp.route('/api/top-items')
@login_required
@require_permissions('reports.view')
def top_items_report():
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = request.args.get('limit', 10, type=int)
        
        # MULTI-TENANT: Filter by business_id
        from flask_login import current_user
        query = db.session.query(
            MenuItem.name,
            MenuCategory.name.label('category'),
            func.sum(SaleLine.qty).label('total_qty'),
            func.sum(SaleLine.line_total).label('total_revenue')
        ).select_from(SaleLine)\
         .join(MenuItem, SaleLine.item_id == MenuItem.id)\
         .join(MenuCategory, MenuItem.category_id == MenuCategory.id)\
         .join(Sale, SaleLine.sale_id == Sale.id)\
         .filter(Sale.business_id == current_user.business_id)
        
        if start_date:
            query = query.filter(func.date(Sale.created_at) >= start_date)
        
        if end_date:
            query = query.filter(func.date(Sale.created_at) <= end_date)
        
        results = query.group_by(MenuItem.id, MenuItem.name, MenuCategory.name)\
                      .order_by(func.sum(SaleLine.qty).desc())\
                      .limit(limit).all()
        
        return jsonify({
            'success': True,
            'data': [{
                'item_name': row.name,
                'category': row.category,
                'total_qty': float(row.total_qty),
                'total_revenue': float(row.total_revenue)
            } for row in results]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/expenses')
@login_required
@require_permissions('reports.view')
def expenses_report():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    group_by = request.args.get('group_by', 'category')
    
    # MULTI-TENANT: Filter by business_id
    from flask_login import current_user
    if group_by == 'category':
        query = db.session.query(
            Expense.category,
            func.count(Expense.id).label('count'),
            func.sum(Expense.amount).label('total_amount')
        ).filter(Expense.business_id == current_user.business_id).group_by(Expense.category)
    else:  # by date
        query = db.session.query(
            func.date(Expense.incurred_at).label('date'),
            func.count(Expense.id).label('count'),
            func.sum(Expense.amount).label('total_amount')
        ).filter(Expense.business_id == current_user.business_id).group_by(func.date(Expense.incurred_at))
    
    if start_date:
        query = query.filter(func.date(Expense.incurred_at) >= start_date)
    
    if end_date:
        query = query.filter(func.date(Expense.incurred_at) <= end_date)
    
    results = query.order_by('total_amount').all()
    
    return jsonify({
        'success': True,
        'data': [{
            'label': str(row[0]),  # category or date
            'count': row.count,
            'total_amount': float(row.total_amount)
        } for row in results]
    })

@bp.route('/api/export/sales')
@login_required
@require_permissions('reports.view')
def export_sales():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # MULTI-TENANT: Export sales: All order types (Cash + Online + Account + Credit) - exclude only payment tracking records
    from flask_login import current_user
    query = Sale.query.filter(
        Sale.business_id == current_user.business_id,
        ~Sale.invoice_no.like('%-PAY-%')
    )
    
    if start_date:
        query = query.filter(func.date(Sale.created_at) >= start_date)
    
    if end_date:
        query = query.filter(func.date(Sale.created_at) <= end_date)
    
    sales = query.order_by(Sale.created_at.desc()).all()
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'Invoice No', 'Date', 'Customer', 'Phone', 'Table', 
        'Subtotal', 'Tax', 'Total', 'Payment Method', 'Cashier'
    ])
    
    # Data
    for sale in sales:
        writer.writerow([
            sale.invoice_no,
            sale.created_at.strftime('%Y-%m-%d %H:%M'),
            sale.customer_name or '',
            sale.customer_phone or '',
            sale.table_number or '',
            float(sale.subtotal),
            float(sale.tax),
            float(sale.total),
            sale.payment_method,
            sale.user.full_name
        ])
    
    output.seek(0)
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=sales_report_{datetime.now(timezone.utc).strftime("%Y%m%d")}.csv'
    
    return response

@bp.route('/api/export/expenses')
@login_required
@require_permissions('reports.view')
def export_expenses():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # MULTI-TENANT: Filter by business_id
    from flask_login import current_user
    query = Expense.query.filter_by(business_id=current_user.business_id)
    
    if start_date:
        query = query.filter(func.date(Expense.incurred_at) >= start_date)
    
    if end_date:
        query = query.filter(func.date(Expense.incurred_at) <= end_date)
    
    expenses = query.order_by(Expense.incurred_at.desc()).all()
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'Date', 'Category', 'Amount', 'Description', 'Added By'
    ])
    
    # Data
    for expense in expenses:
        writer.writerow([
            expense.incurred_at.strftime('%Y-%m-%d'),
            expense.category,
            float(expense.amount),
            expense.note or '',
            expense.user.full_name
        ])
    
    output.seek(0)
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=expenses_report_{datetime.now(timezone.utc).strftime("%Y%m%d")}.csv'
    
    return response

@bp.route('/api/inventory')
@login_required
@require_permissions('reports.view')
def inventory_report():
    from ..models import InventoryItem
    from flask_login import current_user
    
    category = request.args.get('category')
    low_stock_only = request.args.get('low_stock_only', 'false').lower() == 'true'
    
    # MULTI-TENANT: Filter by business_id
    query = InventoryItem.query.filter(
        InventoryItem.business_id == current_user.business_id,
        InventoryItem.is_active == True
    )
    
    if category:
        query = query.filter(InventoryItem.category == category)
    
    if low_stock_only:
        query = query.filter(InventoryItem.current_stock <= InventoryItem.min_stock_level)
    
    items = query.order_by(InventoryItem.name).all()
    
    # Calculate totals
    total_items = len(items)
    total_value = sum(float(item.current_stock) * float(item.unit_cost) for item in items)
    low_stock_items = sum(1 for item in items if item.current_stock <= item.min_stock_level)
    
    return jsonify({
        'success': True,
        'items': [item.to_dict() for item in items],
        'summary': {
            'total_items': total_items,
            'total_value': total_value,
            'low_stock_items': low_stock_items
        }
    })

@bp.route('/api/export/inventory')
@login_required
@require_permissions('reports.view')
def export_inventory():
    from ..models import InventoryItem
    from flask_login import current_user
    
    category = request.args.get('category')
    low_stock_only = request.args.get('low_stock_only', 'false').lower() == 'true'
    
    # MULTI-TENANT: Filter by business_id
    query = InventoryItem.query.filter(
        InventoryItem.business_id == current_user.business_id,
        InventoryItem.is_active == True
    )
    
    if category:
        query = query.filter(InventoryItem.category == category)
    
    if low_stock_only:
        query = query.filter(InventoryItem.current_stock <= InventoryItem.min_stock_level)
    
    items = query.order_by(InventoryItem.name).all()
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'SKU', 'Name', 'Category', 'Unit', 'Current Stock', 
        'Min Stock', 'Max Stock', 'Unit Cost', 'Total Value', 'Status'
    ])
    
    # Data
    for item in items:
        total_value = float(item.current_stock) * float(item.unit_cost)
        status = 'Low Stock' if item.current_stock <= item.min_stock_level else 'Normal'
        
        writer.writerow([
            item.sku,
            item.name,
            item.category,
            item.unit,
            float(item.current_stock),
            float(item.min_stock_level),
            float(item.max_stock_level),
            float(item.unit_cost),
            total_value,
            status
        ])
    
    output.seek(0)
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=inventory_report_{datetime.now(timezone.utc).strftime("%Y%m%d")}.csv'
    
    return response
