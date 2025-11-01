from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta, timezone
from sqlalchemy import func, and_
from ..models import Sale, AuditLog, Expense
from ..extensions import db
from ..auth import require_permissions

bp = Blueprint('dashboard', __name__)

@bp.route('/')
@login_required
@require_permissions('dashboard.view')
def index():
    return render_template('dashboard/index.html')

@bp.route('/api/dashboard/kpis/today')
@login_required
@require_permissions('dashboard.view')
def today_kpis():
    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)
    
    # MULTI-TENANT: Today's revenue = Cash + Online + Account Sales + Credit Payments Received
    revenue = db.session.query(func.sum(Sale.total)).filter(
        and_(
            Sale.business_id == current_user.business_id,
            func.date(Sale.created_at) == today,
            Sale.payment_method.in_(['cash', 'online', 'account']),
            ~Sale.invoice_no.like('%-PAY-%')
        )
    ).scalar() or 0
    
    # MULTI-TENANT: Add credit payments received today (actual cash flow from credit sales)
    from ..models import CreditPayment
    credit_payments_today = db.session.query(func.sum(CreditPayment.payment_amount)).filter(
        and_(
            CreditPayment.business_id == current_user.business_id,
            func.date(CreditPayment.payment_date) == today
        )
    ).scalar() or 0
    
    revenue += credit_payments_today
    
    # MULTI-TENANT: Yesterday's revenue for comparison (exclude credit sales and credit payment sales, add credit payments)
    yesterday_revenue = db.session.query(func.sum(Sale.total)).filter(
        and_(
            Sale.business_id == current_user.business_id,
            func.date(Sale.created_at) == yesterday,
            Sale.payment_method != 'credit',
            ~Sale.invoice_no.like('%-PAY-%')  # Exclude credit payment sale records
        )
    ).scalar() or 0
    
    # MULTI-TENANT: Add yesterday's credit payments
    yesterday_credit_payments = db.session.query(func.sum(CreditPayment.payment_amount)).filter(
        and_(
            CreditPayment.business_id == current_user.business_id,
            func.date(CreditPayment.payment_date) == yesterday
        )
    ).scalar() or 0
    
    yesterday_revenue += yesterday_credit_payments
    
    # Calculate revenue growth percentage
    if yesterday_revenue > 0:
        revenue_growth = round(((float(revenue) - float(yesterday_revenue)) / float(yesterday_revenue)) * 100, 1)
    else:
        revenue_growth = 0 if revenue == 0 else 100
    
    # MULTI-TENANT: Today's orders count (exclude credit payment sales)
    orders = Sale.query.filter(
        and_(
            Sale.business_id == current_user.business_id,
            func.date(Sale.created_at) == today,
            ~Sale.invoice_no.like('%-PAY-%')  # Exclude credit payment sale records
        )
    ).count()
    
    # MULTI-TENANT: Yesterday's orders for comparison (exclude credit payment sales)
    yesterday_orders = Sale.query.filter(
        and_(
            Sale.business_id == current_user.business_id,
            func.date(Sale.created_at) == yesterday,
            ~Sale.invoice_no.like('%-PAY-%')  # Exclude credit payment sale records
        )
    ).count()
    
    # Calculate orders growth percentage
    if yesterday_orders > 0:
        orders_growth = round(((orders - yesterday_orders) / yesterday_orders) * 100, 1)
    else:
        orders_growth = 0 if orders == 0 else 100
    
    # MULTI-TENANT: Today's alerts (low stock items)
    from app.models import InventoryItem
    alerts = InventoryItem.query.filter(
        and_(
            InventoryItem.business_id == current_user.business_id,
            InventoryItem.current_stock <= InventoryItem.min_stock_level
        )
    ).count()
    
    # MULTI-TENANT: Today's expenses
    expenses = db.session.query(func.sum(Expense.amount)).filter(
        and_(
            Expense.business_id == current_user.business_id,
            func.date(Expense.incurred_at) == today
        )
    ).scalar() or 0
    
    return jsonify({
        'revenue': float(revenue),
        'revenue_growth': revenue_growth,
        'orders': orders,
        'orders_growth': orders_growth,
        'alerts': alerts,
        'expenses': float(expenses)
    })

