import tempfile
import shutil
from pathlib import Path

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings

from .models import FileTransfer, Peer, SharedFile


TEST_MEDIA_ROOT = Path(tempfile.gettempdir()) / 'p2p_share_test_media'


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class FileUploadTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.client = Client()
        self.peer = Peer.objects.create(
            username='tester',
            ip_address='127.0.0.1',
            port=settings.P2P_DEFAULT_PORT,
            is_online=True,
        )
        session = self.client.session
        session['peer_id'] = str(self.peer.peer_id)
        session.save()

    def test_upload_creates_shared_file(self):
        upload = SimpleUploadedFile(
            'hello.txt',
            b'hello p2p',
            content_type='text/plain',
        )

        response = self.client.post(
            '/files/upload/',
            {'file_path': upload, 'description': 'Greeting'},
        )

        self.assertRedirects(response, '/dashboard/')
        shared_file = SharedFile.objects.get(peer=self.peer)
        self.assertEqual(shared_file.filename, 'hello.txt')
        self.assertEqual(shared_file.original_filename, 'hello.txt')
        self.assertEqual(shared_file.file_size, 9)
        self.assertEqual(shared_file.file_type, 'document')
        self.assertEqual(shared_file.file_size_display, '9 B')

    def test_duplicate_upload_shows_form_error(self):
        upload = SimpleUploadedFile('hello.txt', b'hello p2p')
        self.client.post('/files/upload/', {'file_path': upload})

        duplicate = SimpleUploadedFile('hello.txt', b'hello p2p')
        response = self.client.post('/files/upload/', {'file_path': duplicate})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'You have already shared this file.')
        self.assertEqual(SharedFile.objects.count(), 1)

    def test_upload_page_uses_aligned_layout(self):
        response = self.client.get('/files/upload/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="page-panel page-panel-narrow"')
        self.assertContains(response, 'Maximum file size: 100 MB.')

    def test_file_detail_uses_aligned_layout(self):
        upload = SimpleUploadedFile('hello.txt', b'hello p2p')
        self.client.post('/files/upload/', {'file_path': upload})
        shared_file = SharedFile.objects.get()

        response = self.client.get(f'/files/{shared_file.file_id}/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="detail-grid"')
        self.assertContains(response, 'class="form-actions"')

    def test_register_peer_creates_session_and_dashboard(self):
        client = Client()

        response = client.post('/peers/register/', {'username': 'newpeer'})

        self.assertRedirects(response, '/dashboard/')
        self.assertTrue(Peer.objects.filter(username='newpeer', is_online=True).exists())
        dashboard = client.get('/dashboard/')
        self.assertContains(dashboard, 'Welcome back, newpeer!')

    def test_file_list_search_and_detail_route(self):
        self.client.post(
            '/files/upload/',
            {
                'file_path': SimpleUploadedFile('notes.txt', b'project notes'),
                'description': 'Searchable planning document',
            },
        )
        shared_file = SharedFile.objects.get()

        list_response = self.client.get('/files/', {'search': 'planning'})
        self.assertContains(list_response, 'notes.txt')
        self.assertContains(list_response, 'Details')

        detail_response = self.client.get(f'/files/{shared_file.file_id}/')
        self.assertContains(detail_response, 'notes.txt')
        self.assertContains(detail_response, 'Download')

    def test_download_by_other_peer_counts_once_and_records_transfer(self):
        self.client.post('/files/upload/', {'file_path': SimpleUploadedFile('paper.txt', b'paper')})
        shared_file = SharedFile.objects.get()

        downloader = Peer.objects.create(
            username='downloader',
            ip_address='127.0.0.2',
            port=settings.P2P_DEFAULT_PORT,
            is_online=True,
        )
        other_client = Client()
        session = other_client.session
        session['peer_id'] = str(downloader.peer_id)
        session.save()

        response = other_client.get(f'/files/{shared_file.file_id}/download/')

        self.assertEqual(response.status_code, 200)
        shared_file.refresh_from_db()
        self.assertEqual(shared_file.download_count, 1)
        transfer = FileTransfer.objects.get(shared_file=shared_file)
        self.assertEqual(transfer.status, 'completed')
        self.assertEqual(transfer.bytes_transferred, shared_file.file_size)

    def test_owner_can_delete_file(self):
        self.client.post('/files/upload/', {'file_path': SimpleUploadedFile('remove.txt', b'remove me')})
        shared_file = SharedFile.objects.get()

        response = self.client.post(f'/files/{shared_file.file_id}/delete/')

        self.assertRedirects(response, '/dashboard/')
        self.assertFalse(SharedFile.objects.filter(file_id=shared_file.file_id).exists())

    def test_non_owner_cannot_delete_file(self):
        self.client.post('/files/upload/', {'file_path': SimpleUploadedFile('protected.txt', b'keep')})
        shared_file = SharedFile.objects.get()
        intruder = Peer.objects.create(
            username='intruder',
            ip_address='127.0.0.3',
            port=settings.P2P_DEFAULT_PORT,
            is_online=True,
        )
        other_client = Client()
        session = other_client.session
        session['peer_id'] = str(intruder.peer_id)
        session.save()

        response = other_client.post(f'/files/{shared_file.file_id}/delete/')

        self.assertRedirects(response, f'/files/{shared_file.file_id}/')
        self.assertTrue(SharedFile.objects.filter(file_id=shared_file.file_id).exists())

    def test_peer_detail_page_renders(self):
        response = self.client.get(f'/peers/{self.peer.peer_id}/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.peer.username)
        self.assertContains(response, 'Peer profile')

    def test_api_status_and_file_search(self):
        self.client.post(
            '/files/upload/',
            {
                'file_path': SimpleUploadedFile('api.txt', b'api content'),
                'description': 'api searchable',
            },
        )

        status_response = self.client.get('/api/peers/status/')
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(status_response.json()['total_files'], 1)

        search_response = self.client.get('/api/files/search/', {'q': 'api'})
        self.assertEqual(search_response.status_code, 200)
        self.assertEqual(search_response.json()['total_count'], 1)
        self.assertEqual(search_response.json()['files'][0]['filename'], 'api.txt')

    def test_transfer_api_requires_session_and_returns_history(self):
        self.client.post('/files/upload/', {'file_path': SimpleUploadedFile('transfer.txt', b'transfer')})
        shared_file = SharedFile.objects.get()
        transfer = FileTransfer.objects.create(
            shared_file=shared_file,
            requester_peer=self.peer,
            provider_peer=self.peer,
            status='completed',
            bytes_transferred=shared_file.file_size,
        )

        anonymous_response = Client().get('/api/transfers/')
        self.assertEqual(anonymous_response.status_code, 401)

        history_response = self.client.get('/api/transfers/')
        self.assertEqual(history_response.status_code, 200)
        self.assertEqual(history_response.json()['transfers'][0]['filename'], 'transfer.txt')

        detail_response = self.client.get(f'/api/transfers/{transfer.transfer_id}/')
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json()['status'], 'completed')
