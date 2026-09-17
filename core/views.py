import json
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.conf import settings
from django.db import IntegrityError
from django.http import HttpResponseForbidden
from django.utils.crypto import constant_time_compare
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Sum, Count, F
from django.db import transaction
from django.utils import timezone
from .models import UserProfile, Category, Product, StockItem, StockTransaction, Order, OrderItem


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'registration/login.html')


@sensitive_post_parameters('password1', 'password2', 'setup_token')
@never_cache
@require_http_methods(['GET', 'POST'])
def register_superuser(request):
    authorized = request.user.is_authenticated and request.user.is_active and request.user.is_superuser
    token = settings.ADMIN_SETUP_TOKEN
    bootstrap = bool(token) and not User.objects.filter(is_superuser=True).exists()
    if not authorized and not bootstrap:
        return HttpResponseForbidden('Superuser registration is restricted to existing superusers.')

    form = UserCreationForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST':
        if not authorized and not constant_time_compare(request.POST.get('setup_token', ''), token):
            return HttpResponseForbidden('Invalid setup token.')
        if form.is_valid():
            try:
                with transaction.atomic():
                    if not authorized and User.objects.filter(is_superuser=True).exists():
                        return HttpResponseForbidden('Initial setup is already complete.')
                    user = form.save(commit=False)
                    user.is_staff = True
                    user.is_superuser = True
                    user.save()
                    UserProfile.objects.create(user=user, role='manager')
            except IntegrityError:
                form.add_error(None, 'Unable to create this account. Please choose another username.')
            else:
                messages.success(request, 'Superuser created. You can now log in.')
                return redirect('login')
    return render(request, 'registration/register_superuser.html', {
        'form': form,
        'requires_setup_token': not authorized,
    })


def logout_view(request):
    logout(request)
    return redirect('login')


def get_user_role(user):
    try:
        return user.profile.role
    except UserProfile.DoesNotExist:
        return None


@login_required
def dashboard(request):
    role = get_user_role(request.user)
    if role == 'manager':
        return redirect('manager_dashboard')
    elif role == 'waiter':
        return redirect('waiter_dashboard')
    elif role == 'stock_manager':
        return redirect('stock_dashboard')
    return redirect('login')


@login_required
def manager_dashboard(request):
    if get_user_role(request.user) != 'manager':
        return redirect('dashboard')
    today = timezone.now().date()
    active_orders = Order.objects.exclude(status__in=['paid', 'cancelled']).count()
    total_orders_today = Order.objects.filter(created_at__date=today).count()
    paid_today = Order.objects.filter(paid_at__date=today, status='paid')
    total_revenue_today = paid_today.aggregate(total=Sum('total_amount'))['total'] or 0
    revenue_cash = paid_today.filter(payment_method='cash').aggregate(t=Sum('total_amount'))['t'] or 0
    revenue_telebirr = paid_today.filter(payment_method='telebirr').aggregate(t=Sum('total_amount'))['t'] or 0
    revenue_cbe = paid_today.filter(payment_method='cbe').aggregate(t=Sum('total_amount'))['t'] or 0
    revenue_card = paid_today.filter(payment_method='card').aggregate(t=Sum('total_amount'))['t'] or 0
    paid_count_today = paid_today.count()
    categories = Category.objects.all()
    recent_orders = Order.objects.select_related('waiter').all()[:10]

    context = {
        'active_orders': active_orders,
        'total_orders_today': total_orders_today,
        'total_revenue_today': total_revenue_today,
        'revenue_cash': revenue_cash,
        'revenue_telebirr': revenue_telebirr,
        'revenue_cbe': revenue_cbe,
        'revenue_card': revenue_card,
        'paid_count_today': paid_count_today,
        'categories': categories,
        'recent_orders': recent_orders,
    }
    return render(request, 'core/manager_dashboard.html', context)


@login_required
def category_list(request):
    if get_user_role(request.user) != 'manager':
        return redirect('dashboard')
    categories = Category.objects.all()
    return render(request, 'core/category_list.html', {'categories': categories})


@login_required
def category_create(request):
    if get_user_role(request.user) != 'manager':
        return redirect('dashboard')
    if request.method == 'POST':
        Category.objects.create(
            name=request.POST['name'],
            description=request.POST.get('description', ''),
            sort_order=int(request.POST.get('sort_order', 0)),
            is_active='is_active' in request.POST,
        )
        messages.success(request, 'Category created successfully.')
        return redirect('category_list')
    return render(request, 'core/category_form.html', {'category': None})


