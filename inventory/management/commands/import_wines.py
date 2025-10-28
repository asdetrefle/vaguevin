import pandas as pd
from django.core.management.base import BaseCommand
from inventory.models import Wine, Category, Supplier

class Command(BaseCommand):
    help = 'Import wine offers from an Excel file without changing the model'

    def add_arguments(self, parser):
        parser.add_argument('excel_file', type=str, help='Path to the Excel file')

    def handle(self, *args, **options):
        file_path = options['excel_file']
        self.stdout.write(self.style.SUCCESS(f"📥 Reading {file_path} ..."))

        try:
            df = pd.read_excel(file_path)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Failed to read Excel: {e}"))
            return

        required_cols = {'Name', 'Vintage', 'Unit price VIP', 'Qty'}
        missing = required_cols - set(df.columns)
        if missing:
            self.stderr.write(self.style.ERROR(f"Excel missing columns: {missing}"))
            return

        # Optional: Create fallback category/supplier
        default_category, _ = Category.objects.get_or_create(name="Imported")
        default_supplier, _ = Supplier.objects.get_or_create(name="Unknown")

        for idx, row in df.iterrows():
            name = str(row['Name']).strip()
            if not name:
                continue

            # Vintage year
            vintage_year = None
            if pd.notna(row['Vintage']):
                try:
                    vintage_year = int(row['Vintage'])
                except ValueError:
                    self.stderr.write(self.style.WARNING(f"⚠️ Invalid vintage for row {idx}: {row['Vintage']}"))
                    vintage_year = None

            # Price
            price = 0
            if pd.notna(row['Unit price VIP']):
                try:
                    price = float(row['Unit price VIP'])
                except ValueError:
                    self.stderr.write(self.style.WARNING(f"⚠️ Invalid price for row {idx}: {row['Unit price VIP']}"))

            # Quantity
            quantity = 0
            if pd.notna(row['Qty']):
                try:
                    quantity = int(row['Qty'])
                except ValueError:
                    self.stderr.write(self.style.WARNING(f"⚠️ Invalid quantity for row {idx}: {row['Qty']}"))

            wine, created = Wine.objects.get_or_create(
                name=name,
                vintage_year=vintage_year,
                defaults={
                    'category': default_category,
                    'supplier': default_supplier,
                    'price': price,
                    'quantity_in_stock': quantity
                }
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"✅ Added: {wine}"))
            else:
                wine.price = price
                wine.quantity_in_stock = quantity
                wine.save()
                self.stdout.write(self.style.WARNING(f"📝 Updated: {wine}"))

        self.stdout.write(self.style.SUCCESS("🎉 Import completed successfully."))
