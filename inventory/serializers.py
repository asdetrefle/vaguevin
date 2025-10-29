class WineItemSerializer:
    def __init__(self, item):
        self.id = item.id                    # WineItem ID
        self.name = item.inventory.wine.name
        self.vintage = item.inventory.wine.vintage
        self.category = item.inventory.wine.category
        self.region = item.inventory.wine.region
        self.appellation = item.inventory.wine.appellation
        self.bottle_size = item.inventory.bottle_size
        self.offer_price = item.offer_price  # Quantity offered to client
        self.offer_qty = item.offer_qty  # Quantity offered to client
        self.note = item.note
    
    def to_dict(self):
        return self.__dict__