@login_required
def category_edit(request, pk):
    if get_user_role(request.user) != 'manager':
        return redirect('dashboard')
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        category.name = request.POST['name']
        category.description = request.POST.get('description', '')
        category.sort_order = int(request.POST.get('sort_order', 0))
        category.is_active = 'is_active' in request.POST
        category.save()
        messages.success(request, 'Category updated successfully.')
        return redirect('category_list')
    return render(request, 'core/category_form.html', {'category': category})


@login_required
def category_delete(request, pk):
    if get_user_role(request.user) != 'manager':
        return redirect('dashboard')
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        category.delete()
        messages.success(request, 'Category deleted.')
        return redirect('category_list')
    return render(request, 'core/category_confirm_delete.html', {'category': category})


@login_required
def product_list(request):
    if get_user_role(request.user) != 'manager':
        return redirect('dashboard')
    category_id = request.GET.get('category')
    products = Product.objects.select_related('category').all()
    if category_id:
        products = products.filter(category_id=category_id)
    categories = Category.objects.filter(is_active=True)
    return render(request, 'core/product_list.html', {
        'products': products,
        'categories': categories,
        'selected_category': category_id,
    })


@login_required
def product_create(request):
    if get_user_role(request.user) != 'manager':
        return redirect('dashboard')
    categories = Category.objects.filter(is_active=True)
    if request.method == 'POST':
        product = Product.objects.create(
            name=request.POST['name'],
            category_id=request.POST['category'],
            price=request.POST['price'],
            description=request.POST.get('description', ''),
            is_available='is_available' in request.POST,
        )
        messages.success(request, 'Product created successfully.')
        return redirect('product_list')
    return render(request, 'core/product_form.html', {'product': None, 'categories': categories})


@login_required
def product_edit(request, pk):
    if get_user_role(request.user) != 'manager':
        return redirect('dashboard')
    product = get_object_or_404(Product, pk=pk)
    categories = Category.objects.filter(is_active=True)
    if request.method == 'POST':
        product.name = request.POST['name']
        product.category_id = request.POST['category']
        product.price = request.POST['price']
        product.description = request.POST.get('description', '')
        product.is_available = 'is_available' in request.POST
        product.save()
        messages.success(request, 'Product updated successfully.')
        return redirect('product_list')
    return render(request, 'core/product_form.html', {
        'product': product,
        'categories': categories,
    })


@login_required
def product_delete(request, pk):
    if get_user_role(request.user) != 'manager':
        return redirect('dashboard')
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Product deleted.')
        return redirect('product_list')
    return render(request, 'core/product_confirm_delete.html', {'product': product})


@login_required
def waiter_dashboard(request):
    if get_user_role(request.user) != 'waiter':
        return redirect('dashboard')
    today = timezone.now().date()
    active_orders = Order.objects.filter(
        waiter=request.user
    ).exclude(status__in=['paid', 'cancelled']).select_related()
    today_orders = Order.objects.filter(
        waiter=request.user, created_at__date=today
    ).select_related()
    return render(request, 'core/waiter_dashboard.html', {
        'active_orders': active_orders,
        'today_orders': today_orders,
    })


@login_required
def waiter_daily_report(request):
    if get_user_role(request.user) != 'waiter':
        return redirect('dashboard')

    report_date_str = request.GET.get('date', '')
    if report_date_str:
        try:
            report_date = timezone.datetime.strptime(report_date_str, '%Y-%m-%d').date()
        except ValueError:
            report_date = timezone.now().date()
    else:
        report_date = timezone.now().date()

    my_paid_orders = Order.objects.filter(
        waiter=request.user, status='paid', paid_at__date=report_date
    ).select_related().prefetch_related('items__product')

    my_all_orders = Order.objects.filter(
        waiter=request.user, created_at__date=report_date
    )

    total_revenue = my_paid_orders.aggregate(t=Sum('total_amount'))['t'] or Decimal('0')
    total_orders = my_all_orders.count()
    paid_count = my_paid_orders.count()
    cancelled_count = my_all_orders.filter(status='cancelled').count()

    revenue_by_method = {}
    for method, label in Order.PAYMENT_METHOD_CHOICES:
        if method:
            rev = my_paid_orders.filter(payment_method=method).aggregate(t=Sum('total_amount'))['t'] or Decimal('0')
            count = my_paid_orders.filter(payment_method=method).count()
            revenue_by_method[method] = {'label': label, 'total': rev, 'count': count}

    product_sales = {}
    for oi in OrderItem.objects.filter(order__in=my_paid_orders).select_related('product'):
        pid = oi.product_id
        if pid not in product_sales:
            product_sales[pid] = {'name': oi.product.name, 'quantity': 0, 'revenue': Decimal('0')}
        product_sales[pid]['quantity'] += oi.quantity
        product_sales[pid]['revenue'] += oi.subtotal
    product_sales_list = sorted(product_sales.values(), key=lambda x: x['quantity'], reverse=True)

    context = {
        'report_date': report_date,
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'paid_count': paid_count,
        'cancelled_count': cancelled_count,
        'revenue_by_method': revenue_by_method,
        'product_sales': product_sales_list,
        'paid_orders': my_paid_orders,
    }
    return render(request, 'core/waiter_daily_report.html', context)


