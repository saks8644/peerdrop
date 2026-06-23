from django.db import models
from django.utils import timezone
from django.contrib import admin
from django.contrib.auth.models import User
import uuid
import hashlib
import os


class Peer(models.Model):
    """Represents a peer in the P2P network"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='peer')
    peer_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    ip_address = models.GenericIPAddressField()
    port = models.IntegerField(default=8000)
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-last_seen']

    def __str__(self):
        return f"{self.username} ({self.ip_address}:{self.port})"

    @property
    def username(self):
        return self.user.username

    def mark_online(self):
        self.is_online = True
        self.last_seen = timezone.now()
        self.save()

    def mark_offline(self):
        self.is_online = False
        self.save()


class SharedFile(models.Model):
    """Represents a file shared by a peer"""
    FILE_TYPES = [
        ('document', 'Document'),
        ('image', 'Image'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('archive', 'Archive'),
        ('other', 'Other'),
    ]

    file_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    peer = models.ForeignKey(Peer, on_delete=models.CASCADE, related_name='shared_files')
    filename = models.CharField(max_length=255)
    original_filename = models.CharField(max_length=255)  # Store original name
    file_path = models.FileField(upload_to='shared_files/')
    file_size = models.BigIntegerField()  # Size in bytes
    file_hash = models.CharField(max_length=64)  # SHA-256 hash
    file_type = models.CharField(max_length=20, choices=FILE_TYPES, default='other')
    description = models.TextField(blank=True)
    is_available = models.BooleanField(default=True)
    download_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['peer', 'filename', 'file_hash']

    def __str__(self):
        return f"{self.filename} by {self.peer.username}"

    def save(self, *args, **kwargs):
        if self.file_path and not self.file_hash:
            # Calculate file hash
            self.file_hash = self.calculate_file_hash()
        if not self.file_size and self.file_path:
            self.file_size = self.file_path.size
        if not self.file_type or self.file_type == 'other':
            self.file_type = self.get_file_type()
        super().save(*args, **kwargs)

    def calculate_file_hash(self):
        """Calculate SHA-256 hash of the file"""
        hash_sha256 = hashlib.sha256()
        if self.file_path:
            for chunk in iter(lambda: self.file_path.read(4096), b""):
                hash_sha256.update(chunk)
            self.file_path.seek(0)  # Reset file pointer
        return hash_sha256.hexdigest()

    def get_file_type(self):
        """Determine file type based on extension"""
        if not self.filename:
            return 'other'

        ext = os.path.splitext(self.filename)[1].lower()

        if ext in ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt']:
            return 'document'
        elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp']:
            return 'image'
        elif ext in ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.webm']:
            return 'video'
        elif ext in ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma']:
            return 'audio'
        elif ext in ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2']:
            return 'archive'
        else:
            return 'other'

    @admin.display(description="Size")
    def get_file_size_display(self):
        """Return a human-readable file size."""
        size = self.file_size
        if not size and self.file_path:
            size = self.file_path.size

        if size < 1024:
            return f"{size} B"
        elif size < 1024**2:
            return f"{size / 1024:.2f} KB"
        elif size < 1024**3:
            return f"{size / 1024**2:.2f} MB"
        else:
            return f"{size / 1024**3:.2f} GB"

    get_file_size_display.short_description = "File Size"

    @property
    def file_size_display(self):
        return self.get_file_size_display()

    def increment_download_count(self):
        """Increment download counter"""
        self.download_count += 1
        self.save(update_fields=['download_count'])


class FileTransfer(models.Model):
    """Track file transfer sessions between peers"""
    TRANSFER_STATUS = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    transfer_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    shared_file = models.ForeignKey(SharedFile, on_delete=models.CASCADE, related_name='transfers')
    requester_peer = models.ForeignKey(Peer, on_delete=models.CASCADE, related_name='requested_transfers')
    provider_peer = models.ForeignKey(Peer, on_delete=models.CASCADE, related_name='provided_transfers')
    status = models.CharField(max_length=20, choices=TRANSFER_STATUS, default='pending')
    bytes_transferred = models.BigIntegerField(default=0)
    transfer_speed = models.FloatField(null=True, blank=True)  # bytes per second
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Transfer {self.transfer_id} - {self.shared_file.filename}"

    def get_progress_percentage(self):
        """Calculate transfer progress percentage"""
        if self.shared_file.file_size == 0:
            return 0
        return (self.bytes_transferred / self.shared_file.file_size) * 100

    def start_transfer(self):
        """Mark transfer as started"""
        self.status = 'active'
        self.started_at = timezone.now()
        self.save()

    def complete_transfer(self):
        """Mark transfer as completed"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.bytes_transferred = self.shared_file.file_size
        self.save()
        # Increment download count for the file
        self.shared_file.increment_download_count()

    def fail_transfer(self):
        """Mark transfer as failed"""
        self.status = 'failed'
        self.save()


class PeerConnection(models.Model):
    """Track active connections between peers"""
    connection_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    peer1 = models.ForeignKey(Peer, on_delete=models.CASCADE, related_name='connections_as_peer1')
    peer2 = models.ForeignKey(Peer, on_delete=models.CASCADE, related_name='connections_as_peer2')
    is_active = models.BooleanField(default=True)
    established_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['peer1', 'peer2']

    def __str__(self):
        return f"Connection: {self.peer1.username} <-> {self.peer2.username}"
