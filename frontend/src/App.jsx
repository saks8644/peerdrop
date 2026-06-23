import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Link, useNavigate, useParams, useLocation } from 'react-router-dom';
import { 
  Folder, UploadCloud, Users, LayoutDashboard, LogIn, LogOut, UserPlus, 
  FileText, Image, Video, Music, Archive, FileQuestion, Search, 
  Download, Trash2, CheckCircle, XCircle, Clock, AlertTriangle, ArrowRight, ShieldCheck
} from 'lucide-react';
import confetti from 'canvas-confetti';

// --- HELPERS ---
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

const apiFetch = async (url, options = {}) => {
  options.credentials = 'include';
  if (!options.headers) options.headers = {};
  
  if (!(options.body instanceof FormData)) {
    options.headers['Content-Type'] = 'application/json';
  }
  
  const csrfToken = getCookie('csrftoken');
  if (csrfToken) {
    options.headers['X-CSRFToken'] = csrfToken;
  }
  
  const response = await fetch(url, options);
  
  // File download check
  const disposition = response.headers.get('content-disposition');
  if (disposition && disposition.indexOf('attachment') !== -1) {
    return response;
  }
  
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || 'Something went wrong');
  }
  return data;
};

const getFileIcon = (type) => {
  switch (type) {
    case 'document': return <FileText className="file-icon" />;
    case 'image': return <Image className="file-icon" />;
    case 'video': return <Video className="file-icon" />;
    case 'audio': return <Music className="file-icon" />;
    case 'archive': return <Archive className="file-icon" />;
    default: return <FileQuestion className="file-icon" />;
  }
};

// --- PAGES & COMPONENTS ---

// 1. Navigation Shell Layout wrapper
function Layout({ user, onLogout, children }) {
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = async () => {
    try {
      await apiFetch('/api/auth/logout/', { method: 'POST' });
      onLogout();
      navigate('/');
    } catch (err) {
      console.error('Logout failed:', err);
    }
  };

  return (
    <div className="app-shell">
      <header className="app-header">
        <nav className="app-nav">
          <Link to="/" className="app-logo">
            <UploadCloud /> PeerDrop
          </Link>
          <ul className="app-nav-links">
            {user ? (
              <>
                <li>
                  <Link to="/dashboard" className={location.pathname === '/dashboard' ? 'active' : ''}>
                    <LayoutDashboard size={18} style={{ verticalAlign: 'middle', marginRight: '4px' }} /> Dashboard
                  </Link>
                </li>
                <li>
                  <Link to="/files" className={location.pathname === '/files' ? 'active' : ''}>
                    <Folder size={18} style={{ verticalAlign: 'middle', marginRight: '4px' }} /> Browse
                  </Link>
                </li>
                <li>
                  <Link to="/peers" className={location.pathname === '/peers' ? 'active' : ''}>
                    <Users size={18} style={{ verticalAlign: 'middle', marginRight: '4px' }} /> Peers
                  </Link>
                </li>
                <li className="user-badge" style={{ marginLeft: '10px' }}>
                  <div className="user-status-dot"></div>
                  {user.username}
                </li>
                <li>
                  <button onClick={handleLogout} className="btn btn-secondary" style={{ padding: '0.4rem 0.8rem', fontSize: '0.85rem' }}>
                    <LogOut size={16} /> Logout
                  </button>
                </li>
              </>
            ) : (
              <>
                <li>
                  <Link to="/login" className="btn btn-secondary" style={{ padding: '0.5rem 1rem' }}>
                    <LogIn size={16} /> Log In
                  </Link>
                </li>
                <li>
                  <Link to="/register" className="btn btn-primary" style={{ padding: '0.5rem 1.1rem' }}>
                    <UserPlus size={16} /> Join Network
                  </Link>
                </li>
              </>
            )}
          </ul>
        </nav>
      </header>
      <main className="app-main">{children}</main>
      <footer className="app-footer">
        <p>&copy; 2026 PeerDrop. Built with Django Channels, React & WebSockets.</p>
      </footer>
    </div>
  );
}