@login_required
def create_order(request):
    if get_user_role(request.user) != 'waiter':
        return redirect('dashboard')
    if request.method == 'POST':
        table_number = request.POST.get('table_number', '')
        notes = request.POST.get('notes', '')
        items_json = request.POST.get('items', '[]')
        items = json.loads(items_json)

        if not items:
            messages.error(request, 'Please add items to the order.')
            return redirect('create_order')

        order = Order.objects.create(
            waiter=request.user,
            table_number=table_number,
            notes=notes,
        )

        for item in items:
            product = Product.objects.get(pk=item['product_id'])
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=item['quantity'],
                price_at_time=product.price,
                notes=item.get('notes', ''),
            )

        order.calculate_total()
        messages.success(request, f'Order #{order.id} created successfully.')
        return redirect('waiter_dashboard')

    categories = Category.objects.filter(is_active=True).prefetch_related('products')
    return render(request, 'core/create_order.html', {'categories': categories})


@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order.objects.select_related('waiter').prefetch_related('items__product'), pk=pk)
    role = get_user_role(request.user)
    if role == 'waiter' and order.waiter != request.user:
        return redirect('waiter_dashboard')
    return render(request, 'core/order_detail.html', {'order': order, 'role': role})


@login_required
def update_order_status(request, pk):
    if request.method != 'POST':
        return redirect('dashboard')
    order = get_object_or_404(Order, pk=pk)
    role = get_user_role(request.user)
    new_status = request.POST.get('status')
    valid_statuses = [s[0] for s in Order.STATUS_CHOICES]

    if new_status not in valid_statuses:
        messages.error(request, 'Invalid status.')
        return redirect('order_detail', pk=pk)

    if role == 'manager' or (role == 'waiter' and order.waiter == request.user):
        order.status = new_status
        if new_status == 'paid':
            order.payment_method = request.POST.get('payment_method', 'cash')
            order.paid_at = timezone.now()
        order.save(update_fields=['status', 'payment_method', 'paid_at'] if new_status == 'paid' else ['status'])
        messages.success(request, f'Order #{order.id} status updated to {new_status}.')
    else:
        messages.error(request, 'You do not have permission to update this order.')

    if role == 'manager':
        return redirect('manager_orders')
    return redirect('waiter_dashboard')


@login_required
def change_payment_method(request, pk):
    if request.method != 'POST':
        return redirect('dashboard')
    order = get_object_or_404(Order, pk=pk)
    role = get_user_role(request.user)
    new_method = request.POST.get('payment_method')

    valid_methods = [m[0] for m in Order.PAYMENT_METHOD_CHOICES if m[0]]
    if new_method not in valid_methods:
        messages.error(request, 'Invalid payment method.')
        return redirect('order_detail', pk=pk)

    if order.status != 'paid':
        messages.error(request, 'Can only change payment method on paid orders.')
        return redirect('order_detail', pk=pk)

    if role == 'manager' or (role == 'waiter' and order.waiter == request.user):
        order.payment_method = new_method
        order.save(update_fields=['payment_method'])
        messages.success(request, f'Order #{order.id} payment changed to {order.get_payment_method_display()}.')
    else:
        messages.error(request, 'You do not have permission to update this order.')

    return redirect('order_detail', pk=pk)


@login_required
def manager_orders(request):
    if get_user_role(request.user) != 'manager':
        return redirect('dashboard')
    status_filter = request.GET.get('status', '')
    orders = Order.objects.select_related('waiter').all()
    if status_filter:
        orders = orders.filter(status=status_filter)
    return render(request, 'core/manager_orders.html', {
        'orders': orders,
        'status_filter': status_filter,
        'status_choices': Order.STATUS_CHOICES,
    })


