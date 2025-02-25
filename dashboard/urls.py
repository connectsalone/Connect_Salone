from django.urls import path
from .views import (
    event_detail, event_view_count, event_analytics, event_search,
    add_event, edit_event, delete_event, sponsor_list, sponsor_add,
    sponsor_edit, sponsor_delete, ticket_list, dashboard, event_list
)

urlpatterns = [
    # Event URLs
    path('events/', event_list, name='events-lists'),  # URL for event list
    path('events/<int:pk>/', event_detail, name='event-detail'),
    path('events/view-count/', event_view_count, name='event-view-count'),
    path('events/analytics/', event_analytics, name='event-analytics'),
    path('events/search/', event_search, name='event-search'),
    path('events/add/', add_event, name='add-event'),
    path('events/<int:event_id>/edit/', edit_event, name='edit-event'),
    path('events/<int:event_id>/delete/', delete_event, name='delete-event'),

    # Sponsor URLs
    path('sponsors/', sponsor_list, name='sponsor-list'),
    path('sponsors/add/', sponsor_add, name='sponsor-add'),
    path('sponsors/<int:pk>/edit/', sponsor_edit, name='sponsor-edit'),
    path('sponsors/<int:pk>/delete/', sponsor_delete, name='sponsor-delete'),

    # Ticket URLs
    path('tickets/', ticket_list, name='ticket-list'),

    # Dashboard URL
    path('dashboard/', dashboard, name='dashboard'),
]


