import pandas as pd
import re
from django.core.management.base import BaseCommand
from inventory.models import Wine
from datetime import datetime

# Map Excel couleur values to Wine model CATEGORY_CHOICES
CATEGORY_MAPPING = {
    'BLANC': 'white',
    'WHITE': 'white',
    'ROUGE': 'red',
    'RED': 'red',
    'ROSE': 'rose',
    'ROSÉ': 'rose',
    'CHAMPAGNE': 'champagne',
    'ROSE CHAMPAGNE': 'rose_champagne',
    'SPARKLING': 'sparkling',
    'YELLOW': 'yellow',
    'LIQUEUR': 'liqueur',
    'DESSERT': 'dessert',
    'FORTIFIED': 'fortified',
    'ORANGE': 'orange'
}

class Command(BaseCommand):
    help = "Import wines from a multi-sheet Excel file. Each sheet name is treated as inventory date."

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Path to the Excel file')

    def handle(self, *args, **options):
        file_path = options['file_path']

        try:
            xls = pd.ExcelFile(file_path)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Failed to read Excel file: {e}"))
            return

        sheet_names = xls.sheet_names
        self.stdout.write(self.style.WARNING(f"📑 Found {len(sheet_names)} sheet(s): {', '.join(sheet_names)}"))

        for sheet_name in sheet_names:
            try:
                purchase_date = datetime.strptime(sheet_name.strip(), "%Y-%m-%d").date()
            except Exception:
                purchase_date = None  # sheet name is not a date

            df = pd.read_excel(file_path, sheet_name=sheet_name)
            df = df.fillna("")

            self.stdout.write(self.style.HTTP_INFO(f"📥 Importing sheet: {sheet_name} ({len(df)} rows)"))

            current_region = None
            for _, row in df.iterrows():
                article = str(row.get('ARTICLE', '')).strip()
                couleur = str(row.get('COULEUR', '')).strip().upper()
                vintage = str(row.get('MILLESIME', '')).strip()
                size = str(row.get('CL', '')).strip()
                qty = str(row.get('UNITÉS', '')).strip()
                price_euro = str(row.get('PRICE EN EUROS', '')).replace('€', '').strip()

                # Skip category/header rows
                if not article or article.upper() in ["WHITE WINE 白葡萄酒", "RED WINE 紅葡萄酒"]:
                    continue
                elif article.upper() in [
                    "CHAMPAGNE 香檳", "BURGUNDY 勃艮第", "LOIRE 魯瓦河", "VALLEY OF RHONE 隆河谷", "SAVOIE 薩瓦河"]:
                    current_region = ''.join(char for char in article.upper() 
                                             if char == " " or (char.isascii() and char.isalpha())).strip().title()
                    continue

                # Convert quantity
                try:
                    qty = int(float(qty))
                except:
                    continue

                # Convert bottle size
                try:
                    size = int(float(size))
                except:
                    size = None

                # Convert price
                try:
                    price_euro = float(price_euro.replace(",", "").replace("€", "")) if price_euro else 0
                except:
                    price_euro = 0

                # Vintage handling — keep NV as string
                if vintage.upper() == "NV":
                    vintage_str = "NV"
                else:
                    try:
                        vintage_str = str(int(float(vintage)))
                    except:
                        vintage_str = "-"

                # Category mapping
                category = CATEGORY_MAPPING.get(couleur, 'other')

                article = article.title()
                article = article.replace("Drc ", "DRC ")
                article = article.replace("1Er ", "1er ")
                article = article.replace("Vv ", "VV ")
                article = article.replace("Jfm ", "JFM ")
                article = article.replace("Jf ", "JF ")
                article = re.sub(r" Vo\b", " VO", article)
                article = article.replace(" Rdj", " RDJ")

                wine = Wine.objects.create(
                    name=article,
                    category=category,
                    vintage=vintage_str,
                    bottle_size=size,
                    region=current_region,
                    purchase_price=price_euro,
                    qty=qty,
                    purchase_date=purchase_date,
                    status="in_stock"
                )

                self.stdout.write(self.style.SUCCESS(f"✅ Imported: {wine.name} ({vintage_str}) Qty={qty}"))

            self.stdout.write(self.style.SUCCESS(f"✅ Finished sheet: {sheet_name}"))

        self.stdout.write(self.style.SUCCESS("🍷 All sheets imported successfully"))