@login_required
def daily_report(request):
    if get_user_role(request.user) != 'manager':
        return redirect('dashboard')

    report_date_str = request.GET.get('date', '')
    tab = request.GET.get('tab', 'orders')
    if report_date_str:
        try:
            report_date = timezone.datetime.strptime(report_date_str, '%Y-%m-%d').date()
        except ValueError:
            report_date = timezone.now().date()
    else:
        report_date = timezone.now().date()

    paid_orders = Order.objects.filter(
        status='paid', paid_at__date=report_date
    ).select_related('waiter').prefetch_related('items__product')

    all_orders_today = Order.objects.filter(created_at__date=report_date)

    total_revenue = paid_orders.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    total_orders = all_orders_today.count()
    paid_count = paid_orders.count()
    cancelled_count = all_orders_today.filter(status='cancelled').count()

    revenue_by_method = {}
    for method, label in Order.PAYMENT_METHOD_CHOICES:
        if method:
            rev = paid_orders.filter(payment_method=method).aggregate(t=Sum('total_amount'))['t'] or Decimal('0')
            count = paid_orders.filter(payment_method=method).count()
            revenue_by_method[method] = {'label': label, 'total': rev, 'count': count}

    product_sales = {}
    for order_item in OrderItem.objects.filter(order__in=paid_orders).select_related('product', 'product__category'):
        pid = order_item.product_id
        if pid not in product_sales:
            product_sales[pid] = {
                'name': order_item.product.name,
                'category': order_item.product.category.name,
                'quantity': 0,
                'revenue': Decimal('0'),
            }
        product_sales[pid]['quantity'] += order_item.quantity
        product_sales[pid]['revenue'] += order_item.subtotal
    product_sales_list = sorted(product_sales.values(), key=lambda x: x['quantity'], reverse=True)

    category_sales = {}
    for ps in product_sales_list:
        cat = ps['category']
        if cat not in category_sales:
            category_sales[cat] = {'quantity': 0, 'revenue': Decimal('0')}
        category_sales[cat]['quantity'] += ps['quantity']
        category_sales[cat]['revenue'] += ps['revenue']
    category_sales_list = sorted(category_sales.items(), key=lambda x: x[1]['revenue'], reverse=True)

    stock_transactions = StockTransaction.objects.filter(
        created_at__date=report_date
    ).select_related('stock_item', 'created_by').order_by('-created_at')

    restock_txns = stock_transactions.filter(action='restock')
    use_txns = stock_transactions.filter(action='use')
    total_restock_cost = restock_txns.aggregate(t=Sum('total_cost'))['t'] or Decimal('0')
    total_use_value = use_txns.aggregate(t=Sum('total_cost'))['t'] or Decimal('0')
    total_restock_qty = restock_txns.aggregate(t=Sum('quantity'))['t'] or 0
    total_use_qty = use_txns.aggregate(t=Sum('quantity'))['t'] or 0

    restock_by_item = {}
    for txn in restock_txns:
        sid = txn.stock_item_id
        if sid not in restock_by_item:
            restock_by_item[sid] = {
                'name': txn.stock_item.name,
                'unit': txn.stock_item.get_unit_display(),
                'quantity': 0,
                'total_cost': Decimal('0'),
            }
        restock_by_item[sid]['quantity'] += txn.quantity
        restock_by_item[sid]['total_cost'] += txn.total_cost

    use_by_item = {}
    for txn in use_txns:
        sid = txn.stock_item_id
        if sid not in use_by_item:
            use_by_item[sid] = {
                'name': txn.stock_item.name,
                'unit': txn.stock_item.get_unit_display(),
                'quantity': 0,
                'total_value': Decimal('0'),
            }
        use_by_item[sid]['quantity'] += txn.quantity
        use_by_item[sid]['total_value'] += txn.total_cost

    context = {
        'report_date': report_date,
        'active_tab': tab,
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'paid_count': paid_count,
        'cancelled_count': cancelled_count,
        'revenue_by_method': revenue_by_method,
        'product_sales': product_sales_list,
        'category_sales': category_sales_list,
        'paid_orders': paid_orders,
        'stock_transactions': stock_transactions,
        'restock_txns': restock_txns,
        'use_txns': use_txns,
        'total_restock_cost': total_restock_cost,
        'total_use_value': total_use_value,
        'total_restock_qty': total_restock_qty,
        'total_use_qty': total_use_qty,
        'restock_by_product': restock_by_item.values(),
        'use_by_product': use_by_item.values(),
    }
    return render(request, 'core/daily_report.html', context)


