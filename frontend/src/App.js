import React, { useState, useEffect, useCallback } from 'react';
import './App.css';

const API = '';

/* ─── Auth helpers ─── */
function getToken() { return localStorage.getItem('pm_token'); }
function setToken(t) { localStorage.setItem('pm_token', t); }
function clearToken() { localStorage.removeItem('pm_token'); localStorage.removeItem('pm_user'); }
function getUser() { try { return JSON.parse(localStorage.getItem('pm_user')); } catch { return null; } }
function setUser(u) { localStorage.setItem('pm_user', JSON.stringify(u)); }

function authHeaders() {
  const t = getToken();
  return t ? { 'Authorization': `Bearer ${t}`, 'Content-Type': 'application/json' } : { 'Content-Type': 'application/json' };
}

async function apiFetch(url, opts = {}) {
  const headers = { ...authHeaders(), ...opts.headers };
  const res = await fetch(url, { ...opts, headers });
  if (res.status === 401) { clearToken(); window.location.reload(); throw new Error('Session expired'); }
  return res;
}

function hasRole(...roles) { const u = getUser(); return u && roles.includes(u.role); }
function hasPerm(feature) { const u = getUser(); if(!u) return false; if(u.role==='admin') return true; return u.permissions ? !!u.permissions[feature] : hasRole('admin'); }

