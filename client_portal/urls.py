from django.urls import path
from . import views

urlpatterns = [
    # New WineList tab
    path("", views.index, name="input_wine_list_id"),

    # path("winelist/", views.wine_list_view, name="client_wine_list"),
    path("winelist/<uuid:uuid>/", views.wine_list_view, name="client_wine_list"),
    path("winelist/<uuid:uuid>/submit/", views.submit_wine_list, name='client_submit_wine_list'),
]
