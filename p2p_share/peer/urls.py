from django.urls import path
from . import views

app_name = 'peer'

urlpatterns = [
    # CSRF Token
    path('api/csrf/', views.api_csrf_token, name='api_csrf_token'),
    
    # Public Stats
    path('api/peers/status/', views.api_peer_status, name='api_peer_status'),
    
    # Authentication APIs
    path('api/auth/register/', views.api_register, name='api_register'),
    path('api/auth/verify/', views.api_verify_email, name='api_verify_email'),
    path('api/auth/login/', views.api_login, name='api_login'),
    path('api/auth/logout/', views.api_logout, name='api_logout'),
    path('api/auth/me/', views.api_me, name='api_me'),
    
    # Dashboard API
    path('api/dashboard/', views.api_dashboard, name='api_dashboard'),
    
    # Files APIs
    path('api/files/', views.api_files_list, name='api_files_list'),
    path('api/files/upload/', views.api_upload_file, name='api_upload_file'),
    path('api/files/<uuid:file_id>/', views.api_file_detail, name='api_file_detail'),
    path('api/files/<uuid:file_id>/download/', views.api_download_file, name='api_download_file'),
    path('api/files/<uuid:file_id>/delete/', views.api_delete_file, name='api_delete_file'),
    
    # Peers APIs
    path('api/peers/', views.api_peer_list, name='api_peer_list'),
    path('api/peers/<uuid:peer_id>/', views.api_peer_detail, name='api_peer_detail'),
    
    # Transfer Tracking APIs
    path('api/transfers/', views.api_transfer_status, name='api_transfer_status'),
    path('api/transfers/<uuid:transfer_id>/', views.api_transfer_detail, name='api_transfer_detail'),
]