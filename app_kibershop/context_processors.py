from app_kiberclub.models import UserData
from app_kibershop.models import Cart, Order


def cart(request):
    if not request.session.get('user_tg_id'):
        return {'carts': []}
    carts = Cart.objects.filter(user=UserData.objects.get(tg_id=request.session.get('user_tg_id')))
    return {'carts': carts if carts.exists() else []}


def kiberons(request):
    if request.session.get('user_tg_id'):
        user_orders = Order.objects.filter(user=UserData.objects.get(tg_id=request.session.get('user_tg_id')))
        if user_orders.exists():
            user_data = UserData.objects.filter(tg_id=request.session.get('user_tg_id')).first()
            if user_data and user_data.kiberons_count_after_orders > 0:
                return {'kiberons': user_data.kiberons_count_after_orders}

    if not request.session.get('user_crm_id'):
        return {'kiberons': 0}
    user_crm_id = request.session.get('user_crm_id')
    user_data = UserData.objects.filter(user_crm_id=user_crm_id).first()
    if user_data:
        return {'kiberons': user_data.kiberons_count}
    return {'kiberons': 0}
