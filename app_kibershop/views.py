import pandas as pd
from django.contrib import messages
from django.db.models import Sum, F
from django.shortcuts import render, redirect

from app_kiberclub.models import UserData
from app_kiberclub.views import GoogleSheet
from app_kibershop.models import Product, Category, Cart, OrderItem, Order


from logger_config import get_logger
logger = get_logger()

CREDENTIALS_FILE = 'kiberone-tg-bot-a43691efe721.json'


# Create your views here.
def catalog(request):
    categories = Category.objects.all()
    context = {
        'categories': categories,
    }
    return render(request, 'app_kibershop/catalog.html', context=context)


def add_to_cart(request, product_id):
    if request.method != 'POST':
        return redirect(request.META.get('HTTP_REFERER'))

    user_id = request.session.get('user_tg_id')
    if not user_id:
        messages.error(request, 'Вы не авторизованы', extra_tags='danger')
        return redirect(request.META.get('HTTP_REFERER'))

    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        messages.error(request, 'Товар не найден', extra_tags='danger')
        return redirect(request.META.get('HTTP_REFERER'))

    try:
        user = UserData.objects.get(tg_id=user_id)
    except UserData.DoesNotExist:
        messages.error(request, 'Вы не авторизованы', extra_tags='danger')
        return redirect(request.META.get('HTTP_REFERER'))

    cart_item, created = Cart.objects.get_or_create(
        user=user,
        product=product,
    )

    if not created:
        cart_item.quantity += 1
        cart_item.save()

    return redirect(request.META.get('HTTP_REFERER'))


def cart(request):
    return render(request, 'app_kibershop/cart_page.html')


def remove_from_cart(request, cart_id):
    cart_item = Cart.objects.get(id=cart_id)
    cart_item.delete()
    return redirect(request.META.get('HTTP_REFERER'))


def cart_minus(request, cart_id):
    cart_item = Cart.objects.get(id=cart_id)
    if cart_item.quantity == 1:
        return redirect(request.META.get('HTTP_REFERER'))
    cart_item.quantity -= 1
    cart_item.save()
    return redirect(request.META.get('HTTP_REFERER'))


def cart_plus(request, cart_id):
    cart_item = Cart.objects.get(id=cart_id)
    cart_item.quantity += 1
    cart_item.save()
    return redirect(request.META.get('HTTP_REFERER'))


def make_order(request):
    if request.method == 'POST':
        logger.info("Начало обработки заказа.")

        try:
            user_in_db = UserData.objects.get(tg_id=request.session.get('user_tg_id'))
            logger.info(f"Пользователь найден: {user_in_db}")
        except UserData.DoesNotExist:
            logger.error("Пользователь не найден.")
            return redirect(request.META.get('HTTP_REFERER'))

        order = Order.objects.create(user=user_in_db)
        logger.info(f"Создан заказ: {order}")

        total_sum = Cart.objects.filter(user=user_in_db).total_sum()
        logger.info(f"Сумма заказа: {total_sum}")
        logger.info(f"Кибероны пользователя: {user_in_db.kiberons_count}")

        if user_in_db.kiberons_count < total_sum:
            logger.error("Недостаточно киберонов для оформления заказа.")
            messages.error(request, 'Недостаточно киберонов', extra_tags='danger')
            return redirect(request.META.get('HTTP_REFERER'))

        for item in Cart.objects.filter(user=user_in_db):
            try:
                product_in_db = Product.objects.get(id=item.product.id)
                logger.info(f"Продукт найден: {product_in_db}")
            except Product.DoesNotExist:
                logger.error(f"Продукт не найден: {item.product.id}")
                return redirect(request.META.get('HTTP_REFERER'))

            if product_in_db.quantity_in_stock < item.quantity:
                logger.error(f"Недостаточно товара на складе: {product_in_db.name}")
                messages.error(request, f'Недостаточно товара на складе: {product_in_db.name}', extra_tags='danger')
                return redirect(request.META.get('HTTP_REFERER'))

            product_in_db.quantity_in_stock -= item.quantity
            if product_in_db.quantity_in_stock == 0:
                product_in_db.in_stock = False
            product_in_db.save()
            logger.info(f"Обновлены данные продукта: {product_in_db}")

            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
            )
            logger.info(f"Создан элемент заказа: {item.product.name} x {item.quantity}")

        user_in_db.kiberons_count_after_orders = user_in_db.kiberons_count - total_sum
        user_in_db.save()
        logger.info(f"Обновлен баланс пользователя после заказа: {user_in_db.kiberons_count_after_orders}")

        spreadsheet_url = request.session.get('spreadsheet_url')
        worksheet_name = request.session.get('worksheet_name')
        logger.info(f"URL таблицы: {spreadsheet_url}, Имя листа: {worksheet_name}")

        google_sheet = GoogleSheet(CREDENTIALS_FILE, spreadsheet_url, worksheet_name)

        try:
            df = google_sheet.load_data_from_google_sheet()
            if df is None:
                logger.error("Не удалось загрузить данные из Google Sheets.")
                return redirect('app_kiberclub:error_page')
        except Exception as e:
            logger.error(f"Ошибка при загрузке данных из Google Sheets: {e}")
            return redirect('app_kiberclub:error_page')

        for index, row in df.iterrows():
            if pd.notna(row["ID ребенка"]):
                if row["ID ребенка"] == user_in_db.user_crm_id:
                    row["Кибершоп"] = row["Кибершоп"] + '\n'.join(
                        [f'Товар: {item.product.name} | Количество: {item.quantity} | Кибероны: {item.product.price * item.quantity}' for item in
                         Cart.objects.filter(user=user_in_db)])
                    logger.info(f"Обновление строки {index} с данными\n: {row['Кибершоп']}")

        try:
            google_sheet.save_data_to_google_sheet(df, worksheet_name)
            logger.info("Данные успешно сохранены в Google Sheets.")
        except Exception as e:
            logger.error(f"Ошибка при сохранении данных в Google Sheets: {e}")
            return redirect('app_kiberclub:error_page')

        Cart.objects.filter(user=user_in_db).delete()
        logger.info("Корзина пользователя очищена.")

    return redirect('app_kibershop:profile_page')


def profile_page(request):
    orders = Order.objects.filter(user=UserData.objects.get(tg_id=request.session.get('user_tg_id')))
    order_items = OrderItem.objects.filter(order__in=orders)
    total_sum = order_items.aggregate(total_sum=Sum(F('product__price') * F('quantity')))['total_sum'] or 0
    total_quantity = order_items.aggregate(total_quantity=Sum('quantity'))['total_quantity'] or 0

    context = {
        'order_items': order_items,
        'total_sum': total_sum,
        'total_quantity': total_quantity,
    }
    return render(request, 'app_kibershop/profile_page.html', context=context)
