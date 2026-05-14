from django.db import models
from django.shortcuts import render, get_object_or_404, redirect
from django.http import FileResponse, JsonResponse
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.conf import settings
import os
from .models import Peer, SharedFile, FileTransfer, PeerConnection
from .forms import FileUploadForm, PeerRegistrationForm


def index(request):
    """Main landing page"""
    total_peers = Peer.objects.filter(is_online=True).count()
    total_files = SharedFile.objects.filter(is_available=True).count()
    recent_files = SharedFile.objects.filter(is_available=True)[:6]
    context = {
        'total_peers': total_peers,
        'total_files': total_files,
        'recent_files': recent_files,
    }
    return render(request, 'index.html', context)


def dashboard(request):
    """Peer dashboard showing their files and activity"""
    peer_id = request.session.get('peer_id')
    if not peer_id:
        return redirect('peer:register_peer')
    
    try:
        peer = Peer.objects.get(peer_id=peer_id)
    except Peer.DoesNotExist:
        return redirect('peer:register_peer')

    my_files = SharedFile.objects.filter(peer=peer, is_available=True)
    recent_transfers = FileTransfer.objects.filter(
        Q(requester_peer=peer) | Q(provider_peer=peer)
    )[:10]
    connected_peers = Peer.objects.filter(is_online=True).exclude(id=peer.id)[:10]

    # Calculate total downloads (optimized)
    total_downloads = my_files.aggregate(total=models.Sum('download_count'))['total'] or 0

    context = {
        'peer': peer,
        'my_files': my_files,
        'recent_transfers': recent_transfers,
        'connected_peers': connected_peers,
        'total_downloads': total_downloads,
    }
    return render(request, 'peer/dashboard.html', context)


def file_list(request):
    """List all available files from all peers"""
    files = SharedFile.objects.filter(is_available=True).select_related('peer')

    # Search query
    query = request.GET.get('search', '').strip()
    if query:
        files = files.filter(
            Q(filename__icontains=query) |
            Q(description__icontains=query) |
            Q(peer__username__icontains=query)
        )

    # Filter by file type only if valid
    file_type = request.GET.get('type', '').strip()
    valid_types = [choice[0] for choice in SharedFile.FILE_TYPES]  # get all type keys
    if file_type and file_type in valid_types:
        files = files.filter(file_type=file_type)

    # Pagination
    paginator = Paginator(files, 12)  # 12 files per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'files': page_obj.object_list,
        'query': query,
        'file_types': SharedFile.FILE_TYPES,
        'selected_type': file_type,
    }

    return render(request, 'peer/file_list.html', context)

def upload_file(request):
    """Handle file upload"""
    peer_id = request.session.get('peer_id')
    if not peer_id:
        return redirect('peer:register_peer')
    
    try:
        peer = Peer.objects.get(peer_id=peer_id)
    except Peer.DoesNotExist:
        return redirect('peer:register_peer')
    
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            shared_file = form.save(commit=False)
            shared_file.peer = peer
            shared_file.original_filename = request.FILES['file_path'].name
            shared_file.filename = shared_file.original_filename
            try:
                with transaction.atomic():
                    shared_file.save()
            except IntegrityError:
                form.add_error('file_path', 'You have already shared this file.')
            else:
                messages.success(request, f'File "{shared_file.filename}" uploaded successfully!')
                return redirect('peer:dashboard')
    else:
        form = FileUploadForm()
    
    return render(request, 'peer/upload.html', {'form': form})


def file_detail(request, file_id):
    """Show details of a specific file"""
    file = get_object_or_404(SharedFile, file_id=file_id, is_available=True)
    peer_id = request.session.get('peer_id')
    is_owner = False
    
    if peer_id:
        try:
            peer = Peer.objects.get(peer_id=peer_id)
            is_owner = file.peer == peer
        except Peer.DoesNotExist:
            pass
    
    recent_transfers = FileTransfer.objects.filter(shared_file=file)[:5]
    
    context = {
        'file': file,
        'is_owner': is_owner,
        'recent_transfers': recent_transfers,
    }
    return render(request, 'peer/file_detail.html', context)


