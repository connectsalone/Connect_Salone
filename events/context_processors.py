from .models import Cart

def cart_count(request):
    count = 0
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            count = cart.cart_count
    else:
        if not request.session.session_key:
            request.session.create()
        count = request.session.get('cart_count', 0)
    return {'cart_count': count}
