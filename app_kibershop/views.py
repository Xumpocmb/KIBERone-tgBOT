from itertools import product
from unicodedata import category
from django.db.models import Sum, F

from django.shortcuts import render, redirect
from django.contrib import messages

from app_kiberclub.models import UserData
from app_kibershop.models import Product, Category, Cart, OrderItem, Order


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
        user_in_db = UserData.objects.get(tg_id=request.session.get('user_tg_id'))
        order = Order.objects.create(
            user=user_in_db,
        )

        for item in Cart.objects.filter(user=UserData.objects.get(tg_id=request.session.get('user_tg_id'))):
            product_in_db = Product.objects.get(id=item.product.id)

            if product_in_db.quantity_in_stock < item.quantity:
                messages.error(request, f'Недостаточно товара на складе: {product_in_db.name}', extra_tags='danger')
                return redirect(request.META.get('HTTP_REFERER'))

            user_orders = Order.objects.filter(user=UserData.objects.get(tg_id=request.session.get('user_tg_id')))
            if user_orders.exists():
                kiberons_in_db = UserData.objects.get(
                    user_crm_id=request.session.get('user_crm_id')).kiberons_count_after_orders
                if kiberons_in_db < Cart.objects.filter(user=UserData.objects.get(tg_id=request.session.get('user_tg_id'))).total_sum():
                    messages.error(request, 'Недостаточно киберонов', extra_tags='danger')
                    return redirect(request.META.get('HTTP_REFERER'))

            if user_in_db.kiberons_count < Cart.objects.filter(user=UserData.objects.get(tg_id=request.session.get('user_tg_id'))).total_sum():
                messages.error(request, 'Недостаточно киберонов', extra_tags='danger')
                return redirect(request.META.get('HTTP_REFERER'))

            product_in_db.quantity_in_stock -= item.quantity
            if product_in_db.quantity_in_stock == 0:
                product_in_db.in_stock = False
            product_in_db.save()

            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
            )

        UserData.objects.filter(tg_id=request.session.get('user_tg_id')).update(
            kiberons_count_after_orders=user_in_db.kiberons_count - Cart.objects.filter(user=UserData.objects.get(tg_id=request.session.get('user_tg_id'))).total_sum(),
        )

        Cart.objects.filter(user=UserData.objects.get(tg_id=request.session.get('user_tg_id'))).delete()
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