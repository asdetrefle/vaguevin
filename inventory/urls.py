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
    path('winelist/', views.wine_list_index_view, name='wine_list_index'),
    path("winelist/create", views.create_wine_list, name="create_wine_list"),
    path("winelist/update-status/", views.update_wine_list_status, name="update_wine_list_status"),
    path('winelist/<uuid:uuid>/submit/', views.submit_wine_list, name='submit_wine_list'),
    path("winelist/<uuid:uuid>/", views.wine_list_view, name="wine_list"),
    path("winelist/<uuid:uuid>/export_pdf/", views.export_wine_list_pdf, name="export_wine_list_pdf"),
]
