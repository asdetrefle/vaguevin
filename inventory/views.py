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

from .models import Wine, WineInventory, STATUS_CHOICES, WineItem, WineList


def login_view(request):
    """
    Displays login page and handles authentication.
    Supports multilingual UI via LocaleMiddleware and language selector.
    """
    if request.user.is_authenticated:
        return redirect('inventory_list')

    error = None

    # Handle login form submission
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('inventory_list')
        else:
            error = _("Invalid credentials")  # translated

    return render(request, 'inventory/login.html', {'error': error})


@login_required
def inventory_list_view(request):
    inventories = WineInventory.objects.select_related('wine').order_by('wine__name')
    context = {
        'inventories': inventories,
        'STATUS_CHOICES': STATUS_CHOICES,
    }
    return render(request, 'inventory/inventory_list.html', context)


def logout_view(request):
    """
    Logs out the user and redirects to the login page.
    """
    logout(request)
    return redirect('login')  # 'login' is the name of your login URL


def set_language(request):
    lang_code = request.GET.get('lang', 'en')
    if lang_code not in dict(settings.LANGUAGES).keys():
        lang_code = 'en'

    # 1. Save in session
    request.session['django_language'] = lang_code
    request.session.modified = True

    # 2. Activate language immediately
    translation.activate(lang_code)

    # 3. Set language cookie so Accept-Language won't override
    response = redirect(request.META.get('HTTP_REFERER', '/inventory/'))
    response.set_cookie(
        settings.LANGUAGE_COOKIE_NAME,
        lang_code,
        max_age=31536000,  # 1 year
        samesite='Lax'
    )

    return response


