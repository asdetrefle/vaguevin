from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),  # 👈 new
    path('set-language/', views.set_language, name='set_language'),
    path('inventory/', views.inventory_list_view, name='inventory_list'),
    path('inventory/export/', views.export_wines, name='export_wines'),
    path('inventory/batch_edit/', views.batch_edit_wines, name='batch_edit_wines'),

    # New WineList tab
    path('wine_list/', views.wine_list_view, name='wine_list'),
]
