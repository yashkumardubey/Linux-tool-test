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
    ...(hasPerm('license') ? [{ key: 'license', label: 'License', icon: '🔑' }] : []),
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
          <div style={{display:'flex',alignItems:'center',gap:8,width:'100%'}}>
            <span className={`status-dot ${health ? 'online' : 'offline'}`}></span>
            <span style={{flex:1}}>{user?.username} <span className="badge badge-info" style={{fontSize:9}}>{user?.role}</span></span>
            <button className="btn btn-sm btn-danger" onClick={handleLogout} style={{padding:'3px 8px',fontSize:11}}>Logout</button>
          </div>
        </div>
      </aside>
      <main className="main-content">
        {/* License warning banners */}
        {licenseInfo && !licenseInfo.activated && (
          <div style={{background:'#dc3545',color:'#fff',padding:'10px 20px',textAlign:'center',fontWeight:600,cursor:'pointer'}} onClick={()=>setPage('license')}>
            ⚠️ No license activated. PatchMaster features are disabled. Click here to activate.
          </div>
        )}
        {licenseInfo && licenseInfo.activated && licenseInfo.expired && (
          <div style={{background:'#dc3545',color:'#fff',padding:'10px 20px',textAlign:'center',fontWeight:600,cursor:'pointer'}} onClick={()=>setPage('license')}>
            ⚠️ License expired on {licenseInfo.expires_at}. PatchMaster features are disabled. Click here to renew.
          </div>
        )}
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
          {page === 'license' && hasPerm('license') && <LicensePage licenseInfo={licenseInfo} onRefresh={fetchAll} />}
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