// 2. Landing Page
function LandingPage({ user }) {
  const [stats, setStats] = useState({ peers_online: 0, total_files: 0, active_transfers: 0 });

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await apiFetch('/api/peers/status/');
        setStats(data);
      } catch (err) {
        console.error(err);
      }
    };
    fetchStats();
    const interval = setInterval(fetchStats, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{ textAlign: 'center', padding: '3rem 1rem' }}>
      <h1 style={{ fontFamily: 'var(--font-heading)', fontSize: '3.5rem', fontWeight: 900, marginBottom: '1.25rem' }}>
        Centralized <span style={{ color: 'var(--accent-indigo)' }}>File Drop</span>
      </h1>
      <p style={{ color: 'var(--text-secondary)', fontSize: '1.2rem', marginBottom: '2.5rem', maxWidth: '600px', margin: '0 auto 2.5rem' }}>
        Connect to your local peers, browse uploaded files, and track real-time transfers inside a sandboxed local network.
      </p>

      <div className="dashboard-grid" style={{ maxWidth: '800px', margin: '0 auto 3rem' }}>
        <div className="glass-panel stat-card">
          <div className="stat-icon-box stat-icon-blue"><Users /></div>
          <div>
            <div className="stat-num">{stats.peers_online}</div>
            <div className="stat-label">Online Peers</div>
          </div>
        </div>
        <div className="glass-panel stat-card">
          <div className="stat-icon-box stat-icon-indigo"><Folder /></div>
          <div>
            <div className="stat-num">{stats.total_files}</div>
            <div className="stat-label">Shared Files</div>
          </div>
        </div>
        <div className="glass-panel stat-card">
          <div className="stat-icon-box stat-icon-cyan"><UploadCloud /></div>
          <div>
            <div className="stat-num">{stats.active_transfers}</div>
            <div className="stat-label">Active Transfers</div>
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
        {user ? (
          <Link to="/dashboard" className="btn btn-primary">
            Go to Dashboard <ArrowRight size={18} />
          </Link>
        ) : (
          <>
            <Link to="/register" className="btn btn-primary">Join Network</Link>
            <Link to="/login" className="btn btn-secondary">Browse Shared Files</Link>
          </>
        )}
      </div>
    </div>
  );
}

// 3. Register Page
function RegisterPage() {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);
    try {
      const data = await apiFetch('/api/auth/register/', {
        method: 'POST',
        body: JSON.stringify({ username, email, password })
      });
      setSuccess('Account created successfully! Since we are in development mode, please look at your Django server console logs to retrieve the account verification email link.');
      setUsername('');
      setEmail('');
      setPassword('');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-panel glass-panel-narrow">
      <h2 className="form-title">Join PeerDrop</h2>
      <p className="form-subtitle">Create your account to start sharing files</p>
      
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Username</label>
          <input 
            type="text" 
            required 
            className="form-control" 
            value={username} 
            onChange={(e) => setUsername(e.target.value)} 
          />
        </div>
        <div className="form-group">
          <label>Email Address</label>
          <input 
            type="email" 
            required 
            className="form-control" 
            value={email} 
            onChange={(e) => setEmail(e.target.value)} 
          />
        </div>
        <div className="form-group">
          <label>Password</label>
          <input 
            type="password" 
            required 
            className="form-control" 
            value={password} 
            onChange={(e) => setPassword(e.target.value)} 
          />
        </div>

        {error && <div className="form-error">{error}</div>}
        {success && <div className="form-success">{success}</div>}

        <button type="submit" disabled={loading} className="btn btn-primary" style={{ width: '100%', marginTop: '1rem' }}>
          {loading ? 'Registering...' : 'Register'}
        </button>
      </form>
      <div className="form-footer">
        Already have an account? <Link to="/login">Log In</Link>
      </div>
    </div>
  );
}