@login_required
def stock_dashboard(request):
    if get_user_role(request.user) != 'stock_manager':
        return redirect('dashboard')
    stock_items = StockItem.objects.all()
    low_stock = [si for si in stock_items if si.is_low_stock]
    out_of_stock = [si for si in stock_items if si.is_out_of_stock]
    return render(request, 'core/stock_dashboard.html', {
        'stock_items': stock_items,
        'low_stock': low_stock,
        'out_of_stock': out_of_stock,
    })


@login_required
def stock_create(request):
    if get_user_role(request.user) != 'stock_manager':
        return redirect('dashboard')
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, 'Stock item name is required.')
            return redirect('stock_create')
        StockItem.objects.create(
            name=name,
            category=request.POST.get('category', ''),
            quantity=Decimal(request.POST.get('quantity', 0) or 0),
            low_stock_threshold=Decimal(request.POST.get('low_stock_threshold', 10) or 10),
            unit=request.POST.get('unit', 'pcs'),
            price_per_unit=Decimal(request.POST.get('price_per_unit', 0) or 0),
        )
        messages.success(request, f'Stock item "{name}" created.')
        return redirect('stock_dashboard')
    return render(request, 'core/stock_form.html')


@login_required
def stock_delete(request, pk):
    if get_user_role(request.user) != 'stock_manager':
        return redirect('dashboard')
    stock_item = get_object_or_404(StockItem, pk=pk)
    if request.method == 'POST':
        name = stock_item.name
        stock_item.delete()
        messages.success(request, f'Stock item "{name}" deleted.')
        return redirect('stock_dashboard')
    return render(request, 'core/stock_confirm_delete.html', {'stock_item': stock_item})


@login_required
def restock_item(request, pk):
    if get_user_role(request.user) != 'stock_manager':
        return redirect('dashboard')
    stock_item = get_object_or_404(StockItem, pk=pk)
    if request.method == 'POST':
        add_quantity = Decimal(request.POST.get('add_quantity', 0))
        stock_item.quantity += add_quantity
        stock_item.save()
        messages.success(request, f'{stock_item.name} restocked by {add_quantity} {stock_item.unit}.')
        return redirect('stock_dashboard')
    return render(request, 'core/restock_form.html', {'stock_item': stock_item})


@login_required
def edit_stock_item(request, pk):
    if get_user_role(request.user) != 'stock_manager':
        return redirect('dashboard')
    stock_item = get_object_or_404(StockItem, pk=pk)
    if request.method == 'POST':
        stock_item.quantity = Decimal(request.POST.get('quantity', stock_item.quantity))
        stock_item.low_stock_threshold = Decimal(request.POST.get('low_stock_threshold', stock_item.low_stock_threshold))
        stock_item.unit = request.POST.get('unit', stock_item.unit)
        stock_item.save()
        messages.success(request, f'{stock_item.name} stock updated.')
        return redirect('stock_dashboard')
    return render(request, 'core/edit_stock.html', {'stock_item': stock_item})


@login_required
def use_stock_item(request, pk):
    if get_user_role(request.user) != 'stock_manager':
        return redirect('dashboard')
    stock_item = get_object_or_404(StockItem, pk=pk)
    if request.method == 'POST':
        use_quantity = Decimal(request.POST.get('use_quantity', 0))
        if use_quantity <= 0:
            messages.error(request, 'Quantity must be greater than zero.')
            return redirect('use_stock_item', pk=pk)
        if use_quantity > stock_item.quantity:
            messages.error(request, f'Cannot use {use_quantity} {stock_item.unit}. Only {stock_item.quantity} available.')
            return redirect('use_stock_item', pk=pk)
        stock_item.quantity -= use_quantity
        stock_item.save()
        messages.success(request, f'{stock_item.name} used: {use_quantity} {stock_item.unit}. Remaining: {stock_item.quantity} {stock_item.unit}.')
        return redirect('stock_dashboard')
    return render(request, 'core/use_stock_form.html', {'stock_item': stock_item})