@bp.route('/api/dashboard/weekly-sales')
@login_required
@require_permissions('dashboard.view')
def weekly_sales():
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=6)
    
    # MULTI-TENANT: Get sales data for the week (all order types: Cash+Online+Account+Credit)
    sales_data = db.session.query(
        func.date(Sale.created_at).label('date'),
        func.sum(Sale.total).label('total')
    ).filter(
        and_(
            Sale.business_id == current_user.business_id,
            func.date(Sale.created_at) >= start_date,
            func.date(Sale.created_at) <= end_date,
            ~Sale.invoice_no.like('%-PAY-%')  # Exclude only credit payment tracking records
        )
    ).group_by(func.date(Sale.created_at)).all()
    
    # MULTI-TENANT: Get credit payments by date
    from ..models import CreditPayment
    credit_payments_data = db.session.query(
        func.date(CreditPayment.payment_date).label('date'),
        func.sum(CreditPayment.payment_amount).label('total')
    ).filter(
        and_(
            CreditPayment.business_id == current_user.business_id,
            func.date(CreditPayment.payment_date) >= start_date,
            func.date(CreditPayment.payment_date) <= end_date
        )
    ).group_by(func.date(CreditPayment.payment_date)).all()
    
    # Create a complete week with zeros for missing days
    sales_dict = {str(row.date): float(row.total) for row in sales_data}
    credit_payments_dict = {str(row.date): float(row.total) for row in credit_payments_data}
    
    labels = []
    data = []
    
    for i in range(7):
        date = start_date + timedelta(days=i)
        labels.append(date.strftime('%a'))  # Mon, Tue, etc.
        # Sales trend shows all orders (Cash+Online+Account+Credit) - no need to add credit payments separately
        daily_sales = sales_dict.get(str(date), 0)
        data.append(daily_sales)
    
    return jsonify({
        'labels': labels,
        'data': data
    })

@bp.route('/api/dashboard/weekly-summary')
@login_required
@require_permissions('dashboard.view')
def weekly_summary():
    """Get weekly summary data for dashboard"""
    try:
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=6)
        
        # MULTI-TENANT: Total revenue for the week = Cash + Online + Account Sales + Credit Payments Received
        total_revenue = db.session.query(func.sum(Sale.total)).filter(
            and_(
                Sale.business_id == current_user.business_id,
                func.date(Sale.created_at) >= start_date,
                func.date(Sale.created_at) <= end_date,
                Sale.payment_method.in_(['cash', 'online', 'account']),
                ~Sale.invoice_no.like('%-PAY-%')
            )
        ).scalar() or 0
        
        # MULTI-TENANT: Add credit payments received during the week
        from ..models import CreditPayment
        credit_payments_week = db.session.query(func.sum(CreditPayment.payment_amount)).filter(
            and_(
                CreditPayment.business_id == current_user.business_id,
                func.date(CreditPayment.payment_date) >= start_date,
                func.date(CreditPayment.payment_date) <= end_date
            )
        ).scalar() or 0
        
        total_revenue += credit_payments_week
        
        # MULTI-TENANT: Total orders for the week (exclude payment tracking records)
        total_orders = Sale.query.filter(
            and_(
                Sale.business_id == current_user.business_id,
                func.date(Sale.created_at) >= start_date,
                func.date(Sale.created_at) <= end_date,
                ~Sale.invoice_no.like('%-PAY-%')
            )
        ).count()
        
        # Average daily orders
        avg_daily_orders = round(total_orders / 7, 1) if total_orders > 0 else 0
        
        # Growth rate calculation (compare with previous week)
        prev_week_start = start_date - timedelta(days=7)
        prev_week_end = start_date - timedelta(days=1)
        
        # MULTI-TENANT: Previous week revenue
        prev_week_revenue = db.session.query(func.sum(Sale.total)).filter(
            and_(
                Sale.business_id == current_user.business_id,
                func.date(Sale.created_at) >= prev_week_start,
                func.date(Sale.created_at) <= prev_week_end,
                Sale.payment_method != 'credit'
            )
        ).scalar() or 0
        
        # MULTI-TENANT: Add previous week's credit payments
        prev_week_credit_payments = db.session.query(func.sum(CreditPayment.payment_amount)).filter(
            and_(
                CreditPayment.business_id == current_user.business_id,
                func.date(CreditPayment.payment_date) >= prev_week_start,
                func.date(CreditPayment.payment_date) <= prev_week_end
            )
        ).scalar() or 0
        
        prev_week_revenue += prev_week_credit_payments
        
        # Calculate growth rate
        if prev_week_revenue > 0:
            growth_rate = round(((total_revenue - prev_week_revenue) / prev_week_revenue) * 100, 1)
        else:
            growth_rate = 0 if total_revenue == 0 else 100
        
        # MULTI-TENANT: Peak day calculation
        peak_day_data = db.session.query(
            func.date(Sale.created_at).label('date'),
            func.sum(Sale.total).label('total')
        ).filter(
            and_(
                Sale.business_id == current_user.business_id,
                func.date(Sale.created_at) >= start_date,
                func.date(Sale.created_at) <= end_date
            )
        ).group_by(func.date(Sale.created_at)).order_by(func.sum(Sale.total).desc()).first()
        
        peak_day = 'N/A'
        peak_day_revenue = 0
        if peak_day_data and hasattr(peak_day_data, 'date') and hasattr(peak_day_data, 'total'):
            # Convert string date to datetime object if needed
            if isinstance(peak_day_data.date, str):
                from datetime import datetime as dt
                date_obj = dt.strptime(peak_day_data.date, '%Y-%m-%d').date()
                peak_day = date_obj.strftime('%A')
            else:
                peak_day = peak_day_data.date.strftime('%A')
            peak_day_revenue = float(peak_day_data.total)
        
        # Average daily revenue
        avg_daily_revenue = round(total_revenue / 7, 2) if total_revenue > 0 else 0
        
        return jsonify({
            'success': True,
            'total_revenue': float(total_revenue),
            'total_orders': total_orders,
            'avg_daily_orders': avg_daily_orders,
            'avg_daily_revenue': avg_daily_revenue,
            'growth_rate': growth_rate,
            'peak_day': peak_day,
            'peak_day_revenue': peak_day_revenue,
            'trend': f'+{growth_rate}%' if growth_rate > 0 else f'{growth_rate}%'
        })
        
    except Exception as e:
        try:
            from logging_config import log_dashboard_error
            log_dashboard_error(f"Weekly summary error: {str(e)}")
        except ImportError:
            pass
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/dashboard/activities')
@login_required
@require_permissions('dashboard.view')
def recent_activities():
    activities = AuditLog.query.order_by(
        AuditLog.created_at.desc()
    ).limit(25).all()
    
    return jsonify([activity.to_dict() for activity in activities])

