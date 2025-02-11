from django.urls import path
from events.views import (
    home, about, event_list, contact, single_event, starter_page, scan_ticket,
    calendar_view, get_events, cart_page, add_to_cart, update_cart
)

urlpatterns = [
    # Traditional views for HTML form-based authentication
    path('home/', home, name='home'),
    path('about/', about, name='about'),
    path('event-list/', event_list, name='event-list'),
    path('contact/', contact, name='contact'),
    path('single-event/<event_id>', single_event, name='single-event'),
    path('starter-page/', starter_page, name='starter-page'),
    path('scan_ticket/<str:signed_token>/', scan_ticket, name='scan_ticket'),

    
    path('calendar/', calendar_view, name='calendar_view'),
    path('get_events/', get_events, name='get_events'),


   
    path('cart/', cart_page, name='cart_page'),
    path("cart/add/<int:event_id>/", add_to_cart, name="add_to_cart"),
    path("cart/update/<int:event_id>/", update_cart, name="update_cart"),
    
    



   
  

   
    
    
]