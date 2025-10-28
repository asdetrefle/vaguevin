import pandas as pd
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext as _
from django.utils import translation
from django.conf import settings
from django.http import HttpResponse

from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login

from .models import Wine, WineInventory, STATUS_CHOICES

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


# def set_language(request):
#     user_language = request.GET.get('lang', 'en')
#     request.session['django_language'] = user_language  # 👈 use string key
#     request.session.modified = True
#     print("Accept-Language:", request.headers.get('Accept-Language'))
#     print("Session language:", request.session.get('django_language'))
#     print("Active language in view:", translation.get_language())
#     return redirect(request.META.get('HTTP_REFERER', '/wines/'))

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
            messages.success(request, f"{len(inventories)} inventory items updated successfully.")
        else:
            messages.info(request, "No changes were applied.")

        return redirect('inventory_list')  # adjust to your inventory list view name

    return redirect('inventory_list')


@login_required
def create_wine_list_view(request):
    return render(request, 'inventory/wine_list.html')


@login_required
def wine_list_view(request):
    return render(request, 'inventory/wine_list.html')
