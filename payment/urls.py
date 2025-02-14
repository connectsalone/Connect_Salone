from django.urls import path
from . import views

urlpatterns = [
    # Payment views
    path('payment/orange/', views.orange_payment, name='orange_payment'),

    # Ticket views
    path('ticket/view/<int:ticket_id>/', views.ticket_view, name='ticket_view'),
    path('ticket/download/<int:ticket_id>/', views.download_ticket, name='download_ticket'),

    # Add a view for displaying all the user's tickets
    path('tickets/', views.tickets_view, name='tickets'),  # New tickets list page
    path('scan_ticket/', views.scan_ticket, name='scan_ticket'),
]