/* ─── Monitoring Tools ─── */
function MonitoringToolsPage() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const masterIp = window.location.hostname;

  useEffect(() => {
    setLoading(true);
    apiFetch(`${API}/api/auth/monitoring-status`).then(r=>r.json()).then(d=>{setStatus(d);setLoading(false);}).catch(()=>setLoading(false));
  }, []);

  const toolInfo = {
    prometheus: { icon: '🔥', desc: 'Metrics collection & alerting', docs: 'https://prometheus.io/docs/' },
    grafana:    { icon: '📊', desc: 'Dashboards & visualization', docs: 'https://grafana.com/docs/' },
    zabbix:     { icon: '🦊', desc: 'Infrastructure monitoring', docs: 'https://www.zabbix.com/documentation' },
  };

  return (
    <div>
      <div className="card">
        <h3>📈 Monitoring Tools</h3>
        <p style={{color:'#9ca3af',marginBottom:16}}>Quick-launch monitoring tools if installed on this infrastructure. PatchMaster exposes <code>/metrics</code> endpoint (Prometheus format) for integration.</p>
        {loading ? <p>Checking services...</p> : !status ? <p className="text-danger">Could not check monitoring status</p> : (
          <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(280px,1fr))',gap:16}}>
            {Object.entries(status).map(([key, s]) => {
              const info = toolInfo[key] || {};
              return (
                <div key={key} style={{
                  padding:20, borderRadius:12,
                  background: s.reachable ? 'rgba(40,167,69,0.1)' : 'rgba(108,117,125,0.08)',
                  border: s.reachable ? '2px solid #28a745' : '2px solid #6c757d',
                }}>
                  <div style={{display:'flex',alignItems:'center',gap:10,marginBottom:12}}>
                    <span style={{fontSize:28}}>{info.icon||'🔧'}</span>
                    <div>
                      <h4 style={{margin:0}}>{s.name}</h4>
                      <span style={{fontSize:12,color:'#9ca3af'}}>{info.desc}</span>
                    </div>
                  </div>
                  <div style={{marginBottom:12}}>
                    <span style={{fontSize:13}}>Port: <strong>{s.port}</strong></span>
                    <span style={{marginLeft:12}}>
                      Status: {s.reachable
                        ? <span className="badge badge-success">Running</span>
                        : <span className="badge badge-danger">Not Detected</span>}
                    </span>
                  </div>
                  {s.reachable && s.url ? (
                    <a href={s.url.replace('localhost', masterIp).replace('127.0.0.1', masterIp)} target="_blank" rel="noopener noreferrer" className="btn btn-primary" style={{width:'100%',textAlign:'center'}}>
                      Open {s.name} ↗
                    </a>
                  ) : (
                    <div style={{padding:12,borderRadius:8,background:'rgba(220,53,69,0.1)',border:'1px solid rgba(220,53,69,0.3)'}}>
                      <p style={{margin:0,fontSize:13,color:'#dc3545',fontWeight:600}}>⚠️ {s.name} is not installed or not running on port {s.port}.</p>
                      <p style={{margin:'8px 0 0',fontSize:12,color:'#9ca3af'}}>
                        To install, run PatchMaster installer with <code>--with-monitoring</code> flag, or set up {s.name} manually and ensure it's listening on port {s.port}.
                      </p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Integration info */}
      <div className="card">
        <h3>🔗 PatchMaster Metrics Endpoint</h3>
        <p>PatchMaster exposes metrics at <code>/metrics</code> in Prometheus format, ready to scrape.</p>
        <pre className="code-block">{`# Prometheus scrape config
- job_name: 'patchmaster'
  metrics_path: '/metrics'
  static_configs:
    - targets: ['${masterIp}:8000']`}</pre>
      </div>

      <div className="card">
        <h3>📋 Setup Commands</h3>
        <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(280px,1fr))',gap:16}}>
          <div>
            <h4>🔥 Prometheus</h4>
            <pre className="code-block" style={{fontSize:11}}>{`sudo apt install prometheus
sudo systemctl enable --now prometheus
# Default: http://localhost:9090`}</pre>
          </div>
          <div>
            <h4>📊 Grafana</h4>
            <pre className="code-block" style={{fontSize:11}}>{`sudo apt install grafana
sudo systemctl enable --now grafana-server
# Default: http://localhost:3001`}</pre>
          </div>
          <div>
            <h4>🦊 Zabbix</h4>
            <pre className="code-block" style={{fontSize:11}}>{`# Install from zabbix.com repository
sudo apt install zabbix-server-pgsql zabbix-frontend-php
sudo systemctl enable --now zabbix-server
# Default: http://localhost:8080`}</pre>
          </div>
        </div>
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

  const deactivate = async () => {
    if (!window.confirm('Deactivate the current license? PatchMaster will stop working.')) return;
    try {
      const r = await apiFetch(`${API}/api/license/deactivate`, { method:'DELETE' });
      if (r.ok) { setMsg('License deactivated'); onRefresh(); }
      else { const d = await r.json(); setMsg(d.detail || 'Failed'); }
    } catch(e) { setMsg('Error: ' + e.message); }
  };

  const statusColor = !li.activated ? '#6c757d' : li.expired ? '#dc3545' : li.days_remaining <= 30 ? '#ffc107' : '#28a745';
  const statusLabel = !li.activated ? 'Not Activated' : li.expired ? 'Expired' : 'Active';

  return (
    <div>
      {/* Current License Status */}
      <div className="card">
        <h3>🔑 License Status</h3>
        <div style={{display:'flex',alignItems:'center',gap:12,marginBottom:16}}>
          <span style={{display:'inline-block',width:14,height:14,borderRadius:'50%',background:statusColor}}></span>
          <span style={{fontSize:18,fontWeight:700}}>{statusLabel}</span>
        </div>
        {li.activated && li.valid ? (
          <table className="table"><tbody>
            <tr><td><strong>Plan</strong></td><td>{li.plan_label}</td></tr>
            <tr><td><strong>Customer</strong></td><td>{li.customer}</td></tr>
            <tr><td><strong>Issued</strong></td><td>{li.issued_at}</td></tr>
            <tr><td><strong>Expires</strong></td><td>
              <span style={{color: li.expired ? '#dc3545' : li.days_remaining<=30 ? '#e67e00' : '#28a745', fontWeight:600}}>
                {li.expires_at} {li.expired ? '(EXPIRED)' : `(${li.days_remaining} days remaining)`}
              </span>
            </td></tr>
            <tr><td><strong>Max Hosts</strong></td><td>{li.max_hosts === 0 ? 'Unlimited' : li.max_hosts}</td></tr>
          </tbody></table>
        ) : li.activated && !li.valid ? (
          <p style={{color:'#dc3545',fontWeight:500}}>License key is invalid: {li.error}</p>
        ) : (
          <p style={{color:'#6c757d'}}>No license key found. Enter a license key below to activate PatchMaster.</p>
        )}
        {li.activated && li.valid && hasRole('admin') && (
          <button className="btn btn-danger" onClick={deactivate} style={{marginTop:12}}>Deactivate License</button>
        )}
      </div>

      {/* Activate / Renew */}
      <div className="card">
        <h3>{li.activated && li.valid && !li.expired ? '🔄 Renew / Change License' : '🔑 Activate License'}</h3>
        <p style={{color:'#666',marginBottom:12}}>Paste the license key provided by your PatchMaster administrator.</p>
        <div className="form-row">
          <input className="input" style={{flex:1,fontFamily:'monospace',fontSize:12}} placeholder="PM1-xxxxxxxxx.xxxxxxxx" value={key} onChange={e => setKey(e.target.value)} />
          <button className="btn btn-primary" onClick={activate} disabled={loading}>{loading ? 'Activating...' : 'Activate'}</button>
        </div>
        {msg && <p style={{marginTop:8,fontWeight:500,color:msg.includes('successfully')?'#28a745':'#dc3545'}}>{msg}</p>}
      </div>

      {/* Plan Reference */}
      <div className="card">
        <h3>📋 Available Plans</h3>
        <table className="table">
          <thead><tr><th>Plan</th><th>Duration</th><th>Description</th></tr></thead>
          <tbody>
            <tr><td><span className="badge badge-info">Testing</span></td><td>1 Month</td><td>Evaluation / testing environment</td></tr>
            <tr><td><span className="badge badge-success">Standard</span></td><td>1 Year</td><td>Production use — annual license</td></tr>
            <tr><td><span className="badge badge-warning">Professional</span></td><td>2 Years</td><td>Extended production license</td></tr>
            <tr><td><span className="badge" style={{background:'#6f42c1',color:'#fff'}}>Enterprise</span></td><td>5 Years</td><td>Long-term enterprise deployment</td></tr>
          </tbody>
        </table>
        <p style={{color:'#888',fontSize:12,marginTop:8}}>Contact your PatchMaster vendor to obtain a license key.</p>
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