@bp.route('/api/dashboard/revenue-details')
@login_required
@require_permissions('dashboard.view')
def revenue_details():
    """Get detailed revenue information for dashboard modal"""
    try:
        today = datetime.now(timezone.utc).date()
        
        # Today's total revenue = Cash + Online + Account Sales + Credit Payments Received
        total_revenue = db.session.query(func.sum(Sale.total)).filter(
            and_(
                func.date(Sale.created_at) == today,
                Sale.payment_method.in_(['cash', 'online', 'account']),
                ~Sale.invoice_no.like('%-PAY-%')
            )
        ).scalar() or 0
        
        # Add credit payments received today (actual cash flow from credit sales)
        from ..models import CreditPayment
        credit_payments_today = db.session.query(func.sum(CreditPayment.payment_amount)).filter(
            func.date(CreditPayment.payment_date) == today
        ).scalar() or 0
        
        total_revenue += credit_payments_today
        
        # Yesterday's revenue for comparison (exclude credit sales and credit payment sales, add credit payments)
        yesterday = today - timedelta(days=1)
        yesterday_revenue = db.session.query(func.sum(Sale.total)).filter(
            and_(
                func.date(Sale.created_at) == yesterday,
                Sale.payment_method != 'credit',
                ~Sale.invoice_no.like('%-PAY-%')  # Exclude credit payment sale records
            )
        ).scalar() or 0
        
        # Add yesterday's credit payments
        yesterday_credit_payments = db.session.query(func.sum(CreditPayment.payment_amount)).filter(
            func.date(CreditPayment.payment_date) == yesterday
        ).scalar() or 0
        
        yesterday_revenue += yesterday_credit_payments
        
        # Calculate growth percentage
        if yesterday_revenue > 0:
            growth_percentage = round(((float(total_revenue) - float(yesterday_revenue)) / float(yesterday_revenue)) * 100, 1)
        else:
            growth_percentage = 0 if total_revenue == 0 else 100
        
        # Cash vs Card sales breakdown (exclude credit payment sales)
        cash_sales = db.session.query(func.sum(Sale.total)).filter(
            and_(
                func.date(Sale.created_at) == today,
                Sale.payment_method == 'cash',
                ~Sale.invoice_no.like('%-PAY-%')  # Exclude credit payment sale records
            )
        ).scalar() or 0
        
        # Account sales (online payments, bank transfers, etc.) - exclude credit payment sales
        account_sales = db.session.query(func.sum(Sale.total)).filter(
            and_(
                func.date(Sale.created_at) == today,
                Sale.payment_method.in_(['online', 'bank_transfer', 'account']),
                ~Sale.invoice_no.like('%-PAY-%')  # Exclude credit payment sale records
            )
        ).scalar() or 0
        
        # Credit sales for today
        from ..models import CreditSale
        credit_sales = db.session.query(func.sum(Sale.total)).filter(
            and_(
                func.date(Sale.created_at) == today,
                Sale.payment_method == 'credit'
            )
        ).scalar() or 0
        
        # Credit payments received today (actual cash flow from credit payments table)
        credit_payments_today = db.session.query(func.sum(CreditPayment.payment_amount)).filter(
            func.date(CreditPayment.payment_date) == today
        ).scalar() or 0
        
        # Credit payments breakdown by method
        credit_payments_cash = db.session.query(func.sum(CreditPayment.payment_amount)).filter(
            and_(
                func.date(CreditPayment.payment_date) == today,
                CreditPayment.payment_method == 'cash'
            )
        ).scalar() or 0
        
        credit_payments_online = db.session.query(func.sum(CreditPayment.payment_amount)).filter(
            and_(
                func.date(CreditPayment.payment_date) == today,
                CreditPayment.payment_method.in_(['online', 'bank_transfer', 'account'])
            )
        ).scalar() or 0
        
        # Outstanding credit amount (total unpaid credit)
        from ..models import CreditPayment
        outstanding_credit = db.session.query(func.sum(CreditSale.remaining_amount)).filter(
            CreditSale.status.in_(['pending', 'partial'])
        ).scalar() or 0
        
        # MULTI-TENANT: Recent transactions (last 10)
        recent_transactions = Sale.query.filter(
            and_(
                Sale.business_id == current_user.business_id,
                func.date(Sale.created_at) == today
            )
        ).order_by(Sale.created_at.desc()).limit(10).all()
        
        transactions_data = []
        for sale in recent_transactions:
            transactions_data.append({
                'id': sale.id,
                'description': f"Order #{sale.invoice_no}",
                'amount': float(sale.total),
                'time': sale.created_at.strftime('%H:%M'),
                'payment_method': sale.payment_method.title(),
                'customer': sale.customer_name or 'Walk-in Customer'
            })
        
        return jsonify({
            'success': True,
            'total_revenue': float(total_revenue),
            'growth_percentage': growth_percentage,
            'cash_sales': float(cash_sales),
            'account_sales': float(account_sales),
            'credit_sales': float(credit_sales),
            'credit_payments': float(credit_payments_today),
            'credit_payments_cash': float(credit_payments_cash),
            'credit_payments_online': float(credit_payments_online),
            'outstanding_credit': float(outstanding_credit),
            'recent_transactions': transactions_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/dashboard/orders-details')
@login_required
@require_permissions('dashboard.view')
def orders_details():
    """Get detailed orders information for dashboard modal"""
    try:
        today = datetime.now(timezone.utc).date()
        
        # MULTI-TENANT: Today's total orders (exclude credit payment sales)
        total_orders = Sale.query.filter(
            and_(
                Sale.business_id == current_user.business_id,
                func.date(Sale.created_at) == today,
                ~Sale.invoice_no.like('%-PAY-%')  # Exclude credit payment sale records
            )
        ).count()
        
        # MULTI-TENANT: Calculate yesterday's orders for comparison (exclude credit payment sales)
        yesterday = today - timedelta(days=1)
        yesterday_orders = Sale.query.filter(
            and_(
                Sale.business_id == current_user.business_id,
                func.date(Sale.created_at) == yesterday,
                ~Sale.invoice_no.like('%-PAY-%')  # Exclude credit payment sale records
            )
        ).count()
        
        # Calculate growth percentage
        if yesterday_orders > 0:
            growth_percentage = round(((total_orders - yesterday_orders) / yesterday_orders) * 100, 1)
        else:
            growth_percentage = 0 if total_orders == 0 else 100
        
        # In this system, all sales are completed orders
        completed_orders = total_orders
        pending_orders = 0  # No pending orders in current system
        
        # Calculate completion rate
        completion_rate = 100 if total_orders > 0 else 0
        pending_rate = 0
        
        # MULTI-TENANT: Recent orders (last 10) - exclude credit payment sales
        recent_orders = Sale.query.filter(
            and_(
                Sale.business_id == current_user.business_id,
                func.date(Sale.created_at) == today,
                ~Sale.invoice_no.like('%-PAY-%')  # Exclude credit payment sale records
            )
        ).order_by(Sale.created_at.desc()).limit(10).all()
        
        orders_data = []
        for sale in recent_orders:
            orders_data.append({
                'id': sale.id,
                'invoice_no': sale.invoice_no,
                'customer': sale.customer_name or 'Walk-in Customer',
                'total': float(sale.total),
                'status': 'completed',
                'time': sale.created_at.strftime('%H:%M'),
                'items_count': len(sale.lines)
            })
        
        return jsonify({
            'success': True,
            'total_orders': total_orders,
            'completed_orders': completed_orders,
            'pending_orders': pending_orders,
            'growth_percentage': growth_percentage,
            'completion_rate': completion_rate,
            'pending_rate': pending_rate,
            'recent_orders': orders_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/dashboard/inventory-details')
@login_required
@require_permissions('dashboard.view')
def inventory_details():
    """Get detailed inventory information for dashboard modal"""
    try:
        from ..models import InventoryItem
        
        # MULTI-TENANT: Critical items (stock < 5)
        critical_items = InventoryItem.query.filter(
            and_(
                InventoryItem.business_id == current_user.business_id,
                InventoryItem.current_stock < 5
            )
        ).count()
        
        # MULTI-TENANT: Low stock items (stock < 10 but >= 5)
        low_stock = InventoryItem.query.filter(
            and_(
                InventoryItem.business_id == current_user.business_id,
                InventoryItem.current_stock >= 5,
                InventoryItem.current_stock < 10
            )
        ).count()
        
        # MULTI-TENANT: Well stocked items (stock >= 10)
        well_stocked = InventoryItem.query.filter(
            and_(
                InventoryItem.business_id == current_user.business_id,
                InventoryItem.current_stock >= 10
            )
        ).count()
        
        # MULTI-TENANT: Alert items (critical and low stock combined)
        alert_items_query = InventoryItem.query.filter(
            and_(
                InventoryItem.business_id == current_user.business_id,
                InventoryItem.current_stock < 10
            )
        ).order_by(InventoryItem.current_stock.asc()).limit(10).all()
        
        alert_items_data = []
        for item in alert_items_query:
            level = 'critical' if item.current_stock < 5 else 'low'
            alert_items_data.append({
                'id': item.id,
                'name': item.name,
                'category': item.category,
                'current_stock': float(item.current_stock),
                'unit': item.unit,
                'level': level
            })
        
        return jsonify({
            'success': True,
            'critical_items': critical_items,
            'low_stock': low_stock,
            'well_stocked': well_stocked,
            'alert_items': alert_items_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/dashboard/expense-details')
@login_required
@require_permissions('dashboard.view')
def expense_details():
    """Get detailed expense information for dashboard modal"""
    try:
        today = datetime.now(timezone.utc).date()
        
        # Today's total expenses
        total_expenses = db.session.query(func.sum(Expense.amount)).filter(
            func.date(Expense.incurred_at) == today
        ).scalar() or 0
        
        # Calculate yesterday's expenses for comparison
        yesterday = today - timedelta(days=1)
        yesterday_expenses = db.session.query(func.sum(Expense.amount)).filter(
            func.date(Expense.incurred_at) == yesterday
        ).scalar() or 0
        
        # Calculate growth percentage
        if yesterday_expenses > 0:
            growth_percentage = round(((float(total_expenses) - float(yesterday_expenses)) / float(yesterday_expenses)) * 100, 1)
        else:
            growth_percentage = 0 if total_expenses == 0 else 100
        
        # Expense breakdown by category
        expense_categories = db.session.query(
            Expense.category,
            func.sum(Expense.amount).label('total'),
            func.count(Expense.id).label('count')
        ).filter(
            func.date(Expense.incurred_at) == today
        ).group_by(Expense.category).all()
        
        categories_data = []
        for category, total, count in expense_categories:
            categories_data.append({
                'name': category,
                'total': float(total),
                'count': count
            })
        
        # MULTI-TENANT: Recent expenses (last 10)
        recent_expenses = Expense.query.filter(
            and_(
                Expense.business_id == current_user.business_id,
                func.date(Expense.incurred_at) == today
            )
        ).order_by(Expense.incurred_at.desc()).limit(10).all()
        
        expenses_data = []
        for expense in recent_expenses:
            expenses_data.append({
                'id': expense.id,
                'category': expense.category,
                'description': expense.note or 'No description',
                'amount': float(expense.amount),
                'time': expense.incurred_at.strftime('%H:%M'),
                'user': expense.user.full_name if expense.user else 'Unknown'
            })
        
        return jsonify({
            'success': True,
            'total_expenses': float(total_expenses),
            'growth_percentage': growth_percentage,
            'categories': categories_data,
            'recent_expenses': expenses_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