// 4. Verify Email Landing Page
function VerifyEmailPage() {
  const { uidb64, token } = useParams();
  const [status, setStatus] = useState('verifying'); // verifying, success, error
  const [msg, setMsg] = useState('');

  useEffect(() => {
    const verify = async () => {
      try {
        const data = await apiFetch('/api/auth/verify/', {
          method: 'POST',
          body: JSON.stringify({ uidb64, token })
        });
        setStatus('success');
        setMsg(data.message);
        confetti({ particleCount: 150, spread: 80 });
      } catch (err) {
        setStatus('error');
        setMsg(err.message);
      }
    };
    verify();
  }, [uidb64, token]);

  return (
    <div className="glass-panel glass-panel-narrow" style={{ textAlign: 'center', padding: '3rem 2rem' }}>
      {status === 'verifying' && (
        <>
          <Clock className="empty-state-icon" size={48} style={{ animation: 'spin 2s linear infinite', margin: '0 auto 1.5rem' }} />
          <h2 className="form-title">Verifying Account</h2>
          <p style={{ color: 'var(--text-secondary)' }}>Checking verification token against the database...</p>
        </>
      )}
      {status === 'success' && (
        <>
          <CheckCircle className="empty-state-icon" size={48} style={{ color: 'var(--accent-emerald)', margin: '0 auto 1.5rem' }} />
          <h2 className="form-title">Verified!</h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem' }}>{msg}</p>
          <Link to="/login" className="btn btn-primary" style={{ width: '100%' }}>Proceed to Login</Link>
        </>
      )}
      {status === 'error' && (
        <>
          <XCircle className="empty-state-icon" size={48} style={{ color: 'var(--accent-rose)', margin: '0 auto 1.5rem' }} />
          <h2 className="form-title">Verification Failed</h2>
          <p style={{ color: 'var(--text-rose)', marginBottom: '2rem' }}>{msg}</p>
          <Link to="/register" className="btn btn-secondary" style={{ width: '100%' }}>Register Again</Link>
        </>
      )}
    </div>
  );
}

// 5. Login Page
function LoginPage({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = await apiFetch('/api/auth/login/', {
        method: 'POST',
        body: JSON.stringify({ username, password })
      });
      onLogin(data.user);
      navigate('/dashboard');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-panel glass-panel-narrow">
      <h2 className="form-title">Sign In</h2>
      <p className="form-subtitle">Connect to the file sharing dashboard</p>

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Username</label>
          <input 
            type="text" 
            required 
            className="form-control" 
            value={username} 
            onChange={(e) => setUsername(e.target.value)} 
          />
        </div>
        <div className="form-group">
          <label>Password</label>
          <input 
            type="password" 
            required 
            className="form-control" 
            value={password} 
            onChange={(e) => setPassword(e.target.value)} 
          />
        </div>

        {error && <div className="form-error">{error}</div>}

        <button type="submit" disabled={loading} className="btn btn-primary" style={{ width: '100%', marginTop: '1rem' }}>
          {loading ? 'Authenticating...' : 'Sign In'}
        </button>
      </form>
      <div className="form-footer">
        Don't have an account yet? <Link to="/register">Create Account</Link>
      </div>
    </div>
  );
}

