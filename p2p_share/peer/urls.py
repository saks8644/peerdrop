from django.urls import path
from . import views

app_name = 'peer'

urlpatterns = [
    # Main pages
    path('', views.index, name='index'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # File management
    path('files/', views.file_list, name='file_list'),
    path('files/upload/', views.upload_file, name='upload_file'),
    path('files/<uuid:file_id>/', views.file_detail, name='file_detail'),
    path('files/<uuid:file_id>/download/', views.download_file, name='download_file'),
    path('files/<uuid:file_id>/delete/', views.delete_file, name='delete_file'),
    
    # Peer management
    path('peers/', views.peer_list, name='peer_list'),
    path('peers/register/', views.register_peer, name='register_peer'),
    path('peers/<uuid:peer_id>/', views.peer_detail, name='peer_detail'),
    
    # API endpoints
    path('api/peers/status/', views.api_peer_status, name='api_peer_status'),
    path('api/files/search/', views.api_search_files, name='api_search_files'),
    path('api/transfers/', views.api_transfer_status, name='api_transfer_status'),
    path('api/transfers/<uuid:transfer_id>/', views.api_transfer_detail, name='api_transfer_detail'),
]