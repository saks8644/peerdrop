import tempfile
import shutil
from pathlib import Path
import json

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core import mail

from .models import FileTransfer, Peer, SharedFile


TEST_MEDIA_ROOT = Path(tempfile.gettempdir()) / 'p2p_share_test_media'


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class P2PApiTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.client = Client()
        # Setup base user and peer
        self.user = User.objects.create_user(
            username='tester',
            email='tester@p2p.local',
            password='testpassword',
            is_active=True
        )
        self.peer = Peer.objects.create(
            user=self.user,
            ip_address='127.0.0.1',
            port=settings.P2P_DEFAULT_PORT,
            is_online=True
        )

    def test_api_registration_creates_inactive_user_and_sends_email(self):
        mail.outbox = [] # Clear mail box
        response = self.client.post(
            '/api/auth/register/',
            data=json.dumps({
                'username': 'newuser',
                'email': 'newuser@p2p.local',
                'password': 'newpassword'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        self.assertIn('Registration successful', response.json()['message'])
        
        # Verify user state
        new_user = User.objects.get(username='newuser')
        self.assertFalse(new_user.is_active)
        
        # Verify email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Verify your PeerDrop Account', mail.outbox[0].subject)
        self.assertEqual(mail.outbox[0].to, ['newuser@p2p.local'])

    def test_api_verification_activates_user(self):
        # Create an inactive user
        inactive_user = User.objects.create_user(
            username='inactive',
            email='inactive@p2p.local',
            password='password123',
            is_active=False
        )
        Peer.objects.create(
            user=inactive_user,
            ip_address='127.0.0.1',
            port=settings.P2P_DEFAULT_PORT
        )
        
        # Generate token
        token = default_token_generator.make_token(inactive_user)
        uidb64 = urlsafe_base64_encode(force_bytes(inactive_user.pk))
        
        response = self.client.post(
            '/api/auth/verify/',
            data=json.dumps({
                'uidb64': uidb64,
                'token': token
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['message'], 'Account verified successfully!')
        
        inactive_user.refresh_from_db()
        self.assertTrue(inactive_user.is_active)

    def test_api_login_fails_for_inactive_account(self):
        # Create inactive user
        inactive_user = User.objects.create_user(
            username='inactive_login',
            email='inactive_login@p2p.local',
            password='password123',
            is_active=False
        )
        
        response = self.client.post(
            '/api/auth/login/',
            data=json.dumps({
                'username': 'inactive_login',
                'password': 'password123'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'Please verify your email first.')

    def test_api_login_succeeds_for_active_account(self):
        response = self.client.post(
            '/api/auth/login/',
            data=json.dumps({
                'username': 'tester',
                'password': 'testpassword'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['user']['username'], 'tester')

    def test_unauthenticated_api_access_throws_401(self):
        anonymous_client = Client()
        response = anonymous_client.get('/api/dashboard/')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['error'], 'Authentication required')

    def test_api_dashboard_returns_correct_stats(self):
        # Authenticate first
        self.client.login(username='tester', password='testpassword')
        
        # Share a test file
        upload = SimpleUploadedFile('dash_file.txt', b'dashboard file content')
        self.client.post(
            '/api/files/upload/',
            {'file': upload, 'description': 'Dashboard File'}
        )
        
        response = self.client.get('/api/dashboard/')
        self.assertEqual(response.status_code, 200)
        
        res_data = response.json()
        self.assertEqual(res_data['peer']['username'], 'tester')
        self.assertEqual(len(res_data['my_files']), 1)
        self.assertEqual(res_data['my_files'][0]['filename'], 'dash_file.txt')

    def test_api_file_upload_and_type_detection(self):
        self.client.login(username='tester', password='testpassword')
        
        upload = SimpleUploadedFile('document.pdf', b'pdf content', content_type='application/pdf')
        response = self.client.post(
            '/api/files/upload/',
            {'file': upload, 'description': 'PDF file description'}
        )
        self.assertEqual(response.status_code, 201)
        
        shared_file = SharedFile.objects.get(filename='document.pdf')
        self.assertEqual(shared_file.file_type, 'document')
        self.assertEqual(shared_file.description, 'PDF file description')

    def test_api_file_download_logs_transfer_correctly(self):
        # Upload a file
        self.client.login(username='tester', password='testpassword')
        upload = SimpleUploadedFile('download_test.zip', b'zip archive content')
        self.client.post('/api/files/upload/', {'file': upload})
        shared_file = SharedFile.objects.get(filename='download_test.zip')
        self.client.logout()
        
        # Download as different user
        downloader = User.objects.create_user(
            username='downloader',
            email='down@p2p.local',
            password='password123',
            is_active=True
        )
        Peer.objects.create(
            user=downloader,
            ip_address='127.0.0.2',
            port=settings.P2P_DEFAULT_PORT,
            is_online=True
        )
        
        downloader_client = Client()
        downloader_client.login(username='downloader', password='password123')
        
        response = downloader_client.get(f'/api/files/{shared_file.file_id}/download/')
        self.assertEqual(response.status_code, 200)
        
        # Verify transfer log was created and marked completed
        transfer = FileTransfer.objects.get(shared_file=shared_file)
        self.assertEqual(transfer.requester_peer.user.username, 'downloader')
        self.assertEqual(transfer.status, 'completed')
        self.assertEqual(transfer.bytes_transferred, shared_file.file_size)

    def test_owner_can_delete_file(self):
        self.client.login(username='tester', password='testpassword')
        upload = SimpleUploadedFile('delete_me.txt', b'discardable text')
        self.client.post('/api/files/upload/', {'file': upload})
        shared_file = SharedFile.objects.get(filename='delete_me.txt')
        
        response = self.client.post(f'/api/files/{shared_file.file_id}/delete/')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(SharedFile.objects.filter(file_id=shared_file.file_id).exists())

    def test_non_owner_cannot_delete_file(self):
        # Owner uploads
        self.client.login(username='tester', password='testpassword')
        upload = SimpleUploadedFile('protected.txt', b'keep this safe')
        self.client.post('/api/files/upload/', {'file': upload})
        shared_file = SharedFile.objects.get(filename='protected.txt')
        self.client.logout()
        
        # Intruder attempts delete
        intruder = User.objects.create_user(
            username='intruder',
            email='intruder@p2p.local',
            password='password123',
            is_active=True
        )
        Peer.objects.create(
            user=intruder,
            ip_address='127.0.0.3',
            port=settings.P2P_DEFAULT_PORT
        )
        
        intruder_client = Client()
        intruder_client.login(username='intruder', password='password123')
        
        response = intruder_client.post(f'/api/files/{shared_file.file_id}/delete/')
        self.assertEqual(response.status_code, 403)
        self.assertTrue(SharedFile.objects.filter(file_id=shared_file.file_id).exists())
