from django.urls import path
from payment.views import orange_payment, ticket, download_ticket, scan_ticket, tickets_view

urlpatterns = [
    # Payment views
    path('payment/orange/', orange_payment, name='orange_payment'),

    # Ticket views
    path('ticket/view/<int:ticket_id>/', ticket, name='ticket_view'),
    path('ticket/download/<int:ticket_id>/', download_ticket, name='download_ticket'),


    # Add a view for displaying all the user's tickets
    path('tickets/', tickets_view, name='tickets'),  # New tickets list page
    path('scan_ticket/', scan_ticket, name='scan_ticket'),
]