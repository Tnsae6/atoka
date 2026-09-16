from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import UserProfile, Category, Product, StockItem


class Command(BaseCommand):
    help = 'Seeds the database with initial data'

    def handle(self, *args, **options):
        users_data = [
            {'username': 'admin', 'password': 'admin123', 'role': 'manager', 'first_name': 'Admin', 'last_name': 'User'},
            {'username': 'waiter1', 'password': 'waiter123', 'role': 'waiter', 'first_name': 'John', 'last_name': 'Smith'},
            {'username': 'waiter2', 'password': 'waiter123', 'role': 'waiter', 'first_name': 'Jane', 'last_name': 'Doe'},
            {'username': 'stock1', 'password': 'stock123', 'role': 'stock_manager', 'first_name': 'Mike', 'last_name': 'Wilson'},
        ]

        for data in users_data:
            if not User.objects.filter(username=data['username']).exists():
                user = User.objects.create_user(
                    username=data['username'],
                    password=data['password'],
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                )
                UserProfile.objects.create(user=user, role=data['role'])
                self.stdout.write(f"Created user: {data['username']} ({data['role']})")
            else:
                self.stdout.write(f"User {data['username']} already exists, skipping.")

        categories_data = [
            {'name': 'Coffee', 'description': 'Coffee beverages', 'sort_order': 1},
            {'name': 'Tea', 'description': 'Tea beverages', 'sort_order': 2},
            {'name': 'Juices & Drinks', 'description': 'Juices, soft drinks, and water', 'sort_order': 3},
            {'name': 'Pastries & Bakery', 'description': 'Pastries, cakes, and baked goods', 'sort_order': 4},
            {'name': 'Ethiopian Breakfast', 'description': 'Traditional Ethiopian breakfast dishes', 'sort_order': 5},
            {'name': 'Lunch', 'description': 'Sandwiches, burgers, pasta, and pizza', 'sort_order': 6},
        ]

        for data in categories_data:
            cat, created = Category.objects.get_or_create(name=data['name'], defaults=data)
            if created:
                self.stdout.write(f"Created category: {data['name']}")

        products_data = [
            # Coffee
            {'name': 'Espresso / ኤስፕሬሶ', 'category': 'Coffee', 'price': 90},
            {'name': 'Double Espresso / ድርብ ኤስፕሬሶ', 'category': 'Coffee', 'price': 160},
            {'name': 'Macchiato / ማኪያቶ', 'category': 'Coffee', 'price': 100},
            {'name': 'Double Macchiato / ድርብ ማኪያቶ', 'category': 'Coffee', 'price': 170},
            {'name': 'Cappuccino / ካፑቺኖ', 'category': 'Coffee', 'price': 160},
            {'name': 'Café Latte / ካፌ ላቴ', 'category': 'Coffee', 'price': 150},
            {'name': 'Americano / አሜሪካኖ', 'category': 'Coffee', 'price': 120},
            {'name': 'Mocha / ሞካ', 'category': 'Coffee', 'price': 180},
            {'name': 'Traditional Coffee (Jebena) / የጀበና ቡና', 'category': 'Coffee', 'price': 90},
            {'name': 'Coffee Pot (2 People) / ጀበና ቡና (ለ2 ሰው)', 'category': 'Coffee', 'price': 180},
            {'name': 'Iced Latte / ቀዝቃዛ ላቴ', 'category': 'Coffee', 'price': 200},
            {'name': 'Iced Coffee / ቀዝቃዛ ቡና', 'category': 'Coffee', 'price': 170},
            # Tea
            {'name': 'Black Tea / ጥቁር ሻይ', 'category': 'Tea', 'price': 70},
            {'name': 'Lemon Tea / የሎሚ ሻይ', 'category': 'Tea', 'price': 80},
            {'name': 'Ginger Tea / የዝንጅብል ሻይ', 'category': 'Tea', 'price': 80},
            {'name': 'Mint Tea / የናና ሻይ', 'category': 'Tea', 'price': 80},
            {'name': 'Green Tea / አረንጓዴ ሻይ', 'category': 'Tea', 'price': 100},
            {'name': 'Special Ethiopian Tea / ልዩ የኢትዮጵያ ሻይ', 'category': 'Tea', 'price': 120},
            # Juices & Drinks
            {'name': 'Orange Juice / ብርቱካን ጭማቂ', 'category': 'Juices & Drinks', 'price': 220},
            {'name': 'Mango Juice / ማንጎ ጭማቂ', 'category': 'Juices & Drinks', 'price': 230},
            {'name': 'Avocado Juice / አቮካዶ ጭማቂ', 'category': 'Juices & Drinks', 'price': 230},
            {'name': 'Mixed Fruit Juice / የፍራፍሬ ድብልቅ ጭማቂ', 'category': 'Juices & Drinks', 'price': 260},
            {'name': 'Bottled Water / የታሸገ ውሃ', 'category': 'Juices & Drinks', 'price': 45},
            {'name': 'Coca-Cola / ኮካ ኮላ', 'category': 'Juices & Drinks', 'price': 70},
            {'name': 'Fanta / ፋንታ', 'category': 'Juices & Drinks', 'price': 70},
            {'name': 'Sprite / ስፕራይት', 'category': 'Juices & Drinks', 'price': 70},
            # Pastries & Bakery
            {'name': 'Plain Croissant / ክሮሳን', 'category': 'Pastries & Bakery', 'price': 130},
            {'name': 'Chocolate Croissant / ቸኮሌት ክሮሳን', 'category': 'Pastries & Bakery', 'price': 150},
            {'name': 'Muffin / ማፊን', 'category': 'Pastries & Bakery', 'price': 120},
            {'name': 'Cinnamon Roll / ቀረፋ ሮል', 'category': 'Pastries & Bakery', 'price': 140},
            {'name': 'Marble Cake / ማርብል ኬክ', 'category': 'Pastries & Bakery', 'price': 140},
            {'name': 'Cheesecake / ቺዝ ኬክ', 'category': 'Pastries & Bakery', 'price': 250},
            {'name': 'Chocolate Cake / ቸኮሌት ኬክ', 'category': 'Pastries & Bakery', 'price': 220},
            # Ethiopian Breakfast
            {'name': 'Ful / ፉል', 'category': 'Ethiopian Breakfast', 'price': 220},
            {'name': 'Chechebsa / ጨጨብሳ', 'category': 'Ethiopian Breakfast', 'price': 260},
            {'name': 'Egg Sandwich / የእንቁላል ሳንድዊች', 'category': 'Ethiopian Breakfast', 'price': 220},
            {'name': 'Cheese Sandwich / የአይብ ሳንድዊች', 'category': 'Ethiopian Breakfast', 'price': 240},
            {'name': 'Omelette & Bread / ኦምሌት ከዳቦ ጋር', 'category': 'Ethiopian Breakfast', 'price': 260},
            {'name': 'Scrambled Eggs & Toast / የተቀላቀለ እንቁላል ከቶስት ጋር', 'category': 'Ethiopian Breakfast', 'price': 240},
            # Lunch
            {'name': 'Chicken Sandwich / የዶሮ ሳንድዊች', 'category': 'Lunch', 'price': 350},
            {'name': 'Club Sandwich / ክለብ ሳንድዊች', 'category': 'Lunch', 'price': 420},
            {'name': 'Beef Burger / የበሬ በርገር', 'category': 'Lunch', 'price': 480},
            {'name': 'Margherita Pizza / ማርጋሪታ ፒዛ', 'category': 'Lunch', 'price': 520},
            {'name': 'Chicken Pasta / የዶሮ ፓስታ', 'category': 'Lunch', 'price': 430},
        ]

        for data in products_data:
            cat = Category.objects.get(name=data['category'])
            product, created = Product.objects.get_or_create(
                name=data['name'],
                category=cat,
                defaults={'price': data['price']},
            )
            if created:
                self.stdout.write(f"  {data['name']} ({data['price']} Birr)")

        stock_data = [
            {'name': 'Coffee Beans', 'category': 'Beverages', 'quantity': 50, 'unit': 'kg', 'price_per_unit': 10, 'low_stock_threshold': 5},
            {'name': 'Sugar', 'category': 'Beverages', 'quantity': 30, 'unit': 'kg', 'price_per_unit': 2, 'low_stock_threshold': 5},
            {'name': 'Milk', 'category': 'Beverages', 'quantity': 40, 'unit': 'l', 'price_per_unit': 1, 'low_stock_threshold': 10},
            {'name': 'Tea Leaves', 'category': 'Beverages', 'quantity': 20, 'unit': 'kg', 'price_per_unit': 5, 'low_stock_threshold': 3},
            {'name': 'Cocoa Powder', 'category': 'Beverages', 'quantity': 10, 'unit': 'kg', 'price_per_unit': 5, 'low_stock_threshold': 2},
            {'name': 'Orange Juice Concentrate', 'category': 'Beverages', 'quantity': 15, 'unit': 'l', 'price_per_unit': 3, 'low_stock_threshold': 3},
            {'name': 'Mango Pulp', 'category': 'Beverages', 'quantity': 10, 'unit': 'l', 'price_per_unit': 4, 'low_stock_threshold': 2},
            {'name': 'Avocado', 'category': 'Beverages', 'quantity': 30, 'unit': 'pcs', 'price_per_unit': 3, 'low_stock_threshold': 10},
            {'name': 'Water Bottles', 'category': 'Beverages', 'quantity': 200, 'unit': 'pcs', 'price_per_unit': 0.5, 'low_stock_threshold': 50},
            {'name': 'Coca-Cola', 'category': 'Beverages', 'quantity': 100, 'unit': 'pcs', 'price_per_unit': 1, 'low_stock_threshold': 30},
            {'name': 'Fanta', 'category': 'Beverages', 'quantity': 100, 'unit': 'pcs', 'price_per_unit': 1, 'low_stock_threshold': 30},
            {'name': 'Sprite', 'category': 'Beverages', 'quantity': 100, 'unit': 'pcs', 'price_per_unit': 1, 'low_stock_threshold': 30},
            {'name': 'Croissants', 'category': 'Kitchen', 'quantity': 50, 'unit': 'pcs', 'price_per_unit': 3, 'low_stock_threshold': 10},
            {'name': 'Muffins', 'category': 'Kitchen', 'quantity': 40, 'unit': 'pcs', 'price_per_unit': 3, 'low_stock_threshold': 10},
            {'name': 'Flour', 'category': 'Kitchen', 'quantity': 25, 'unit': 'kg', 'price_per_unit': 1, 'low_stock_threshold': 5},
            {'name': 'Eggs', 'category': 'Kitchen', 'quantity': 200, 'unit': 'pcs', 'price_per_unit': 0.5, 'low_stock_threshold': 50},
            {'name': 'Cheese', 'category': 'Kitchen', 'quantity': 15, 'unit': 'kg', 'price_per_unit': 5, 'low_stock_threshold': 3},
            {'name': 'Chicken Breast', 'category': 'Kitchen', 'quantity': 25, 'unit': 'kg', 'price_per_unit': 8, 'low_stock_threshold': 5},
            {'name': 'Beef', 'category': 'Kitchen', 'quantity': 20, 'unit': 'kg', 'price_per_unit': 10, 'low_stock_threshold': 5},
            {'name': 'Bread', 'category': 'Kitchen', 'quantity': 100, 'unit': 'pcs', 'price_per_unit': 0.5, 'low_stock_threshold': 20},
            {'name': 'Ful', 'category': 'Kitchen', 'quantity': 15, 'unit': 'kg', 'price_per_unit': 2, 'low_stock_threshold': 3},
            {'name': 'Pizza Dough', 'category': 'Kitchen', 'quantity': 30, 'unit': 'pcs', 'price_per_unit': 3, 'low_stock_threshold': 10},
            {'name': 'Pasta', 'category': 'Kitchen', 'quantity': 20, 'unit': 'kg', 'price_per_unit': 2, 'low_stock_threshold': 5},
            {'name': 'Butter', 'category': 'Kitchen', 'quantity': 10, 'unit': 'kg', 'price_per_unit': 4, 'low_stock_threshold': 2},
            {'name': 'Cooking Gas', 'category': 'Kitchen', 'quantity': 2, 'unit': 'btl', 'price_per_unit': 35, 'low_stock_threshold': 1},
        ]

        for data in stock_data:
            item, created = StockItem.objects.get_or_create(
                name=data['name'],
                defaults={
                    'category': data.get('category', ''),
                    'quantity': data['quantity'],
                    'unit': data['unit'],
                    'price_per_unit': data['price_per_unit'],
                    'low_stock_threshold': data['low_stock_threshold'],
                },
            )
            if created:
                self.stdout.write(f"  Stock: {data['name']} ({data['quantity']} {data['unit']})")

        self.stdout.write(self.style.SUCCESS('Database seeded successfully!'))
