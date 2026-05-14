# P2P File Share

A Django-based peer-to-peer style file sharing application. Users can register as peers, upload files, browse shared files from other peers, download files, and monitor transfer activity.

## Features

- Peer registration and login via username
- Peer dashboard with uploaded files and recent transfers
- File sharing with upload, download, detail view, and delete support
- Search and filter shared files by name, description, peer, or file type
- Peer listing with online status
- Basic API endpoints for peer status, file search, and transfer tracking
- SQLite database for easy local setup
- File uploads stored in `media/shared_files/`

## Prerequisites

- Python 3.10+ (recommended)
- pip

## Required Python packages

- Django
- channels
- python-dotenv

## Setup

1. Clone or copy the repository into your workspace.
2. Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Install dependencies:

```powershell
pip install django channels python-dotenv
```

4. Create a `.env` file in the repository root if you want to override defaults:

```text
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:8000
```

5. Apply migrations:

```powershell
python manage.py migrate
```

6. Create a superuser for admin access (optional):

```powershell
python manage.py createsuperuser
```

## Running the app

Start the development server:

```powershell
python manage.py runserver
```

Then open your browser at `http://127.0.0.1:8000/`.

## Application workflow

- Visit the home page to see total online peers, available files, and recent uploads.
- Register a peer account at `/peers/register/`.
- Upload files from the dashboard at `/files/upload/`.
- Browse all shared files at `/files/`.
- Download a file from the detail page.
- View peers online at `/peers/`.

## File storage

Uploaded files are saved to `media/shared_files/` by default.

## Configuration

Settings are loaded from `.env` using `python-dotenv`.

Key settings supported:

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`

## API endpoints

- `GET /peers/api/peers/status/` - returns current online peer and file counts
- `GET /peers/api/files/search/?q=...&type=...` - search shared files
- `GET /peers/api/transfers/` - current peer transfer list
- `GET /peers/api/transfers/<transfer_id>/` - transfer detail

## Notes

- The project uses Django Channels with an in-memory channel layer for ASGI support.
- The default file upload limit is configured in `settings.py` as 100MB.
- This application is intended for local development and demonstration purposes.

## License

No license is specified. Add one if you want to open-source the project.