@login_required
def stock_inline_action(request):
    if get_user_role(request.user) != 'stock_manager':
        return JsonResponse({'error': 'Permission denied'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    action = request.POST.get('action')
    stock_id = request.POST.get('stock_id')
    stock_item = get_object_or_404(StockItem, pk=stock_id)

    if action == 'restock':
        qty = Decimal(request.POST.get('quantity', 0))
        price = Decimal(request.POST.get('price_per_unit', 0))
        if qty <= 0:
            return JsonResponse({'error': 'Quantity must be greater than zero.'}, status=400)
        if price < 0:
            return JsonResponse({'error': 'Price cannot be negative.'}, status=400)
        qty_before = stock_item.quantity
        stock_item.quantity += qty
        if price > 0:
            stock_item.price_per_unit = price
        stock_item.save()
        StockTransaction.objects.create(
            stock_item=stock_item,
            action='restock',
            quantity=qty,
            price_per_unit=stock_item.price_per_unit,
            total_cost=qty * stock_item.price_per_unit,
            quantity_before=qty_before,
            quantity_after=stock_item.quantity,
            created_by=request.user,
        )
        return JsonResponse({'success': True, 'message': f'Added {qty} {stock_item.unit}. New stock: {stock_item.quantity}', 'new_quantity': str(stock_item.quantity)})

    elif action == 'use':
        qty = Decimal(request.POST.get('quantity', 0))
        if qty <= 0:
            return JsonResponse({'error': 'Quantity must be greater than zero.'}, status=400)
        if qty > stock_item.quantity:
            return JsonResponse({'error': f'Cannot use {qty}. Only {stock_item.quantity} available.'}, status=400)
        qty_before = stock_item.quantity
        stock_item.quantity -= qty
        stock_item.save()
        StockTransaction.objects.create(
            stock_item=stock_item,
            action='use',
            quantity=qty,
            price_per_unit=stock_item.price_per_unit,
            total_cost=qty * stock_item.price_per_unit,
            quantity_before=qty_before,
            quantity_after=stock_item.quantity,
            created_by=request.user,
        )
        return JsonResponse({'success': True, 'message': f'Used {qty} {stock_item.unit}. Remaining: {stock_item.quantity}', 'new_quantity': str(stock_item.quantity)})

    elif action == 'edit':
        qty_before = stock_item.quantity
        stock_item.quantity = Decimal(request.POST.get('quantity', stock_item.quantity))
        stock_item.low_stock_threshold = Decimal(request.POST.get('low_stock_threshold', stock_item.low_stock_threshold))
        stock_item.unit = request.POST.get('unit', stock_item.unit)
        price = request.POST.get('price_per_unit')
        if price is not None and price != '':
            stock_item.price_per_unit = Decimal(price)
        stock_item.save()
        StockTransaction.objects.create(
            stock_item=stock_item,
            action='edit',
            quantity=abs(stock_item.quantity - qty_before),
            price_per_unit=stock_item.price_per_unit,
            total_cost=0,
            quantity_before=qty_before,
            quantity_after=stock_item.quantity,
            created_by=request.user,
        )
        return JsonResponse({'success': True, 'message': 'Stock updated.', 'new_quantity': str(stock_item.quantity)})

    return JsonResponse({'error': 'Unknown action'}, status=400)


@login_required
def stock_report(request):
    if get_user_role(request.user) != 'stock_manager':
        return redirect('dashboard')

    report_date_str = request.GET.get('date', '')
    if report_date_str:
        try:
            report_date = timezone.datetime.strptime(report_date_str, '%Y-%m-%d').date()
        except ValueError:
            report_date = timezone.now().date()
    else:
        report_date = timezone.now().date()

    day_start = timezone.make_aware(timezone.datetime.combine(report_date, timezone.datetime.min.time()))
    day_end = timezone.make_aware(timezone.datetime.combine(report_date, timezone.datetime.max.time()))

    transactions = StockTransaction.objects.filter(
        created_at__date=report_date
    ).select_related('stock_item', 'created_by').order_by('-created_at')

    restock_txns = transactions.filter(action='restock')
    use_txns = transactions.filter(action='use')

    total_restock_cost = restock_txns.aggregate(t=Sum('total_cost'))['t'] or Decimal('0')
    total_use_value = use_txns.aggregate(t=Sum('total_cost'))['t'] or Decimal('0')
    total_restock_qty = restock_txns.aggregate(t=Sum('quantity'))['t'] or 0
    total_use_qty = use_txns.aggregate(t=Sum('quantity'))['t'] or 0

    restock_by_item = {}
    for txn in restock_txns:
        sid = txn.stock_item_id
        if sid not in restock_by_item:
            restock_by_item[sid] = {
                'name': txn.stock_item.name,
                'unit': txn.stock_item.get_unit_display(),
                'quantity': 0,
                'total_cost': Decimal('0'),
            }
        restock_by_item[sid]['quantity'] += txn.quantity
        restock_by_item[sid]['total_cost'] += txn.total_cost

    use_by_item = {}
    for txn in use_txns:
        sid = txn.stock_item_id
        if sid not in use_by_item:
            use_by_item[sid] = {
                'name': txn.stock_item.name,
                'unit': txn.stock_item.get_unit_display(),
                'quantity': 0,
                'total_value': Decimal('0'),
            }
        use_by_item[sid]['quantity'] += txn.quantity
        use_by_item[sid]['total_value'] += txn.total_cost

    context = {
        'report_date': report_date,
        'transactions': transactions,
        'restock_txns': restock_txns,
        'use_txns': use_txns,
        'total_restock_cost': total_restock_cost,
        'total_use_value': total_use_value,
        'total_restock_qty': total_restock_qty,
        'total_use_qty': total_use_qty,
        'restock_by_product': restock_by_item.values(),
        'use_by_product': use_by_item.values(),
    }
    return render(request, 'core/stock_report.html', context)


@login_required
def get_products_json(request):
    category_id = request.GET.get('category')
    products = Product.objects.filter(is_available=True)
    if category_id:
        products = products.filter(category_id=category_id)
    data = [{
        'id': p.id,
        'name': p.name,
        'price': str(p.price),
    } for p in products]
    return JsonResponse({'products': data})


@login_required
def create_user(request):
    if get_user_role(request.user) != 'manager':
        return redirect('dashboard')
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        role = request.POST['role']
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return redirect('create_user')
        user = User.objects.create_user(
            username=username, password=password,
            first_name=first_name, last_name=last_name,
        )
        UserProfile.objects.create(user=user, role=role)
        messages.success(request, f'User {username} created as {role}.')
        return redirect('manage_users')
    return render(request, 'core/create_user.html')


@login_required
def manage_users(request):
    if get_user_role(request.user) != 'manager':
        return redirect('dashboard')
    users = User.objects.select_related('profile').all()
    return render(request, 'core/manage_users.html', {'users': users})


@login_required
def delete_user(request, pk):
    if get_user_role(request.user) != 'manager':
        return redirect('dashboard')
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, 'You cannot delete yourself.')
        return redirect('manage_users')
    if request.method == 'POST':
        user.delete()
        messages.success(request, f'User {user.username} deleted.')
        return redirect('manage_users')
    return render(request, 'core/delete_user.html', {'delete_user': user})


@login_required
def edit_order(request, pk):
    if get_user_role(request.user) != 'waiter':
        return redirect('dashboard')
    order = get_object_or_404(Order, pk=pk)
    if order.waiter != request.user:
        messages.error(request, 'You can only edit your own orders.')
        return redirect('waiter_dashboard')
    if order.status not in ('pending', 'preparing', 'ready', 'served'):
        messages.error(request, 'Cannot edit an order that has already been paid.')
        return redirect('waiter_dashboard')

    categories = Category.objects.filter(is_active=True).prefetch_related('products')

    if request.method == 'POST':
        new_table = request.POST.get('table_number', '').strip()
        items_json = request.POST.get('items', '[]')
        items = json.loads(items_json)

        if not items:
            messages.error(request, 'Order must have at least one item.')
            return redirect('edit_order', pk=pk)

        if new_table:
            order.table_number = new_table

        order.notes = request.POST.get('notes', '')
        order.save(update_fields=['table_number', 'notes'])

        order.items.all().delete()
        for item in items:
            product = Product.objects.get(pk=item['product_id'])
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=item['quantity'],
                price_at_time=product.price,
                notes=item.get('notes', ''),
            )

        order.calculate_total()
        messages.success(request, f'Order #{order.id} updated successfully.')
        return redirect('waiter_dashboard')

    existing_items = []
    for item in order.items.select_related('product').all():
        existing_items.append({
            'product_id': item.product_id,
            'name': item.product.name,
            'price': str(item.product.price),
            'quantity': item.quantity,
            'notes': item.notes,
        })

    return render(request, 'core/edit_order.html', {
        'order': order,
        'categories': categories,
        'existing_items_json': json.dumps(existing_items),
    })