def download_file(request, file_id):
    """Handle file download"""
    file = get_object_or_404(SharedFile, file_id=file_id, is_available=True)
    
    if not file.file_path or not os.path.exists(file.file_path.path):
        messages.error(request, 'File not found on disk.')
        return redirect('peer:file_detail', file_id=file_id)
    
    peer_id = request.session.get('peer_id')
    requester_peer = None
    
    if peer_id:
        try:
            requester_peer = Peer.objects.get(peer_id=peer_id)
        except Peer.DoesNotExist:
            pass
    
    # Create transfer record for non-owner downloads
    transfer = None
    if requester_peer and requester_peer != file.peer:
        transfer = FileTransfer.objects.create(
            shared_file=file,
            requester_peer=requester_peer,
            provider_peer=file.peer,
            status='active'
        )
        transfer.start_transfer()
    
    try:
        response = FileResponse(
            open(file.file_path.path, 'rb'),
            as_attachment=True,
            filename=file.original_filename,
        )

        file.download_count = models.F('download_count') + 1
        file.save(update_fields=['download_count'])

        if transfer:
            transfer.status = 'completed'
            transfer.completed_at = timezone.now()
            transfer.bytes_transferred = file.file_size
            transfer.save(update_fields=['status', 'completed_at', 'bytes_transferred'])

        return response
    except Exception as e:
        messages.error(request, f'Error downloading file: {str(e)}')
        if transfer:
            transfer.status = 'failed'
            transfer.save(update_fields=['status'])
        return redirect('peer:file_detail', file_id=file_id)


def delete_file(request, file_id):
    """Delete a file (only owner can delete)"""
    file = get_object_or_404(SharedFile, file_id=file_id)
    peer_id = request.session.get('peer_id')
    
    if not peer_id:
        return redirect('peer:register_peer')
    
    try:
        peer = Peer.objects.get(peer_id=peer_id)
        if file.peer != peer:
            messages.error(request, 'You can only delete your own files.')
            return redirect('peer:file_detail', file_id=file_id)
    except Peer.DoesNotExist:
        return redirect('peer:register_peer')
    
    if request.method == 'POST':
        filename = file.filename
        # Remove file from disk if it exists
        if file.file_path and os.path.exists(file.file_path.path):
            try:
                os.remove(file.file_path.path)
            except OSError:
                pass  # File might be in use or already deleted
        
        file.delete()
        messages.success(request, f'File "{filename}" deleted successfully.')
        return redirect('peer:dashboard')
    
    return render(request, 'peer/delete_confirm.html', {'file': file})


def peer_list(request):
    """List all online peers with search and pagination"""
    peers = Peer.objects.filter(is_online=True).order_by('-last_seen')
    query = request.GET.get('search', '')

    if query:
        peers = peers.filter(username__icontains=query)

    paginator = Paginator(peers, 12)  # 🔹 12 per page (your grid is 3x4)
    page_number = request.GET.get('page') or 1
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,            # 🔹 used in template
        "query": query,                  # 🔹 used in template
        "paginator": paginator,          # extra (not strictly required)
        "page_number": page_obj.number,  # extra (not strictly required)
        "is_paginated": page_obj.has_other_pages(),
    }
    return render(request, "peer/peer_list.html", context)


def register_peer(request):
    """Register a new peer or login existing peer"""
    if request.method == 'POST':
        form = PeerRegistrationForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            peer, created = Peer.objects.get_or_create(
                username=username,
                defaults={
                    'ip_address': get_client_ip(request),
                    'port': 8000,
                }
            )
            peer.ip_address = get_client_ip(request)
            peer.mark_online()
            request.session['peer_id'] = str(peer.peer_id)
            
            if created:
                messages.success(request, f'Welcome {username}! You are now connected to PeerDrop.')
            else:
                messages.success(request, f'Welcome back {username}!')
            
            return redirect('peer:dashboard')
    else:
        form = PeerRegistrationForm()
    
    return render(request, 'peer/register.html', {'form': form})


