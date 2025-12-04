from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date, timezone, timedelta
from sqlalchemy import func, and_
from ..models import Sale, Expense, DailyClosing, CreditPayment
from ..extensions import db
from ..auth import require_permissions, log_audit
from ..utils.timezone_utils import safe_fromisoformat
from ..utils.business_hours import get_business_day, get_business_day_range
from ..utils.currency_utils import get_system_currency, get_currency_symbol

bp = Blueprint('finance', __name__)

@bp.route('/')
@login_required
@require_permissions('finance.view')
def index():
    currency_code = get_system_currency(current_user.business_id)
    currency_symbol = get_currency_symbol(currency_code)
    return render_template('finance/index.html', currency_code=currency_code, currency_symbol=currency_symbol)

@bp.route('/api/summary')
@login_required
@require_permissions('finance.view')
def financial_summary():
    # Get current business day (accounts for new_day_start_time)
    today = get_business_day()
    today_start, today_end = get_business_day_range(today)
    
    # Today's revenue (excluding credit payment tracking sales + including credit payments received)
    # Today's revenue = Cash Sales + Account Sales + Credit Payments Received
    # Exclude credit payment tracking sales AND unpaid credit sales
    # MULTI-TENANT: Filter by business_id
    cash_account_sales = db.session.query(func.sum(Sale.total)).filter(
        Sale.business_id == current_user.business_id,
        Sale.created_at >= today_start,
        Sale.created_at < today_end,
        ~Sale.invoice_no.like('%-PAY-%'),
        Sale.payment_method.in_(['cash', 'online', 'account'])
    ).scalar() or 0
    
    # MULTI-TENANT: Filter by business_id
    credit_payments_revenue = db.session.query(func.sum(CreditPayment.payment_amount)).filter(
        CreditPayment.business_id == current_user.business_id,
        CreditPayment.payment_date >= today_start,
        CreditPayment.payment_date < today_end
    ).scalar() or 0
    
    today_revenue = float(cash_account_sales) + float(credit_payments_revenue)
    
    # Today's expenses
    # MULTI-TENANT: Filter by business_id
    today_expenses = db.session.query(func.sum(Expense.amount)).filter(
        Expense.business_id == current_user.business_id,
        Expense.incurred_at >= today_start,
        Expense.incurred_at < today_end
    ).scalar() or 0
    
    # Today's profit
    today_profit = float(today_revenue) - float(today_expenses)
    
    # This month's totals
    month_start = today.replace(day=1)
    
    # This month's revenue = Cash Sales + Account Sales + Credit Payments Received
    # Exclude credit payment tracking sales AND unpaid credit sales
    # MULTI-TENANT: Filter by business_id
    month_cash_account_sales = db.session.query(func.sum(Sale.total)).filter(
        Sale.business_id == current_user.business_id,
        func.date(Sale.created_at) >= month_start,
        ~Sale.invoice_no.like('%-PAY-%'),
        Sale.payment_method.in_(['cash', 'online', 'account'])
    ).scalar() or 0
    
    # MULTI-TENANT: Filter by business_id
    month_credit_payments = db.session.query(func.sum(CreditPayment.payment_amount)).filter(
        CreditPayment.business_id == current_user.business_id,
        func.date(CreditPayment.payment_date) >= month_start
    ).scalar() or 0
    
    month_revenue = float(month_cash_account_sales) + float(month_credit_payments)
    
    # MULTI-TENANT: Filter by business_id
    month_expenses = db.session.query(func.sum(Expense.amount)).filter(
        Expense.business_id == current_user.business_id,
        func.date(Expense.incurred_at) >= month_start
    ).scalar() or 0
    
    month_profit = float(month_revenue) - float(month_expenses)
    
    return jsonify({
        'today_revenue': float(today_revenue),
        'today_expenses': float(today_expenses),
        'net_profit': today_profit,
        'month_revenue': float(month_revenue),
        'month_expenses': float(month_expenses),
        'month_profit': month_profit
    })

@bp.route('/api/expenses')
@login_required
@require_permissions('finance.view')
def list_expenses():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    category = request.args.get('category')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    # MULTI-TENANT: Filter by business_id
    query = Expense.query.filter_by(business_id=current_user.business_id)
    
    if start_date:
        query = query.filter(func.date(Expense.incurred_at) >= start_date)
    
    if end_date:
        query = query.filter(func.date(Expense.incurred_at) <= end_date)
    
    if category:
        query = query.filter(Expense.category == category)
    
    expenses = query.order_by(Expense.incurred_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'success': True,
        'expenses': [expense.to_dict() for expense in expenses.items],
        'pagination': {
            'total': expenses.total,
            'pages': expenses.pages,
            'page': page,
            'per_page': per_page,
            'has_prev': expenses.has_prev,
            'has_next': expenses.has_next
        }
    })

