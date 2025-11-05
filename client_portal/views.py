import pandas as pd
import json
import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.translation import gettext as _
from django.utils import translation
from django.http import HttpResponse, JsonResponse

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from inventory.models import Wine, WineInventory, STATUS_CHOICES, WineItem, WineList
from client_portal.serializers import WineItemSerializer


# views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_http_methods

def index(request):
    return render(request, 'client_portal/index.html')

# @require_http_methods(["GET", "POST"])
# def wine_list_view(request):
#     if request.method == 'POST':
#         wine_list_id = request.POST.get('wine_list_id', '').strip()
        
#         if not wine_list_id:
#             messages.error(request, 'Please enter a Wine List ID')
#             return render(request, 'wine_search.html')
        
#         # Here you would typically:
#         # 1. Validate the wine_list_id
#         # 2. Fetch the wine list from database
#         # 3. Process and display the results


#         wine_list = get_object_or_404(
#         WineList.objects.exclude(status='archived'), uuid=uuid)
#         items = wine_list.items.all()
#         display_items = [WineItemSerializer(item) for item in items]

#         return render(request, "client_portal/wine_list.html", {
#             "wine_list": wine_list,
#             "display_items": display_items
#         })
            
#         try:
#             # Example: Convert to integer if your IDs are numeric
#             wine_list_id_int = int(wine_list_id)
            
#             # Your logic to fetch and process the wine list
#             # wine_list = WineList.objects.get(id=wine_list_id_int)
            
#             # For now, redirect to a results page or render template
#             messages.success(request, f'Found wine list: {wine_list_id}')
#             return render(request, "client_portal/wine_list.html", {
#                 "wine_list": wine_list,
#                 "display_items": display_items
#             })
            
#         except ValueError:
#             messages.error(request, 'Please enter a valid numeric Wine List ID')
#             return render(request, 'wine_search.html', {
#                 'wine_list_id': wine_list_id
#             })
#         except Exception as e:
#             messages.error(request, f'Error finding wine list: {str(e)}')
#             return render(request, 'wine_search.html', {
#                 'wine_list_id': wine_list_id
#             })
    
#     # GET request - show the search form
#     return render(request, 'index.html')

def wine_list_view(request, uuid):
    wine_list = get_object_or_404(
        WineList.objects.exclude(status='archived'), uuid=uuid)
    items = wine_list.items.all()
    display_items = [WineItemSerializer(item) for item in items]

    return render(request, "client_portal/wine_list.html", {
        "wine_list": wine_list,
        "display_items": display_items
    })


@csrf_exempt  # if using JSON and fetch, csrf token header is sent anyway
def submit_wine_list(request, uuid):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid method"}, status=405)

    wine_list = get_object_or_404(WineList, uuid=uuid)

    if wine_list.status != "created":
        return JsonResponse({"success": False, "error": "Wine list has already been submitted"}, status=400)

    try:
        data = json.loads(request.body)
        items_data = data.get("items", [])
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

    if not items_data:
        return JsonResponse({"success": False, "error": "No items provided"}, status=400)

    # Update each item
    for item_info in items_data:
        item_id = item_info.get("item_id")
        accept_qty = item_info.get("accept_qty", 0)

        if not item_id or accept_qty < 0:
            continue  # skip invalid

        try:
            wine_item = WineItem.objects.get(id=item_id, wine_list=wine_list)
            wine_item.accept_qty = min(
                accept_qty, wine_item.offer_qty)  # don't exceed offer
            wine_item.save()
        except WineItem.DoesNotExist:
            continue  # skip missing

    # Update wine list status
    wine_list.status = "submitted"
    wine_list.save()
    return JsonResponse({"success": True})
