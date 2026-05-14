from django.contrib import admin
from .models import Peer, SharedFile, FileTransfer, PeerConnection

@admin.register(Peer)
class PeerAdmin(admin.ModelAdmin):
    list_display = ('username', 'ip_address', 'port', 'is_online', 'last_seen', 'created_at')
    search_fields = ('username', 'ip_address')
    list_filter = ('is_online',)
    ordering = ('-last_seen',)


@admin.register(SharedFile)
class SharedFileAdmin(admin.ModelAdmin):
    list_display = (
        'filename',
        'peer',
        'file_type',
        'file_size_display',   # ✅ use the decorated wrapper
        'is_available',
        'download_count',
        'created_at',
    )
    search_fields = ('filename', 'peer__username', 'description')
    list_filter = ('file_type', 'is_available')
    readonly_fields = ('file_hash', 'file_size', 'download_count', 'created_at', 'updated_at')

    @admin.display(description="File Size")
    def file_size_display(self, obj):
        return obj.get_file_size_display()




@admin.register(FileTransfer)
class FileTransferAdmin(admin.ModelAdmin):
    list_display = ('shared_file', 'requester_peer', 'provider_peer', 'status', 'bytes_transferred', 'transfer_speed', 'started_at', 'completed_at')
    search_fields = ('shared_file__filename', 'requester_peer__username', 'provider_peer__username')
    list_filter = ('status',)
    readonly_fields = ('created_at', 'started_at', 'completed_at')


@admin.register(PeerConnection)
class PeerConnectionAdmin(admin.ModelAdmin):
    list_display = ('peer1', 'peer2', 'is_active', 'established_at', 'last_activity')
    search_fields = ('peer1__username', 'peer2__username')
    list_filter = ('is_active',)
    readonly_fields = ('established_at', 'last_activity')