def export_wines(request):
    if request.method == 'POST':
        selected_ids = request.POST.getlist('selected_wines')
        wines = Wine.objects.filter(id__in=selected_ids)

        data = []
        for w in wines:
            data.append({
                'Name': w.name,
                'Category': w.get_category_display(),
                'Vintage': w.vintage or '—',
                'Region': w.region or '—',
                'Bottle Size (cl)': w.bottle_size or '—',
                'Price (€)': float(w.purchase_price) if w.purchase_price else 0.0,
                'Quantity': w.qty,
                'Status': w.get_status_display(),
                'Total (€)': (float(w.purchase_price) * w.qty) if w.purchase_price else 0.0,
                'Source': w.source or '—',
                'Purchase Date': w.purchase_date.strftime('%Y-%m-%d') if w.purchase_date else '—',
                'Location': w.location or '—',
                'Rating': w.rating or '—',
                'Note': w.note or '',
            })

        df = pd.DataFrame(data)

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="selected_wines.xlsx"'

        with pd.ExcelWriter(response, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Selected Wines', index=False)

        return response

    return HttpResponse(status=400)


def batch_edit_wines(request):
    if request.method == 'POST':
        ids = request.POST.get('selected_wines', '')
        ids = [int(i) for i in ids.split(',') if i.strip().isdigit()]
        inventories = WineInventory.objects.filter(id__in=ids)

        # Fields belonging to Wine (definition)
        wine_fields = ['vintage', 'category', 'region']
        # Fields belonging to WineInventory (stock-specific)
        inventory_fields = ['bottle_size', 'status', 'qty', 'purchase_price']

        # Collect updates
        wine_updates = {}
        inventory_updates = {}

        for f in wine_fields:
            val = request.POST.get(f)
            if val:
                wine_updates[f] = val

        for f in inventory_fields:
            val = request.POST.get(f)
            if val:
                # convert numeric fields
                if f in ['bottle_size', 'qty']:
                    try:
                        val = int(val)
                    except ValueError:
                        continue
                elif f == 'purchase_price':
                    try:
                        val = float(val)
                    except ValueError:
                        continue
                inventory_updates[f] = val

        # Apply updates
        for inv in inventories:
            # Update Wine definition if needed
            if wine_updates:
                wine = inv.wine
                for k, v in wine_updates.items():
                    setattr(wine, k, v)
                wine.save()
            # Update inventory-specific fields
            if inventory_updates:
                for k, v in inventory_updates.items():
                    setattr(inv, k, v)
                inv.save()

        if wine_updates or inventory_updates:
            messages.success(
                request, f"{len(inventories)} inventory items updated successfully.")
        else:
            messages.info(request, "No changes were applied.")

        return redirect('inventory_list')  # adjust to your inventory list view name

    return redirect('inventory_list')


@login_required
@csrf_exempt
@require_POST
def create_wine_list(request):
    data = json.loads(request.body)

    name = data.get("name")
    description = data.get("description", None)
    items = data.get("items", [])

    if not items:
        return JsonResponse({"success": False, "error": "No items selected"})

    # create wine list with UUID
    wine_list = WineList.objects.create(
        uuid=uuid.uuid4(), name=name, description=description, status="created")

    for it in items:
        inventory_id = it.get("inventory_id")
        offer_qty = it.get("offer_qty", 1)
        try:
            inventory = WineInventory.objects.get(id=inventory_id)
            WineItem.objects.create(
                inventory=inventory,
                wine_list=wine_list,
                offer_qty=offer_qty,
                offer_price=inventory.purchase_price  # or your logic
            )
        except WineInventory.DoesNotExist:
            continue

    return JsonResponse({"success": True, "uuid": str(wine_list.uuid)})


@login_required
def wine_list_index_view(request):
    """
    Display all WineLists for the logged-in user except archived ones.
    """
    wine_lists = (
        WineList.objects.exclude(status__in=["archived"])
        .prefetch_related("items")  # optimize item count queries
        .order_by("-created_at")
    )

    context = {
        "wine_lists": wine_lists,
    }
    return render(request, "inventory/wine_list_index.html", context)


def wine_list_view(request, uuid):
    wine_list = get_object_or_404(
        WineList.objects.exclude(status='archived'), uuid=uuid)
    items = wine_list.items.all()

    return render(request, "inventory/wine_list.html", {
        "wine_list": wine_list,
        "display_items": items,
    })


@csrf_exempt  # if using JSON and fetch, csrf token header is sent anyway
@login_required
def amend_wine_list(request, uuid):
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
        offer_price = item_info.get("offer_price", 0)
        accept_qty = item_info.get("accept_qty", 0)

        if not item_id or accept_qty < 0:
            continue  # skip invalid

        try:
            wine_item = WineItem.objects.get(id=item_id, wine_list=wine_list)
            wine_item.offer_price = max(offer_price, wine_item.inventory.purchase_price)  # not below purchase
            wine_item.accept_qty = min(accept_qty, wine_item.offer_qty)  # don't exceed offer
            wine_item.save()
        except WineItem.DoesNotExist:
            continue  # skip missing

    # Update wine list status
    wine_list.save()
    return JsonResponse({"success": True})


@require_POST
@login_required
def update_wine_list_status(request):
    """Bulk update the status of selected wine lists."""
    try:
        data = json.loads(request.body.decode('utf-8'))
        uuids = data.get('uuids', [])
        status = data.get('status')

        if not uuids or not status:
            return JsonResponse({'success': False, 'error': 'Missing data.'}, status=400)

        valid_statuses = [choice[0] for choice in WineList.STATUS_CHOICES]
        if status not in valid_statuses:
            return JsonResponse({'success': False, 'error': 'Invalid status.'}, status=400)

        updated = WineList.objects.filter(uuid__in=uuids).update(status=status)

        return JsonResponse({'success': True, 'updated_count': updated})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@login_required
def export_wine_list_pdf(request, uuid):
    from weasyprint import HTML
    import io

    # Get the wine list
    wine_list = get_object_or_404(
        WineList.objects.exclude(status='archived'), uuid=uuid)
    items = wine_list.items.all()  # adjust if you use related_name

    # Build a pandas DataFrame
    data = []
    for item in items:
        data.append({
            "Name": item.inventory.wine.name,
            "Vintage": item.inventory.wine.vintage or "",
            "Category": item.inventory.wine.category,
            "Region": item.inventory.wine.region or "",
            "Bottle Size (cl)": item.inventory.bottle_size,
            "Qty": item.accept_qty or item.offer_qty,
            "Note": item.note or "",
        })
    df = pd.DataFrame(data)

    # Convert DataFrame to HTML
    html_content = df.to_html(index=False, border=0, justify='left')

    # Optional: Wrap HTML in a minimal template
    html = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; font-size: 12px; }}
            th {{ background-color: #f2f2f2; }}
        </style>
    </head>
    <body>
        <h2>Wine List: {wine_list.name or wine_list.uuid}</h2>
        {html_content}
    </body>
    </html>
    """

    # Generate PDF
    pdf_file = io.BytesIO()
    HTML(string=html).write_pdf(pdf_file)
    pdf_file.seek(0)

    # Return PDF as response
    response = HttpResponse(pdf_file.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="WineList_{wine_list.name or wine_list.uuid}.pdf"'
    return response