@bp.route('/api/expenses', methods=['POST'])
@login_required
@require_permissions('finance.create')
def create_expense():
    data = request.get_json()
    
    try:
        # MULTI-TENANT: Add business_id
        expense = Expense(
            business_id=current_user.business_id,
            category=data['category'],
            note=data.get('note', ''),
            amount=data['amount'],
            incurred_at=safe_fromisoformat(data.get('incurred_at')),
            user_id=current_user.id
        )
        
        db.session.add(expense)
        db.session.commit()
        
        log_audit('create', 'expense', expense.id, {
            'category': expense.category,
            'amount': float(expense.amount)
        })
        
        return jsonify({
            'success': True,
            'expense': expense.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@bp.route('/api/daily-closing')
@login_required
@require_permissions('finance.view')
def list_daily_closings():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 30, type=int)
    
    # MULTI-TENANT: Filter by business_id
    closings = DailyClosing.query.filter_by(business_id=current_user.business_id).order_by(DailyClosing.date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'success': True,
        'closings': [{
            'id': closing.id,
            'date': closing.date.isoformat(),
            'opening_cash': float(closing.opening_cash),
            'sales_total': float(closing.sales_total),
            'expense_total': float(closing.expense_total),
            'closing_cash': float(closing.closing_cash),
            'user': closing.user.full_name,
            'created_at': closing.created_at.isoformat()
        } for closing in closings.items],
        'pagination': {
            'total': closings.total,
            'pages': closings.pages,
            'page': page,
            'per_page': per_page
        }
    })

@bp.route('/api/daily-closing', methods=['POST'])
@login_required
@require_permissions('finance.create')
def create_daily_closing():
    data = request.get_json()
    closing_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
    
    # Check if closing already exists for this date (for this business)
    existing = DailyClosing.query.filter_by(business_id=current_user.business_id, date=closing_date).first()
    if existing:
        return jsonify({'error': 'Daily closing already exists for this date'}), 400
    
    try:
        # Calculate totals for the day = Cash Sales + Account Sales + Credit Payments Received
        # Exclude credit payment tracking sales AND unpaid credit sales
        # MULTI-TENANT: Filter by business_id
        cash_account_sales_total = db.session.query(func.sum(Sale.total)).filter(
            Sale.business_id == current_user.business_id,
            func.date(Sale.created_at) == closing_date,
            ~Sale.invoice_no.like('%-PAY-%'),
            Sale.payment_method.in_(['cash', 'online', 'account'])
        ).scalar() or 0
        
        credit_payments_total = db.session.query(func.sum(CreditPayment.payment_amount)).filter(
            CreditPayment.business_id == current_user.business_id,
            func.date(CreditPayment.payment_date) == closing_date
        ).scalar() or 0
        
        sales_total = float(cash_account_sales_total) + float(credit_payments_total)
        
        # MULTI-TENANT: Filter by business_id
        expense_total = db.session.query(func.sum(Expense.amount)).filter(
            Expense.business_id == current_user.business_id,
            func.date(Expense.incurred_at) == closing_date
        ).scalar() or 0
        
        closing = DailyClosing(
            business_id=current_user.business_id,
            date=closing_date,
            opening_cash=data['opening_cash'],
            sales_total=sales_total,
            expense_total=expense_total,
            closing_cash=data['closing_cash'],
            notes=data.get('notes', ''),
            user_id=current_user.id
        )
        
        db.session.add(closing)
        db.session.commit()
        
        log_audit('create', 'daily_closing', closing.id, {
            'date': closing_date.isoformat(),
            'sales_total': float(sales_total),
            'closing_cash': float(data['closing_cash'])
        })
        
        return jsonify({'success': True}), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# Add missing endpoints
