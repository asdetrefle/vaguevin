from django.db import models
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

