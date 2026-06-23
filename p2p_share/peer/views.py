import json
import os
import urllib.request
from functools import wraps
from django.db import models, IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.http import JsonResponse, FileResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.middleware.csrf import get_token
from django.utils import timezone
from django.conf import settings
from .models import Peer, SharedFile, FileTransfer, PeerConnection


# Decorator for REST APIs that require an authenticated peer session
def api_peer_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        if not hasattr(request.user, 'peer'):
            return JsonResponse({'error': 'Peer profile required'}, status=403)
        return view_func(request, *args, **kwargs)
    return _wrapped_view


# Helper to get client IP address
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip or '127.0.0.1'


# Helper to send email via Resend HTTPS API or print to Console log
def send_verification_email(username, email, verification_link):
    # Always print verification link to the server console as a backup
    print(f"\n[EMAIL BACKUP] Verification link for user '{username}': {verification_link}\n", flush=True)
    
    resend_api_key = os.getenv('RESEND_API_KEY', '')
    
    if resend_api_key:
        url = "https://api.resend.com/emails"
        from_email = os.getenv('DEFAULT_FROM_EMAIL', 'onboarding@resend.dev')
        
        payload = {
            "from": from_email,
            "to": [email],
            "subject": "Verify your PeerDrop Account",
            "text": (
                f"Hi {username},\n\n"
                f"Please verify your PeerDrop account by clicking the link below:\n\n"
                f"{verification_link}\n\n"
                f"Happy sharing!\n"
                f"The PeerDrop Team"
            )
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={
                "Authorization": f"Bearer {resend_api_key}",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        
        try:
            with urllib.request.urlopen(req) as response:
                response.read()
            print(f"Successfully sent verification email to {email} via Resend.", flush=True)
        except urllib.error.HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode('utf-8')
            except Exception:
                pass
            print(f"Resend API HTTP Error {e.code}: {e.reason}. Response body: {error_body}", flush=True)
            print_to_console(username, email, verification_link)
        except Exception as e:
            # Fall back to console log if API fails
            print(f"Resend API unexpected error: {str(e)}. Falling back to console logging.", flush=True)
            print_to_console(username, email, verification_link)
    else:
        print_to_console(username, email, verification_link)


def print_to_console(username, email, verification_link):
    print("-------------------------------------------------------------------------------", flush=True)
    print("Content-Type: text/plain; charset=\"utf-8\"", flush=True)
    print("Subject: Verify your PeerDrop Account", flush=True)
    print("From: noreply@peerdrop.local", flush=True)
    print(f"To: {email}", flush=True)
    print(f"\nHi {username},\n\nPlease verify your PeerDrop account by clicking the link below:\n\n{verification_link}\n\nHappy sharing!\nThe PeerDrop Team", flush=True)
    print("-------------------------------------------------------------------------------", flush=True)


# CSRF Token Provider
@ensure_csrf_cookie
def api_csrf_token(request):
    """Exposes a CSRF token to client cookies"""
    return JsonResponse({'csrfToken': get_token(request)})


# Public stats endpoint
def api_peer_status(request):
    """API endpoint for public peer status"""
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


# Authentication API Endpoints
@csrf_exempt
def api_register(request):
    """Handles User Registration and creates an active user account directly"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body)
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        if not username or not email or not password:
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        if User.objects.filter(username=username).exists():
            return JsonResponse({'error': 'Username already exists'}, status=400)
        
        if User.objects.filter(email=email).exists():
            return JsonResponse({'error': 'Email already registered'}, status=400)
        
        # Create active user (email verification disabled)
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_active=True
        )
        print(f"[REGISTER SUCCESS] Registered user '{username}' (email: '{email}')", flush=True)
        
        # Create associated Peer
        Peer.objects.create(
            user=user,
            ip_address=get_client_ip(request),
            port=settings.P2P_DEFAULT_PORT
        )
        
        return JsonResponse({'message': 'Registration successful. You can now log in.'}, status=201)
    except Exception as e:
        print(f"[REGISTER FAILED] Error registering '{username if 'username' in locals() else 'unknown'}': {str(e)}", flush=True)
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def api_verify_email(request):
    """Verifies user using uidb64 and token"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body)
        uidb64 = data.get('uidb64')
        token = data.get('token')
        
        if not uidb64 or not token:
            return JsonResponse({'error': 'Missing fields'}, status=400)
            
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None
            
        if user is not None and default_token_generator.check_token(user, token):
            user.is_active = True
            user.save()
            # Mark peer online
            if hasattr(user, 'peer'):
                user.peer.mark_online()
            return JsonResponse({'message': 'Account verified successfully!'})
        else:
            return JsonResponse({'error': 'Invalid or expired token'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def api_login(request):
    """Authenticates user and returns session data"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            print(f"[LOGIN FAILED] Username '{username}' does not exist in the database.", flush=True)
            return JsonResponse({'error': 'Invalid credentials'}, status=401)
            
        if user.check_password(password):
            if not user.is_active:
                print(f"[LOGIN FAILED] User '{username}' is inactive.", flush=True)
                return JsonResponse({'error': 'Please verify your email first.'}, status=403)
                
            login(request, user)
            print(f"[LOGIN SUCCESS] User '{username}' logged in successfully.", flush=True)
            
            # Ensure peer exists and mark online
            peer, created = Peer.objects.get_or_create(
                user=user,
                defaults={
                    'ip_address': get_client_ip(request),
                    'port': settings.P2P_DEFAULT_PORT
                }
            )
            peer.ip_address = get_client_ip(request)
            peer.mark_online()
            
            return JsonResponse({
                'message': 'Login successful',
                'user': {
                    'username': user.username,
                    'email': user.email,
                    'peer_id': str(peer.peer_id),
                    'ip_address': peer.ip_address,
                    'port': peer.port,
                    'is_online': peer.is_online
                }
            })
        else:
            print(f"[LOGIN FAILED] Password mismatch for user '{username}'.", flush=True)
            return JsonResponse({'error': 'Invalid credentials'}, status=401)
    except Exception as e:
        print(f"[LOGIN EXCEPTION] Error logging in '{username if 'username' in locals() else 'unknown'}': {str(e)}", flush=True)
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def api_logout(request):
    """Logs out user and sets peer offline"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        
    if request.user.is_authenticated:
        if hasattr(request.user, 'peer'):
            request.user.peer.mark_offline()
        logout(request)
        
    return JsonResponse({'message': 'Logged out successfully'})


@api_peer_required
def api_me(request):
    """Retrieves authenticated peer profiles"""
    peer = request.user.peer
    return JsonResponse({
        'user': {
            'username': request.user.username,
            'email': request.user.email,
            'peer_id': str(peer.peer_id),
            'ip_address': peer.ip_address,
            'port': peer.port,
            'is_online': peer.is_online,
        }
    })


# Dashboard API Endpoint
@api_peer_required
def api_dashboard(request):
    """Returns dashboard counts, user files, recent transfers, and peers"""
    peer = request.user.peer
    my_files = SharedFile.objects.filter(peer=peer, is_available=True)
    recent_transfers = FileTransfer.objects.filter(
        Q(requester_peer=peer) | Q(provider_peer=peer)
    ).order_by('-created_at')[:10]
    connected_peers = Peer.objects.filter(is_online=True).exclude(id=peer.id)[:10]
    total_downloads = my_files.aggregate(total=models.Sum('download_count'))['total'] or 0
    
    my_files_data = []
    for file in my_files:
        my_files_data.append({
            'file_id': str(file.file_id),
            'filename': file.filename,
            'file_size_display': file.file_size_display,
            'file_type': file.file_type,
            'download_count': file.download_count,
            'created_at': file.created_at.isoformat(),
        })
        
    transfers_data = []
    for t in recent_transfers:
        transfers_data.append({
            'transfer_id': str(t.transfer_id),
            'filename': t.shared_file.filename,
            'direction': 'download' if t.requester_peer == peer else 'upload',
            'peer_username': t.provider_peer.user.username if t.requester_peer == peer else t.requester_peer.user.username,
            'status': t.status,
            'created_at': t.created_at.isoformat(),
        })
        
    peers_data = []
    for p in connected_peers:
        peers_data.append({
            'peer_id': str(p.peer_id),
            'username': p.user.username,
            'files_count': p.shared_files.count(),
        })
        
    return JsonResponse({
        'peer': {
            'username': peer.user.username,
            'peer_id': str(peer.peer_id),
            'ip_address': peer.ip_address,
            'port': peer.port,
            'is_online': peer.is_online,
            'last_seen': peer.last_seen.isoformat(),
        },
        'my_files': my_files_data,
        'recent_transfers': transfers_data,
        'connected_peers': peers_data,
        'total_downloads': total_downloads
    })


# Files Management REST APIs
@api_peer_required
def api_files_list(request):
    """Lists files with search and type filters"""
    files = SharedFile.objects.filter(is_available=True).select_related('peer__user')
    
    query = request.GET.get('search', '').strip()
    if query:
        files = files.filter(
            Q(filename__icontains=query) |
            Q(description__icontains=query) |
            Q(peer__user__username__icontains=query)
        )

    file_type = request.GET.get('type', '').strip()
    valid_types = [choice[0] for choice in SharedFile.FILE_TYPES]
    if file_type and file_type in valid_types:
        files = files.filter(file_type=file_type)

    files_data = []
    for file in files:
        files_data.append({
            'file_id': str(file.file_id),
            'filename': file.filename,
            'file_size_display': file.file_size_display,
            'file_type': file.file_type,
            'description': file.description,
            'download_count': file.download_count,
            'created_at': file.created_at.isoformat(),
            'peer': {
                'username': file.peer.user.username,
                'peer_id': str(file.peer.peer_id),
            }
        })
    return JsonResponse({'files': files_data})


@csrf_exempt
@api_peer_required
def api_upload_file(request):
    """Accepts file upload and adds to shared library"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        
    if 'file' not in request.FILES:
        return JsonResponse({'error': 'No file uploaded'}, status=400)
        
    uploaded_file = request.FILES['file']
    description = request.POST.get('description', '')
    
    max_size = getattr(settings, 'P2P_MAX_FILE_SIZE', 100 * 1024 * 1024)
    if uploaded_file.size > max_size:
        return JsonResponse({'error': f'File too large. Max size is {max_size // (1024*1024)}MB.'}, status=400)
        
    shared_file = SharedFile(
        peer=request.user.peer,
        file_path=uploaded_file,
        original_filename=uploaded_file.name,
        filename=uploaded_file.name,
        description=description,
    )
    
    try:
        with transaction.atomic():
            shared_file.save()
    except IntegrityError:
        return JsonResponse({'error': 'You have already shared this file.'}, status=400)
        
    return JsonResponse({
        'message': 'File uploaded successfully',
        'file': {
            'file_id': str(shared_file.file_id),
            'filename': shared_file.filename,
            'file_size_display': shared_file.file_size_display,
        }
    }, status=201)


@api_peer_required
def api_file_detail(request, file_id):
    """Details details for a file and historical logs"""
    file = get_object_or_404(SharedFile, file_id=file_id, is_available=True)
    is_owner = file.peer == request.user.peer
    recent_transfers = FileTransfer.objects.filter(shared_file=file)[:5]
    
    transfers_data = []
    for t in recent_transfers:
        transfers_data.append({
            'transfer_id': str(t.transfer_id),
            'requester': t.requester_peer.user.username,
            'status': t.status,
            'created_at': t.created_at.isoformat(),
        })
        
    return JsonResponse({
        'file': {
            'file_id': str(file.file_id),
            'filename': file.filename,
            'file_size_display': file.file_size_display,
            'file_type': file.file_type,
            'file_hash': file.file_hash,
            'description': file.description,
            'download_count': file.download_count,
            'created_at': file.created_at.isoformat(),
            'peer': {
                'username': file.peer.user.username,
                'peer_id': str(file.peer.peer_id),
            }
        },
        'is_owner': is_owner,
        'recent_transfers': transfers_data
    })


@api_peer_required
def api_download_file(request, file_id):
    """Fetches the actual physical file and creates a transfer log"""
    file = get_object_or_404(SharedFile, file_id=file_id, is_available=True)
    if not file.file_path or not os.path.exists(file.file_path.path):
        return JsonResponse({'error': 'File not found on disk.'}, status=404)
        
    requester_peer = request.user.peer
    transfer = None
    if requester_peer != file.peer:
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
            filename=file.original_filename
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
        if transfer:
            transfer.status = 'failed'
            transfer.save(update_fields=['status'])
        return JsonResponse({'error': f'Error downloading file: {str(e)}'}, status=500)


@csrf_exempt
@api_peer_required
def api_delete_file(request, file_id):
    """Deletes the physical file and updates registry"""
    if request.method != 'DELETE' and request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        
    file = get_object_or_404(SharedFile, file_id=file_id)
    if file.peer != request.user.peer:
        return JsonResponse({'error': 'You can only delete your own files.'}, status=403)
        
    filename = file.filename
    if file.file_path and os.path.exists(file.file_path.path):
        try:
            os.remove(file.file_path.path)
        except OSError:
            pass
            
    file.delete()
    return JsonResponse({'message': f'File "{filename}" deleted successfully.'})


# Peer Network REST APIs
@api_peer_required
def api_peer_list(request):
    """Lists online peers"""
    peers = Peer.objects.filter(is_online=True).exclude(id=request.user.peer.id)
    query = request.GET.get('search', '').strip()
    if query:
        peers = peers.filter(user__username__icontains=query)
        
    peers_data = []
    for p in peers:
        peers_data.append({
            'peer_id': str(p.peer_id),
            'username': p.user.username,
            'ip_address': p.ip_address,
            'port': p.port,
            'is_online': p.is_online,
            'files_count': p.shared_files.count(),
            'last_seen': p.last_seen.isoformat(),
        })
    return JsonResponse({'peers': peers_data})


@api_peer_required
def api_peer_detail(request, peer_id):
    """Details a specific online peer and their files list"""
    peer = get_object_or_404(Peer, peer_id=peer_id)
    shared_files = SharedFile.objects.filter(peer=peer, is_available=True)[:10]
    current_peer = request.user.peer
    
    is_connected = PeerConnection.objects.filter(
        Q(peer1=current_peer, peer2=peer) | Q(peer1=peer, peer2=current_peer),
        is_active=True
    ).exists()
    
    files_data = []
    for file in shared_files:
        files_data.append({
            'file_id': str(file.file_id),
            'filename': file.filename,
            'file_size_display': file.file_size_display,
            'file_type': file.file_type,
            'download_count': file.download_count,
        })
        
    return JsonResponse({
        'peer': {
            'peer_id': str(peer.peer_id),
            'username': peer.user.username,
            'ip_address': peer.ip_address,
            'port': peer.port,
            'is_online': peer.is_online,
            'last_seen': peer.last_seen.isoformat(),
        },
        'shared_files': files_data,
        'is_connected': is_connected
    })


# Existing Transfer REST APIs adapted for standard user model
@api_peer_required
def api_transfer_status(request):
    """Lists recent transfers for currently authenticated peer"""
    peer = request.user.peer
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


@api_peer_required
def api_transfer_detail(request, transfer_id):
    """Retrieves full details for a transfer session"""
    transfer = get_object_or_404(FileTransfer, transfer_id=transfer_id)
    
    return JsonResponse({
        'transfer_id': str(transfer.transfer_id),
        'filename': transfer.shared_file.filename,
        'file_size': transfer.shared_file.file_size,
        'status': transfer.status,
        'bytes_transferred': transfer.bytes_transferred,
        'progress': transfer.get_progress_percentage(),
        'transfer_speed': transfer.transfer_speed,
        'requester': transfer.requester_peer.user.username,
        'provider': transfer.provider_peer.user.username,
        'started_at': transfer.started_at.isoformat() if transfer.started_at else None,
        'completed_at': transfer.completed_at.isoformat() if transfer.completed_at else None,
    })
