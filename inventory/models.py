import uuid
from decimal import Decimal

from django.db import models
from django.db.models import F, Sum, Value
from django.db.models.functions import Coalesce
from django.utils.translation import gettext_lazy as _

# Create your models here.


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class Supplier(models.Model):
    name = models.CharField(max_length=200)
    contact_email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


# -----------------------------------
# Category Choices
# -----------------------------------
CATEGORY_CHOICES = [
    ('red', 'Red'),
    ('white', 'White'),
    ('rose', 'Rosé'),
    ('champagne', 'Champagne'),
    ('rose_champagne', 'Rosé Champagne'),
    ('sparkling', 'Sparkling'),
    ('yellow', 'Yellow'),
    ('liqueur', 'Liqueur'),
    ('dessert', 'Dessert'),        # optional
    ('fortified', 'Fortified'),    # optional
    ('orange', 'Orange'),          # optional
    ('other', 'Other'),
]

# -----------------------------------
# Status Choices (optional)
# -----------------------------------
STATUS_CHOICES = [
    ('in_bond', _('In Bond')),
    ('in_stock', _('In Stock')),
    ('reserved', _('Reserved')),
    ('sold', _('Sold')),
    ('consumed', _('Consumed')),
    ('other', _('Other')),
]


class Wine(models.Model):
    name = models.CharField(max_length=255)
    vintage = models.CharField(max_length=10, blank=True, null=True)  # NV or year
    category = models.CharField(
        max_length=50, choices=CATEGORY_CHOICES, default='other')
    region = models.CharField(max_length=255, blank=True, null=True)
    appellation = models.CharField(max_length=255, blank=True, null=True)
    rating = models.CharField(max_length=50, blank=True, null=True,
                              help_text="Critic or personal rating")
    note = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['name', 'vintage']

    def __str__(self):
        return f"{self.name} ({self.vintage or 'NV'})"


class WineInventory(models.Model):
    wine = models.ForeignKey(Wine, on_delete=models.CASCADE, related_name='inventories')
    bottle_size = models.PositiveIntegerField(
        blank=True, null=True, help_text="Size in cl (e.g., 75)")
    qty = models.PositiveIntegerField(default=0)
    purchase_price = models.DecimalField(
        max_digits=12, decimal_places=2, blank=True, null=True)
    source = models.CharField(max_length=255, blank=True, null=True)
    purchase_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='in_stock')
    location = models.CharField(max_length=255, blank=True,
                                null=True, help_text="Cellar or storage location")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.wine} — {self.bottle_size or '?'}cl [{self.status}]"

    def total_value(self):
        """Return total value of the stock for this wine."""
        if self.purchase_price and self.qty:
            return self.purchase_price * self.qty
        return None


class WineList(models.Model):
    """
    Represents a curated list of wines proposed to or confirmed by a client.
    """

    STATUS_CHOICES = [
        ('created', 'Client Review'),
        ('submitted', 'Submitted'),
        ('confirmed', 'Confirmed'),
        ('delivered', 'Delivered'),
        ('finalized', 'Finalized'),
        ('archived', 'Archived'),
    ]

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=255,
                            help_text="Client name or ref of the wine list: (e.g. 'Xavier Luo Offer')")
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_sent_to_client = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

    def total_value(self):
        """Compute total retail value of wines in this list."""
        total = self.items.aggregate(
            total=Sum(F('offer_price') * Coalesce(F('accept_qty'), F('offer_qty')))
        )['total']
        return total or Decimal('0')

    def total_items(self):
        """Return number of wines in this list."""
        return self.items.count()


class WineItem(models.Model):
    """
    A single wine entry in a WineList.
    References WineInventory for stock and Wine through it.
    """

    wine_list = models.ForeignKey(
        WineList, on_delete=models.CASCADE, related_name='items')
    inventory = models.ForeignKey(
        WineInventory, on_delete=models.PROTECT, related_name='wine_items')

    offer_price = models.DecimalField(max_digits=12, decimal_places=2,
                                      help_text="Proposed unit offer price to client")
    offer_qty = models.PositiveIntegerField(default=0)
    note = models.TextField(blank=True, null=True,
                            help_text="Optional note for the client (e.g. tasting note)")

    accept_qty = models.PositiveIntegerField(default=None, null=True,
                                             help_text="if None, equals offer_qty")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('wine_list', 'inventory')
        ordering = ['inventory__wine__name']

    def __str__(self):
        return f"{self.inventory.wine.name} ({self.quantity}x) – {self.price}€"

    def subtotal(self):
        return self.price * self.quantity