/* ─── Main App ─── */
function App() {
  const [token, setTokenState] = useState(getToken());
  const [user, setUserState] = useState(getUser());
  const [page, setPage] = useState('dashboard');
  const [health, setHealth] = useState(null);
  const [hosts, setHosts] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [licenseInfo, setLicenseInfo] = useState(null);
  const [showLicensePopup, setShowLicensePopup] = useState(false);

  const handleLogin = (t, u) => { setToken(t); setUser(u); setTokenState(t); setUserState(u); };
  const handleLogout = () => { clearToken(); setTokenState(null); setUserState(null); };

  const fetchAll = useCallback(() => {
    if (!getToken()) return;
    fetch(`${API}/api/health`).then(r => r.json()).then(setHealth).catch(() => setHealth(null));
    fetch(`${API}/api/license/status`).then(r => r.json()).then(setLicenseInfo).catch(() => {});
    apiFetch(`${API}/api/hosts/`).then(r => r.json()).then(setHosts).catch(() => {});
    apiFetch(`${API}/api/jobs/`).then(r => r.json()).then(setJobs).catch(() => {});
  }, []);

  useEffect(() => { if (token) { fetchAll(); const t = setInterval(fetchAll, 15000); return () => clearInterval(t); } }, [token, fetchAll]);

  // Auto-show license popup when license is expired or not activated
  useEffect(() => {
    if (licenseInfo && (!licenseInfo.activated || licenseInfo.expired)) {
      setShowLicensePopup(true);
    } else {
      setShowLicensePopup(false);
    }
  }, [licenseInfo]);

  if (!token) return <LoginPage onLogin={handleLogin} />;

  const navItems = [
    { key: 'dashboard', label: 'Dashboard', icon: '📊' },
    ...(hasPerm('compliance') ? [{ key: 'compliance', label: 'Compliance', icon: '🛡️' }] : []),
    ...(hasPerm('hosts') ? [{ key: 'hosts', label: 'Hosts', icon: '🖥️' }] : []),
    ...(hasPerm('groups') ? [{ key: 'groups', label: 'Groups & Tags', icon: '📁' }] : []),
    ...(hasPerm('patches') ? [{ key: 'patches', label: 'Patch Manager', icon: '🔄' }] : []),
    ...(hasPerm('snapshots') ? [{ key: 'snapshots', label: 'Snapshots', icon: '📸' }] : []),
    ...(hasPerm('compare') ? [{ key: 'compare', label: 'Compare Packages', icon: '🔍' }] : []),
    ...(hasPerm('offline') ? [{ key: 'offline', label: 'Offline Patching', icon: '📦' }] : []),
    ...(hasPerm('schedules') ? [{ key: 'schedules', label: 'Schedules', icon: '📅' }] : []),
    ...(hasPerm('cve') ? [{ key: 'cve', label: 'CVE Tracker', icon: '🔒' }] : []),
    ...(hasPerm('jobs') ? [{ key: 'jobs', label: 'Job History', icon: '⚙️' }] : []),
    ...(hasPerm('audit') ? [{ key: 'audit', label: 'Audit Trail', icon: '📋' }] : []),
    ...(hasPerm('notifications') ? [{ key: 'notifications', label: 'Notifications', icon: '🔔' }] : []),
    ...(hasPerm('users') ? [{ key: 'users', label: 'User Management', icon: '👤' }] : []),
    { key: 'license', label: 'License', icon: '🔑' },
    ...(hasPerm('cicd') ? [{ key: 'cicd', label: 'CI/CD Pipelines', icon: '🚀' }] : []),
    { key: 'monitoring', label: 'Monitoring Tools', icon: '📈' },
    { key: 'onboarding', label: 'Onboarding', icon: '🚀' },
    { key: 'settings', label: 'Settings', icon: '🔧' },
  ];

  return (
    <div className="app-container">
      <aside className="sidebar">
        <div className="sidebar-header">
          <h2>PatchMaster</h2>
          <span className="sidebar-subtitle">Enterprise Patch Management</span>
        </div>
        <nav className="sidebar-nav">
          {navItems.map(n => (
            <button key={n.key} className={`nav-btn ${page === n.key ? 'active' : ''}`} onClick={() => setPage(n.key)}>
              <span className="nav-icon">{n.icon}</span> {n.label}
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          {/* License status indicator */}
          {licenseInfo && (
            <div style={{marginBottom:8,padding:'6px 10px',borderRadius:6,fontSize:11,cursor:'pointer',
              background: !licenseInfo.activated ? '#374151' : licenseInfo.expired ? '#7f1d1d' : licenseInfo.days_remaining<=30 ? '#78350f' : '#064e3b',
              color: !licenseInfo.activated ? '#9ca3af' : licenseInfo.expired ? '#fca5a5' : licenseInfo.days_remaining<=30 ? '#fcd34d' : '#6ee7b7',
              border: `1px solid ${!licenseInfo.activated ? '#4b5563' : licenseInfo.expired ? '#dc2626' : licenseInfo.days_remaining<=30 ? '#f59e0b' : '#10b981'}`
            }} onClick={()=>setPage('license')}>
              <div style={{fontWeight:600}}>
                {!licenseInfo.activated ? '⚠️ No License' : licenseInfo.expired ? '🔴 License Expired' : `🟢 ${licenseInfo.tier_label || 'Licensed'}`}
              </div>
              {licenseInfo.activated && !licenseInfo.expired && (
                <div style={{marginTop:2,opacity:0.85}}>{licenseInfo.days_remaining} days remaining</div>
              )}
              {licenseInfo.activated && licenseInfo.expired && (
                <div style={{marginTop:2,opacity:0.85}}>Expired — click to renew</div>
              )}
            </div>
          )}
          <div style={{display:'flex',alignItems:'center',gap:8,width:'100%'}}>
            <span className={`status-dot ${health ? 'online' : 'offline'}`}></span>
            <span style={{flex:1}}>{user?.username} <span className="badge badge-info" style={{fontSize:9}}>{user?.role}</span></span>
            <button className="btn btn-sm btn-danger" onClick={handleLogout} style={{padding:'3px 8px',fontSize:11}}>Logout</button>
          </div>
        </div>
      </aside>
      <main className="main-content">
        {/* License expired/not-activated popup modal */}
        {showLicensePopup && <LicensePopup licenseInfo={licenseInfo} onSuccess={() => { setShowLicensePopup(false); fetchAll(); }} />}
        {/* Expiring soon warning banner */}
        {licenseInfo && licenseInfo.valid && !licenseInfo.expired && licenseInfo.days_remaining <= 30 && (
          <div style={{background:'#ffc107',color:'#000',padding:'8px 20px',textAlign:'center',fontWeight:600,cursor:'pointer'}} onClick={()=>setPage('license')}>
            ⚠️ License expires in {licenseInfo.days_remaining} day{licenseInfo.days_remaining!==1?'s':''} ({licenseInfo.expires_at}). Click here to manage.
          </div>
        )}
        <header className="top-bar">
          <h1 className="page-title">{navItems.find(n => n.key === page)?.label || 'Dashboard'}</h1>
          <div className="top-bar-actions">
            <button className="btn btn-sm" onClick={fetchAll}>Refresh</button>
          </div>
        </header>
        <div className="content-area">
          {page === 'dashboard' && <DashboardPage health={health} hosts={hosts} jobs={jobs} setPage={setPage} />}
          {page === 'compliance' && <CompliancePage />}
          {page === 'hosts' && <HostsPage hosts={hosts} setHosts={setHosts} />}
          {page === 'groups' && <GroupsPage />}
          {page === 'patches' && <PatchManagerPage hosts={hosts} />}
          {page === 'snapshots' && <SnapshotsPage hosts={hosts} />}
          {page === 'compare' && <ComparePackagesPage hosts={hosts} />}
          {page === 'offline' && <OfflinePatchPage hosts={hosts} />}
          {page === 'schedules' && <SchedulesPage />}
          {page === 'cve' && <CVEPage />}
          {page === 'jobs' && <JobsPage jobs={jobs} setJobs={setJobs} />}
          {page === 'audit' && <AuditPage />}
          {page === 'notifications' && <NotificationsPage />}
          {page === 'users' && hasPerm('users') && <UsersPage />}
          {page === 'license' && <LicensePage licenseInfo={licenseInfo} onRefresh={fetchAll} />}
          {page === 'cicd' && hasPerm('cicd') && <CICDPage />}
          {page === 'monitoring' && <MonitoringToolsPage />}
          {page === 'onboarding' && <OnboardingPage />}
          {page === 'settings' && <SettingsPage health={health} hosts={hosts} jobs={jobs} />}
        </div>
      </main>
    </div>
  );
}

/* ─── Login Page ─── */
function LoginPage({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault(); setError(''); setLoading(true);
    try {
      if (isRegister) {
        const r = await fetch(`${API}/api/auth/register`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({username,password,email}) });
        const d = await r.json(); if (!r.ok) { setError(d.detail||'Registration failed'); setLoading(false); return; }
        setIsRegister(false); setError(''); alert('Registered! First user gets admin role. Please login.');
      } else {
        const r = await fetch(`${API}/api/auth/login`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({username,password}) });
        const d = await r.json(); if (!r.ok) { setError(d.detail||'Login failed'); setLoading(false); return; }
        const me = await fetch(`${API}/api/auth/me`, { headers:{'Authorization':`Bearer ${d.access_token}`}}).then(r=>r.json());
        onLogin(d.access_token, me);
      }
    } catch(e) { setError('Connection failed'); }
    setLoading(false);
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <h2>🛡️ PatchMaster</h2>
        <p className="login-subtitle">{isRegister ? 'Create Account' : 'Sign In'}</p>
        <form onSubmit={submit}>
          <input className="input login-input" placeholder="Username" value={username} onChange={e=>setUsername(e.target.value)} required />
          {isRegister && <input className="input login-input" type="email" placeholder="Email" value={email} onChange={e=>setEmail(e.target.value)} required />}
          <input className="input login-input" type="password" placeholder="Password" value={password} onChange={e=>setPassword(e.target.value)} required />
          {error && <p className="text-danger" style={{fontSize:13,margin:'8px 0'}}>{error}</p>}
          <button className="btn btn-primary btn-lg login-btn" disabled={loading}>{loading ? '...' : isRegister ? 'Register' : 'Login'}</button>
        </form>
        <p style={{marginTop:16,fontSize:13,color:'#6b7280',cursor:'pointer'}} onClick={()=>{setIsRegister(!isRegister);setError('');}}>
          {isRegister ? 'Already have an account? Login' : 'First time? Register (first user = admin)'}
        </p>
      </div>
    </div>
  );
}

/* ─── License Expired / Not Activated Popup ─── */
function LicensePopup({ licenseInfo, onSuccess }) {
  const [key, setKey] = useState('');
  const [msg, setMsg] = useState('');
  const [loading, setLoading] = useState(false);
  const li = licenseInfo || {};
  const isExpired = li.activated && li.expired;

  const activate = async () => {
    if (!key.trim()) { setMsg('Please enter a license key'); return; }
    setLoading(true); setMsg('');
    try {
      const r = await apiFetch(`${API}/api/license/activate`, { method:'POST', body: JSON.stringify({ license_key: key.trim() }) });
      const d = await r.json();
      if (r.ok) { setMsg(''); onSuccess(); }
      else { setMsg(d.detail || 'Activation failed'); }
    } catch(e) { setMsg('Error: ' + e.message); }
    setLoading(false);
  };

  const handleKeyDown = (e) => { if (e.key === 'Enter') activate(); };

  return (
    <div style={{
      position:'fixed',top:0,left:0,right:0,bottom:0,
      background:'rgba(0,0,0,0.75)',backdropFilter:'blur(6px)',
      display:'flex',alignItems:'center',justifyContent:'center',
      zIndex:10000,
    }}>
      <div style={{
        background:'#1a1a2e',border:'1px solid #374151',borderRadius:16,
        padding:40,maxWidth:520,width:'90%',textAlign:'center',
        boxShadow:'0 20px 60px rgba(0,0,0,0.5)',
      }}>
        <div style={{fontSize:56,marginBottom:16}}>{isExpired ? '⏰' : '🔑'}</div>
        <h2 style={{color:'#f9fafb',marginBottom:8,fontSize:22}}>
          {isExpired ? 'License Expired' : 'License Required'}
        </h2>
        <p style={{color:'#9ca3af',marginBottom:8,fontSize:14,lineHeight:1.6}}>
          {isExpired
            ? `Your PatchMaster license expired on ${li.expires_at}. All services are paused until a valid license is activated.`
            : 'PatchMaster requires a valid license to operate. Please enter your license key to activate all services.'}
        </p>
        {isExpired && li.customer && (
          <p style={{color:'#6b7280',fontSize:12,marginBottom:16}}>
            Customer: {li.customer} | Plan: {li.plan_label} | Tier: {li.tier_label}
          </p>
        )}
        <p style={{color:'#d1d5db',fontSize:13,marginBottom:20}}>
          Contact your PatchMaster vendor to obtain a new license key.
        </p>
        <div style={{display:'flex',gap:10,marginBottom:12}}>
          <input
            className="input"
            style={{flex:1,fontFamily:'monospace',fontSize:12,padding:'10px 14px',background:'#111827',border:'1px solid #374151',color:'#f9fafb',borderRadius:8}}
            placeholder="PM1-xxxxxxxxx.xxxxxxxx"
            value={key}
            onChange={e => setKey(e.target.value)}
            onKeyDown={handleKeyDown}
            autoFocus
          />
          <button
            className="btn btn-primary"
            onClick={activate}
            disabled={loading}
            style={{padding:'10px 24px',borderRadius:8,fontWeight:600}}
          >
            {loading ? 'Activating...' : 'Activate'}
          </button>
        </div>
        {msg && <p style={{color:'#dc3545',fontWeight:500,fontSize:13,marginTop:8}}>{msg}</p>}
      </div>
    </div>
  );
}

/* ─── Dashboard ─── */
function DashboardPage({ health, hosts, jobs, setPage }) {
  const [stats, setStats] = useState(null);
  useEffect(() => { apiFetch(`${API}/api/compliance/overview`).then(r=>r.json()).then(setStats).catch(()=>{}); }, []);
  const running = jobs.filter(j => j.status === 'running').length;
  const completed = jobs.filter(j => j.status === 'completed' || j.status === 'success').length;
  const failed = jobs.filter(j => j.status === 'failed' || j.status === 'error').length;
  const pending = jobs.filter(j => j.status === 'pending' || j.status === 'scheduled').length;
  return (
    <div>
      <div className="stats-grid">
        <div className="stat-card" onClick={() => setPage('hosts')}><div className="stat-icon">🖥️</div><div className="stat-info"><span className="stat-number">{stats?.total_hosts||hosts.length}</span><span className="stat-label">Total Hosts</span></div></div>
        <div className="stat-card success" onClick={() => setPage('hosts')}><div className="stat-icon">🟢</div><div className="stat-info"><span className="stat-number">{stats?.online_hosts||0}</span><span className="stat-label">Online</span></div></div>
        <div className="stat-card" onClick={() => setPage('compliance')}><div className="stat-icon">🛡️</div><div className="stat-info"><span className="stat-number">{stats?.avg_compliance||0}%</span><span className="stat-label">Avg Compliance</span></div></div>
        <div className="stat-card warning" onClick={() => setPage('cve')}><div className="stat-icon">🔒</div><div className="stat-info"><span className="stat-number">{stats?.cves?.critical||0}</span><span className="stat-label">Critical CVEs</span></div></div>
        <div className="stat-card danger"><div className="stat-icon">⚠️</div><div className="stat-info"><span className="stat-number">{stats?.reboot_required||0}</span><span className="stat-label">Reboot Needed</span></div></div>
        <div className="stat-card info" onClick={() => setPage('jobs')}><div className="stat-icon">⚙️</div><div className="stat-info"><span className="stat-number">{jobs.length}</span><span className="stat-label">Total Jobs</span></div></div>
      </div>
      {stats && (
        <div className="grid-2">
          <div className="card">
            <h3>Compliance Distribution</h3>
            <div className="compliance-bars">
              <div className="comp-bar-row"><span>Fully Patched (100%)</span><div className="comp-bar"><div className="comp-fill success" style={{width:`${stats.total_hosts?((stats.compliance_distribution.fully_patched/stats.total_hosts)*100):0}%`}}></div></div><span>{stats.compliance_distribution.fully_patched}</span></div>
              <div className="comp-bar-row"><span>Mostly Patched (80-99%)</span><div className="comp-bar"><div className="comp-fill warning" style={{width:`${stats.total_hosts?((stats.compliance_distribution.mostly_patched/stats.total_hosts)*100):0}%`}}></div></div><span>{stats.compliance_distribution.mostly_patched}</span></div>
              <div className="comp-bar-row"><span>Needs Attention (&lt;80%)</span><div className="comp-bar"><div className="comp-fill danger" style={{width:`${stats.total_hosts?((stats.compliance_distribution.needs_attention/stats.total_hosts)*100):0}%`}}></div></div><span>{stats.compliance_distribution.needs_attention}</span></div>
            </div>
          </div>
          <div className="card">
            <h3>Jobs (Last 30 Days)</h3>
            <div style={{display:'flex',gap:20,marginTop:8}}>
              <div className="mini-stat success"><span className="stat-number">{stats.jobs_30d.success}</span><span className="stat-label">Success</span></div>
              <div className="mini-stat danger"><span className="stat-number">{stats.jobs_30d.failed}</span><span className="stat-label">Failed</span></div>
              <div className="mini-stat warning"><span className="stat-number">{running}</span><span className="stat-label">Running</span></div>
              <div className="mini-stat info"><span className="stat-number">{pending}</span><span className="stat-label">Pending</span></div>
            </div>
          </div>
        </div>
      )}
      <div className="card">
        <h3>Backend Status</h3>
        {health ? <p className="text-success">Backend is <strong>online</strong> — status: {health.status}</p> : <p className="text-danger">Backend is <strong>offline</strong>. Check Docker containers.</p>}
      </div>
      <div className="grid-2">
        <div className="card"><h3>Recent Hosts</h3>{hosts.length === 0 ? <p className="text-muted">No hosts registered yet.</p> : <table className="table"><thead><tr><th>Name</th><th>IP</th><th>OS</th></tr></thead><tbody>{hosts.slice(0,5).map(h => <tr key={h.id}><td>{h.hostname||h.name}</td><td>{h.ip}</td><td>{h.os||''}</td></tr>)}</tbody></table>}</div>
        <div className="card"><h3>Recent Jobs</h3>{jobs.length === 0 ? <p className="text-muted">No jobs created yet.</p> : <table className="table"><thead><tr><th>Action</th><th>Status</th></tr></thead><tbody>{jobs.slice(0,5).map(j => <tr key={j.id}><td>{j.action||j.name}</td><td><span className={`badge badge-${j.status==='completed'||j.status==='success'?'success':j.status==='running'?'warning':j.status==='failed'?'danger':'info'}`}>{j.status}</span></td></tr>)}</tbody></table>}</div>
      </div>
      <div className="card"><h3>Quick Actions</h3><div className="btn-group">
        <button className="btn btn-primary" onClick={() => setPage('patches')}>🔄 Patch Servers</button>
        <button className="btn btn-primary" onClick={() => setPage('snapshots')}>📸 Manage Snapshots</button>
        <button className="btn btn-primary" onClick={() => setPage('compliance')}>🛡️ Compliance</button>
        <button className="btn btn-primary" onClick={() => setPage('cve')}>🔒 CVE Tracker</button>
        <button className="btn btn-success" onClick={() => setPage('onboarding')}>🚀 Onboard New Host</button>
      </div></div>
    </div>
  );
}

/* ─── Hosts ─── */
function HostsPage({ hosts, setHosts }) {
  const [search, setSearch] = useState('');
  const [agentStatus, setAgentStatus] = useState({});

  const refreshHosts = () => { apiFetch(`${API}/api/hosts/`).then(r=>r.json()).then(setHosts).catch(()=>{}); };

  const checkAgent = async (ip) => {
    try {
      const r = await apiFetch(`${API}/api/agent/${ip}/health`);
      const d = await r.json();
      setAgentStatus(prev => ({...prev, [ip]: { online: true, state: d.state }}));
    } catch {
      setAgentStatus(prev => ({...prev, [ip]: { online: false }}));
    }
  };

  useEffect(() => { hosts.forEach(h => checkAgent(h.ip)); }, [hosts]);

  const deleteHost = id => { if (!window.confirm('Delete this host?')) return; apiFetch(`${API}/api/hosts/${id}`, { method: 'DELETE' }).then(() => refreshHosts()); };
  const filtered = hosts.filter(h => (h.hostname||h.name||'').toLowerCase().includes(search.toLowerCase()) || (h.ip||'').includes(search) || (h.os||'').toLowerCase().includes(search.toLowerCase()));

  return (
    <div>
      <div className="card">
        <div className="card-header"><h3>Registered Hosts ({filtered.length})</h3><div className="form-row"><input className="input search-input" placeholder="Search hosts..." value={search} onChange={e => setSearch(e.target.value)} /><button className="btn btn-sm" onClick={refreshHosts}>Refresh</button></div></div>
        {filtered.length === 0 ? <p className="text-muted">No hosts found. Agents auto-register on startup.</p> : (
          <table className="table"><thead><tr><th>Hostname</th><th>IP</th><th>OS</th><th>Compliance</th><th>CVEs</th><th>Upgradable</th><th>Agent</th><th>Actions</th></tr></thead>
            <tbody>{filtered.map(h => (
              <tr key={h.id}>
                <td><strong>{h.hostname||h.name}</strong></td>
                <td>{h.ip}</td>
                <td>{h.os} {h.os_version||''}</td>
                <td><span className={`badge badge-${(h.compliance_score||0)>=90?'success':(h.compliance_score||0)>=70?'warning':'danger'}`}>{h.compliance_score||0}%</span></td>
                <td>{h.cve_count||0}</td>
                <td>{h.upgradable_count||0}</td>
                <td>{agentStatus[h.ip]?.online || h.is_online ? <span className="badge badge-success">Online</span> : <span className="badge badge-danger">Offline</span>}</td>
                <td>{hasRole('admin','operator') && <button className="btn btn-sm btn-danger" onClick={()=>deleteHost(h.id)}>Del</button>} <button className="btn btn-sm" onClick={()=>checkAgent(h.ip)}>Ping</button></td>
              </tr>
            ))}</tbody></table>
        )}
      </div>
    </div>
  );
}


/* ─── Compliance ─── */
function CompliancePage() {
  const [overview, setOverview] = useState(null);
  const [byGroup, setByGroup] = useState([]);
  const [hostDetail, setHostDetail] = useState([]);
  const [view, setView] = useState('overview');
  useEffect(() => {
    apiFetch(`${API}/api/compliance/overview`).then(r=>r.json()).then(setOverview).catch(()=>{});
    apiFetch(`${API}/api/compliance/by-group`).then(r=>r.json()).then(setByGroup).catch(()=>{});
    apiFetch(`${API}/api/compliance/hosts-detail`).then(r=>r.json()).then(setHostDetail).catch(()=>{});
  }, []);
  return (
    <div>
      <div className="btn-group" style={{marginBottom:16}}>
        <button className={`btn ${view==='overview'?'btn-primary':''}`} onClick={()=>setView('overview')}>Overview</button>
        <button className={`btn ${view==='groups'?'btn-primary':''}`} onClick={()=>setView('groups')}>By Group</button>
        <button className={`btn ${view==='hosts'?'btn-primary':''}`} onClick={()=>setView('hosts')}>By Host</button>
      </div>
      {view==='overview' && overview && (
        <div>
          <div className="stats-grid">
            <div className="stat-card"><div className="stat-icon">🖥️</div><div className="stat-info"><span className="stat-number">{overview.total_hosts}</span><span className="stat-label">Total Hosts</span></div></div>
            <div className="stat-card success"><div className="stat-icon">🟢</div><div className="stat-info"><span className="stat-number">{overview.online_hosts}</span><span className="stat-label">Online</span></div></div>
            <div className="stat-card"><div className="stat-icon">🛡️</div><div className="stat-info"><span className="stat-number">{overview.avg_compliance}%</span><span className="stat-label">Avg Compliance</span></div></div>
            <div className="stat-card danger"><div className="stat-icon">🔴</div><div className="stat-info"><span className="stat-number">{overview.cves.critical}</span><span className="stat-label">Critical CVEs</span></div></div>
            <div className="stat-card warning"><div className="stat-icon">🟡</div><div className="stat-info"><span className="stat-number">{overview.cves.high}</span><span className="stat-label">High CVEs</span></div></div>
            <div className="stat-card info"><div className="stat-icon">📦</div><div className="stat-info"><span className="stat-number">{overview.total_upgradable}</span><span className="stat-label">Upgradable Pkgs</span></div></div>
          </div>
          <div className="card">
            <h3>Compliance Distribution</h3>
            <div className="compliance-bars">
              <div className="comp-bar-row"><span>Fully Patched (100%)</span><div className="comp-bar"><div className="comp-fill success" style={{width:`${overview.total_hosts?((overview.compliance_distribution.fully_patched/overview.total_hosts)*100):0}%`}}></div></div><span>{overview.compliance_distribution.fully_patched}</span></div>
              <div className="comp-bar-row"><span>Mostly Patched (80-99%)</span><div className="comp-bar"><div className="comp-fill warning" style={{width:`${overview.total_hosts?((overview.compliance_distribution.mostly_patched/overview.total_hosts)*100):0}%`}}></div></div><span>{overview.compliance_distribution.mostly_patched}</span></div>
              <div className="comp-bar-row"><span>Needs Attention (&lt;80%)</span><div className="comp-bar"><div className="comp-fill danger" style={{width:`${overview.total_hosts?((overview.compliance_distribution.needs_attention/overview.total_hosts)*100):0}%`}}></div></div><span>{overview.compliance_distribution.needs_attention}</span></div>
            </div>
          </div>
        </div>
      )}
      {view==='groups' && (
        <div className="card">
          <h3>Compliance by Group</h3>
          {byGroup.length===0 ? <p className="text-muted">No groups with hosts found.</p> : (
            <table className="table"><thead><tr><th>Group</th><th>Hosts</th><th>Online</th><th>Avg Compliance</th><th>Min Compliance</th><th>CVEs</th><th>Upgradable</th></tr></thead>
            <tbody>{byGroup.map((g,i)=><tr key={i}><td><strong>{g.group}</strong></td><td>{g.host_count}</td><td>{g.online}</td><td><span className={`badge badge-${g.avg_compliance>=90?'success':g.avg_compliance>=70?'warning':'danger'}`}>{g.avg_compliance}%</span></td><td>{g.min_compliance}%</td><td>{g.total_cves}</td><td>{g.total_upgradable}</td></tr>)}</tbody></table>
          )}
        </div>
      )}
      {view==='hosts' && (
        <div className="card">
          <h3>Per-Host Compliance</h3>
          <table className="table"><thead><tr><th>Hostname</th><th>IP</th><th>OS</th><th>Online</th><th>Compliance</th><th>CVEs</th><th>Upgradable</th><th>Reboot</th><th>Groups</th></tr></thead>
          <tbody>{hostDetail.map(h=><tr key={h.id}><td><strong>{h.hostname}</strong></td><td>{h.ip}</td><td>{h.os}</td><td>{h.is_online?<span className="badge badge-success">Yes</span>:<span className="badge badge-danger">No</span>}</td><td><span className={`badge badge-${h.compliance_score>=90?'success':h.compliance_score>=70?'warning':'danger'}`}>{h.compliance_score}%</span></td><td>{h.cve_count}</td><td>{h.upgradable_count}</td><td>{h.reboot_required?'⚠️':''}</td><td>{(h.groups||[]).join(', ')}</td></tr>)}</tbody></table>
        </div>
      )}
    </div>
  );
}

/* ─── Groups & Tags ─── */
function GroupsPage() {
  const [groups, setGroups] = useState([]);
  const [tags, setTags] = useState([]);
  const [newGroup, setNewGroup] = useState('');
  const [newGroupDesc, setNewGroupDesc] = useState('');
  const [expandedGroup, setExpandedGroup] = useState(null);
  const [groupHosts, setGroupHosts] = useState([]);

  const refresh = () => {
    apiFetch(`${API}/api/groups/`).then(r=>r.json()).then(setGroups).catch(()=>{});
    apiFetch(`${API}/api/tags/`).then(r=>r.json()).then(setTags).catch(()=>{});
  };
  useEffect(refresh, []);

  const createGroup = () => {
    if (!newGroup) return;
    apiFetch(`${API}/api/groups/`, { method:'POST', body: JSON.stringify({name:newGroup,description:newGroupDesc}) }).then(()=>{ setNewGroup(''); setNewGroupDesc(''); refresh(); });
  };
  const deleteGroup = id => { if(!window.confirm('Delete group?')) return; apiFetch(`${API}/api/groups/${id}`,{method:'DELETE'}).then(refresh); };
  const toggleExpand = async (id) => {
    if (expandedGroup===id) { setExpandedGroup(null); return; }
    const r = await apiFetch(`${API}/api/groups/${id}`); const d = await r.json();
    setGroupHosts(d.hosts||[]); setExpandedGroup(id);
  };

  return (
    <div>
      <div className="card">
        <h3>Create Host Group</h3>
        <div className="form-row">
          <input className="input" placeholder="Group name" value={newGroup} onChange={e=>setNewGroup(e.target.value)} />
          <input className="input" placeholder="Description" value={newGroupDesc} onChange={e=>setNewGroupDesc(e.target.value)} style={{flex:1}} />
          <button className="btn btn-primary" onClick={createGroup}>Create Group</button>
        </div>
      </div>
      <div className="card">
        <h3>Groups ({groups.length})</h3>
        {groups.length===0 ? <p className="text-muted">No groups created.</p> : (
          <table className="table"><thead><tr><th>Name</th><th>Description</th><th>Hosts</th><th>Actions</th></tr></thead>
          <tbody>{groups.map(g=><React.Fragment key={g.id}>
            <tr><td><strong>{g.name}</strong></td><td>{g.description||'—'}</td><td>{g.host_count||0}</td>
            <td><button className="btn btn-sm" onClick={()=>toggleExpand(g.id)}>{expandedGroup===g.id?'Collapse':'View Hosts'}</button> {hasRole('admin')&&<button className="btn btn-sm btn-danger" onClick={()=>deleteGroup(g.id)}>Del</button>}</td></tr>
            {expandedGroup===g.id && <tr><td colSpan="4"><div style={{padding:'8px 12px',background:'#f8f9fa',borderRadius:6}}>
              {groupHosts.length===0 ? <p className="text-muted">No hosts in this group.</p> : groupHosts.map(h=><span key={h.id} className="badge badge-info" style={{marginRight:6}}>{h.hostname} ({h.ip})</span>)}
            </div></td></tr>}
          </React.Fragment>)}</tbody></table>
        )}
      </div>
      <div className="card">
        <h3>Tags ({tags.length})</h3>
        {tags.length===0 ? <p className="text-muted">No tags. Tags are auto-created when assigned to hosts.</p> : (
          <div style={{display:'flex',gap:8,flexWrap:'wrap'}}>{tags.map(t=><span key={t.id} className="badge badge-info">{t.name}</span>)}</div>
        )}
      </div>
    </div>
  );
}

/* ─── Patch Manager ─── */
function PatchManagerPage({ hosts }) {
  const [selectedHost, setSelectedHost] = useState('');
  const [upgradable, setUpgradable] = useState([]);
  const [loading, setLoading] = useState(false);
  const [patchResult, setPatchResult] = useState(null);
  const [selectedPkgs, setSelectedPkgs] = useState([]);
  const [holdPkgs, setHoldPkgs] = useState('');
  const [autoSnapshot, setAutoSnapshot] = useState(true);
  const [autoRollback, setAutoRollback] = useState(true);
  const [dryRun, setDryRun] = useState(false);
  const [patchLoading, setPatchLoading] = useState(false);
  const [patchPhase, setPatchPhase] = useState('');

  const fetchUpgradable = async () => {
    if (!selectedHost) return alert('Select a host first');
    setLoading(true); setUpgradable([]); setPatchResult(null);
    try {
      const r = await apiFetch(`${API}/api/agent/${selectedHost}/packages/upgradable`);
      const d = await r.json();
      setUpgradable(d.packages || []);
    } catch (e) { alert('Could not reach agent: ' + e.message); }
    setLoading(false);
  };

  const togglePkg = (name) => {
    setSelectedPkgs(prev => prev.includes(name) ? prev.filter(p => p !== name) : [...prev, name]);
  };
  const selectAll = () => setSelectedPkgs(upgradable.map(p => p.name));
  const selectNone = () => setSelectedPkgs([]);

  const executePatch = async () => {
    if (!selectedHost) return alert('Select a host');
    const mode = dryRun ? 'DRY RUN' : 'EXECUTE';
    if (!window.confirm(`${mode} server-side patching on ${selectedHost}?\n\nAuto-Snapshot: ${autoSnapshot}\nAuto-Rollback: ${autoRollback}\nPackages: ${selectedPkgs.length || 'ALL upgradable'}`)) return;
    setPatchLoading(true); setPatchResult(null); setPatchPhase('Starting...');
    try {
      const body = { packages: selectedPkgs, hold: holdPkgs.split(',').map(s => s.trim()).filter(Boolean), dry_run: dryRun, auto_snapshot: autoSnapshot, auto_rollback: autoRollback };
      setPatchPhase('Server downloading packages & patching agent...');
      const r = await apiFetch(`${API}/api/agent/${selectedHost}/patch/server-patch`, { method: 'POST', body: JSON.stringify(body) });
      const d = await r.json(); setPatchResult(d); setPatchPhase('');
    } catch (e) { setPatchResult({ error: e.message }); setPatchPhase(''); }
    setPatchLoading(false);
  };

  return (
    <div>
      <div className="card highlight-card">
        <h3>🔄 Patch Manager — Server Download → Push → Install</h3>
        <p>Server downloads packages from internet, pushes to agent, installs offline with snapshot protection. <strong>Agents don't need internet.</strong></p>
        <div className="workflow-steps">
          <div className="workflow-step"><span className="step-num">1</span> Select Host</div><div className="workflow-arrow">→</div>
          <div className="workflow-step"><span className="step-num">2</span> Server Downloads .debs</div><div className="workflow-arrow">→</div>
          <div className="workflow-step"><span className="step-num">3</span> Push to Agent</div><div className="workflow-arrow">→</div>
          <div className="workflow-step"><span className="step-num">4</span> Offline Install + Snapshot</div>
        </div>
      </div>
      <div className="card"><h3>Select Host</h3>
        <div className="form-row">
          <select className="input" value={selectedHost} onChange={e=>{setSelectedHost(e.target.value);setUpgradable([]);setPatchResult(null);}}>
            <option value="">-- Select Host --</option>
            {hosts.map(h => <option key={h.id} value={h.ip}>{h.hostname||h.name} ({h.ip})</option>)}
          </select>
          <button className="btn btn-primary" onClick={fetchUpgradable} disabled={loading}>{loading ? 'Checking...' : 'Check Updates'}</button>
        </div>
      </div>
      {upgradable.length > 0 && (
        <div className="card">
          <div className="card-header"><h3>Available Updates ({upgradable.length})</h3><div className="btn-group"><button className="btn btn-sm btn-primary" onClick={selectAll}>Select All</button><button className="btn btn-sm" onClick={selectNone}>Deselect All</button></div></div>
          <div className="package-list"><table className="table"><thead><tr><th style={{width:'40px'}}>✓</th><th>Package</th><th>Current</th><th>Available</th></tr></thead>
          <tbody>{upgradable.map((p,i)=><tr key={i} className={selectedPkgs.includes(p.name)?'row-selected':''}><td><input type="checkbox" checked={selectedPkgs.includes(p.name)} onChange={()=>togglePkg(p.name)} /></td><td><strong>{p.name}</strong></td><td><code>{p.current_version||'—'}</code></td><td><code className="text-success-inline">{p.available_version}</code></td></tr>)}</tbody></table></div>
        </div>
      )}
      <div className="card"><h3>Patch Options</h3>
        <div className="options-grid">
          <label className="toggle-option"><input type="checkbox" checked={autoSnapshot} onChange={e=>setAutoSnapshot(e.target.checked)} /> <span>📸 Auto-Snapshot before install</span></label>
          <label className="toggle-option"><input type="checkbox" checked={autoRollback} onChange={e=>setAutoRollback(e.target.checked)} /> <span>⏪ Auto-Rollback on failure</span></label>
          <label className="toggle-option"><input type="checkbox" checked={dryRun} onChange={e=>setDryRun(e.target.checked)} /> <span>🧪 Dry Run</span></label>
        </div>
        <div className="form-row" style={{marginTop:'12px'}}><input className="input" placeholder="Hold packages (comma-separated)" value={holdPkgs} onChange={e=>setHoldPkgs(e.target.value)} style={{flex:1}} /></div>
        <div style={{marginTop:'16px'}}>
          <button className="btn btn-lg btn-success" onClick={executePatch} disabled={patchLoading||!selectedHost}>{patchLoading?'⏳ Patching...':dryRun?'🧪 Simulate':'🚀 Download & Patch'}</button>
          {patchPhase && <span style={{marginLeft:'16px',color:'#6b7280',fontStyle:'italic'}}>{patchPhase}</span>}
        </div>
      </div>
      {patchResult && (
        <div className={`card ${patchResult.success?'result-success':'result-failure'}`}>
          <h3>{patchResult.success?'✅ Patch Successful':'❌ Patch Failed'}</h3>
          {patchResult.dry_run && <p><span className="badge badge-info">DRY RUN</span> {patchResult.message||''}</p>}
          {patchResult.dry_run && patchResult.packages_to_download && <div style={{margin:'8px 0'}}><strong>Packages:</strong><ul>{patchResult.packages_to_download.map((f,i)=><li key={i}><code>{f}</code></li>)}</ul></div>}
          {!patchResult.dry_run && patchResult.downloaded?.length>0 && <p>📦 Downloaded: <strong>{patchResult.downloaded.length}</strong> packages</p>}
          {!patchResult.dry_run && patchResult.pushed>0 && <p>📤 Pushed: <strong>{patchResult.pushed}</strong> .deb files</p>}
          {patchResult.install_result?.snapshot && <p>📸 Snapshot: <strong>{patchResult.install_result.snapshot.name}</strong></p>}
          {patchResult.install_result?.rollback && <p>⏪ Rollback: <strong>{patchResult.install_result.rollback.success?'Restored':'FAILED'}</strong></p>}
          {patchResult.error && <p className="text-danger">Error: {patchResult.error}</p>}
          <details><summary>Full Details</summary><pre className="code-block">{JSON.stringify(patchResult,null,2)}</pre></details>
        </div>
      )}
    </div>
  );
}

/* ─── Snapshots ─── */
function SnapshotsPage({ hosts }) {
  const [selectedHost, setSelectedHost] = useState('');
  const [snapshots, setSnapshots] = useState([]);
  const [loading, setLoading] = useState(false);
  const [snapName, setSnapName] = useState('');
  const [actionResult, setActionResult] = useState(null);

  const fetchSnapshots = useCallback(async () => {
    if (!selectedHost) return;
    setLoading(true);
    try { const r = await apiFetch(`${API}/api/agent/${selectedHost}/snapshot/list`); const d = await r.json(); setSnapshots(d.snapshots||[]); } catch { setSnapshots([]); }
    setLoading(false);
  }, [selectedHost]);

  useEffect(() => { fetchSnapshots(); }, [fetchSnapshots]);

  const createSnap = async () => {
    setActionResult(null);
    try { const r = await apiFetch(`${API}/api/agent/${selectedHost}/snapshot/create`, { method:'POST', body: JSON.stringify({name:snapName||undefined}) }); const d = await r.json(); setActionResult(d); setSnapName(''); fetchSnapshots(); } catch (e) { setActionResult({error:e.message}); }
  };
  const rollbackSnap = async (name) => {
    if (!window.confirm(`ROLLBACK to snapshot "${name}"?`)) return;
    try { const r = await apiFetch(`${API}/api/agent/${selectedHost}/snapshot/rollback`, { method:'POST', body:JSON.stringify({name}) }); setActionResult(await r.json()); } catch(e) { setActionResult({error:e.message}); }
  };
  const deleteSnap = async (name) => {
    if (!window.confirm(`Delete snapshot "${name}"?`)) return;
    try { await apiFetch(`${API}/api/agent/${selectedHost}/snapshot/delete`, { method:'POST', body:JSON.stringify({name}) }); fetchSnapshots(); } catch {}
  };

  return (
    <div>
      <div className="card highlight-card"><h3>📸 Snapshot Manager</h3><p>Create snapshots before patching. Rollback if something goes wrong.</p></div>
      <div className="card"><h3>Select Host</h3><select className="input" value={selectedHost} onChange={e=>setSelectedHost(e.target.value)}><option value="">-- Select Host --</option>{hosts.map(h=><option key={h.id} value={h.ip}>{h.hostname||h.name} ({h.ip})</option>)}</select></div>
      {selectedHost && <>
        <div className="card"><h3>Create Snapshot</h3><div className="form-row"><input className="input" placeholder="Snapshot name (optional)" value={snapName} onChange={e=>setSnapName(e.target.value)} style={{flex:1}} /><button className="btn btn-success" onClick={createSnap}>📸 Create</button></div></div>
        <div className="card"><div className="card-header"><h3>Snapshots ({snapshots.length})</h3><button className="btn btn-sm" onClick={fetchSnapshots}>{loading?'Loading...':'Refresh'}</button></div>
          {snapshots.length===0?<p className="text-muted">No snapshots found.</p>:(
            <table className="table"><thead><tr><th>Name</th><th>Created</th><th>Packages</th><th>Actions</th></tr></thead>
            <tbody>{snapshots.map((s,i)=><tr key={i}><td><strong>{s.name}</strong></td><td>{s.created||'—'}</td><td>{s.packages_count||'—'}</td><td><button className="btn btn-sm btn-warning" onClick={()=>rollbackSnap(s.name)}>⏪ Rollback</button> <button className="btn btn-sm btn-danger" onClick={()=>deleteSnap(s.name)}>🗑️ Delete</button></td></tr>)}</tbody></table>
          )}
        </div>
      </>}
      {actionResult && <div className={`card ${actionResult.success?'result-success':'result-failure'}`}><h3>{actionResult.success?'✅ Success':'❌ Failed'}</h3><details><summary>Details</summary><pre className="code-block">{JSON.stringify(actionResult,null,2)}</pre></details></div>}
    </div>
  );
}

/* ─── Compare Packages ─── */
function ComparePackagesPage({ hosts }) {
  const [selectedHost, setSelectedHost] = useState('');
  const [installed, setInstalled] = useState([]);
  const [upgradable, setUpgradable] = useState([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [view, setView] = useState('all');

  const fetchData = async () => {
    if (!selectedHost) return alert('Select a host first');
    setLoading(true); setInstalled([]); setUpgradable([]);
    try {
      const [rI, rU] = await Promise.all([apiFetch(`${API}/api/agent/${selectedHost}/packages/installed`), apiFetch(`${API}/api/agent/${selectedHost}/packages/upgradable`)]);
      setInstalled((await rI.json()).packages||[]); setUpgradable((await rU.json()).packages||[]);
    } catch(e) { alert('Could not reach agent: '+e.message); }
    setLoading(false);
  };

  const upgMap = {}; upgradable.forEach(p=>{upgMap[p.name]=p;});
  const merged = installed.map(p=>({name:p.name,installed_version:p.version,available_version:upgMap[p.name]?.available_version||null,has_update:!!upgMap[p.name]}));
  const filtered = merged.filter(p=>{if(view==='upgradable'&&!p.has_update)return false;if(view==='uptodate'&&p.has_update)return false;if(search&&!p.name.toLowerCase().includes(search.toLowerCase()))return false;return true;});

  return (
    <div>
      <div className="card highlight-card"><h3>🔍 Package Comparison</h3><p>Compare installed vs available package versions.</p></div>
      <div className="card"><div className="form-row">
        <select className="input" value={selectedHost} onChange={e=>setSelectedHost(e.target.value)}><option value="">-- Select Host --</option>{hosts.map(h=><option key={h.id} value={h.ip}>{h.hostname||h.name} ({h.ip})</option>)}</select>
        <button className="btn btn-primary" onClick={fetchData} disabled={loading}>{loading?'Scanning...':'🔍 Scan'}</button>
      </div></div>
      {installed.length>0 && <>
        <div className="stats-grid">
          <div className="stat-card" onClick={()=>setView('all')}><div className="stat-icon">📦</div><div className="stat-info"><span className="stat-number">{installed.length}</span><span className="stat-label">Installed</span></div></div>
          <div className="stat-card warning" onClick={()=>setView('upgradable')}><div className="stat-icon">🔄</div><div className="stat-info"><span className="stat-number">{upgradable.length}</span><span className="stat-label">Updates</span></div></div>
          <div className="stat-card success" onClick={()=>setView('uptodate')}><div className="stat-icon">✅</div><div className="stat-info"><span className="stat-number">{installed.length-upgradable.length}</span><span className="stat-label">Up-to-date</span></div></div>
        </div>
        <div className="card"><div className="card-header"><h3>Packages ({filtered.length})</h3><input className="input search-input" placeholder="Search..." value={search} onChange={e=>setSearch(e.target.value)} /></div>
          <div className="package-list"><table className="table"><thead><tr><th>Package</th><th>Installed</th><th>Available</th><th>Status</th></tr></thead>
          <tbody>{filtered.slice(0,200).map((p,i)=><tr key={i} className={p.has_update?'row-update':''}><td><strong>{p.name}</strong></td><td><code>{p.installed_version}</code></td><td>{p.available_version?<code className="text-success-inline">{p.available_version}</code>:<span className="text-muted">—</span>}</td><td>{p.has_update?<span className="badge badge-warning">Update</span>:<span className="badge badge-success">OK</span>}</td></tr>)}</tbody></table>
          {filtered.length>200&&<p className="text-muted">Showing first 200. Use search to filter.</p>}</div>
        </div>
      </>}
    </div>
  );
}

/* ─── Offline Patching ─── */
function OfflinePatchPage({ hosts }) {
  const [selectedHost, setSelectedHost] = useState('');
  const [offlineDebs, setOfflineDebs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [installResult, setInstallResult] = useState(null);
  const [autoSnapshot, setAutoSnapshot] = useState(true);
  const [autoRollback, setAutoRollback] = useState(true);
  const [selectedFiles, setSelectedFiles] = useState([]);

  const fetchDebs = useCallback(async () => {
    if (!selectedHost) return;
    setLoading(true);
    try { const r = await apiFetch(`${API}/api/agent/${selectedHost}/offline/list`); setOfflineDebs((await r.json()).debs||[]); } catch { setOfflineDebs([]); }
    setLoading(false);
  }, [selectedHost]);
  useEffect(()=>{fetchDebs();},[fetchDebs]);

  const installOffline = async () => {
    if (!window.confirm(`Install ${selectedFiles.length||'ALL'} .deb files on ${selectedHost}?`)) return;
    setInstallResult(null); setLoading(true);
    try { const r = await apiFetch(`${API}/api/agent/${selectedHost}/offline/install`, { method:'POST', body:JSON.stringify({files:selectedFiles.length>0?selectedFiles:[],auto_snapshot:autoSnapshot,auto_rollback:autoRollback}) }); setInstallResult(await r.json()); fetchDebs(); } catch(e) { setInstallResult({error:e.message}); }
    setLoading(false);
  };
  const clearDebs = async () => { if(!window.confirm('Remove all .deb files?'))return; await apiFetch(`${API}/api/agent/${selectedHost}/offline/clear`,{method:'POST'}); fetchDebs(); };

  return (
    <div>
      <div className="card highlight-card"><h3>📦 Offline Patching</h3><p>For air-gapped environments. Copy .deb files to agent, then install with snapshot protection.</p></div>
      <div className="card"><h3>Select Host</h3><select className="input" value={selectedHost} onChange={e=>setSelectedHost(e.target.value)}><option value="">-- Select Host --</option>{hosts.map(h=><option key={h.id} value={h.ip}>{h.hostname||h.name} ({h.ip})</option>)}</select></div>
      {selectedHost && <>
        <div className="card"><h3>Upload Instructions</h3><pre className="code-block">{`scp *.deb user@${selectedHost}:/var/lib/patch-agent/offline-debs/`}</pre></div>
        <div className="card"><div className="card-header"><h3>.deb Files ({offlineDebs.length})</h3><div className="btn-group"><button className="btn btn-sm" onClick={fetchDebs}>Refresh</button><button className="btn btn-sm btn-danger" onClick={clearDebs}>Clear All</button></div></div>
          {offlineDebs.length===0?<p className="text-muted">No .deb files found.</p>:(
            <table className="table"><thead><tr><th style={{width:'40px'}}>✓</th><th>Filename</th><th>Size</th></tr></thead>
            <tbody>{offlineDebs.map((d,i)=><tr key={i} className={selectedFiles.includes(d.name)?'row-selected':''}><td><input type="checkbox" checked={selectedFiles.includes(d.name)} onChange={()=>setSelectedFiles(prev=>prev.includes(d.name)?prev.filter(f=>f!==d.name):[...prev,d.name])} /></td><td><strong>{d.name}</strong></td><td>{d.size_mb} MB</td></tr>)}</tbody></table>
          )}
        </div>
        <div className="card"><h3>Options</h3>
          <div className="options-grid">
            <label className="toggle-option"><input type="checkbox" checked={autoSnapshot} onChange={e=>setAutoSnapshot(e.target.checked)} /> 📸 Auto-Snapshot</label>
            <label className="toggle-option"><input type="checkbox" checked={autoRollback} onChange={e=>setAutoRollback(e.target.checked)} /> ⏪ Auto-Rollback</label>
          </div>
          <div style={{marginTop:16}}><button className="btn btn-lg btn-success" onClick={installOffline} disabled={loading||offlineDebs.length===0}>{loading?'⏳ Installing...':`📦 Install ${selectedFiles.length||'All'} .deb(s)`}</button></div>
        </div>
      </>}
      {installResult && <div className={`card ${installResult.success?'result-success':'result-failure'}`}><h3>{installResult.success?'✅ Success':'❌ Failed'}</h3>{installResult.error&&<p className="text-danger">{installResult.error}</p>}<details><summary>Output</summary><pre className="code-block">{installResult.install_output||JSON.stringify(installResult,null,2)}</pre></details></div>}
    </div>
  );
}

/* ─── Schedules ─── */
function SchedulesPage() {
  const [schedules, setSchedules] = useState([]);
  const [groups, setGroups] = useState([]);
  const [form, setForm] = useState({ group_id:'', cron_expression:'0 2 * * SAT', action:'upgrade', auto_snapshot:true, auto_rollback:true, auto_reboot:false });

  const refresh = () => { apiFetch(`${API}/api/schedules/`).then(r=>r.json()).then(setSchedules).catch(()=>{}); };
  useEffect(()=>{ refresh(); apiFetch(`${API}/api/groups/`).then(r=>r.json()).then(setGroups).catch(()=>{}); },[]);

  const create = () => {
    if(!form.group_id) return alert('Select a group');
    apiFetch(`${API}/api/schedules/`, { method:'POST', body:JSON.stringify({...form,group_id:parseInt(form.group_id)}) }).then(()=>{refresh();setForm({group_id:'',cron_expression:'0 2 * * SAT',action:'upgrade',auto_snapshot:true,auto_rollback:true,auto_reboot:false});});
  };
  const del = id => { if(!window.confirm('Delete schedule?'))return; apiFetch(`${API}/api/schedules/${id}`,{method:'DELETE'}).then(refresh); };
  const toggle = async (id, enabled) => { await apiFetch(`${API}/api/schedules/${id}`,{method:'PUT',body:JSON.stringify({is_enabled:!enabled})}); refresh(); };

  return (
    <div>
      <div className="card"><h3>Create Schedule</h3>
        <div className="form-row">
          <select className="input" value={form.group_id} onChange={e=>setForm(f=>({...f,group_id:e.target.value}))}>
            <option value="">-- Select Group --</option>{groups.map(g=><option key={g.id} value={g.id}>{g.name}</option>)}
          </select>
          <input className="input" placeholder="Cron (e.g. 0 2 * * SAT)" value={form.cron_expression} onChange={e=>setForm(f=>({...f,cron_expression:e.target.value}))} />
          <select className="input" value={form.action} onChange={e=>setForm(f=>({...f,action:e.target.value}))}><option value="upgrade">Upgrade</option><option value="server_patch">Server Patch</option></select>
          <button className="btn btn-primary" onClick={create}>Create</button>
        </div>
        <div className="options-grid" style={{marginTop:10}}>
          <label className="toggle-option"><input type="checkbox" checked={form.auto_snapshot} onChange={e=>setForm(f=>({...f,auto_snapshot:e.target.checked}))} /> Auto-Snapshot</label>
          <label className="toggle-option"><input type="checkbox" checked={form.auto_rollback} onChange={e=>setForm(f=>({...f,auto_rollback:e.target.checked}))} /> Auto-Rollback</label>
          <label className="toggle-option"><input type="checkbox" checked={form.auto_reboot} onChange={e=>setForm(f=>({...f,auto_reboot:e.target.checked}))} /> Auto-Reboot</label>
        </div>
      </div>
      <div className="card"><h3>Schedules ({schedules.length})</h3>
        {schedules.length===0?<p className="text-muted">No schedules created.</p>:(
          <table className="table"><thead><tr><th>Group</th><th>Cron</th><th>Action</th><th>Snapshot</th><th>Rollback</th><th>Enabled</th><th>Next Run</th><th>Actions</th></tr></thead>
          <tbody>{schedules.map(s=><tr key={s.id}><td><strong>{s.group_name||s.group_id}</strong></td><td><code>{s.cron_expression}</code></td><td>{s.action}</td><td>{s.auto_snapshot?'✅':'❌'}</td><td>{s.auto_rollback?'✅':'❌'}</td><td><button className={`btn btn-sm ${s.is_enabled?'btn-success':'btn-secondary'}`} onClick={()=>toggle(s.id,s.is_enabled)}>{s.is_enabled?'ON':'OFF'}</button></td><td>{s.next_run||'—'}</td><td><button className="btn btn-sm btn-danger" onClick={()=>del(s.id)}>Del</button></td></tr>)}</tbody></table>
        )}
      </div>
    </div>
  );
}

/* ─── CVE Tracker ─── */
function CVEPage() {
  const [cves, setCves] = useState([]);
  const [stats, setStats] = useState(null);
  const [search, setSearch] = useState('');
  const [severity, setSeverity] = useState('');
  const [form, setForm] = useState({ cve_id:'', description:'', severity:'medium', cvss_score:'', affected_packages:'', advisory_url:'' });

  const refresh = () => {
    const params = new URLSearchParams(); if(severity) params.set('severity',severity); if(search) params.set('search',search);
    apiFetch(`${API}/api/cve/?${params}`).then(r=>r.json()).then(setCves).catch(()=>{});
    apiFetch(`${API}/api/cve/stats`).then(r=>r.json()).then(setStats).catch(()=>{});
  };
  useEffect(refresh, [severity, search]);

  const create = () => {
    if(!form.cve_id) return alert('CVE ID required');
    const body = { ...form, cvss_score: form.cvss_score?parseFloat(form.cvss_score):null, affected_packages: form.affected_packages?form.affected_packages.split(',').map(s=>s.trim()):[] };
    apiFetch(`${API}/api/cve/`, { method:'POST', body:JSON.stringify(body) }).then(()=>{refresh();setForm({cve_id:'',description:'',severity:'medium',cvss_score:'',affected_packages:'',advisory_url:''});}).catch(e=>alert(e.message));
  };
  const del = id => { if(!window.confirm('Delete CVE?'))return; apiFetch(`${API}/api/cve/${id}`,{method:'DELETE'}).then(refresh); };

  return (
    <div>
      {stats && <div className="stats-grid">
        <div className="stat-card"><div className="stat-icon">🔒</div><div className="stat-info"><span className="stat-number">{stats.total_cves}</span><span className="stat-label">Total CVEs</span></div></div>
        <div className="stat-card danger"><div className="stat-icon">🔴</div><div className="stat-info"><span className="stat-number">{stats.by_severity?.critical||0}</span><span className="stat-label">Critical</span></div></div>
        <div className="stat-card warning"><div className="stat-icon">🟡</div><div className="stat-info"><span className="stat-number">{stats.by_severity?.high||0}</span><span className="stat-label">High</span></div></div>
        <div className="stat-card info"><div className="stat-icon">🔵</div><div className="stat-info"><span className="stat-number">{stats.open_vulnerabilities||0}</span><span className="stat-label">Open Vulns</span></div></div>
        <div className="stat-card success"><div className="stat-icon">✅</div><div className="stat-info"><span className="stat-number">{stats.patched_vulnerabilities||0}</span><span className="stat-label">Patched</span></div></div>
      </div>}
      {hasRole('admin','operator') && <div className="card"><h3>Add CVE</h3>
        <div className="form-row">
          <input className="input" placeholder="CVE-2024-XXXX" value={form.cve_id} onChange={e=>setForm(f=>({...f,cve_id:e.target.value}))} />
          <input className="input" placeholder="Description" value={form.description} onChange={e=>setForm(f=>({...f,description:e.target.value}))} style={{flex:1}} />
          <select className="input" value={form.severity} onChange={e=>setForm(f=>({...f,severity:e.target.value}))}><option value="critical">Critical</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select>
          <input className="input" placeholder="CVSS" value={form.cvss_score} onChange={e=>setForm(f=>({...f,cvss_score:e.target.value}))} style={{width:70}} />
          <button className="btn btn-primary" onClick={create}>Add</button>
        </div>
      </div>}
      <div className="card"><div className="card-header"><h3>CVEs ({cves.length})</h3><div className="form-row">
        <select className="input" value={severity} onChange={e=>setSeverity(e.target.value)}><option value="">All Severities</option><option value="critical">Critical</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select>
        <input className="input search-input" placeholder="Search CVEs..." value={search} onChange={e=>setSearch(e.target.value)} />
      </div></div>
        {cves.length===0?<p className="text-muted">No CVEs tracked yet.</p>:(
          <table className="table"><thead><tr><th>CVE ID</th><th>Severity</th><th>CVSS</th><th>Hosts</th><th>Patched</th><th>Description</th><th>Actions</th></tr></thead>
          <tbody>{cves.map(c=><tr key={c.id}><td><strong>{c.cve_id}</strong></td><td><span className={`badge badge-${c.severity==='critical'?'danger':c.severity==='high'?'warning':c.severity==='medium'?'info':'success'}`}>{c.severity}</span></td><td>{c.cvss_score||'—'}</td><td>{c.affected_hosts}</td><td>{c.patched_hosts}</td><td style={{maxWidth:300,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{c.description||'—'}</td><td>{hasRole('admin')&&<button className="btn btn-sm btn-danger" onClick={()=>del(c.id)}>Del</button>}</td></tr>)}</tbody></table>
        )}
      </div>
    </div>
  );
}

/* ─── Jobs ─── */
function JobsPage({ jobs, setJobs }) {
  const [search, setSearch] = useState('');
  const refresh = () => { apiFetch(`${API}/api/jobs/`).then(r=>r.json()).then(setJobs).catch(()=>{}); };
  const deleteJob = id => { if(!window.confirm('Delete job?'))return; apiFetch(`${API}/api/jobs/${id}`,{method:'DELETE'}).then(refresh); };
  const filtered = jobs.filter(j => (j.action||j.name||'').toLowerCase().includes(search.toLowerCase()) || (j.status||'').toLowerCase().includes(search.toLowerCase()));
  return (
    <div>
      <div className="card"><div className="card-header"><h3>Jobs ({filtered.length})</h3><div className="form-row"><input className="input search-input" placeholder="Search..." value={search} onChange={e=>setSearch(e.target.value)} /><button className="btn btn-sm" onClick={refresh}>Refresh</button></div></div>
        {filtered.length===0?<p className="text-muted">No jobs.</p>:<table className="table"><thead><tr><th>ID</th><th>Host</th><th>Action</th><th>Status</th><th>Initiated By</th><th>Created</th><th>Actions</th></tr></thead>
        <tbody>{filtered.map(j=><tr key={j.id}><td>{j.id}</td><td>{j.host_id||'—'}</td><td>{j.action||j.name}</td><td><span className={`badge badge-${j.status==='success'?'success':j.status==='running'?'warning':j.status==='failed'?'danger':'info'}`}>{j.status}</span></td><td>{j.initiated_by||'—'}</td><td>{j.created_at?new Date(j.created_at).toLocaleString():'—'}</td><td>{hasRole('admin','operator')&&<button className="btn btn-sm btn-danger" onClick={()=>deleteJob(j.id)}>Del</button>}</td></tr>)}</tbody></table>}
      </div>
    </div>
  );
}

/* ─── Audit Trail ─── */
function AuditPage() {
  const [logs, setLogs] = useState([]);
  const [stats, setStats] = useState(null);
  const [actionFilter, setActionFilter] = useState('');
  const [days, setDays] = useState(7);

  const refresh = () => {
    const params = new URLSearchParams(); if(actionFilter) params.set('action',actionFilter); params.set('days',days);
    apiFetch(`${API}/api/audit/?${params}`).then(r=>r.json()).then(setLogs).catch(()=>{});
    apiFetch(`${API}/api/audit/stats`).then(r=>r.json()).then(setStats).catch(()=>{});
  };
  useEffect(refresh, [actionFilter, days]);

  return (
    <div>
      {stats && <div className="stats-grid">
        <div className="stat-card"><div className="stat-icon">📋</div><div className="stat-info"><span className="stat-number">{stats.today}</span><span className="stat-label">Today</span></div></div>
        <div className="stat-card info"><div className="stat-icon">📅</div><div className="stat-info"><span className="stat-number">{stats.this_week}</span><span className="stat-label">This Week</span></div></div>
      </div>}
      <div className="card"><div className="card-header"><h3>Audit Logs</h3><div className="form-row">
        <input className="input" placeholder="Filter by action" value={actionFilter} onChange={e=>setActionFilter(e.target.value)} />
        <select className="input" value={days} onChange={e=>setDays(e.target.value)}><option value={1}>Last 1 day</option><option value={7}>Last 7 days</option><option value={30}>Last 30 days</option><option value={90}>Last 90 days</option></select>
      </div></div>
        {logs.length===0?<p className="text-muted">No audit logs found.</p>:(
          <table className="table"><thead><tr><th>Time</th><th>User</th><th>Action</th><th>Resource</th><th>Details</th></tr></thead>
          <tbody>{logs.map(l=><tr key={l.id}><td style={{whiteSpace:'nowrap'}}>{new Date(l.created_at).toLocaleString()}</td><td>{l.username||l.user_id||'system'}</td><td><span className="badge badge-info">{l.action}</span></td><td>{l.resource_type} {l.resource_id?`#${l.resource_id}`:''}</td><td style={{maxWidth:300,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{l.details?JSON.stringify(l.details):''}</td></tr>)}</tbody></table>
        )}
      </div>
    </div>
  );
}

/* ─── Notifications ─── */
function NotificationsPage() {
  const [channels, setChannels] = useState([]);
  const [form, setForm] = useState({ name:'', channel_type:'webhook', config_url:'', events:'job_failed,cve_critical' });

  const refresh = () => { apiFetch(`${API}/api/notifications/channels`).then(r=>r.json()).then(setChannels).catch(()=>{}); };
  useEffect(refresh, []);

  const create = () => {
    if(!form.name) return alert('Name required');
    const config = form.channel_type==='slack'?{webhook_url:form.config_url}:{url:form.config_url};
    const events = form.events.split(',').map(s=>s.trim()).filter(Boolean);
    apiFetch(`${API}/api/notifications/channels`, { method:'POST', body:JSON.stringify({name:form.name,channel_type:form.channel_type,config,events}) }).then(()=>{refresh();setForm({name:'',channel_type:'webhook',config_url:'',events:'job_failed,cve_critical'});});
  };
  const del = id => { if(!window.confirm('Delete channel?'))return; apiFetch(`${API}/api/notifications/channels/${id}`,{method:'DELETE'}).then(refresh); };
  const test = async (id) => { try { await apiFetch(`${API}/api/notifications/test/${id}`,{method:'POST'}); alert('Test sent!'); } catch(e) { alert('Test failed: '+e.message); } };

  return (
    <div>
      {hasRole('admin') && <div className="card"><h3>Add Notification Channel</h3>
        <div className="form-row">
          <input className="input" placeholder="Channel name" value={form.name} onChange={e=>setForm(f=>({...f,name:e.target.value}))} />
          <select className="input" value={form.channel_type} onChange={e=>setForm(f=>({...f,channel_type:e.target.value}))}><option value="webhook">Webhook</option><option value="slack">Slack</option><option value="telegram">Telegram</option><option value="email">Email</option></select>
          <input className="input" placeholder="URL / Webhook URL" value={form.config_url} onChange={e=>setForm(f=>({...f,config_url:e.target.value}))} style={{flex:1}} />
          <button className="btn btn-primary" onClick={create}>Add</button>
        </div>
        <div className="form-row" style={{marginTop:8}}><input className="input" placeholder="Events (comma-separated)" value={form.events} onChange={e=>setForm(f=>({...f,events:e.target.value}))} style={{flex:1}} /><span className="text-muted" style={{fontSize:11}}>e.g. job_failed, cve_critical, patch_complete</span></div>
      </div>}
      <div className="card"><h3>Channels ({channels.length})</h3>
        {channels.length===0?<p className="text-muted">No notification channels configured.</p>:(
          <table className="table"><thead><tr><th>Name</th><th>Type</th><th>Events</th><th>Enabled</th><th>Actions</th></tr></thead>
          <tbody>{channels.map(c=><tr key={c.id}><td><strong>{c.name}</strong></td><td><span className="badge badge-info">{c.channel_type}</span></td><td>{(c.events||[]).join(', ')}</td><td>{c.is_enabled?<span className="badge badge-success">Yes</span>:<span className="badge badge-danger">No</span>}</td><td><button className="btn btn-sm" onClick={()=>test(c.id)}>Test</button> {hasRole('admin')&&<button className="btn btn-sm btn-danger" onClick={()=>del(c.id)}>Del</button>}</td></tr>)}</tbody></table>
        )}
      </div>
    </div>
  );
}

/* ─── User Management (admin) ─── */
function UsersPage() {
  const [users, setUsers] = useState([]);
  const [showCreate, setShowCreate] = useState(false);
  const [newUser, setNewUser] = useState({username:'',email:'',password:'',full_name:'',role:'viewer'});
  const [createMsg, setCreateMsg] = useState('');
  const [resetPw, setResetPw] = useState({userId:null,password:''});
  const [resetMsg, setResetMsg] = useState('');
  const [editPermsUser, setEditPermsUser] = useState(null);
  const [editPerms, setEditPerms] = useState({});
  const [permsMsg, setPermsMsg] = useState('');
  const [roleDefaults, setRoleDefaults] = useState(null);
  const [allFeatures, setAllFeatures] = useState([]);
  const [viewTab, setViewTab] = useState('users');

  const refresh = () => { apiFetch(`${API}/api/auth/users`).then(r=>r.json()).then(setUsers).catch(()=>{}); };
  useEffect(() => {
    refresh();
    apiFetch(`${API}/api/auth/role-defaults`).then(r=>r.json()).then(d => {
      setRoleDefaults(d.role_defaults);
      setAllFeatures(d.features);
    }).catch(()=>{});
  }, []);

  const changeRole = async (id, role) => {
    await apiFetch(`${API}/api/auth/users/${id}`, { method:'PUT', body:JSON.stringify({role}) });
    refresh();
  };
  const toggleActive = async (id, is_active) => {
    await apiFetch(`${API}/api/auth/users/${id}`, { method:'PUT', body:JSON.stringify({is_active: !is_active}) });
    refresh();
  };
  const del = id => { if(!window.confirm('Delete this user? This cannot be undone.'))return; apiFetch(`${API}/api/auth/users/${id}`,{method:'DELETE'}).then(refresh); };

  const createUser = async () => {
    setCreateMsg('');
    if(!newUser.username||!newUser.email||!newUser.password) { setCreateMsg('All fields are required'); return; }
    try {
      const r = await apiFetch(`${API}/api/auth/users`, { method:'POST', body:JSON.stringify(newUser) });
      const d = await r.json();
      if(r.ok) { setCreateMsg('User created successfully!'); setNewUser({username:'',email:'',password:'',full_name:'',role:'viewer'}); setShowCreate(false); refresh(); }
      else { setCreateMsg(d.detail||'Failed to create user'); }
    } catch(e) { setCreateMsg('Error: '+e.message); }
  };

  const adminResetPassword = async () => {
    setResetMsg('');
    if(!resetPw.password) { setResetMsg('Enter a new password'); return; }
    try {
      const r = await apiFetch(`${API}/api/auth/users/${resetPw.userId}/reset-password`, { method:'POST', body:JSON.stringify({new_password:resetPw.password}) });
      const d = await r.json();
      if(r.ok) { setResetMsg('Password reset!'); setResetPw({userId:null,password:''}); }
      else { setResetMsg(d.detail||'Failed'); }
    } catch(e) { setResetMsg('Error: '+e.message); }
  };

  const openPermsEditor = (u) => {
    setEditPermsUser(u);
    setEditPerms(u.effective_permissions || {});
    setPermsMsg('');
  };
  const togglePerm = (feat) => {
    setEditPerms(p => ({...p, [feat]: !p[feat]}));
  };
  const savePerms = async () => {
    setPermsMsg('');
    if(!editPermsUser) return;
    // Only save overrides that differ from role defaults
    const roleDef = roleDefaults ? roleDefaults[editPermsUser.role] : {};
    const overrides = {};
    for(const f of allFeatures) {
      if(editPerms[f] !== roleDef[f]) overrides[f] = editPerms[f];
    }
    try {
      const r = await apiFetch(`${API}/api/auth/users/${editPermsUser.id}/permissions`, { method:'PUT', body:JSON.stringify({permissions: Object.keys(overrides).length ? overrides : null}) });
      if(r.ok) { setPermsMsg('Permissions saved!'); refresh(); }
      else { const d = await r.json(); setPermsMsg(d.detail||'Failed'); }
    } catch(e) { setPermsMsg('Error: '+e.message); }
  };
  const resetPermsToRole = () => {
    if(editPermsUser && roleDefaults) {
      setEditPerms({...roleDefaults[editPermsUser.role]});
    }
  };

  const featureLabels = {
    dashboard:'Dashboard', compliance:'Compliance', hosts:'Hosts', groups:'Groups & Tags',
    patches:'Patch Manager', snapshots:'Snapshots', compare:'Compare Packages', offline:'Offline Patching',
    schedules:'Schedules', cve:'CVE Tracker', jobs:'Job History', audit:'Audit Trail',
    notifications:'Notifications', users:'User Management', license:'License', onboarding:'Onboarding', settings:'Settings'
  };

  return (
    <div>
      {/* Tab navigation */}
      <div style={{display:'flex',gap:4,marginBottom:16}}>
        {[{k:'users',l:'👤 Users'},{k:'permissions',l:'🛡️ RBAC Matrix'},{k:'peruser',l:'⚙️ Per-User Permissions'}].map(t=>(
          <button key={t.k} className={`btn ${viewTab===t.k?'btn-primary':''}`} onClick={()=>setViewTab(t.k)}>{t.l}</button>
        ))}
      </div>

      {/* ── TAB 1: Users List ── */}
      {viewTab === 'users' && (<>
        {/* Create User */}
        <div className="card">
          <div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
            <h3>👤 Users ({users.length})</h3>
            <button className="btn btn-primary" onClick={()=>setShowCreate(!showCreate)}>{showCreate?'Cancel':'+ New User'}</button>
          </div>
          {showCreate && (
            <div style={{marginTop:16,padding:16,background:'rgba(255,255,255,0.05)',borderRadius:8}}>
              <h4 style={{marginBottom:12}}>Create New User</h4>
              <div className="form-row" style={{flexWrap:'wrap',gap:8}}>
                <input className="input" placeholder="Username *" value={newUser.username} onChange={e=>setNewUser(f=>({...f,username:e.target.value}))} style={{minWidth:150}} />
                <input className="input" type="email" placeholder="Email *" value={newUser.email} onChange={e=>setNewUser(f=>({...f,email:e.target.value}))} style={{minWidth:200}} />
                <input className="input" type="password" placeholder="Password * (min 8 chars)" value={newUser.password} onChange={e=>setNewUser(f=>({...f,password:e.target.value}))} style={{minWidth:180}} />
                <input className="input" placeholder="Full Name" value={newUser.full_name} onChange={e=>setNewUser(f=>({...f,full_name:e.target.value}))} style={{minWidth:150}} />
                <select className="input" value={newUser.role} onChange={e=>setNewUser(f=>({...f,role:e.target.value}))}>
                  <option value="admin">Admin</option><option value="operator">Operator</option><option value="viewer">Viewer</option><option value="auditor">Auditor</option>
                </select>
                <button className="btn btn-primary" onClick={createUser}>Create User</button>
              </div>
              {createMsg && <p style={{marginTop:8,fontWeight:500,color:createMsg.includes('success')?'#28a745':'#dc3545'}}>{createMsg}</p>}
            </div>
          )}
        </div>

        {/* Users Table */}
        <div className="card">
          <table className="table">
            <thead><tr><th>Username</th><th>Email</th><th>Full Name</th><th>Role</th><th>Active</th><th>Created</th><th>Actions</th></tr></thead>
            <tbody>{users.map(u=><tr key={u.id}>
              <td><strong>{u.username}</strong></td>
              <td>{u.email||'—'}</td>
              <td>{u.full_name||'—'}</td>
              <td>
                <select className="input input-sm" value={u.role} onChange={e=>changeRole(u.id,e.target.value)} style={{minWidth:100}}>
                  <option value="admin">Admin</option><option value="operator">Operator</option><option value="viewer">Viewer</option><option value="auditor">Auditor</option>
                </select>
              </td>
              <td>
                <button className={`btn btn-sm ${u.is_active?'btn-success':'btn-danger'}`} onClick={()=>toggleActive(u.id,u.is_active)} style={{minWidth:70}}>
                  {u.is_active?'Active':'Disabled'}
                </button>
              </td>
              <td>{u.created_at?new Date(u.created_at).toLocaleDateString():'—'}</td>
              <td style={{display:'flex',gap:4,flexWrap:'wrap'}}>
                <button className="btn btn-sm btn-info" onClick={()=>{openPermsEditor(u);setViewTab('peruser');}}>Perms</button>
                <button className="btn btn-sm btn-warning" onClick={()=>{setResetPw({userId:u.id,password:''});setResetMsg('');}}>Reset PW</button>
                <button className="btn btn-sm btn-danger" onClick={()=>del(u.id)}>Delete</button>
              </td>
            </tr>)}</tbody>
          </table>
        </div>

        {/* Reset Password Panel */}
        {resetPw.userId && (
          <div className="card" style={{border:'2px solid #ffc107'}}>
            <h3>🔑 Reset Password for: {users.find(u=>u.id===resetPw.userId)?.username}</h3>
            <div className="form-row">
              <input className="input" type="password" placeholder="New password (min 8 chars)" value={resetPw.password} onChange={e=>setResetPw(f=>({...f,password:e.target.value}))} />
              <button className="btn btn-warning" onClick={adminResetPassword}>Reset Password</button>
              <button className="btn" onClick={()=>setResetPw({userId:null,password:''})}>Cancel</button>
            </div>
            {resetMsg && <p style={{marginTop:8,fontWeight:500,color:resetMsg.includes('reset')?'#28a745':'#dc3545'}}>{resetMsg}</p>}
          </div>
        )}
      </>)}

      {/* ── TAB 2: RBAC Permissions Matrix ── */}
      {viewTab === 'permissions' && (
        <div className="card">
          <h3>🛡️ Role-Based Access Control (RBAC) Matrix</h3>
          <p style={{color:'#9ca3af',marginBottom:12}}>Shows default permissions for each role. Admin can override per user in the "Per-User Permissions" tab.</p>
          {roleDefaults ? (
            <div style={{overflowX:'auto'}}>
              <table className="table">
                <thead>
                  <tr>
                    <th style={{minWidth:180}}>Feature</th>
                    <th style={{textAlign:'center'}}>Admin</th>
                    <th style={{textAlign:'center'}}>Operator</th>
                    <th style={{textAlign:'center'}}>Viewer</th>
                    <th style={{textAlign:'center'}}>Auditor</th>
                  </tr>
                </thead>
                <tbody>
                  {allFeatures.map(f => (
                    <tr key={f}>
                      <td><strong>{featureLabels[f]||f}</strong></td>
                      {['admin','operator','viewer','auditor'].map(role => (
                        <td key={role} style={{textAlign:'center'}}>
                          {roleDefaults[role]?.[f] ? <span style={{color:'#28a745',fontSize:18}}>✅</span> : <span style={{color:'#6c757d',fontSize:14}}>—</span>}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : <p>Loading...</p>}

          {/* Per-user effective permissions */}
          <h3 style={{marginTop:24}}>👥 All Users — Effective Permissions</h3>
          <p style={{color:'#9ca3af',marginBottom:12}}>Shows actual permissions per user (role defaults + custom overrides). Custom overrides shown in <span style={{color:'#f39c12',fontWeight:600}}>orange</span>.</p>
          {users.length > 0 && allFeatures.length > 0 && (
            <div style={{overflowX:'auto'}}>
              <table className="table">
                <thead>
                  <tr>
                    <th style={{minWidth:120}}>Feature</th>
                    {users.map(u => <th key={u.id} style={{textAlign:'center',minWidth:80}}><div>{u.username}</div><div style={{fontSize:10,color:'#9ca3af'}}>({u.role})</div></th>)}
                  </tr>
                </thead>
                <tbody>
                  {allFeatures.map(f => (
                    <tr key={f}>
                      <td><strong>{featureLabels[f]||f}</strong></td>
                      {users.map(u => {
                        const ep = u.effective_permissions || {};
                        const hasCustom = u.custom_permissions && u.custom_permissions[f] !== undefined;
                        return (
                          <td key={u.id} style={{textAlign:'center', background: hasCustom ? 'rgba(243,156,18,0.1)' : 'transparent'}}>
                            {ep[f] ? <span style={{color: hasCustom ? '#f39c12' : '#28a745',fontSize:16}}>✅</span> : <span style={{color:'#6c757d',fontSize:14}}>—</span>}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ── TAB 3: Per-User Permissions Editor ── */}
      {viewTab === 'peruser' && (
        <div>
          {!editPermsUser ? (
            <div className="card">
              <h3>⚙️ Per-User Permissions</h3>
              <p style={{color:'#9ca3af'}}>Select a user to customize their feature access beyond their role defaults.</p>
              <div style={{display:'flex',flexWrap:'wrap',gap:8,marginTop:12}}>
                {users.map(u => (
                  <button key={u.id} className="btn" onClick={()=>openPermsEditor(u)} style={{minWidth:120}}>
                    <strong>{u.username}</strong><br/><span style={{fontSize:11,color:'#9ca3af'}}>{u.role}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="card" style={{border:'2px solid #3b82f6'}}>
              <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',flexWrap:'wrap',gap:8}}>
                <h3>⚙️ Permissions for: {editPermsUser.username} <span className="badge badge-info">{editPermsUser.role}</span></h3>
                <div style={{display:'flex',gap:8}}>
                  <button className="btn" onClick={resetPermsToRole}>Reset to Role Defaults</button>
                  <button className="btn btn-primary" onClick={savePerms}>Save Permissions</button>
                  <button className="btn" onClick={()=>{setEditPermsUser(null);setPermsMsg('');}}>Close</button>
                </div>
              </div>
              {permsMsg && <p style={{marginTop:8,fontWeight:500,color:permsMsg.includes('saved')?'#28a745':'#dc3545'}}>{permsMsg}</p>}
              <p style={{color:'#9ca3af',margin:'8px 0'}}>Toggle features ON/OFF for this user. Changes override their role defaults.</p>
              <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(200px,1fr))',gap:8,marginTop:12}}>
                {allFeatures.map(f => {
                  const isOn = !!editPerms[f];
                  const roleDef = roleDefaults ? !!roleDefaults[editPermsUser.role]?.[f] : false;
                  const isOverride = isOn !== roleDef;
                  return (
                    <div key={f} onClick={()=>togglePerm(f)} style={{
                      padding:'10px 14px', borderRadius:8, cursor:'pointer', display:'flex', alignItems:'center', gap:10,
                      background: isOn ? 'rgba(40,167,69,0.15)' : 'rgba(108,117,125,0.1)',
                      border: isOverride ? '2px solid #f39c12' : '2px solid transparent',
                    }}>
                      <span style={{fontSize:20}}>{isOn ? '✅' : '❌'}</span>
                      <div>
                        <div style={{fontWeight:600}}>{featureLabels[f]||f}</div>
                        {isOverride && <div style={{fontSize:10,color:'#f39c12'}}>Custom override</div>}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ─── CI/CD Pipelines ─── */
function CICDPage() {
  const [tab, setTab] = useState('pipelines');
  const [pipelines, setPipelines] = useState([]);
  const [builds, setBuilds] = useState([]);
  const [templates, setTemplates] = useState({});
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editPipeline, setEditPipeline] = useState(null);
  const [selectedPipeline, setSelectedPipeline] = useState(null);
  const [scriptView, setScriptView] = useState(null);
  const [form, setForm] = useState({ name:'', description:'', tool:'jenkins', server_url:'', auth_type:'token', auth_user:'', auth_token:'', job_path:'', script_type:'groovy', script_content:'', trigger_events:[] });
  const [msg, setMsg] = useState('');
  const [triggerParams, setTriggerParams] = useState('');

  /* ── Git Repos state ── */
  const [gitRepos, setGitRepos] = useState([]);
  const [gitLoading, setGitLoading] = useState(false);
  const [showRepoForm, setShowRepoForm] = useState(false);
  const [repoForm, setRepoForm] = useState({ name:'', provider:'github', server_url:'', repo_full_name:'', default_branch:'main', auth_token:'' });
  const [selectedRepo, setSelectedRepo] = useState(null);
  const [repoBranches, setRepoBranches] = useState([]);
  const [repoCommits, setRepoCommits] = useState([]);
  const [repoPulls, setRepoPulls] = useState([]);
  const [repoTags, setRepoTags] = useState([]);
  const [repoTree, setRepoTree] = useState([]);
  const [repoFile, setRepoFile] = useState(null);
  const [repoSubTab, setRepoSubTab] = useState('info');
  const [treePath, setTreePath] = useState('');
  const [discoverResults, setDiscoverResults] = useState(null);
  const [discoverLoading, setDiscoverLoading] = useState(false);

  const fetchPipelines = useCallback(() => {
    setLoading(true);
    apiFetch(`${API}/api/cicd/pipelines`).then(r=>r.json()).then(d=>{setPipelines(d);setLoading(false);}).catch(()=>setLoading(false));
  }, []);

  const fetchBuilds = useCallback((pipelineId) => {
    const url = pipelineId ? `${API}/api/cicd/builds?pipeline_id=${pipelineId}` : `${API}/api/cicd/builds`;
    apiFetch(url).then(r=>r.json()).then(setBuilds).catch(()=>{});
  }, []);

  const fetchTemplates = useCallback(() => {
    apiFetch(`${API}/api/cicd/templates`).then(r=>r.json()).then(setTemplates).catch(()=>{});
  }, []);

  useEffect(() => { fetchPipelines(); fetchBuilds(); fetchTemplates(); fetchGitRepos(); }, [fetchPipelines, fetchBuilds, fetchTemplates]);

  /* ── Git Repos functions ── */
  const fetchGitRepos = useCallback(() => {
    setGitLoading(true);
    apiFetch(`${API}/api/git/repos`).then(r=>r.json()).then(d=>{setGitRepos(d);setGitLoading(false);}).catch(()=>setGitLoading(false));
  }, []);

  const saveRepo = async () => {
    setMsg('');
    try {
      const r = await apiFetch(`${API}/api/git/repos`, { method:'POST', body: JSON.stringify(repoForm) });
      if (!r.ok) { const d = await r.json(); setMsg(d.detail || 'Save failed'); return; }
      setMsg('Repository connected!'); setShowRepoForm(false);
      setRepoForm({ name:'', provider:'github', server_url:'', repo_full_name:'', default_branch:'main', auth_token:'' });
      fetchGitRepos();
    } catch { setMsg('Error saving repository'); }
  };

  const deleteRepo = async (id) => { if (!window.confirm('Remove this repository?')) return; await apiFetch(`${API}/api/git/repos/${id}`, { method:'DELETE' }); fetchGitRepos(); setSelectedRepo(null); };

  const testRepoConn = async (id) => { setMsg('Testing...'); const r = await apiFetch(`${API}/api/git/repos/${id}/test`, { method:'POST' }); const d = await r.json(); setMsg(d.ok ? `✅ ${d.message}` : `❌ ${d.message}`); if (d.ok) fetchGitRepos(); };

  const syncRepo = async (id) => { setMsg('Syncing...'); const r = await apiFetch(`${API}/api/git/repos/${id}/sync`, { method:'POST' }); const d = await r.json(); setMsg(d.ok ? '✅ Synced!' : `❌ ${d.message||'Sync failed'}`); fetchGitRepos(); };

  const registerWebhook = async (id) => { setMsg('Registering webhook...'); const r = await apiFetch(`${API}/api/git/repos/${id}/webhook/register`, { method:'POST' }); const d = await r.json(); setMsg(d.ok ? `✅ ${d.message}` : `❌ ${d.message}`); fetchGitRepos(); };

  const removeWebhook = async (id) => { const r = await apiFetch(`${API}/api/git/repos/${id}/webhook`, { method:'DELETE' }); const d = await r.json(); setMsg(d.ok ? '✅ Webhook removed' : `❌ ${d.message}`); fetchGitRepos(); };

  const loadRepoBranches = async (id) => { apiFetch(`${API}/api/git/repos/${id}/branches`).then(r=>r.json()).then(setRepoBranches).catch(()=>setRepoBranches([])); };
  const loadRepoCommits = async (id, branch) => { const q = branch ? `?branch=${branch}` : ''; apiFetch(`${API}/api/git/repos/${id}/commits${q}`).then(r=>r.json()).then(setRepoCommits).catch(()=>setRepoCommits([])); };
  const loadRepoPulls = async (id) => { apiFetch(`${API}/api/git/repos/${id}/pulls`).then(r=>r.json()).then(setRepoPulls).catch(()=>setRepoPulls([])); };
  const loadRepoTags = async (id) => { apiFetch(`${API}/api/git/repos/${id}/tags`).then(r=>r.json()).then(setRepoTags).catch(()=>setRepoTags([])); };
  const loadRepoTree = async (id, path) => { const q = path ? `?path=${encodeURIComponent(path)}` : ''; apiFetch(`${API}/api/git/repos/${id}/tree${q}`).then(r=>r.json()).then(setRepoTree).catch(()=>setRepoTree([])); };
  const loadRepoFile = async (id, path) => { apiFetch(`${API}/api/git/repos/${id}/file?path=${encodeURIComponent(path)}`).then(r=>r.json()).then(setRepoFile).catch(()=>setRepoFile(null)); };

  const openRepoDetail = (repo) => {
    setSelectedRepo(repo); setRepoSubTab('info');
    setRepoBranches([]); setRepoCommits([]); setRepoPulls([]); setRepoTags([]); setRepoTree([]); setRepoFile(null); setTreePath('');
    loadRepoBranches(repo.id); loadRepoCommits(repo.id); loadRepoPulls(repo.id);
  };

  const discoverRepos = async () => {
    setDiscoverLoading(true); setDiscoverResults(null);
    const q = `?provider=${repoForm.provider}&token=${encodeURIComponent(repoForm.auth_token)}${repoForm.server_url ? '&server_url=' + encodeURIComponent(repoForm.server_url) : ''}`;
    const r = await apiFetch(`${API}/api/git/discover${q}`); const d = await r.json();
    setDiscoverResults(d); setDiscoverLoading(false);
  };

  const resetForm = () => setForm({ name:'', description:'', tool:'jenkins', server_url:'', auth_type:'token', auth_user:'', auth_token:'', job_path:'', script_type:'groovy', script_content:'', trigger_events:[] });

  const savePipeline = async () => {
    setMsg('');
    const payload = {
      name: form.name, description: form.description, tool: form.tool,
      server_url: form.server_url, auth_type: form.auth_type,
      auth_credentials: form.auth_type !== 'none' ? { user: form.auth_user, token: form.auth_token } : {},
      job_path: form.job_path, script_type: form.script_type,
      script_content: form.script_content, trigger_events: form.trigger_events,
    };
    try {
      const url = editPipeline ? `${API}/api/cicd/pipelines/${editPipeline.id}` : `${API}/api/cicd/pipelines`;
      const method = editPipeline ? 'PUT' : 'POST';
      const r = await apiFetch(url, { method, body: JSON.stringify(payload) });
      if (!r.ok) { const d = await r.json(); setMsg(d.detail || 'Save failed'); return; }
      setMsg('Pipeline saved!');
      setShowForm(false); setEditPipeline(null); resetForm(); fetchPipelines();
    } catch { setMsg('Error saving pipeline'); }
  };

  const deletePipeline = async (id) => {
    if (!window.confirm('Delete this pipeline and all its builds?')) return;
    await apiFetch(`${API}/api/cicd/pipelines/${id}`, { method:'DELETE' });
    fetchPipelines(); fetchBuilds();
  };

  const triggerBuild = async (id) => {
    setMsg('');
    let params = {};
    if (triggerParams.trim()) { try { params = JSON.parse(triggerParams); } catch { setMsg('Invalid JSON parameters'); return; } }
    const r = await apiFetch(`${API}/api/cicd/pipelines/${id}/trigger`, { method:'POST', body: JSON.stringify({ parameters: params }) });
    const d = await r.json();
    if (r.ok) { setMsg(`Build triggered — status: ${d.status}`); fetchBuilds(selectedPipeline); fetchPipelines(); }
    else { setMsg(d.detail || 'Trigger failed'); }
  };

  const testConnection = async (id) => {
    setMsg('Testing...');
    const r = await apiFetch(`${API}/api/cicd/pipelines/${id}/test`, { method:'POST' });
    const d = await r.json();
    setMsg(d.ok ? `✅ ${d.message}` : `❌ ${d.message}`);
  };

  const toggleStatus = async (p) => {
    const newStatus = p.status === 'active' ? 'paused' : 'active';
    await apiFetch(`${API}/api/cicd/pipelines/${p.id}`, { method:'PUT', body: JSON.stringify({ status: newStatus }) });
    fetchPipelines();
  };

  const startEdit = (p) => {
    const creds = p.auth_credentials || {};
    setForm({
      name: p.name, description: p.description, tool: p.tool,
      server_url: p.server_url, auth_type: p.auth_type,
      auth_user: creds.user || '', auth_token: creds.token || creds.password || '',
      job_path: p.job_path, script_type: p.script_type,
      script_content: p.script_content, trigger_events: p.trigger_events || [],
    });
    setEditPipeline(p); setShowForm(true);
  };

  const loadTemplate = (type) => {
    if (templates[type]) {
      setForm(f => ({ ...f, script_type: type, script_content: templates[type].content }));
    }
  };

  const statusBadge = (s) => {
    const map = { success:'badge-success', failed:'badge-danger', running:'badge-info', pending:'badge-warning', aborted:'badge-secondary', active:'badge-success', paused:'badge-warning', disabled:'badge-danger' };
    return <span className={`badge ${map[s]||'badge-secondary'}`}>{s}</span>;
  };

  const triggerEvents = ['patch.success','patch.failed','cve.critical','snapshot.created','schedule.executed','compliance.changed'];

  return (
    <div>
      {/* Tab nav */}
      <div style={{display:'flex',gap:8,marginBottom:16,flexWrap:'wrap'}}>
        {[{k:'pipelines',l:'🚀 Pipelines'},{k:'repositories',l:'📦 Repositories'},{k:'builds',l:'📋 Builds'},{k:'scripts',l:'📜 Templates'}].map(t => (
          <button key={t.k} className={`btn ${tab===t.k?'btn-primary':'btn-secondary'}`} onClick={()=>{setTab(t.k);if(t.k==='builds')fetchBuilds(selectedPipeline);if(t.k==='repositories')fetchGitRepos();}}>{t.l}</button>
        ))}
      </div>
      {msg && <div style={{padding:'8px 16px',borderRadius:8,background:msg.includes('✅')||msg.includes('saved')||msg.includes('triggered')?'rgba(40,167,69,0.15)':'rgba(220,53,69,0.15)',marginBottom:12,fontWeight:500}}>{msg}</div>}

      {/* ── Pipelines Tab ── */}
      {tab === 'pipelines' && (
        <div>
          <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:16}}>
            <h3 style={{margin:0}}>🚀 CI/CD Pipelines</h3>
            {hasRole('admin','operator') && <button className="btn btn-primary" onClick={()=>{resetForm();setEditPipeline(null);setShowForm(!showForm);}}>
              {showForm ? 'Cancel' : '+ New Pipeline'}
            </button>}
          </div>

          {/* Create/Edit form */}
          {showForm && (
            <div className="card" style={{marginBottom:16,border:'2px solid #3b82f6'}}>
              <h4 style={{marginTop:0}}>{editPipeline ? 'Edit Pipeline' : 'Create Pipeline'}</h4>
              <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:12}}>
                <div>
                  <label style={{fontSize:12,fontWeight:600}}>Pipeline Name *</label>
                  <input className="input" placeholder="e.g. Production Patch Pipeline" value={form.name} onChange={e=>setForm(f=>({...f,name:e.target.value}))} />
                </div>
                <div>
                  <label style={{fontSize:12,fontWeight:600}}>CI/CD Tool *</label>
                  <select className="input" value={form.tool} onChange={e=>setForm(f=>({...f,tool:e.target.value}))}>
                    <option value="jenkins">Jenkins</option>
                    <option value="gitlab">GitLab CI</option>
                    <option value="github">GitHub Actions</option>
                    <option value="custom">Custom Webhook</option>
                  </select>
                </div>
                <div style={{gridColumn:'1/-1'}}>
                  <label style={{fontSize:12,fontWeight:600}}>Description</label>
                  <input className="input" placeholder="Pipeline description" value={form.description} onChange={e=>setForm(f=>({...f,description:e.target.value}))} />
                </div>
                <div>
                  <label style={{fontSize:12,fontWeight:600}}>{form.tool === 'jenkins' ? 'Jenkins Server URL *' : 'Server / Webhook URL *'}</label>
                  <input className="input" placeholder={form.tool==='jenkins'?'http://jenkins.example.com:8080':'https://...'} value={form.server_url} onChange={e=>setForm(f=>({...f,server_url:e.target.value}))} />
                </div>
                <div>
                  <label style={{fontSize:12,fontWeight:600}}>{form.tool === 'jenkins' ? 'Job Path *' : 'Project / Repo Path'}</label>
                  <input className="input" placeholder={form.tool==='jenkins'?'my-folder/my-job':'owner/repo'} value={form.job_path} onChange={e=>setForm(f=>({...f,job_path:e.target.value}))} />
                </div>
                <div>
                  <label style={{fontSize:12,fontWeight:600}}>Auth Type</label>
                  <select className="input" value={form.auth_type} onChange={e=>setForm(f=>({...f,auth_type:e.target.value}))}>
                    <option value="token">API Token</option>
                    <option value="basic">Basic Auth</option>
                    <option value="none">None</option>
                  </select>
                </div>
                {form.auth_type !== 'none' && (<>
                  <div>
                    <label style={{fontSize:12,fontWeight:600}}>Username</label>
                    <input className="input" placeholder="Username" value={form.auth_user} onChange={e=>setForm(f=>({...f,auth_user:e.target.value}))} />
                  </div>
                  <div>
                    <label style={{fontSize:12,fontWeight:600}}>{form.auth_type==='token'?'API Token':'Password'}</label>
                    <input className="input" type="password" placeholder="Token / Password" value={form.auth_token} onChange={e=>setForm(f=>({...f,auth_token:e.target.value}))} />
                  </div>
                </>)}
              </div>

              {/* Script editor */}
              <div style={{marginTop:16}}>
                <div style={{display:'flex',alignItems:'center',gap:12,marginBottom:8}}>
                  <label style={{fontSize:12,fontWeight:600,margin:0}}>Pipeline Script</label>
                  <select className="input" value={form.script_type} onChange={e=>setForm(f=>({...f,script_type:e.target.value}))} style={{width:140}}>
                    <option value="groovy">Groovy (Jenkinsfile)</option>
                    <option value="yaml">YAML</option>
                    <option value="shell">Shell</option>
                  </select>
                  <button className="btn btn-sm btn-secondary" onClick={()=>loadTemplate(form.script_type)}>Load Template</button>
                </div>
                <textarea className="input" style={{width:'100%',minHeight:220,fontFamily:'monospace',fontSize:12,whiteSpace:'pre',overflowWrap:'normal',overflowX:'auto'}}
                  value={form.script_content} onChange={e=>setForm(f=>({...f,script_content:e.target.value}))}
                  placeholder={`Paste your ${form.script_type} pipeline script here...`} />
              </div>

              {/* Trigger events */}
              <div style={{marginTop:12}}>
                <label style={{fontSize:12,fontWeight:600}}>Auto-Trigger on Events</label>
                <div style={{display:'flex',flexWrap:'wrap',gap:8,marginTop:4}}>
                  {triggerEvents.map(ev => (
                    <label key={ev} style={{display:'flex',alignItems:'center',gap:4,fontSize:12,cursor:'pointer'}}>
                      <input type="checkbox" checked={form.trigger_events.includes(ev)}
                        onChange={e => setForm(f => ({...f, trigger_events: e.target.checked ? [...f.trigger_events, ev] : f.trigger_events.filter(x=>x!==ev)}))} />
                      {ev}
                    </label>
                  ))}
                </div>
              </div>

              <div style={{marginTop:16,display:'flex',gap:8}}>
                <button className="btn btn-primary" onClick={savePipeline}>💾 Save Pipeline</button>
                <button className="btn btn-secondary" onClick={()=>{setShowForm(false);setEditPipeline(null);resetForm();}}>Cancel</button>
              </div>
            </div>
          )}

          {/* Pipeline list */}
          {loading ? <p>Loading...</p> : pipelines.length === 0 ? (
            <div className="card" style={{textAlign:'center',padding:40,color:'#9ca3af'}}>
              <p style={{fontSize:40,margin:0}}>🚀</p>
              <p style={{fontWeight:600}}>No CI/CD Pipelines configured yet</p>
              <p>Create a pipeline to integrate with Jenkins, GitLab CI, or GitHub Actions</p>
            </div>
          ) : (
            <div style={{display:'grid',gap:12}}>
              {pipelines.map(p => (
                <div key={p.id} className="card" style={{border: p.status==='active' ? '1px solid rgba(40,167,69,0.3)' : '1px solid rgba(108,117,125,0.3)'}}>
                  <div style={{display:'flex',justifyContent:'space-between',alignItems:'flex-start'}}>
                    <div>
                      <div style={{display:'flex',alignItems:'center',gap:10}}>
                        <span style={{fontSize:22}}>{p.tool==='jenkins'?'🔧':p.tool==='gitlab'?'🦊':p.tool==='github'?'🐙':'🔗'}</span>
                        <div>
                          <h4 style={{margin:0}}>{p.name}</h4>
                          <span style={{fontSize:12,color:'#9ca3af'}}>{p.tool.charAt(0).toUpperCase()+p.tool.slice(1)} • {p.server_url} • {p.job_path || 'No job path'}</span>
                        </div>
                      </div>
                      {p.description && <p style={{margin:'6px 0 0',fontSize:13,color:'#9ca3af'}}>{p.description}</p>}
                    </div>
                    <div style={{display:'flex',gap:6,alignItems:'center'}}>
                      {statusBadge(p.status)}
                      <span className="badge badge-info" style={{fontSize:10}}>{p.build_count} builds</span>
                      {p.last_build_status && statusBadge(p.last_build_status)}
                    </div>
                  </div>

                  {/* Webhook URL */}
                  <div style={{marginTop:10,padding:8,borderRadius:6,background:'rgba(59,130,246,0.08)',fontSize:12}}>
                    <strong>Webhook URL:</strong> <code style={{wordBreak:'break-all'}}>{p.webhook_url}</code>
                    <br/><strong>Secret:</strong> <code>{p.webhook_secret}</code>
                  </div>

                  {/* Trigger events */}
                  {p.trigger_events && p.trigger_events.length > 0 && (
                    <div style={{marginTop:8,fontSize:12}}>
                      <strong>Auto-triggers:</strong> {p.trigger_events.map(e=><span key={e} className="badge badge-info" style={{fontSize:10,marginLeft:4}}>{e}</span>)}
                    </div>
                  )}

                  {/* Actions */}
                  <div style={{marginTop:12,display:'flex',gap:6,flexWrap:'wrap'}}>
                    {hasRole('admin','operator') && p.status === 'active' && (
                      <button className="btn btn-sm btn-primary" onClick={()=>triggerBuild(p.id)}>▶ Trigger Build</button>
                    )}
                    <button className="btn btn-sm btn-secondary" onClick={()=>testConnection(p.id)}>🔌 Test Connection</button>
                    <button className="btn btn-sm btn-secondary" onClick={()=>{setSelectedPipeline(p.id);setTab('builds');fetchBuilds(p.id);}}>📋 Builds</button>
                    <button className="btn btn-sm btn-secondary" onClick={()=>setScriptView(scriptView===p.id?null:p.id)}>📜 {scriptView===p.id?'Hide':'View'} Script</button>
                    {hasRole('admin','operator') && <button className="btn btn-sm btn-warning" onClick={()=>startEdit(p)}>✏️ Edit</button>}
                    {hasRole('admin','operator') && <button className="btn btn-sm btn-secondary" onClick={()=>toggleStatus(p)}>{p.status==='active'?'⏸ Pause':'▶ Resume'}</button>}
                    {hasRole('admin') && <button className="btn btn-sm btn-danger" onClick={()=>deletePipeline(p.id)}>🗑 Delete</button>}
                  </div>

                  {/* Trigger parameters (inline) */}
                  {hasRole('admin','operator') && p.status === 'active' && (
                    <div style={{marginTop:8}}>
                      <input className="input" style={{fontSize:12,width:300}} placeholder='Trigger params JSON e.g. {"branch":"main"}' value={triggerParams} onChange={e=>setTriggerParams(e.target.value)} />
                    </div>
                  )}

                  {/* Script viewer */}
                  {scriptView === p.id && (
                    <div style={{marginTop:10}}>
                      <div style={{display:'flex',alignItems:'center',gap:8,marginBottom:4}}>
                        <span className="badge badge-info">{p.script_type}</span>
                        <span style={{fontSize:12,color:'#9ca3af'}}>Pipeline Script</span>
                      </div>
                      <pre className="code-block" style={{maxHeight:400,overflow:'auto',fontSize:11}}>{p.script_content || '(no script)'}</pre>
                    </div>
                  )}

                  {p.last_triggered && <div style={{marginTop:8,fontSize:11,color:'#9ca3af'}}>Last triggered: {new Date(p.last_triggered).toLocaleString()}</div>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Builds Tab ── */}
      {tab === 'builds' && (
        <div>
          <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:16}}>
            <h3 style={{margin:0}}>📋 Build History</h3>
            <div style={{display:'flex',gap:8,alignItems:'center'}}>
              <select className="input" style={{width:200}} value={selectedPipeline||''} onChange={e=>{const v=e.target.value?parseInt(e.target.value):null;setSelectedPipeline(v);fetchBuilds(v);}}>
                <option value="">All Pipelines</option>
                {pipelines.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
              <button className="btn btn-sm" onClick={()=>fetchBuilds(selectedPipeline)}>Refresh</button>
            </div>
          </div>
          {builds.length === 0 ? (
            <div className="card" style={{textAlign:'center',padding:30,color:'#9ca3af'}}>
              <p>No builds yet. Trigger a pipeline or wait for webhook callbacks.</p>
            </div>
          ) : (
            <table className="table">
              <thead><tr><th>#</th><th>Pipeline</th><th>Status</th><th>Trigger</th><th>Duration</th><th>Started</th><th>Actions</th></tr></thead>
              <tbody>
                {builds.map(b => (
                  <tr key={b.id}>
                    <td><strong>#{b.build_number}</strong></td>
                    <td>{b.pipeline_name}</td>
                    <td>{statusBadge(b.status)}</td>
                    <td><span className="badge badge-secondary" style={{fontSize:10}}>{b.trigger_type}</span></td>
                    <td>{b.duration_seconds ? `${b.duration_seconds}s` : '—'}</td>
                    <td style={{fontSize:12}}>{b.started_at ? new Date(b.started_at).toLocaleString() : '—'}</td>
                    <td style={{display:'flex',gap:4}}>
                      {b.external_url && <a href={b.external_url} target="_blank" rel="noopener noreferrer" className="btn btn-sm btn-info">Open ↗</a>}
                      {b.output && <button className="btn btn-sm btn-secondary" title={b.output} onClick={()=>alert(b.output)}>📄 Log</button>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* ── Repositories Tab ── */}
      {tab === 'repositories' && (
        <div>
          {!selectedRepo ? (
            <div>
              <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:16}}>
                <h3>📦 Git Repositories</h3>
                <button className="btn btn-primary" onClick={()=>setShowRepoForm(!showRepoForm)}>{showRepoForm ? '✕ Cancel' : '+ Connect Repository'}</button>
              </div>

              {showRepoForm && (
                <div className="card" style={{marginBottom:20,padding:20}}>
                  <h4 style={{marginBottom:12}}>Connect New Repository</h4>
                  <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:12}}>
                    <div>
                      <label>Name</label>
                      <input className="form-control" value={repoForm.name} onChange={e=>setRepoForm({...repoForm, name:e.target.value})} placeholder="My Project" />
                    </div>
                    <div>
                      <label>Provider</label>
                      <select className="form-control" value={repoForm.provider} onChange={e=>setRepoForm({...repoForm, provider:e.target.value})}>
                        <option value="github">GitHub</option>
                        <option value="gitlab">GitLab</option>
                        <option value="bitbucket">Bitbucket</option>
                        <option value="gitbucket">GitBucket (Self-hosted)</option>
                      </select>
                    </div>
                    {(repoForm.provider === 'gitlab' || repoForm.provider === 'gitbucket') && (
                      <div style={{gridColumn:'1/3'}}>
                        <label>Server URL</label>
                        <input className="form-control" value={repoForm.server_url} onChange={e=>setRepoForm({...repoForm, server_url:e.target.value})} placeholder={repoForm.provider === 'gitbucket' ? 'http://your-server:8080' : 'https://gitlab.example.com'} />
                      </div>
                    )}
                    <div>
                      <label>Repository Full Name</label>
                      <input className="form-control" value={repoForm.repo_full_name} onChange={e=>setRepoForm({...repoForm, repo_full_name:e.target.value})} placeholder="owner/repo-name" />
                    </div>
                    <div>
                      <label>Default Branch</label>
                      <input className="form-control" value={repoForm.default_branch} onChange={e=>setRepoForm({...repoForm, default_branch:e.target.value})} placeholder="main" />
                    </div>
                    <div style={{gridColumn:'1/3'}}>
                      <label>Access Token</label>
                      <input className="form-control" type="password" value={repoForm.auth_token} onChange={e=>setRepoForm({...repoForm, auth_token:e.target.value})} placeholder="Personal access token / App password" />
                    </div>
                  </div>
                  <div style={{marginTop:12,display:'flex',gap:8}}>
                    <button className="btn btn-primary" onClick={saveRepo}>💾 Save & Connect</button>
                    {repoForm.auth_token && <button className="btn btn-info" onClick={discoverRepos} disabled={discoverLoading}>{discoverLoading ? '⏳ Discovering...' : '🔍 Discover Repos'}</button>}
                  </div>

                  {discoverResults && (
                    <div style={{marginTop:16}}>
                      <h5>Discovered Repositories ({discoverResults.length})</h5>
                      <div style={{maxHeight:250,overflowY:'auto',border:'1px solid #374151',borderRadius:8,padding:8}}>
                        {discoverResults.map((dr,i) => (
                          <div key={i} style={{display:'flex',justifyContent:'space-between',alignItems:'center',padding:'6px 8px',borderBottom:'1px solid #1f2937'}}>
                            <div>
                              <strong>{dr.full_name}</strong>
                              <span style={{marginLeft:8,fontSize:12,color:'#9ca3af'}}>{dr.description ? dr.description.substring(0,60) : ''}</span>
                              {dr.private && <span style={{marginLeft:6,background:'#f59e0b',color:'#000',padding:'1px 6px',borderRadius:10,fontSize:11}}>Private</span>}
                            </div>
                            <button className="btn btn-sm btn-success" onClick={()=>{setRepoForm({...repoForm, name:dr.full_name.split('/')[1]||dr.full_name, repo_full_name:dr.full_name, default_branch:dr.default_branch||'main'})}}>Quick Fill</button>
                          </div>
                        ))}
                        {discoverResults.length === 0 && <p style={{color:'#9ca3af',textAlign:'center',padding:16}}>No repositories found. Check your token permissions.</p>}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {gitLoading ? <p>Loading repositories...</p> : gitRepos.length === 0 ? (
                <div className="card" style={{textAlign:'center',padding:40}}>
                  <p style={{fontSize:48,marginBottom:8}}>📦</p>
                  <p style={{color:'#9ca3af'}}>No repositories connected yet. Click "Connect Repository" to get started.</p>
                </div>
              ) : (
                <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(340px,1fr))',gap:16}}>
                  {gitRepos.map(repo => (
                    <div key={repo.id} className="card" style={{padding:16,cursor:'pointer',border:repo.is_active ? '1px solid #10b981' : '1px solid #374151'}} onClick={()=>openRepoDetail(repo)}>
                      <div style={{display:'flex',justifyContent:'space-between',alignItems:'flex-start'}}>
                        <div>
                          <span style={{fontSize:20,marginRight:6}}>
                            {repo.provider === 'github' ? '🐙' : repo.provider === 'gitlab' ? '🦊' : repo.provider === 'bitbucket' ? '🪣' : '🗄️'}
                          </span>
                          <strong>{repo.name}</strong>
                          <span style={{marginLeft:8,background:'#374151',padding:'2px 8px',borderRadius:10,fontSize:11,textTransform:'uppercase'}}>{repo.provider}</span>
                        </div>
                        <span style={{width:10,height:10,borderRadius:'50%',background:repo.is_active ? '#10b981' : '#ef4444',display:'inline-block',marginTop:6}}></span>
                      </div>
                      <p style={{color:'#9ca3af',fontSize:13,margin:'8px 0 4px'}}>{repo.repo_full_name}</p>
                      <div style={{display:'flex',gap:8,fontSize:12,color:'#6b7280'}}>
                        <span>🌿 {repo.default_branch}</span>
                        {repo.webhook_id && <span>🔗 Webhook active</span>}
                        {repo.last_synced && <span>🔄 {new Date(repo.last_synced).toLocaleDateString()}</span>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            /* ── Repo Detail View ── */
            <div>
              <button className="btn btn-secondary" onClick={()=>setSelectedRepo(null)} style={{marginBottom:12}}>← Back to Repositories</button>
              <div className="card" style={{padding:20,marginBottom:16}}>
                <div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
                  <div>
                    <span style={{fontSize:24,marginRight:8}}>
                      {selectedRepo.provider === 'github' ? '🐙' : selectedRepo.provider === 'gitlab' ? '🦊' : selectedRepo.provider === 'bitbucket' ? '🪣' : '🗄️'}
                    </span>
                    <h3 style={{display:'inline'}}>{selectedRepo.name}</h3>
                    <span style={{marginLeft:12,background:'#374151',padding:'2px 10px',borderRadius:10,fontSize:12,textTransform:'uppercase'}}>{selectedRepo.provider}</span>
                    <span style={{marginLeft:8,background:selectedRepo.is_active ? '#065f46' : '#7f1d1d',padding:'2px 10px',borderRadius:10,fontSize:12}}>{selectedRepo.is_active ? 'Active' : 'Inactive'}</span>
                  </div>
                  <div style={{display:'flex',gap:6}}>
                    <button className="btn btn-sm btn-info" onClick={()=>testRepoConn(selectedRepo.id)}>🔌 Test</button>
                    <button className="btn btn-sm btn-primary" onClick={()=>syncRepo(selectedRepo.id)}>🔄 Sync</button>
                    {!selectedRepo.webhook_id ? <button className="btn btn-sm btn-success" onClick={()=>registerWebhook(selectedRepo.id)}>🔗 Add Webhook</button>
                      : <button className="btn btn-sm btn-warning" onClick={()=>removeWebhook(selectedRepo.id)}>🔗 Remove Webhook</button>}
                    <button className="btn btn-sm btn-danger" onClick={()=>deleteRepo(selectedRepo.id)}>🗑️ Delete</button>
                  </div>
                </div>
                <p style={{color:'#9ca3af',marginTop:8}}>{selectedRepo.repo_full_name} • Branch: {selectedRepo.default_branch} {selectedRepo.last_synced && ` • Last synced: ${new Date(selectedRepo.last_synced).toLocaleString()}`}</p>
              </div>

              {/* Sub-tabs */}
              <div style={{display:'flex',gap:4,marginBottom:16,flexWrap:'wrap'}}>
                {[{k:'info',l:'ℹ️ Info'},{k:'branches',l:'🌿 Branches'},{k:'commits',l:'📝 Commits'},{k:'pulls',l:'🔀 Pull Requests'},{k:'tags',l:'🏷️ Tags'},{k:'files',l:'📁 Files'}].map(t => (
                  <button key={t.k} className={`btn btn-sm ${repoSubTab===t.k ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={()=>{
                      setRepoSubTab(t.k);
                      if (t.k==='branches') loadRepoBranches(selectedRepo.id);
                      if (t.k==='commits') loadRepoCommits(selectedRepo.id);
                      if (t.k==='pulls') loadRepoPulls(selectedRepo.id);
                      if (t.k==='tags') loadRepoTags(selectedRepo.id);
                      if (t.k==='files') { setTreePath(''); setRepoFile(null); loadRepoTree(selectedRepo.id,''); }
                    }}>{t.l}</button>
                ))}
              </div>

              {/* Info Sub-tab */}
              {repoSubTab === 'info' && (
                <div className="card" style={{padding:20}}>
                  <h4>Repository Information</h4>
                  <table style={{width:'100%',marginTop:12}}>
                    <tbody>
                      {[['Name', selectedRepo.name],['Provider', selectedRepo.provider],['Full Name', selectedRepo.repo_full_name],['Default Branch', selectedRepo.default_branch],['Server URL', selectedRepo.server_url || 'Default (cloud)'],['Webhook ID', selectedRepo.webhook_id || 'None'],['Created', new Date(selectedRepo.created_at).toLocaleString()],['Last Synced', selectedRepo.last_synced ? new Date(selectedRepo.last_synced).toLocaleString() : 'Never']].map(([k,v]) => (
                        <tr key={k}><td style={{padding:'6px 12px',color:'#9ca3af',width:160}}>{k}</td><td style={{padding:'6px 12px'}}>{v}</td></tr>
                      ))}
                    </tbody>
                  </table>
                  {selectedRepo.repo_meta && (
                    <div style={{marginTop:16}}>
                      <h5>Metadata</h5>
                      <div style={{display:'flex',gap:16,flexWrap:'wrap',marginTop:8}}>
                        {selectedRepo.repo_meta.stars != null && <span>⭐ {selectedRepo.repo_meta.stars} stars</span>}
                        {selectedRepo.repo_meta.forks != null && <span>🍴 {selectedRepo.repo_meta.forks} forks</span>}
                        {selectedRepo.repo_meta.open_issues != null && <span>🐛 {selectedRepo.repo_meta.open_issues} issues</span>}
                        {selectedRepo.repo_meta.language && <span>💻 {selectedRepo.repo_meta.language}</span>}
                        {selectedRepo.repo_meta.description && <p style={{width:'100%',color:'#9ca3af',marginTop:8}}>{selectedRepo.repo_meta.description}</p>}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Branches Sub-tab */}
              {repoSubTab === 'branches' && (
                <div className="card" style={{padding:20}}>
                  <h4>🌿 Branches ({repoBranches.length})</h4>
                  {repoBranches.length === 0 ? <p style={{color:'#9ca3af'}}>Loading branches...</p> : (
                    <table style={{width:'100%',marginTop:12}}>
                      <thead><tr><th style={{textAlign:'left',padding:6}}>Branch</th><th style={{textAlign:'left',padding:6}}>Latest Commit</th></tr></thead>
                      <tbody>{repoBranches.map((b,i) => (
                        <tr key={i}><td style={{padding:6}}>
                          {b.name}{b.name === selectedRepo.default_branch && <span style={{marginLeft:6,background:'#065f46',padding:'1px 6px',borderRadius:10,fontSize:11}}>default</span>}
                        </td><td style={{padding:6,color:'#9ca3af',fontSize:13}}>{b.sha ? b.sha.substring(0,8) : '—'}</td></tr>
                      ))}</tbody>
                    </table>
                  )}
                </div>
              )}

              {/* Commits Sub-tab */}
              {repoSubTab === 'commits' && (
                <div className="card" style={{padding:20}}>
                  <h4>📝 Recent Commits</h4>
                  {repoCommits.length === 0 ? <p style={{color:'#9ca3af'}}>Loading commits...</p> : (
                    <div style={{marginTop:12}}>
                      {repoCommits.map((c,i) => (
                        <div key={i} style={{borderBottom:'1px solid #1f2937',padding:'10px 0'}}>
                          <div style={{display:'flex',justifyContent:'space-between'}}>
                            <strong style={{fontSize:14}}>{c.message ? c.message.split('\n')[0] : '—'}</strong>
                            <code style={{color:'#60a5fa',fontSize:12}}>{c.sha ? c.sha.substring(0,8) : ''}</code>
                          </div>
                          <div style={{fontSize:12,color:'#6b7280',marginTop:4}}>
                            {c.author || 'Unknown'} • {c.date ? new Date(c.date).toLocaleString() : ''}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Pull Requests Sub-tab */}
              {repoSubTab === 'pulls' && (
                <div className="card" style={{padding:20}}>
                  <h4>🔀 Pull Requests / Merge Requests</h4>
                  {repoPulls.length === 0 ? <p style={{color:'#9ca3af'}}>No open pull requests.</p> : (
                    <div style={{marginTop:12}}>
                      {repoPulls.map((pr,i) => (
                        <div key={i} style={{borderBottom:'1px solid #1f2937',padding:'10px 0',display:'flex',justifyContent:'space-between',alignItems:'center'}}>
                          <div>
                            <span style={{color:'#10b981',marginRight:6}}>#{pr.number}</span>
                            <strong>{pr.title}</strong>
                            <div style={{fontSize:12,color:'#6b7280',marginTop:4}}>by {pr.author || 'Unknown'} • {pr.created ? new Date(pr.created).toLocaleDateString() : ''}</div>
                          </div>
                          <span style={{background: pr.state === 'open' ? '#065f46' : pr.state === 'merged' ? '#581c87' : '#7f1d1d', padding:'2px 10px',borderRadius:10,fontSize:12}}>{pr.state || 'open'}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Tags Sub-tab */}
              {repoSubTab === 'tags' && (
                <div className="card" style={{padding:20}}>
                  <h4>🏷️ Tags</h4>
                  <button className="btn btn-sm btn-secondary" onClick={()=>loadRepoTags(selectedRepo.id)} style={{marginBottom:12}}>🔄 Refresh</button>
                  {repoTags.length === 0 ? <p style={{color:'#9ca3af'}}>No tags found.</p> : (
                    <table style={{width:'100%'}}>
                      <thead><tr><th style={{textAlign:'left',padding:6}}>Tag</th><th style={{textAlign:'left',padding:6}}>SHA</th></tr></thead>
                      <tbody>{repoTags.map((t,i) => (
                        <tr key={i}><td style={{padding:6}}>🏷️ {t.name}</td><td style={{padding:6,color:'#9ca3af',fontSize:13}}>{t.sha ? t.sha.substring(0,8) : '—'}</td></tr>
                      ))}</tbody>
                    </table>
                  )}
                </div>
              )}

              {/* Files Sub-tab */}
              {repoSubTab === 'files' && (
                <div className="card" style={{padding:20}}>
                  <h4>📁 File Browser</h4>
                  <div style={{marginBottom:12,display:'flex',gap:8,alignItems:'center'}}>
                    <span style={{color:'#9ca3af',fontSize:13}}>Path:</span>
                    <span style={{color:'#60a5fa',fontSize:13,cursor:'pointer'}} onClick={()=>{setTreePath('');setRepoFile(null);loadRepoTree(selectedRepo.id,'');}}>root</span>
                    {treePath && treePath.split('/').map((seg,i,arr)=>{
                      const p = arr.slice(0,i+1).join('/');
                      return <span key={i}><span style={{color:'#6b7280'}}> / </span><span style={{color:'#60a5fa',fontSize:13,cursor:'pointer'}} onClick={()=>{setTreePath(p);setRepoFile(null);loadRepoTree(selectedRepo.id,p);}}>{seg}</span></span>;
                    })}
                  </div>

                  {repoFile ? (
                    <div>
                      <button className="btn btn-sm btn-secondary" onClick={()=>setRepoFile(null)} style={{marginBottom:8}}>← Back to tree</button>
                      <div style={{background:'#0d1117',padding:16,borderRadius:8,overflowX:'auto'}}>
                        <div style={{display:'flex',justifyContent:'space-between',marginBottom:8}}>
                          <strong>{repoFile.name}</strong>
                          <span style={{color:'#6b7280',fontSize:12}}>{repoFile.size ? `${(repoFile.size/1024).toFixed(1)} KB` : ''} • {repoFile.encoding || ''}</span>
                        </div>
                        <pre style={{margin:0,fontSize:13,lineHeight:1.5,color:'#e6edf3',whiteSpace:'pre-wrap',wordBreak:'break-all'}}>{repoFile.content || '(binary or empty)'}</pre>
                      </div>
                    </div>
                  ) : (
                    <div>
                      {repoTree.length === 0 ? <p style={{color:'#9ca3af'}}>Loading file tree...</p> : (
                        <table style={{width:'100%'}}>
                          <tbody>{repoTree.map((item,i) => (
                            <tr key={i} style={{cursor:'pointer',borderBottom:'1px solid #1f2937'}} onClick={()=>{
                              if (item.type === 'dir' || item.type === 'tree') {
                                const np = treePath ? `${treePath}/${item.name}` : item.name;
                                setTreePath(np); setRepoFile(null); loadRepoTree(selectedRepo.id, np);
                              } else {
                                const fp = treePath ? `${treePath}/${item.name}` : item.name;
                                loadRepoFile(selectedRepo.id, fp);
                              }
                            }}>
                              <td style={{padding:'6px 8px',width:30}}>{item.type === 'dir' || item.type === 'tree' ? '📁' : '📄'}</td>
                              <td style={{padding:'6px 8px',color: item.type === 'dir' || item.type === 'tree' ? '#60a5fa' : '#e5e7eb'}}>{item.name}</td>
                              <td style={{padding:'6px 8px',color:'#6b7280',fontSize:12,textAlign:'right'}}>{item.size ? `${(item.size/1024).toFixed(1)} KB` : ''}</td>
                            </tr>
                          ))}</tbody>
                        </table>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Script Templates Tab ── */}
      {tab === 'scripts' && (
        <div>
          <h3>📜 Pipeline Script Templates</h3>
          <p style={{color:'#9ca3af',marginBottom:16}}>Ready-to-use pipeline scripts for Jenkins (Groovy), GitLab CI / GitHub Actions (YAML), and Shell. Copy and customize for your environment.</p>
          {Object.entries(templates).map(([key, tpl]) => (
            <div key={key} className="card" style={{marginBottom:16}}>
              <div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
                <h4 style={{margin:0}}>{key==='groovy'?'🔧':key==='yaml'?'📝':'💻'} {tpl.label}</h4>
                <button className="btn btn-sm btn-primary" onClick={()=>{navigator.clipboard.writeText(tpl.content);setMsg(`${key} template copied to clipboard!`);}}>📋 Copy</button>
              </div>
              <pre className="code-block" style={{marginTop:10,maxHeight:350,overflow:'auto',fontSize:11}}>{tpl.content}</pre>
            </div>
          ))}

          {/* Webhook setup guide */}
          <div className="card">
            <h4>🔗 Webhook Setup Guide</h4>
            <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(300px,1fr))',gap:16}}>
              <div>
                <h5>Jenkins</h5>
                <ol style={{fontSize:13,paddingLeft:20}}>
                  <li>Install "Generic Webhook Trigger" plugin</li>
                  <li>In job config → Build Triggers → Generic Webhook Trigger</li>
                  <li>Set Token to your pipeline's webhook secret</li>
                  <li>For notifications back: Install "Notification" plugin, add webhook URL</li>
                  <li>Jenkinsfile supports Groovy declarative & scripted pipelines</li>
                </ol>
              </div>
              <div>
                <h5>GitLab CI</h5>
                <ol style={{fontSize:13,paddingLeft:20}}>
                  <li>Go to Settings → Webhooks</li>
                  <li>Enter the PatchMaster webhook URL</li>
                  <li>Set Secret Token to your pipeline's webhook secret</li>
                  <li>Select "Pipeline events" trigger</li>
                  <li>Use <code>.gitlab-ci.yml</code> with YAML template</li>
                </ol>
              </div>
              <div>
                <h5>GitHub Actions</h5>
                <ol style={{fontSize:13,paddingLeft:20}}>
                  <li>Go to Settings → Webhooks → Add webhook</li>
                  <li>Enter the PatchMaster webhook URL</li>
                  <li>Set Secret to your pipeline's webhook secret</li>
                  <li>Select "Workflow runs" events</li>
                  <li>Use <code>.github/workflows/*.yml</code> with YAML template</li>
                </ol>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ─── Monitoring Tools ─── */
function MonitoringToolsPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [enforcing, setEnforcing] = useState(false);
  const [actionMsg, setActionMsg] = useState('');
  const masterIp = window.location.hostname;

  const fetchStatus = () => {
    setLoading(true);
    apiFetch(`${API}/api/monitoring/status`).then(r=>r.json()).then(d=>{setData(d);setLoading(false);}).catch(()=>setLoading(false));
  };

  useEffect(()=>{fetchStatus();},[]);

  const handleEnforce = () => {
    setEnforcing(true); setActionMsg('');
    apiFetch(`${API}/api/monitoring/enforce`,{method:'POST'}).then(r=>r.json()).then(d=>{
      setActionMsg(d.action === 'started' ? 'Monitoring services started successfully!' : 'Monitoring services stopped.');
      setEnforcing(false); fetchStatus();
    }).catch(()=>{setActionMsg('Enforcement failed');setEnforcing(false);});
  };

  const handleInstallStart = () => {
    setEnforcing(true); setActionMsg('Installing & starting monitoring services...');
    apiFetch(`${API}/api/monitoring/enforce`,{method:'POST'}).then(r=>r.json()).then(d=>{
      setActionMsg('Monitoring services installed and started!');
      setEnforcing(false); fetchStatus();
    }).catch(()=>{setActionMsg('Operation failed');setEnforcing(false);});
  };

  const toolInfo = {
    prometheus: { icon: '🔥', name: 'Prometheus', desc: 'Metrics collection & alerting', urlPort: 9090 },
    grafana:    { icon: '📊', name: 'Grafana',    desc: 'Dashboards & visualization', urlPort: 3001 },
    zabbix:     { icon: '🦊', name: 'Zabbix',     desc: 'Infrastructure monitoring', urlPort: 10051 },
  };

  const licensed = data?.licensed;
  const services = data?.services || {};
  const allRunning = Object.values(services).every(s => s.running);
  const allInstalled = Object.values(services).every(s => s.installed);
  const anyRunning = Object.values(services).some(s => s.running);

  return (
    <div>
      {/* License Tier Banner */}
      <div className="card" style={{
        background: licensed ? 'linear-gradient(135deg, #064e3b 0%, #065f46 100%)' : 'linear-gradient(135deg, #7f1d1d 0%, #991b1b 100%)',
        border: licensed ? '2px solid #10b981' : '2px solid #dc2626',
      }}>
        <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',flexWrap:'wrap',gap:16}}>
          <div>
            <h3 style={{margin:0,color:'#fff'}}>
              {licensed ? '✅ Monitoring Licensed' : '🔒 Monitoring Not Available'}
            </h3>
            <p style={{margin:'8px 0 0',color:licensed?'#a7f3d0':'#fca5a5',fontSize:14}}>
              {licensed
                ? `Your ${data?.tier_label || 'license'} tier includes Prometheus, Grafana & Zabbix monitoring.`
                : `Monitoring requires Standard tier or above. Current tier: ${data?.tier_label || 'Basic'}. Upgrade your license to enable monitoring.`}
            </p>
          </div>
          {licensed && hasRole('admin') && (
            <button className="btn btn-primary" onClick={handleEnforce} disabled={enforcing} style={{whiteSpace:'nowrap'}}>
              {enforcing ? 'Working...' : allRunning ? '🔄 Re-enforce' : '🚀 Install & Start All'}
            </button>
          )}
        </div>
        {actionMsg && <p style={{margin:'10px 0 0',color:'#fcd34d',fontWeight:600}}>{actionMsg}</p>}
      </div>

      {/* Service Status Cards */}
      {loading ? <div className="card"><p>Checking monitoring services...</p></div> : (
        <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(300px,1fr))',gap:16,marginBottom:16}}>
          {Object.entries(services).map(([key, s]) => {
            const info = toolInfo[key] || {};
            const isUp = s.running;
            const isInstalled = s.installed;
            return (
              <div key={key} className="card" style={{
                border: !licensed ? '2px solid #4b5563' : isUp ? '2px solid #10b981' : isInstalled ? '2px solid #f59e0b' : '2px solid #dc2626',
                opacity: licensed ? 1 : 0.6,
              }}>
                <div style={{display:'flex',alignItems:'center',gap:12,marginBottom:14}}>
                  <span style={{fontSize:32}}>{info.icon||'🔧'}</span>
                  <div style={{flex:1}}>
                    <h4 style={{margin:0}}>{info.name || s.name || key}</h4>
                    <span style={{fontSize:12,color:'#9ca3af'}}>{info.desc}</span>
                  </div>
                  {isUp ? (
                    <span className="badge badge-success" style={{fontSize:12,padding:'4px 10px'}}>Running</span>
                  ) : isInstalled ? (
                    <span className="badge badge-warning" style={{fontSize:12,padding:'4px 10px'}}>Stopped</span>
                  ) : (
                    <span className="badge badge-danger" style={{fontSize:12,padding:'4px 10px'}}>Not Installed</span>
                  )}
                </div>

                <div style={{fontSize:13,marginBottom:12}}>
                  <span>Port: <strong>{s.port}</strong></span>
                  <span style={{marginLeft:16}}>Installed: <strong>{isInstalled ? 'Yes' : 'No'}</strong></span>
                </div>

                {!licensed ? (
                  <div style={{padding:12,borderRadius:8,background:'rgba(107,114,128,0.15)',border:'1px solid rgba(107,114,128,0.3)'}}>
                    <p style={{margin:0,fontSize:13,color:'#9ca3af'}}>🔒 Upgrade to Standard tier or above to enable monitoring services.</p>
                  </div>
                ) : isUp ? (
                  <a href={`http://${masterIp}:${info.urlPort || s.port}`} target="_blank" rel="noopener noreferrer"
                    className="btn btn-primary" style={{width:'100%',textAlign:'center'}}>
                    Open {info.name} ↗
                  </a>
                ) : (
                  <div style={{padding:12,borderRadius:8,background:'rgba(245,158,11,0.1)',border:'1px solid rgba(245,158,11,0.3)'}}>
                    <p style={{margin:0,fontSize:13,color:'#f59e0b',fontWeight:600}}>
                      {isInstalled ? '⏸️ Service is installed but stopped.' : '📦 Service not installed.'}
                    </p>
                    <p style={{margin:'6px 0 0',fontSize:12,color:'#9ca3af'}}>
                      {isInstalled
                        ? 'Click "Install & Start All" above to start monitoring services.'
                        : 'Click "Install & Start All" above — PatchMaster will install and configure automatically.'}
                    </p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Tier comparison for monitoring */}
      <div className="card">
        <h3>📋 Monitoring by License Tier</h3>
        <table className="table" style={{fontSize:13}}>
          <thead><tr><th>Feature</th><th>Basic</th><th>Standard</th><th>DevOps</th><th>Enterprise</th></tr></thead>
          <tbody>
            <tr><td>Prometheus (Metrics)</td><td style={{color:'#dc3545'}}>✗</td><td style={{color:'#28a745'}}>✓</td><td style={{color:'#28a745'}}>✓</td><td style={{color:'#28a745'}}>✓</td></tr>
            <tr><td>Grafana (Dashboards)</td><td style={{color:'#dc3545'}}>✗</td><td style={{color:'#28a745'}}>✓</td><td style={{color:'#28a745'}}>✓</td><td style={{color:'#28a745'}}>✓</td></tr>
            <tr><td>Zabbix (Infrastructure)</td><td style={{color:'#dc3545'}}>✗</td><td style={{color:'#28a745'}}>✓</td><td style={{color:'#28a745'}}>✓</td><td style={{color:'#28a745'}}>✓</td></tr>
            <tr><td>Auto Install & Configure</td><td style={{color:'#dc3545'}}>✗</td><td style={{color:'#28a745'}}>✓</td><td style={{color:'#28a745'}}>✓</td><td style={{color:'#28a745'}}>✓</td></tr>
            <tr><td>License-based Auto Start/Stop</td><td style={{color:'#dc3545'}}>✗</td><td style={{color:'#28a745'}}>✓</td><td style={{color:'#28a745'}}>✓</td><td style={{color:'#28a745'}}>✓</td></tr>
          </tbody>
        </table>
      </div>

      {/* Integration info - always visible */}
      <div className="card">
        <h3>🔗 PatchMaster Metrics Endpoint</h3>
        <p style={{color:'#9ca3af'}}>PatchMaster exposes metrics at <code>/metrics</code> in Prometheus format, ready to scrape.</p>
        <pre className="code-block">{`# Prometheus scrape config
- job_name: 'patchmaster'
  metrics_path: '/metrics'
  static_configs:
    - targets: ['${masterIp}:8000']`}</pre>
      </div>
    </div>
  );
}

/* ─── Onboarding ─── */
function OnboardingPage() {
  const [masterIp, setMasterIp] = useState('');
  const [copied, setCopied] = useState(false);
  useEffect(()=>{setMasterIp(window.location.hostname);},[]);
  const installCmd = `curl -sS http://${masterIp||'<master-ip>'}:3000/download/install.sh | sudo bash -s -- ${masterIp||'<master-ip>'}`;
  const copyCmd = () => { navigator.clipboard.writeText(installCmd).then(()=>{setCopied(true);setTimeout(()=>setCopied(false),2000);}); };

  return (
    <div>
      <div className="card highlight-card">
        <h3>🚀 Quick Install (One Command)</h3>
        <p>Run this on any <strong>Debian/Ubuntu</strong> machine:</p>
        <div className="install-master-ip"><label>Master IP: </label><input type="text" value={masterIp} onChange={e=>setMasterIp(e.target.value)} placeholder="e.g. 192.168.1.100" style={{width:'200px',marginLeft:'8px'}} className="input" /></div>
        <div className="install-cmd-box"><pre className="code-block install-code">{installCmd}</pre><button className={`btn btn-sm copy-btn ${copied?'btn-success':'btn-primary'}`} onClick={copyCmd}>{copied?'Copied!':'Copy'}</button></div>
        <p className="hint-text">The first registered user automatically becomes <strong>admin</strong>.</p>
      </div>
      <div className="card"><h3>📋 Manual Steps</h3>
        <ol><li>Download the <code>.deb</code> from <code>http://{masterIp}:3000/download/patch-agent.deb</code></li><li>Install: <code>sudo dpkg -i patch-agent.deb</code></li><li>Edit <code>/etc/patch-agent/config.env</code> to set CONTROLLER_URL</li><li>Restart: <code>sudo systemctl restart patch-agent</code></li></ol>
      </div>
      <div className="card"><h3>✅ Verify</h3><pre className="code-block">{`sudo systemctl status patch-agent\nsudo journalctl -u patch-agent -f`}</pre></div>
    </div>
  );
}

/* ─── Settings ─── */
/* ─── License Page ─── */
function LicensePage({ licenseInfo, onRefresh }) {
  const [key, setKey] = useState('');
  const [msg, setMsg] = useState('');
  const [loading, setLoading] = useState(false);
  const li = licenseInfo || {};

  const activate = async () => {
    if (!key.trim()) { setMsg('Please enter a license key'); return; }
    setLoading(true); setMsg('');
    try {
      const r = await apiFetch(`${API}/api/license/activate`, { method:'POST', body: JSON.stringify({ license_key: key.trim() }) });
      const d = await r.json();
      if (r.ok) { setMsg('License activated successfully!'); setKey(''); onRefresh(); }
      else { setMsg(d.detail || 'Activation failed'); }
    } catch(e) { setMsg('Error: ' + e.message); }
    setLoading(false);
  };

  const statusColor = !li.activated ? '#6c757d' : li.expired ? '#dc3545' : li.days_remaining <= 30 ? '#ffc107' : '#28a745';
  const statusLabel = !li.activated ? 'Not Activated' : li.expired ? 'Expired' : 'Active';
  const tierColors = { basic:'#3b82f6', standard:'#10b981', devops:'#f59e0b', enterprise:'#8b5cf6' };
  const tierIcons = { basic:'📦', standard:'⭐', devops:'🚀', enterprise:'👑' };

  return (
    <div>
      {/* Current License Status */}
      <div className="card">
        <h3>🔑 License Status</h3>
        <div style={{display:'flex',alignItems:'center',gap:12,marginBottom:16}}>
          <span style={{display:'inline-block',width:14,height:14,borderRadius:'50%',background:statusColor}}></span>
          <span style={{fontSize:18,fontWeight:700}}>{statusLabel}</span>
          {li.tier && (
            <span style={{background:tierColors[li.tier]||'#6c757d',color:'#fff',padding:'3px 12px',borderRadius:12,fontSize:13,fontWeight:600}}>
              {tierIcons[li.tier]||'🔑'} {li.tier_label || li.tier}
            </span>
          )}
        </div>
        {li.activated && li.valid ? (
          <div>
            <table className="table"><tbody>
              <tr><td><strong>License ID</strong></td><td><code>{li.license_id || 'legacy'}</code></td></tr>
              <tr><td><strong>Plan</strong></td><td>{li.plan_label}</td></tr>
              <tr><td><strong>Tier</strong></td><td>
                <span style={{background:tierColors[li.tier]||'#374151',color:'#fff',padding:'2px 10px',borderRadius:10,fontSize:12}}>{li.tier_label || li.tier || 'Enterprise'}</span>
              </td></tr>
              <tr><td><strong>Customer</strong></td><td>{li.customer}</td></tr>
              <tr><td><strong>Issued</strong></td><td>{li.issued_at}</td></tr>
              <tr><td><strong>Expires</strong></td><td>
                <span style={{color: li.expired ? '#dc3545' : li.days_remaining<=30 ? '#e67e00' : '#28a745', fontWeight:600}}>
                  {li.expires_at} {li.expired ? '(EXPIRED)' : `(${li.days_remaining} days remaining)`}
                </span>
              </td></tr>
              <tr><td><strong>Max Hosts</strong></td><td>{li.max_hosts === 0 ? 'Unlimited' : li.max_hosts}</td></tr>
              <tr><td><strong>Version</strong></td><td>v{li.tool_version || '2.0'} (compatible: {li.version_compat || '2.x'})</td></tr>
            </tbody></table>

            {/* Licensed Features */}
            {li.features && li.features.length > 0 && (
              <div style={{marginTop:16}}>
                <h4>Licensed Features ({li.features.length})</h4>
                <div style={{display:'flex',flexWrap:'wrap',gap:6,marginTop:8}}>
                  {li.features.map(f => (
                    <span key={f} style={{
                      padding:'4px 10px',borderRadius:10,fontSize:12,fontWeight:500,
                      background:'#065f46',color:'#6ee7b7',border:'1px solid #10b981',
                    }}>
                      ✓ {f}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : li.activated && !li.valid ? (
          <p style={{color:'#dc3545',fontWeight:500}}>License key is invalid: {li.error}</p>
        ) : (
          <p style={{color:'#6c757d'}}>No license key found. Enter a license key below to activate PatchMaster.</p>
        )}
      </div>

      {/* Activate / Renew */}
      <div className="card">
        <h3>{li.activated && li.valid && !li.expired ? '🔄 Renew / Change License' : '🔑 Activate License'}</h3>
        <p style={{color:'#666',marginBottom:12}}>Paste the license key provided by your PatchMaster vendor.</p>
        <div className="form-row">
          <input className="input" style={{flex:1,fontFamily:'monospace',fontSize:12}} placeholder="PM1-xxxxxxxxx.xxxxxxxx" value={key} onChange={e => setKey(e.target.value)} />
          <button className="btn btn-primary" onClick={activate} disabled={loading}>{loading ? 'Activating...' : 'Activate'}</button>
        </div>
        {msg && <p style={{marginTop:8,fontWeight:500,color:msg.includes('successfully')?'#28a745':'#dc3545'}}>{msg}</p>}
      </div>
    </div>
  );
}

function SettingsPage({ health, hosts, jobs }) {
  const [changePw, setChangePw] = useState({current:'',new_password:'',confirm_password:''});
  const [pwMsg, setPwMsg] = useState('');
  const masterIp = window.location.hostname;
  const frontendUrl = `http://${masterIp}:${window.location.port||'3000'}`;

  const changePassword = async () => {
    if(changePw.new_password !== changePw.confirm_password) { setPwMsg('New passwords do not match'); return; }
    if(changePw.new_password.length < 8) { setPwMsg('Password must be at least 8 characters'); return; }
    try {
      const r = await apiFetch(`${API}/api/auth/change-password`, { method:'POST', body:JSON.stringify({old_password:changePw.current,new_password:changePw.new_password}) });
      if(r.ok) { setPwMsg('Password changed successfully!'); setChangePw({current:'',new_password:'',confirm_password:''}); } else { const d=await r.json(); setPwMsg(d.detail||'Failed'); }
    } catch(e) { setPwMsg('Error: '+e.message); }
  };

  return (
    <div>
      <div className="card"><h3>🖥️ System Information</h3>
        <table className="table"><tbody>
          <tr><td><strong>Backend Status</strong></td><td>{health?<span className="badge badge-success">Online</span>:<span className="badge badge-danger">Offline</span>}</td></tr>
          <tr><td><strong>Master IP</strong></td><td><code>{masterIp}</code></td></tr>
          <tr><td><strong>Total Hosts</strong></td><td>{hosts.length}</td></tr>
          <tr><td><strong>Total Jobs</strong></td><td>{jobs.length}</td></tr>
          <tr><td><strong>Version</strong></td><td>2.0.0 Enterprise</td></tr>
        </tbody></table>
      </div>
      <div className="card"><h3>🔑 Change My Password</h3>
        <div className="form-row" style={{flexWrap:'wrap',gap:8}}>
          <input className="input" type="password" placeholder="Current password" value={changePw.current} onChange={e=>setChangePw(f=>({...f,current:e.target.value}))} />
          <input className="input" type="password" placeholder="New password (min 8 chars)" value={changePw.new_password} onChange={e=>setChangePw(f=>({...f,new_password:e.target.value}))} />
          <input className="input" type="password" placeholder="Confirm new password" value={changePw.confirm_password} onChange={e=>setChangePw(f=>({...f,confirm_password:e.target.value}))} />
          <button className="btn btn-primary" onClick={changePassword}>Change Password</button>
        </div>
        {pwMsg && <p style={{marginTop:8,fontWeight:500,color:pwMsg.includes('success')?'#28a745':'#dc3545'}}>{pwMsg}</p>}
      </div>
      <div className="card"><h3>⚡ Quick Agent Install</h3><pre className="code-block">{`curl -sS ${frontendUrl}/download/install.sh | sudo bash -s -- ${masterIp}`}</pre></div>
      <div className="card"><h3>🐳 Docker Commands</h3><pre className="code-block">{`docker compose build --no-cache\ndocker compose up -d\ndocker compose logs -f backend\ndocker compose down`}</pre></div>
    </div>
  );
}

export default App;

