from django.contrib import admin
from .models import Category, Supplier, Wine, WineInventory

# Register your models here.

admin.site.register(Category)
admin.site.register(Supplier)
admin.site.register(Wine)
admin.site.register(WineInventory)