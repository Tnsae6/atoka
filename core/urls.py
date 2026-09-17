from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('eyob26neba/', views.register_superuser, name='register_superuser'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.dashboard, name='dashboard'),

    # Manager
    path('manager/', views.manager_dashboard, name='manager_dashboard'),
    path('manager/menu/', views.menu_management, name='menu_management'),
    path('manager/menu/category/action/', views.category_inline_action, name='category_inline_action'),
    path('manager/menu/product/action/', views.product_inline_action, name='product_inline_action'),
    path('manager/categories/', views.category_list, name='category_list'),
    path('manager/categories/create/', views.category_create, name='category_create'),
    path('manager/categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('manager/categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
    path('manager/products/', views.product_list, name='product_list'),
    path('manager/products/create/', views.product_create, name='product_create'),
    path('manager/products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('manager/products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('manager/orders/', views.manager_orders, name='manager_orders'),
    path('manager/report/', views.daily_report, name='daily_report'),
    path('manager/users/', views.manage_users, name='manage_users'),
    path('manager/users/create/', views.create_user, name='create_user'),
    path('manager/users/<int:pk>/delete/', views.delete_user, name='delete_user'),

    # Waiter
    path('waiter/', views.waiter_dashboard, name='waiter_dashboard'),
    path('waiter/report/', views.waiter_daily_report, name='waiter_daily_report'),
    path('waiter/order/new/', views.create_order, name='create_order'),
    path('waiter/order/<int:pk>/edit/', views.edit_order, name='edit_order'),
    path('waiter/merge/', views.merge_orders, name='merge_orders'),

    # Shared
    path('orders/<int:pk>/', views.order_detail, name='order_detail'),
    path('orders/<int:pk>/status/', views.update_order_status, name='update_order_status'),
    path('orders/<int:pk>/change-payment/', views.change_payment_method, name='change_payment_method'),

    # Stock Manager
    path('stock/', views.stock_dashboard, name='stock_dashboard'),
    path('stock/create/', views.stock_create, name='stock_create'),
    path('stock/report/', views.stock_report, name='stock_report'),
    path('stock/<int:pk>/restock/', views.restock_item, name='restock_item'),
    path('stock/<int:pk>/use/', views.use_stock_item, name='use_stock_item'),
    path('stock/<int:pk>/edit/', views.edit_stock_item, name='edit_stock_item'),
    path('stock/<int:pk>/delete/', views.stock_delete, name='stock_delete'),
    path('stock/action/', views.stock_inline_action, name='stock_inline_action'),

    # JSON API for dynamic product loading
    path('api/products/', views.get_products_json, name='get_products_json'),
    path('health/', views.health_check, name='health_check'),
]