// 6. Dashboard Page
function DashboardPage({ user }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchDashboard = async () => {
    try {
      const res = await apiFetch('/api/dashboard/');
      setData(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
    const interval = setInterval(fetchDashboard, 15000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return <div style={{ textAlign: 'center', padding: '4rem' }}>Loading Dashboard...</div>;
  if (error) return <div className="form-error" style={{ maxWidth: '600px', margin: '2rem auto' }}>{error}</div>;

  return (
    <div>
      <div className="glass-panel" style={{ marginBottom: '2rem', padding: '1.5rem 2rem' }}>
        <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.75rem', marginBottom: '0.5rem' }}>
          Welcome back, {user.username}!
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
          <div><strong>Peer ID:</strong> {data.peer.peer_id}</div>
          <div><strong>IP Address:</strong> {data.peer.ip_address}:{data.peer.port}</div>
          <div><strong>Status:</strong> <span style={{ color: 'var(--accent-emerald)', fontWeight: 700 }}>Online</span></div>
        </div>
      </div>

      <div className="dashboard-grid">
        <div className="glass-panel stat-card">
          <div className="stat-icon-box stat-icon-blue"><Folder /></div>
          <div>
            <div className="stat-num">{data.my_files.length}</div>
            <div className="stat-label">My Files</div>
          </div>
        </div>
        <div className="glass-panel stat-card">
          <div className="stat-icon-box stat-icon-indigo"><Download /></div>
          <div>
            <div className="stat-num">{data.total_downloads}</div>
            <div className="stat-label">Total Downloads</div>
          </div>
        </div>
        <div className="glass-panel stat-card">
          <div className="stat-icon-box stat-icon-cyan"><Clock /></div>
          <div>
            <div className="stat-num">{data.recent_transfers.length}</div>
            <div className="stat-label">Recent Transfers</div>
          </div>
        </div>
        <div className="glass-panel stat-card">
          <div className="stat-icon-box stat-icon-emerald"><Users /></div>
          <div>
            <div className="stat-num">{data.connected_peers.length}</div>
            <div className="stat-label">Connected Peers</div>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '2rem' }}>
        <div>
          <div className="glass-panel section-card">
            <div className="section-title-bar">
              <h2>My Shared Files</h2>
              <Link to="/files/upload" className="btn btn-primary" style={{ padding: '0.4rem 1rem', fontSize: '0.88rem' }}>+ Share File</Link>
            </div>
            {data.my_files.length > 0 ? (
              <div className="files-grid">
                {data.my_files.map(file => (
                  <div key={file.file_id} className="glass-panel file-card" style={{ padding: '1.25rem' }}>
                    <div className="file-card-header">
                      {getFileIcon(file.file_type)}
                      <span className={`badge badge-${file.file_type}`}>{file.file_type}</span>
                    </div>
                    <div className="file-name">{file.filename}</div>
                    <div className="file-meta">
                      <span>{file.file_size_display}</span>
                      <span>{file.download_count} DLs</span>
                    </div>
                    <div className="file-actions">
                      <Link to={`/files/${file.file_id}`} className="btn btn-secondary">Details</Link>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state">
                <Folder className="empty-state-icon" size={32} />
                <h3>No files shared</h3>
                <p>Upload files to start sharing with other online peers.</p>
              </div>
            )}
          </div>

          <div className="glass-panel section-card">
            <div className="section-title-bar">
              <h2>Recent Transfers</h2>
            </div>
            {data.recent_transfers.length > 0 ? (
              <div className="transfers-list">
                {data.recent_transfers.map(t => (
                  <div key={t.transfer_id} className="glass-panel transfer-item">
                    <div className="transfer-left">
                      <div className="transfer-file">{t.filename}</div>
                      <div className="transfer-sub">
                        {t.direction === 'download' ? 'Downloaded from' : 'Uploaded to'} {t.peer_username}
                      </div>
                    </div>
                    <div className="transfer-right">
                      <span className={`badge badge-${t.status}`}>{t.status}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state">
                <Clock className="empty-state-icon" size={32} />
                <h3>No recent transfer history</h3>
                <p>Transfer sessions appear here when downloading files.</p>
              </div>
            )}
          </div>
        </div>

        <div>
          <div className="glass-panel section-card" style={{ height: '100%' }}>
            <div className="section-title-bar">
              <h2>Online Peers</h2>
            </div>
            {data.connected_peers.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {data.connected_peers.map(p => (
                  <Link to={`/peers/${p.peer_id}`} key={p.peer_id} style={{ textDecoration: 'none', color: 'inherit' }}>
                    <div className="glass-panel" style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '1rem', border: '1px solid rgba(255,255,255,0.05)', transition: 'border-color 0.25s' }} className="peer-hover">
                      <div className="peer-avatar" style={{ margin: 0, width: '40px', height: '40px' }}>
                        {p.username[0].toUpperCase()}
                      </div>
                      <div>
                        <div style={{ fontWeight: 700 }}>{p.username}</div>
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{p.files_count} files shared</div>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="empty-state">
                <Users className="empty-state-icon" size={32} />
                <h3>Waiting for Peers</h3>
                <p>No other peers are online right now.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// 7. Browse Files Page
function BrowseFilesPage() {
  const [files, setFiles] = useState([]);
  const [search, setSearch] = useState('');
  const [selectedType, setSelectedType] = useState('');
  const [loading, setLoading] = useState(true);

  const fetchFiles = async () => {
    try {
      const data = await apiFetch(`/api/files/?search=${search}&type=${selectedType}`);
      setFiles(data.files);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFiles();
  }, [search, selectedType]);

  const handleDownload = async (fileId, filename) => {
    try {
      const response = await apiFetch(`/api/files/${fileId}/download/`);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
    } catch (err) {
      alert(`Download failed: ${err.message}`);
    }
  };

  return (
    <div>
      <div className="section-title-bar">
        <h1 style={{ fontFamily: 'var(--font-heading)', fontSize: '2rem' }}>Browse Shared Files</h1>
        <Link to="/files/upload" className="btn btn-primary">+ Upload / Share</Link>
      </div>

      <div className="glass-panel" style={{ marginBottom: '2.5rem', padding: '1.25rem 2rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '1rem' }}>
          <div className="form-group" style={{ margin: 0 }}>
            <div style={{ position: 'relative' }}>
              <Search style={{ position: 'absolute', left: '12px', top: '13px', color: 'var(--text-muted)' }} size={18} />
              <input 
                type="text" 
                placeholder="Search files..." 
                className="form-control" 
                style={{ paddingLeft: '2.5rem' }} 
                value={search} 
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>
          <div className="form-group" style={{ margin: 0 }}>
            <select 
              className="form-control" 
              value={selectedType} 
              onChange={(e) => setSelectedType(e.target.value)}
            >
              <option value="">All Categories</option>
              <option value="document">Document</option>
              <option value="image">Image</option>
              <option value="video">Video</option>
              <option value="audio">Audio</option>
              <option value="archive">Archive</option>
              <option value="other">Other</option>
            </select>
          </div>
        </div>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '3rem' }}>Fetching file list...</div>
      ) : files.length > 0 ? (
        <div className="files-grid">
          {files.map(file => (
            <div key={file.file_id} className="glass-panel file-card">
              <div className="file-card-header">
                {getFileIcon(file.file_type)}
                <span className={`badge badge-${file.file_type}`}>{file.file_type}</span>
              </div>
              <div className="file-name" title={file.filename}>{file.filename}</div>
              <div className="file-desc">{file.description || 'No description provided.'}</div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1.25rem' }}>
                Shared by: <span style={{ color: 'var(--accent-indigo)', fontWeight: 700 }}>{file.peer.username}</span>
              </div>
              <div className="file-meta">
                <span>{file.file_size_display}</span>
                <span>{file.download_count} DLs</span>
              </div>
              <div className="file-actions">
                <button onClick={() => handleDownload(file.file_id, file.filename)} className="btn btn-primary">
                  <Download size={16} /> Download
                </button>
                <Link to={`/files/${file.file_id}`} className="btn btn-secondary">Details</Link>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="glass-panel empty-state">
          <Folder className="empty-state-icon" size={48} />
          <h3>No matching files found</h3>
          <p>We couldn't find any shared files that match your search filters.</p>
        </div>
      )}
    </div>
  );
}

// 8. Upload Page
function UploadPage() {
  const [file, setFile] = useState(null);
  const [description, setDescription] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      setError('Please choose a file to share.');
      return;
    }
    setError('');
    setSuccess('');
    setLoading(true);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('description', description);

    try {
      await apiFetch('/api/files/upload/', {
        method: 'POST',
        body: formData
      });
      setSuccess('File uploaded successfully!');
      confetti({ particleCount: 100, spread: 60 });
      setTimeout(() => navigate('/dashboard'), 1500);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-panel glass-panel-narrow">
      <h2 className="form-title">Share a File</h2>
      <p className="form-subtitle">Share documents, archives, or media with peers</p>

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>File</label>
          <div className="upload-dropzone">
            <UploadCloud className="upload-dropzone-icon" size={32} />
            <input 
              type="file" 
              required 
              style={{ display: 'none' }} 
              id="file-selector" 
              onChange={handleFileChange} 
            />
            <label htmlFor="file-selector" className="btn btn-secondary" style={{ padding: '0.4rem 1rem', fontSize: '0.85rem' }}>
              Choose File
            </label>
            {file && (
              <div style={{ marginTop: '1rem', fontSize: '0.9rem', color: 'var(--accent-cyan)', fontWeight: 600 }}>
                Selected: {file.name} ({ (file.size / (1024*1024)).toFixed(2) } MB)
              </div>
            )}
          </div>
        </div>

        <div className="form-group">
          <label>Description (Optional)</label>
          <textarea 
            className="form-control" 
            rows="3" 
            placeholder="Add brief details about the file..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>

        {error && <div className="form-error">{error}</div>}
        {success && <div className="form-success">{success}</div>}

        <div style={{ display: 'flex', gap: '1rem', marginTop: '1.5rem' }}>
          <button type="button" onClick={() => navigate('/dashboard')} className="btn btn-secondary" style={{ flex: 1 }}>
            Cancel
          </button>
          <button type="submit" disabled={loading} className="btn btn-primary" style={{ flex: 2 }}>
            {loading ? 'Uploading...' : 'Upload & Share'}
          </button>
        </div>
      </form>
    </div>
  );
}

// 9. File Detail Page
function FileDetailPage({ user }) {
  const { fileId } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const fetchDetail = async () => {
    try {
      const res = await apiFetch(`/api/files/${fileId}/`);
      setData(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetail();
  }, [fileId]);

  const handleDownload = async () => {
    try {
      const response = await apiFetch(`/api/files/${fileId}/download/`);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', data.file.filename);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      fetchDetail(); // Refresh download counts
    } catch (err) {
      alert(`Download failed: ${err.message}`);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to delete this file? This action is permanent.')) return;
    try {
      await apiFetch(`/api/files/${fileId}/delete/`, { method: 'POST' });
      navigate('/dashboard');
    } catch (err) {
      alert(`Delete failed: ${err.message}`);
    }
  };

  if (loading) return <div style={{ textAlign: 'center', padding: '4rem' }}>Fetching file details...</div>;
  if (error) return <div className="form-error" style={{ maxWidth: '600px', margin: '2rem auto' }}>{error}</div>;

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto' }}>
      <div className="glass-panel" style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '2rem', marginBottom: '2rem' }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', borderRight: '1px solid var(--border-glass)', paddingRight: '2rem' }}>
          <div style={{ background: 'rgba(255,255,255,0.02)', padding: '2rem', borderRadius: '16px', marginBottom: '1rem' }}>
            {getFileIcon(data.file.file_type)}
          </div>
          <span className={`badge badge-${data.file.file_type}`}>{data.file.file_type}</span>
        </div>

        <div>
          <h1 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.8rem', fontWeight: 800, marginBottom: '1rem' }}>{data.file.filename}</h1>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>{data.file.description || 'No description provided.'}</p>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '2rem' }}>
            <div><strong>Size:</strong> {data.file.file_size_display}</div>
            <div><strong>Downloads:</strong> {data.file.download_count}</div>
            <div><strong>Shared By:</strong> {data.file.peer.username}</div>
            <div><strong>Shared Date:</strong> {new Date(data.file.created_at).toLocaleDateString()}</div>
            <div style={{ gridColumn: 'span 2' }}><strong>SHA-256 Hash:</strong> <code style={{ wordBreak: 'break-all', color: 'var(--accent-cyan)' }}>{data.file.file_hash}</code></div>
          </div>

          <div style={{ display: 'flex', gap: '1rem' }}>
            <button onClick={handleDownload} className="btn btn-primary" style={{ flex: 2 }}>
              <Download size={18} /> Download
            </button>
            {data.is_owner && (
              <button onClick={handleDelete} className="btn btn-danger" style={{ flex: 1 }}>
                <Trash2 size={18} /> Delete
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="glass-panel">
        <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.25rem', marginBottom: '1rem' }}>Recent Transfer Logs</h2>
        {data.recent_transfers.length > 0 ? (
          <div className="transfers-list">
            {data.recent_transfers.map(t => (
              <div key={t.transfer_id} className="glass-panel transfer-item" style={{ background: 'rgba(255,255,255,0.01)' }}>
                <div className="transfer-left">
                  <div style={{ fontWeight: 600 }}>{t.requester}</div>
                  <div className="transfer-sub">{new Date(t.created_at).toLocaleString()}</div>
                </div>
                <span className={`badge badge-${t.status}`}>{t.status}</span>
              </div>
            ))}
          </div>
        ) : (
          <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem' }}>No downloads recorded for this file yet.</p>
        )}
      </div>
    </div>
  );
}

// 10. Peers Page
function PeersPage() {
  const [peers, setPeers] = useState([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  const fetchPeers = async () => {
    try {
      const data = await apiFetch(`/api/peers/?search=${search}`);
      setPeers(data.peers);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPeers();
  }, [search]);

  return (
    <div>
      <div className="section-title-bar">
        <h1 style={{ fontFamily: 'var(--font-heading)', fontSize: '2rem' }}>Active Peers</h1>
      </div>

      <div className="glass-panel" style={{ marginBottom: '2.5rem', padding: '1.25rem 2rem' }}>
        <div style={{ position: 'relative' }}>
          <Search style={{ position: 'absolute', left: '12px', top: '13px', color: 'var(--text-muted)' }} size={18} />
          <input 
            type="text" 
            placeholder="Search peers by username..." 
            className="form-control" 
            style={{ paddingLeft: '2.5rem' }} 
            value={search} 
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '3rem' }}>Fetching peers list...</div>
      ) : peers.length > 0 ? (
        <div className="peers-grid">
          {peers.map(p => (
            <div key={p.peer_id} className="glass-panel peer-card">
              <div className="peer-avatar">
                {p.username[0].toUpperCase()}
              </div>
              <div className="peer-username">{p.username}</div>
              <div className="peer-status-label">
                <div className="user-status-dot"></div> Online
              </div>
              <div className="peer-meta">{p.files_count} Shared Files</div>
              <Link to={`/peers/${p.peer_id}`} className="btn btn-secondary" style={{ width: '100%', marginTop: '1.25rem', fontSize: '0.85rem', padding: '0.5rem' }}>
                View Files
              </Link>
            </div>
          ))}
        </div>
      ) : (
        <div className="glass-panel empty-state">
          <Users className="empty-state-icon" size={48} />
          <h3>No online peers found</h3>
          <p>There are no other active peers matching your search filters.</p>
        </div>
      )}
    </div>
  );
}

// 11. Peer Detail Page
function PeerDetailPage() {
  const { peerId } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchPeerDetail = async () => {
      try {
        const res = await apiFetch(`/api/peers/${peerId}/`);
        setData(res);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchPeerDetail();
  }, [peerId]);

  const handleDownload = async (fileId, filename) => {
    try {
      const response = await apiFetch(`/api/files/${fileId}/download/`);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
    } catch (err) {
      alert(`Download failed: ${err.message}`);
    }
  };

  if (loading) return <div style={{ textAlign: 'center', padding: '4rem' }}>Fetching peer profile...</div>;
  if (error) return <div className="form-error" style={{ maxWidth: '600px', margin: '2rem auto' }}>{error}</div>;

  return (
    <div>
      <div className="glass-panel" style={{ display: 'flex', alignItems: 'center', gap: '2.5rem', marginBottom: '2.5rem', padding: '2rem' }}>
        <div className="peer-avatar" style={{ margin: 0, width: '80px', height: '80px', fontSize: '2rem' }}>
          {data.peer.username[0].toUpperCase()}
        </div>
        <div>
          <h1 style={{ fontFamily: 'var(--font-heading)', fontSize: '2rem', fontWeight: 800, marginBottom: '0.25rem' }}>{data.peer.username}</h1>
          <div className="peer-status-label" style={{ marginBottom: '0.5rem' }}>
            <div className="user-status-dot"></div> Online
          </div>
          <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
            <strong>Network node:</strong> {data.peer.ip_address}:{data.peer.port}
          </div>
        </div>
      </div>

      <div className="glass-panel section-card">
        <div className="section-title-bar">
          <h2>Shared Files by {data.peer.username}</h2>
        </div>
        {data.shared_files.length > 0 ? (
          <div className="files-grid">
            {data.shared_files.map(file => (
              <div key={file.file_id} className="glass-panel file-card">
                <div className="file-card-header">
                  {getFileIcon(file.file_type)}
                  <span className={`badge badge-${file.file_type}`}>{file.file_type}</span>
                </div>
                <div className="file-name" title={file.filename}>{file.filename}</div>
                <div className="file-meta" style={{ border: 0, paddingTop: 0, marginBottom: '1.25rem' }}>
                  <span>Size: {file.file_size_display}</span>
                  <span>{file.download_count} DLs</span>
                </div>
                <div className="file-actions" style={{ marginTop: 'auto' }}>
                  <button onClick={() => handleDownload(file.file_id, file.filename)} className="btn btn-primary">
                    <Download size={16} /> Download
                  </button>
                  <Link to={`/files/${file.file_id}`} className="btn btn-secondary">Details</Link>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <Folder className="empty-state-icon" size={32} />
            <h3>No files shared yet</h3>
            <p>This peer hasn't published any files to the network library yet.</p>
          </div>
        )}
      </div>
    </div>
  );
}

// --- MAIN ROUTER APP ---
export default function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const data = await apiFetch('/api/auth/me/');
        setUser(data.user);
      } catch (err) {
        setUser(null);
      } finally {
        setLoading(false);
      }
    };
    
    // Warm up the CSRF token on mount
    const fetchCsrf = async () => {
      try {
        await apiFetch('/api/csrf/');
      } catch (err) {
        console.error('Failed to retrieve CSRF token:', err);
      }
      checkAuth();
    };
    fetchCsrf();
  }, []);

  const handleLogin = (authenticatedUser) => {
    setUser(authenticatedUser);
  };

  const handleLogout = () => {
    setUser(null);
  };

  if (loading) {
    return (
      <div style={{ background: 'var(--bg-main)', color: 'white', height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'var(--font-heading)', fontSize: '1.25rem', fontWeight: 600 }}>
        Waking up local nodes...
      </div>
    );
  }

  return (
    <BrowserRouter>
      <Layout user={user} onLogout={handleLogout}>
        <Routes>
          <Route path="/" element={<LandingPage user={user} />} />
          <Route path="/register" element={user ? <DashboardPage user={user} /> : <RegisterPage />} />
          <Route path="/verify-email/:uidb64/:token" element={<VerifyEmailPage />} />
          <Route path="/login" element={user ? <DashboardPage user={user} /> : <LoginPage onLogin={handleLogin} />} />
          
          {/* Protected Routes */}
          <Route path="/dashboard" element={user ? <DashboardPage user={user} /> : <LoginPage onLogin={handleLogin} />} />
          <Route path="/files" element={user ? <BrowseFilesPage /> : <LoginPage onLogin={handleLogin} />} />
          <Route path="/files/upload" element={user ? <UploadPage /> : <LoginPage onLogin={handleLogin} />} />
          <Route path="/files/:fileId" element={user ? <FileDetailPage user={user} /> : <LoginPage onLogin={handleLogin} />} />
          <Route path="/peers" element={user ? <PeersPage /> : <LoginPage onLogin={handleLogin} />} />
          <Route path="/peers/:peerId" element={user ? <PeerDetailPage /> : <LoginPage onLogin={handleLogin} />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