@bp.route('/api/expenses/<int:expense_id>')
@login_required
@require_permissions('finance.view')
def get_expense(expense_id):
    """Get a specific expense"""
    try:
        expense = Expense.query.get_or_404(expense_id)
        return jsonify({
            'success': True,
            'expense': expense.to_dict()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/expenses/<int:expense_id>', methods=['PUT'])
@login_required
@require_permissions('finance.edit')
def update_expense(expense_id):
    """Update an expense"""
    try:
        expense = Expense.query.get_or_404(expense_id)
        data = request.get_json()
        
        # Store old values for audit
        old_values = {
            'category': expense.category,
            'amount': float(expense.amount),
            'note': expense.note
        }
        
        # Update expense
        expense.category = data.get('category', expense.category)
        expense.amount = data.get('amount', expense.amount)
        expense.note = data.get('note', expense.note)
        if 'incurred_at' in data:
            expense.incurred_at = safe_fromisoformat(data['incurred_at'])
        
        db.session.commit()
        
        log_audit('update', 'expense', expense.id, {
            'old': old_values,
            'new': {
                'category': expense.category,
                'amount': float(expense.amount),
                'note': expense.note
            }
        })
        
        return jsonify({
            'success': True,
            'expense': expense.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@bp.route('/api/expenses/<int:expense_id>', methods=['DELETE'])
@login_required
@require_permissions('finance.delete')
def delete_expense(expense_id):
    """Delete an expense"""
    try:
        expense = Expense.query.get_or_404(expense_id)
        
        log_audit('delete', 'expense', expense.id, {
            'category': expense.category,
            'amount': float(expense.amount)
        })
        
        db.session.delete(expense)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@bp.route('/api/closing-data')
@login_required
@require_permissions('finance.view')
def get_closing_data():
    """Get sales and expense totals for a specific date"""
    date_str = request.args.get('date')
    if not date_str:
        return jsonify({'error': 'Date parameter required'}), 400
    
    try:
        closing_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Calculate totals for the day = Cash Sales + Account Sales + Credit Payments Received
        # Exclude credit payment tracking sales AND unpaid credit sales
        # MULTI-TENANT: Filter by business_id
        cash_account_sales_total = db.session.query(func.sum(Sale.total)).filter(
            Sale.business_id == current_user.business_id,
            func.date(Sale.created_at) == closing_date,
            ~Sale.invoice_no.like('%-PAY-%'),
            Sale.payment_method.in_(['cash', 'online', 'account'])
        ).scalar() or 0
        
        # MULTI-TENANT: Filter by business_id
        credit_payments_total = db.session.query(func.sum(CreditPayment.payment_amount)).filter(
            CreditPayment.business_id == current_user.business_id,
            func.date(CreditPayment.payment_date) == closing_date
        ).scalar() or 0
        
        sales_total = float(cash_account_sales_total) + float(credit_payments_total)
        
        # MULTI-TENANT: Filter by business_id
        expense_total = db.session.query(func.sum(Expense.amount)).filter(
            Expense.business_id == current_user.business_id,
            func.date(Expense.incurred_at) == closing_date
        ).scalar() or 0
        
        return jsonify({
            'success': True,
            'sales_total': float(sales_total),
            'expense_total': float(expense_total)
        })
        
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# Daily closing CRUD endpoints
@bp.route('/api/daily-closing/<int:closing_id>')
@login_required
@require_permissions('finance.view')
def get_daily_closing(closing_id):
    """Get a specific daily closing"""
    try:
        closing = DailyClosing.query.get_or_404(closing_id)
        return jsonify({
            'success': True,
            'closing': closing.to_dict()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/daily-closing/<int:closing_id>', methods=['PUT'])
@login_required
@require_permissions('finance.edit')
def update_daily_closing(closing_id):
    """Update a daily closing"""
    try:
        closing = DailyClosing.query.get_or_404(closing_id)
        data = request.get_json()
        
        # Store old values for audit
        old_values = {
            'date': closing.date.isoformat(),
            'opening_cash': float(closing.opening_cash),
            'closing_cash': float(closing.closing_cash),
            'sales_total': float(closing.sales_total)
        }
        
        # Update closing
        if 'date' in data:
            closing.date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        closing.opening_cash = data.get('opening_cash', closing.opening_cash)
        closing.closing_cash = data.get('closing_cash', closing.closing_cash)
        closing.sales_total = data.get('sales_total', closing.sales_total)
        
        db.session.commit()
        
        log_audit('update', 'daily_closing', closing.id, {
            'old': old_values,
            'new': {
                'date': closing.date.isoformat(),
                'opening_cash': float(closing.opening_cash),
                'closing_cash': float(closing.closing_cash),
                'sales_total': float(closing.sales_total)
            }
        })
        
        return jsonify({
            'success': True,
            'closing': closing.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@bp.route('/api/daily-closing/<int:closing_id>', methods=['DELETE'])
@login_required
@require_permissions('finance.delete')
def delete_daily_closing(closing_id):
    """Delete a daily closing"""
    try:
        closing = DailyClosing.query.get_or_404(closing_id)
        
        log_audit('delete', 'daily_closing', closing.id, {
            'date': closing.date.isoformat(),
            'sales_total': float(closing.sales_total),
            'closing_cash': float(closing.closing_cash)
        })
        
        db.session.delete(closing)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
