from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta, timezone
from sqlalchemy import func, and_
from ..models import Sale, AuditLog, Expense, Business
from ..extensions import db
from ..auth import require_permissions
from ..utils.business_hours import get_business_day, get_business_day_range
from ..utils.currency_utils import get_system_currency, get_currency_symbol

bp = Blueprint('dashboard', __name__)

@bp.route('/')
@login_required
@require_permissions('dashboard.view')
def index():
    # Redirect system administrators to their dedicated interface
    if current_user.role == 'system_administrator':
        from flask import redirect, url_for
        return redirect(url_for('system_admin_dashboard.index'))
    
    currency_code = get_system_currency(current_user.business_id)
    currency_symbol = get_currency_symbol(currency_code)
    business = Business.query.get(current_user.business_id)
    return render_template('dashboard/index.html', 
                         currency_code=currency_code, 
                         currency_symbol=currency_symbol,
                         business=business)

@bp.route('/api/kpis/today')
@login_required
@require_permissions('dashboard.view')
def today_kpis():
    # Get current business day (accounts for new_day_start_time)
    today = get_business_day()
    yesterday = today - timedelta(days=1)
    
    # Get datetime ranges for filtering
    today_start, today_end = get_business_day_range(today)
    yesterday_start, yesterday_end = get_business_day_range(yesterday)
    
    # MULTI-TENANT: Today's revenue = Cash + Online + Account Sales + Credit Payments Received
    revenue = db.session.query(func.sum(Sale.total)).filter(
        and_(
            Sale.business_id == current_user.business_id,
            Sale.created_at >= today_start,
            Sale.created_at < today_end,
            Sale.payment_method.in_(['cash', 'online', 'account']),
            ~Sale.invoice_no.like('%-PAY-%')
        )
    ).scalar() or 0
    
    # MULTI-TENANT: Add credit payments received today (actual cash flow from credit sales)
    from ..models import CreditPayment
    credit_payments_today = db.session.query(func.sum(CreditPayment.payment_amount)).filter(
        and_(
            CreditPayment.business_id == current_user.business_id,
            CreditPayment.payment_date >= today_start,
            CreditPayment.payment_date < today_end
        )
    ).scalar() or 0
    
    revenue += credit_payments_today
    
    # MULTI-TENANT: Yesterday's revenue for comparison (exclude credit sales and credit payment sales, add credit payments)
    yesterday_revenue = db.session.query(func.sum(Sale.total)).filter(
        and_(
            Sale.business_id == current_user.business_id,
            Sale.created_at >= yesterday_start,
            Sale.created_at < yesterday_end,
            Sale.payment_method != 'credit',
            ~Sale.invoice_no.like('%-PAY-%')  # Exclude credit payment sale records
        )
    ).scalar() or 0
    
    # MULTI-TENANT: Add yesterday's credit payments
    yesterday_credit_payments = db.session.query(func.sum(CreditPayment.payment_amount)).filter(
        and_(
            CreditPayment.business_id == current_user.business_id,
            CreditPayment.payment_date >= yesterday_start,
            CreditPayment.payment_date < yesterday_end
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
            Sale.created_at >= today_start,
            Sale.created_at < today_end,
            ~Sale.invoice_no.like('%-PAY-%')  # Exclude credit payment sale records
        )
    ).count()
    
    # MULTI-TENANT: Yesterday's orders for comparison (exclude credit payment sales)
    yesterday_orders = Sale.query.filter(
        and_(
            Sale.business_id == current_user.business_id,
            Sale.created_at >= yesterday_start,
            Sale.created_at < yesterday_end,
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
            Expense.incurred_at >= today_start,
            Expense.incurred_at < today_end
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
    # Use business day to keep dashboard synchronized
    end_date = get_business_day()
    start_date = end_date - timedelta(days=6)
    
    # Build data for each day using business day ranges
    labels = []
    data = []
    
    for i in range(7):
        date = start_date + timedelta(days=i)
        labels.append(date.strftime('%a'))  # Mon, Tue, etc.
        
        # Get the business day range (converted to UTC for database queries)
        day_start, day_end = get_business_day_range(date)
        
        # MULTI-TENANT: Query sales for this specific business day
        daily_total = db.session.query(func.sum(Sale.total)).filter(
            and_(
                Sale.business_id == current_user.business_id,
                Sale.created_at >= day_start,
                Sale.created_at < day_end,
                ~Sale.invoice_no.like('%-PAY-%')  # Exclude only credit payment tracking records
            )
        ).scalar() or 0
        
        data.append(float(daily_total))
    
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
        # Use business day to keep dashboard synchronized
        end_date = get_business_day()
        start_date = end_date - timedelta(days=6)
        
        # Get datetime ranges for the entire week using business day logic
        week_start, _ = get_business_day_range(start_date)
        _, week_end = get_business_day_range(end_date)
        
        # MULTI-TENANT: Total revenue for the week = All sales (Cash+Online+Account+Credit)
        total_revenue = db.session.query(func.sum(Sale.total)).filter(
            and_(
                Sale.business_id == current_user.business_id,
                Sale.created_at >= week_start,
                Sale.created_at < week_end,
                ~Sale.invoice_no.like('%-PAY-%')
            )
        ).scalar() or 0
        
        # MULTI-TENANT: Total orders for the week (exclude payment tracking records)
        total_orders = Sale.query.filter(
            and_(
                Sale.business_id == current_user.business_id,
                Sale.created_at >= week_start,
                Sale.created_at < week_end,
                ~Sale.invoice_no.like('%-PAY-%')
            )
        ).count()
        
        # Average daily orders
        avg_daily_orders = round(total_orders / 7, 1) if total_orders > 0 else 0
        
        # Growth rate calculation (compare with previous week)
        prev_week_end = start_date - timedelta(days=1)
        prev_week_start = prev_week_end - timedelta(days=6)
        
        prev_week_start_dt, _ = get_business_day_range(prev_week_start)
        _, prev_week_end_dt = get_business_day_range(prev_week_end)
        
        # MULTI-TENANT: Previous week revenue
        prev_week_revenue = db.session.query(func.sum(Sale.total)).filter(
            and_(
                Sale.business_id == current_user.business_id,
                Sale.created_at >= prev_week_start_dt,
                Sale.created_at < prev_week_end_dt,
                ~Sale.invoice_no.like('%-PAY-%')
            )
        ).scalar() or 0
        
        # Calculate growth rate
        if prev_week_revenue > 0:
            growth_rate = round(((total_revenue - prev_week_revenue) / prev_week_revenue) * 100, 1)
        else:
            growth_rate = 0 if total_revenue == 0 else 100
        
        # MULTI-TENANT: Find peak day by checking each business day
        peak_day = 'N/A'
        peak_day_revenue = 0
        
        for i in range(7):
            date = start_date + timedelta(days=i)
            day_start, day_end = get_business_day_range(date)
            
            day_revenue = db.session.query(func.sum(Sale.total)).filter(
                and_(
                    Sale.business_id == current_user.business_id,
                    Sale.created_at >= day_start,
                    Sale.created_at < day_end,
                    ~Sale.invoice_no.like('%-PAY-%')
                )
            ).scalar() or 0
            
            if day_revenue > peak_day_revenue:
                peak_day_revenue = day_revenue
                peak_day = date.strftime('%A')
        
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
    # MULTI-TENANT: Filter audit logs by business_id
    # System admins see all, regular users see only their business
    if current_user.role == 'system_administrator':
        activities = AuditLog.query.order_by(
            AuditLog.created_at.desc()
        ).limit(25).all()
    else:
        activities = AuditLog.query.filter(
            AuditLog.business_id == current_user.business_id
        ).order_by(
            AuditLog.created_at.desc()
        ).limit(25).all()
    
    return jsonify([activity.to_dict() for activity in activities])

@bp.route('/api/dashboard/revenue-details')
@login_required
@require_permissions('dashboard.view')
def revenue_details():
    """Get detailed revenue information for dashboard modal"""
    try:
        # Get current business day (accounts for new_day_start_time)
        today = get_business_day()
        today_start, today_end = get_business_day_range(today)
        
        # Today's total revenue = Cash + Online + Account Sales + Credit Payments Received
        total_revenue = db.session.query(func.sum(Sale.total)).filter(
            and_(
                Sale.created_at >= today_start,
                Sale.created_at < today_end,
                Sale.payment_method.in_(['cash', 'online', 'account']),
                ~Sale.invoice_no.like('%-PAY-%')
            )
        ).scalar() or 0
        
        # Add credit payments received today (actual cash flow from credit sales)
        from ..models import CreditPayment
        credit_payments_today = db.session.query(func.sum(CreditPayment.payment_amount)).filter(
            and_(
                CreditPayment.payment_date >= today_start,
                CreditPayment.payment_date < today_end
            )
        ).scalar() or 0
        
        total_revenue += credit_payments_today
        
        # Yesterday's revenue for comparison (exclude credit sales and credit payment sales, add credit payments)
        yesterday = today - timedelta(days=1)
        yesterday_start, yesterday_end = get_business_day_range(yesterday)
        yesterday_revenue = db.session.query(func.sum(Sale.total)).filter(
            and_(
                Sale.created_at >= yesterday_start,
                Sale.created_at < yesterday_end,
                Sale.payment_method != 'credit',
                ~Sale.invoice_no.like('%-PAY-%')  # Exclude credit payment sale records
            )
        ).scalar() or 0
        
        # Add yesterday's credit payments
        yesterday_credit_payments = db.session.query(func.sum(CreditPayment.payment_amount)).filter(
            and_(
                CreditPayment.payment_date >= yesterday_start,
                CreditPayment.payment_date < yesterday_end
            )
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
                Sale.created_at >= today_start,
                Sale.created_at < today_end,
                Sale.payment_method == 'cash',
                ~Sale.invoice_no.like('%-PAY-%')  # Exclude credit payment sale records
            )
        ).scalar() or 0
        
        # Get cash credit payments to add to cash sales
        credit_payments_cash_temp = db.session.query(func.sum(CreditPayment.payment_amount)).filter(
            and_(
                CreditPayment.business_id == current_user.business_id,
                CreditPayment.payment_date >= today_start,
                CreditPayment.payment_date < today_end,
                CreditPayment.payment_method == 'cash'
            )
        ).scalar() or 0
        
        # Add cash credit payments to cash sales for proper Cash total
        cash_sales += credit_payments_cash_temp
        
        # Account sales (online payments, bank transfers, etc.) - exclude credit payment sales
        account_sales = db.session.query(func.sum(Sale.total)).filter(
            and_(
                Sale.created_at >= today_start,
                Sale.created_at < today_end,
                Sale.payment_method.in_(['online', 'bank_transfer', 'account']),
                ~Sale.invoice_no.like('%-PAY-%')  # Exclude credit payment sale records
            )
        ).scalar() or 0
        
        # Get online credit payments to add to account sales
        credit_payments_online_temp = db.session.query(func.sum(CreditPayment.payment_amount)).filter(
            and_(
                CreditPayment.business_id == current_user.business_id,
                CreditPayment.payment_date >= today_start,
                CreditPayment.payment_date < today_end,
                CreditPayment.payment_method.in_(['online', 'bank_transfer', 'account'])
            )
        ).scalar() or 0
        
        # Add online credit payments to account sales for proper Account total
        account_sales += credit_payments_online_temp
        
        # Credit sales for today
        from ..models import CreditSale
        credit_sales = db.session.query(func.sum(Sale.total)).filter(
            and_(
                Sale.business_id == current_user.business_id,
                Sale.created_at >= today_start,
                Sale.created_at < today_end,
                Sale.payment_method == 'credit'
            )
        ).scalar() or 0
        
        # Credit payments received today (actual cash flow from credit payments table)
        credit_payments_today = db.session.query(func.sum(CreditPayment.payment_amount)).filter(
            and_(
                CreditPayment.business_id == current_user.business_id,
                CreditPayment.payment_date >= today_start,
                CreditPayment.payment_date < today_end
            )
        ).scalar() or 0
        
        # Credit payments breakdown by method
        credit_payments_cash = db.session.query(func.sum(CreditPayment.payment_amount)).filter(
            and_(
                CreditPayment.business_id == current_user.business_id,
                CreditPayment.payment_date >= today_start,
                CreditPayment.payment_date < today_end,
                CreditPayment.payment_method == 'cash'
            )
        ).scalar() or 0
        
        credit_payments_online = db.session.query(func.sum(CreditPayment.payment_amount)).filter(
            and_(
                CreditPayment.business_id == current_user.business_id,
                CreditPayment.payment_date >= today_start,
                CreditPayment.payment_date < today_end,
                CreditPayment.payment_method.in_(['online', 'bank_transfer', 'account'])
            )
        ).scalar() or 0
        
        # Outstanding credit amount (total unpaid credit)
        from ..models import CreditPayment
        outstanding_credit = db.session.query(func.sum(CreditSale.remaining_amount)).filter(
            and_(
                CreditSale.business_id == current_user.business_id,
                CreditSale.status.in_(['pending', 'partial'])
            )
        ).scalar() or 0
        
        # MULTI-TENANT: Recent transactions (last 10)
        recent_transactions = Sale.query.filter(
            and_(
                Sale.business_id == current_user.business_id,
                Sale.created_at >= today_start,
                Sale.created_at < today_end
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
        # Get current business day (accounts for new_day_start_time)
        today = get_business_day()
        today_start, today_end = get_business_day_range(today)
        
        # MULTI-TENANT: Today's total orders (exclude credit payment sales)
        total_orders = Sale.query.filter(
            and_(
                Sale.business_id == current_user.business_id,
                Sale.created_at >= today_start,
                Sale.created_at < today_end,
                ~Sale.invoice_no.like('%-PAY-%')  # Exclude credit payment sale records
            )
        ).count()
        
        # MULTI-TENANT: Calculate yesterday's orders for comparison (exclude credit payment sales)
        yesterday = today - timedelta(days=1)
        yesterday_start, yesterday_end = get_business_day_range(yesterday)
        yesterday_orders = Sale.query.filter(
            and_(
                Sale.business_id == current_user.business_id,
                Sale.created_at >= yesterday_start,
                Sale.created_at < yesterday_end,
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
                Sale.created_at >= today_start,
                Sale.created_at < today_end,
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
        # Get current business day (accounts for new_day_start_time)
        today = get_business_day()
        today_start, today_end = get_business_day_range(today)
        
        # MULTI-TENANT: Today's total expenses
        total_expenses = db.session.query(func.sum(Expense.amount)).filter(
            and_(
                Expense.business_id == current_user.business_id,
                Expense.incurred_at >= today_start,
                Expense.incurred_at < today_end
            )
        ).scalar() or 0
        
        # MULTI-TENANT: Calculate yesterday's expenses for comparison
        yesterday = today - timedelta(days=1)
        yesterday_start, yesterday_end = get_business_day_range(yesterday)
        yesterday_expenses = db.session.query(func.sum(Expense.amount)).filter(
            and_(
                Expense.business_id == current_user.business_id,
                Expense.incurred_at >= yesterday_start,
                Expense.incurred_at < yesterday_end
            )
        ).scalar() or 0
        
        # Calculate growth percentage
        if yesterday_expenses > 0:
            growth_percentage = round(((float(total_expenses) - float(yesterday_expenses)) / float(yesterday_expenses)) * 100, 1)
        else:
            growth_percentage = 0 if total_expenses == 0 else 100
        
        # MULTI-TENANT: Expense breakdown by category
        expense_categories = db.session.query(
            Expense.category,
            func.sum(Expense.amount).label('total'),
            func.count(Expense.id).label('count')
        ).filter(
            and_(
                Expense.business_id == current_user.business_id,
                Expense.incurred_at >= today_start,
                Expense.incurred_at < today_end
            )
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
                Expense.incurred_at >= today_start,
                Expense.incurred_at < today_end
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