@login_required
def merge_orders(request):
    if get_user_role(request.user) != 'waiter':
        return redirect('dashboard')

    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        if order_id:
            order = get_object_or_404(Order, pk=order_id, waiter=request.user)
            if order.status in ('paid', 'cancelled'):
                messages.error(request, 'Cannot add items to a paid or cancelled order.')
            else:
                return redirect('edit_order', pk=order.pk)
        else:
            table_number = request.POST.get('table_number', '').strip()
            if table_number:
                existing = Order.objects.filter(
                    table_number=table_number,
                ).exclude(status__in=['paid', 'cancelled']).first()
                if existing:
                    return redirect('edit_order', pk=existing.pk)
                else:
                    return redirect('create_order')
            else:
                messages.error(request, 'Please select an order or enter a table number.')

    active_orders = Order.objects.filter(
        waiter=request.user
    ).exclude(status__in=['paid', 'cancelled']).select_related().prefetch_related('items__product')

    return render(request, 'core/merge_orders.html', {
        'active_orders': active_orders,
    })


@login_required
def menu_management(request):
    if get_user_role(request.user) != 'manager':
        return redirect('dashboard')
    categories = Category.objects.prefetch_related('products').all()
    return render(request, 'core/menu_management.html', {'categories': categories})


@login_required
def category_inline_action(request):
    if get_user_role(request.user) != 'manager':
        return JsonResponse({'error': 'Permission denied'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    action = request.POST.get('action')

    if action == 'create':
        name = request.POST.get('name', '').strip()
        if not name:
            return JsonResponse({'error': 'Name is required.'}, status=400)
        cat = Category.objects.create(
            name=name,
            description=request.POST.get('description', ''),
            sort_order=int(request.POST.get('sort_order', 0) or 0),
            is_active='is_active' in request.POST,
        )
        return JsonResponse({
            'success': True,
            'id': cat.id,
            'name': cat.name,
            'description': cat.description,
            'sort_order': cat.sort_order,
            'is_active': cat.is_active,
        })

    elif action == 'update':
        cat = get_object_or_404(Category, pk=request.POST.get('id'))
        cat.name = request.POST.get('name', cat.name).strip()
        cat.description = request.POST.get('description', cat.description)
        cat.sort_order = int(request.POST.get('sort_order', cat.sort_order) or 0)
        cat.is_active = 'is_active' in request.POST
        cat.save()
        return JsonResponse({
            'success': True,
            'id': cat.id,
            'name': cat.name,
            'description': cat.description,
            'sort_order': cat.sort_order,
            'is_active': cat.is_active,
        })

    elif action == 'delete':
        cat = get_object_or_404(Category, pk=request.POST.get('id'))
        cat.delete()
        return JsonResponse({'success': True, 'id': cat.id})

    return JsonResponse({'error': 'Unknown action'}, status=400)


@login_required
def product_inline_action(request):
    if get_user_role(request.user) != 'manager':
        return JsonResponse({'error': 'Permission denied'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    action = request.POST.get('action')

    if action == 'create':
        name = request.POST.get('name', '').strip()
        category_id = request.POST.get('category_id')
        price = request.POST.get('price')
        if not name or not category_id or price is None:
            return JsonResponse({'error': 'Name, category, and price are required.'}, status=400)
        product = Product.objects.create(
            name=name,
            category_id=category_id,
            price=Decimal(price),
            description=request.POST.get('description', ''),
            is_available='is_available' in request.POST,
        )
        return JsonResponse({
            'success': True,
            'id': product.id,
            'name': product.name,
            'category_id': product.category_id,
            'category_name': product.category.name,
            'price': str(product.price),
            'description': product.description,
            'is_available': product.is_available,
        })

    elif action == 'update':
        product = get_object_or_404(Product, pk=request.POST.get('id'))
        product.name = request.POST.get('name', product.name).strip()
        product.category_id = request.POST.get('category_id', product.category_id)
        price = request.POST.get('price')
        if price is not None and price != '':
            product.price = Decimal(price)
        product.description = request.POST.get('description', product.description)
        product.is_available = 'is_available' in request.POST
        product.save()
        return JsonResponse({
            'success': True,
            'id': product.id,
            'name': product.name,
            'category_id': product.category_id,
            'category_name': product.category.name,
            'price': str(product.price),
            'description': product.description,
            'is_available': product.is_available,
        })

    elif action == 'delete':
        product = get_object_or_404(Product, pk=request.POST.get('id'))
        product.delete()
        return JsonResponse({'success': True, 'id': product.id})

    return JsonResponse({'error': 'Unknown action'}, status=400)