def peer_detail(request, peer_id):
    """Show details of a specific peer"""
    peer = get_object_or_404(Peer, peer_id=peer_id)
    shared_files = SharedFile.objects.filter(peer=peer, is_available=True)[:10]
    current_peer_id = request.session.get('peer_id')
    is_connected = False
    
    if current_peer_id:
        try:
            current_peer = Peer.objects.get(peer_id=current_peer_id)
            is_connected = PeerConnection.objects.filter(
                Q(peer1=current_peer, peer2=peer) | Q(peer1=peer, peer2=current_peer),
                is_active=True
            ).exists()
        except Peer.DoesNotExist:
            pass
    
    context = {
        'peer': peer,
        'shared_files': shared_files,
        'is_connected': is_connected,
    }
    return render(request, 'peer/peer_detail.html', context)


@csrf_exempt
def api_peer_status(request):
    """API endpoint for peer status"""
    online_peers = Peer.objects.filter(is_online=True).count()
    total_files = SharedFile.objects.filter(is_available=True).count()
    active_transfers = FileTransfer.objects.filter(status='active').count()
    
    return JsonResponse({
        'status': 'online',
        'peers_online': online_peers,
        'total_files': total_files,
        'active_transfers': active_transfers,
        'timestamp': timezone.now().isoformat(),
    })


@csrf_exempt
def api_search_files(request):
    """API endpoint for file search"""
    query = request.GET.get('q', '')
    file_type = request.GET.get('type', '')
    files = SharedFile.objects.filter(is_available=True)
    
    if query:
        files = files.filter(
            Q(filename__icontains=query) |
            Q(description__icontains=query)
        )
    
    if file_type:
        files = files.filter(file_type=file_type)
    
    files_data = []
    for file in files[:20]:
        files_data.append({
            'file_id': str(file.file_id),
            'filename': file.filename,
            'file_size': file.get_file_size_display(),
            'file_type': file.file_type,
            'peer_username': file.peer.username,
            'download_count': file.download_count,
            'created_at': file.created_at.isoformat(),
        })
    
    return JsonResponse({
        'files': files_data,
        'total_count': files.count(),
    })


@csrf_exempt
def api_transfer_status(request):
    """API endpoint for transfer status"""
    peer_id = request.session.get('peer_id')
    if not peer_id:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    try:
        peer = Peer.objects.get(peer_id=peer_id)
        transfers = FileTransfer.objects.filter(
            Q(requester_peer=peer) | Q(provider_peer=peer)
        ).order_by('-created_at')[:10]
        
        transfers_data = []
        for transfer in transfers:
            transfers_data.append({
                'transfer_id': str(transfer.transfer_id),
                'filename': transfer.shared_file.filename,
                'status': transfer.status,
                'progress': transfer.get_progress_percentage(),
                'created_at': transfer.created_at.isoformat(),
            })
        
        return JsonResponse({'transfers': transfers_data})
    except Peer.DoesNotExist:
        return JsonResponse({'error': 'Peer not found'}, status=404)


def api_transfer_detail(request, transfer_id):
    """API endpoint for specific transfer details"""
    transfer = get_object_or_404(FileTransfer, transfer_id=transfer_id)
    
    return JsonResponse({
        'transfer_id': str(transfer.transfer_id),
        'filename': transfer.shared_file.filename,
        'file_size': transfer.shared_file.file_size,
        'status': transfer.status,
        'bytes_transferred': transfer.bytes_transferred,
        'progress': transfer.get_progress_percentage(),
        'transfer_speed': transfer.transfer_speed,
        'requester': transfer.requester_peer.username,
        'provider': transfer.provider_peer.username,
        'started_at': transfer.started_at.isoformat() if transfer.started_at else None,
        'completed_at': transfer.completed_at.isoformat() if transfer.completed_at else None,
    })


def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip or '127.0.0.1'
