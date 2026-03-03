import React, { useState, useEffect, useCallback } from 'react';
import './App.css';

const API = '';

function App() {
  const [page, setPage] = useState('dashboard');
  const [health, setHealth] = useState(null);
  const [hosts, setHosts] = useState([]);
  const [jobs, setJobs] = useState([]);

  const fetchAll = useCallback(() => {
    fetch(`${API}/api/health`).then(r => r.json()).then(setHealth).catch(() => setHealth(null));
    fetch(`${API}/api/hosts/`).then(r => r.json()).then(setHosts).catch(() => {});
    fetch(`${API}/api/jobs/`).then(r => r.json()).then(setJobs).catch(() => {});
  }, []);

  useEffect(() => { fetchAll(); const t = setInterval(fetchAll, 15000); return () => clearInterval(t); }, [fetchAll]);

  const navItems = [
    { key: 'dashboard', label: 'Dashboard', icon: '📊' },
    { key: 'hosts', label: 'Hosts', icon: '🖥️' },
    { key: 'patches', label: 'Patch Manager', icon: '🔄' },
    { key: 'snapshots', label: 'Snapshots', icon: '📸' },
    { key: 'compare', label: 'Compare Packages', icon: '🔍' },
    { key: 'offline', label: 'Offline Patching', icon: '📦' },
    { key: 'jobs', label: 'Job History', icon: '⚙️' },
    { key: 'onboarding', label: 'Onboarding', icon: '🚀' },
    { key: 'settings', label: 'Settings', icon: '🔧' },
  ];

  return (
    <div className="app-container">
      <aside className="sidebar">
        <div className="sidebar-header">
          <h2>PatchMaster</h2>
          <span className="sidebar-subtitle">Centralized Patch Tool</span>
        </div>
        <nav className="sidebar-nav">
          {navItems.map(n => (
            <button key={n.key} className={`nav-btn ${page === n.key ? 'active' : ''}`} onClick={() => setPage(n.key)}>
              <span className="nav-icon">{n.icon}</span> {n.label}
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span className={`status-dot ${health ? 'online' : 'offline'}`}></span>
          {health ? 'Backend Online' : 'Backend Offline'}
        </div>
      </aside>
      <main className="main-content">
        <header className="top-bar">
          <h1 className="page-title">{navItems.find(n => n.key === page)?.label || 'Dashboard'}</h1>
          <div className="top-bar-actions">
            <button className="btn btn-sm" onClick={fetchAll}>Refresh</button>
          </div>
        </header>
        <div className="content-area">
          {page === 'dashboard' && <DashboardPage health={health} hosts={hosts} jobs={jobs} setPage={setPage} />}
          {page === 'hosts' && <HostsPage hosts={hosts} setHosts={setHosts} />}
          {page === 'patches' && <PatchManagerPage hosts={hosts} />}
          {page === 'snapshots' && <SnapshotsPage hosts={hosts} />}
          {page === 'compare' && <ComparePackagesPage hosts={hosts} />}
          {page === 'offline' && <OfflinePatchPage hosts={hosts} />}
          {page === 'jobs' && <JobsPage jobs={jobs} setJobs={setJobs} />}
          {page === 'onboarding' && <OnboardingPage />}
          {page === 'settings' && <SettingsPage health={health} hosts={hosts} jobs={jobs} />}
        </div>
      </main>
    </div>
  );
}

/* ─── Dashboard ─── */
function DashboardPage({ health, hosts, jobs, setPage }) {
  const running = jobs.filter(j => j.status === 'running').length;
  const completed = jobs.filter(j => j.status === 'completed' || j.status === 'success').length;
  const failed = jobs.filter(j => j.status === 'failed' || j.status === 'error').length;
  const pending = jobs.filter(j => j.status === 'pending' || j.status === 'scheduled').length;
  return (
    <div>
      <div className="stats-grid">
        <div className="stat-card" onClick={() => setPage('hosts')}><div className="stat-icon">🖥️</div><div className="stat-info"><span className="stat-number">{hosts.length}</span><span className="stat-label">Total Hosts</span></div></div>
        <div className="stat-card" onClick={() => setPage('jobs')}><div className="stat-icon">⚙️</div><div className="stat-info"><span className="stat-number">{jobs.length}</span><span className="stat-label">Total Jobs</span></div></div>
        <div className="stat-card success"><div className="stat-icon">✅</div><div className="stat-info"><span className="stat-number">{completed}</span><span className="stat-label">Completed</span></div></div>
        <div className="stat-card warning"><div className="stat-icon">🔄</div><div className="stat-info"><span className="stat-number">{running}</span><span className="stat-label">Running</span></div></div>
        <div className="stat-card danger"><div className="stat-icon">❌</div><div className="stat-info"><span className="stat-number">{failed}</span><span className="stat-label">Failed</span></div></div>
        <div className="stat-card info"><div className="stat-icon">🕐</div><div className="stat-info"><span className="stat-number">{pending}</span><span className="stat-label">Pending</span></div></div>
      </div>
      <div className="card">
        <h3>Backend Status</h3>
        {health ? <p className="text-success">Backend is <strong>online</strong> — status: {health.status}</p> : <p className="text-danger">Backend is <strong>offline</strong>. Check Docker containers.</p>}
      </div>
      <div className="grid-2">
        <div className="card"><h3>Recent Hosts</h3>{hosts.length === 0 ? <p className="text-muted">No hosts registered yet.</p> : <table className="table"><thead><tr><th>Name</th><th>IP</th><th>OS</th></tr></thead><tbody>{hosts.slice(0,5).map(h => <tr key={h.id}><td>{h.name}</td><td>{h.ip}</td><td>{h.os}</td></tr>)}</tbody></table>}</div>
        <div className="card"><h3>Recent Jobs</h3>{jobs.length === 0 ? <p className="text-muted">No jobs created yet.</p> : <table className="table"><thead><tr><th>Name</th><th>Status</th></tr></thead><tbody>{jobs.slice(0,5).map(j => <tr key={j.id}><td>{j.name}</td><td><span className={`badge badge-${j.status==='completed'||j.status==='success'?'success':j.status==='running'?'warning':j.status==='failed'?'danger':'info'}`}>{j.status}</span></td></tr>)}</tbody></table>}</div>
      </div>
      <div className="card"><h3>Quick Actions</h3><div className="btn-group">
        <button className="btn btn-primary" onClick={() => setPage('patches')}>🔄 Patch Servers</button>
        <button className="btn btn-primary" onClick={() => setPage('snapshots')}>📸 Manage Snapshots</button>
        <button className="btn btn-primary" onClick={() => setPage('compare')}>🔍 Compare Packages</button>
        <button className="btn btn-primary" onClick={() => setPage('offline')}>📦 Offline Patching</button>
        <button className="btn btn-success" onClick={() => setPage('onboarding')}>🚀 Onboard New Host</button>
      </div></div>
    </div>
  );
}

/* ─── Hosts ─── */
function HostsPage({ hosts, setHosts }) {
  const [form, setForm] = useState({ name: '', ip: '', os: 'Ubuntu 22.04' });
  const [search, setSearch] = useState('');
  const [editId, setEditId] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [agentStatus, setAgentStatus] = useState({});

  const nextId = hosts.length > 0 ? Math.max(...hosts.map(h => h.id)) + 1 : 1;

  const checkAgent = async (ip) => {
    try {
      const r = await fetch(`${API}/api/agent/${ip}/health`);
      const d = await r.json();
      setAgentStatus(prev => ({...prev, [ip]: { online: true, state: d.state }}));
    } catch {
      setAgentStatus(prev => ({...prev, [ip]: { online: false }}));
    }
  };

  useEffect(() => { hosts.forEach(h => checkAgent(h.ip)); }, [hosts]);

  const addHost = () => {
    if (!form.name || !form.ip) return alert('Name and IP are required');
    fetch(`${API}/api/hosts/`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...form, id: nextId }) })
      .then(r => r.json()).then(h => { setHosts(prev => [...prev, h]); setForm({ name: '', ip: '', os: 'Ubuntu 22.04' }); });
  };
  const deleteHost = id => { if (!window.confirm('Delete this host?')) return; fetch(`${API}/api/hosts/${id}`, { method: 'DELETE' }).then(() => setHosts(prev => prev.filter(h => h.id !== id))); };
  const startEdit = h => { setEditId(h.id); setEditForm({ name: h.name, ip: h.ip, os: h.os }); };
  const saveEdit = id => {
    fetch(`${API}/api/hosts/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...editForm, id }) })
      .then(r => r.json()).then(u => { setHosts(prev => prev.map(h => h.id === id ? u : h)); setEditId(null); });
  };
  const filtered = hosts.filter(h => h.name.toLowerCase().includes(search.toLowerCase()) || h.ip.includes(search) || h.os.toLowerCase().includes(search.toLowerCase()));

  return (
    <div>
      <div className="card"><h3>Add New Host</h3>
        <div className="form-row">
          <input className="input" placeholder="Hostname" value={form.name} onChange={e => setForm(f => ({...f, name: e.target.value}))} />
          <input className="input" placeholder="IP Address" value={form.ip} onChange={e => setForm(f => ({...f, ip: e.target.value}))} />
          <select className="input" value={form.os} onChange={e => setForm(f => ({...f, os: e.target.value}))}>
            <option>Ubuntu 22.04</option><option>Ubuntu 24.04</option><option>Ubuntu 20.04</option><option>Debian 12</option><option>Debian 11</option><option>CentOS 9</option><option>RHEL 8</option><option>RHEL 9</option><option>Other</option>
          </select>
          <button className="btn btn-primary" onClick={addHost}>Add Host</button>
        </div>
      </div>
      <div className="card">
        <div className="card-header"><h3>Registered Hosts ({filtered.length})</h3><input className="input search-input" placeholder="Search hosts..." value={search} onChange={e => setSearch(e.target.value)} /></div>
        {filtered.length === 0 ? <p className="text-muted">No hosts found.</p> : (
          <table className="table"><thead><tr><th>ID</th><th>Hostname</th><th>IP</th><th>OS</th><th>Agent</th><th>Actions</th></tr></thead>
            <tbody>{filtered.map(h => (
              <tr key={h.id}>
                <td>{h.id}</td>
                <td>{editId===h.id ? <input className="input input-sm" value={editForm.name} onChange={e=>setEditForm(f=>({...f,name:e.target.value}))} /> : h.name}</td>
                <td>{editId===h.id ? <input className="input input-sm" value={editForm.ip} onChange={e=>setEditForm(f=>({...f,ip:e.target.value}))} /> : h.ip}</td>
                <td>{editId===h.id ? <input className="input input-sm" value={editForm.os} onChange={e=>setEditForm(f=>({...f,os:e.target.value}))} /> : h.os}</td>
                <td>{agentStatus[h.ip]?.online ? <span className="badge badge-success">Online{agentStatus[h.ip]?.state ? ` (${agentStatus[h.ip].state})` : ''}</span> : <span className="badge badge-danger">Offline</span>}</td>
                <td>{editId===h.id ? <><button className="btn btn-sm btn-success" onClick={()=>saveEdit(h.id)}>Save</button> <button className="btn btn-sm" onClick={()=>setEditId(null)}>Cancel</button></> : <><button className="btn btn-sm btn-primary" onClick={()=>startEdit(h)}>Edit</button> <button className="btn btn-sm btn-danger" onClick={()=>deleteHost(h.id)}>Del</button> <button className="btn btn-sm" onClick={()=>checkAgent(h.ip)}>Ping</button></>}</td>
              </tr>
            ))}</tbody></table>
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
      const r = await fetch(`${API}/api/agent/${selectedHost}/packages/upgradable`);
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
    if (!window.confirm(`${mode} server-side patching on ${selectedHost}?\n\nWorkflow: Server downloads .debs → pushes to agent → agent installs offline\n\nAuto-Snapshot: ${autoSnapshot}\nAuto-Rollback: ${autoRollback}\nPackages: ${selectedPkgs.length || 'ALL upgradable'}`)) return;
    setPatchLoading(true); setPatchResult(null); setPatchPhase('Starting...');
    try {
      const body = {
        packages: selectedPkgs,
        hold: holdPkgs.split(',').map(s => s.trim()).filter(Boolean),
        dry_run: dryRun,
        auto_snapshot: autoSnapshot,
        auto_rollback: autoRollback
      };
      setPatchPhase('Server downloading packages & patching agent...');
      const r = await fetch(`${API}/api/agent/${selectedHost}/patch/server-patch`, {
        method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body)
      });
      const d = await r.json();
      setPatchResult(d);
      setPatchPhase('');
    } catch (e) { setPatchResult({ error: e.message }); setPatchPhase(''); }
    setPatchLoading(false);
  };

  return (
    <div>
      <div className="card highlight-card">
        <h3>🔄 Patch Manager — Server Download → Push → Install</h3>
        <p>Server downloads packages from internet, pushes to agent, installs offline with snapshot protection. <strong>Agents don't need internet.</strong></p>
        <div className="workflow-steps">
          <div className="workflow-step"><span className="step-num">1</span> Select Host</div>
          <div className="workflow-arrow">→</div>
          <div className="workflow-step"><span className="step-num">2</span> Server Downloads .debs</div>
          <div className="workflow-arrow">→</div>
          <div className="workflow-step"><span className="step-num">3</span> Push to Agent</div>
          <div className="workflow-arrow">→</div>
          <div className="workflow-step"><span className="step-num">4</span> Offline Install + Snapshot</div>
        </div>
      </div>

      <div className="card">
        <h3>Select Host</h3>
        <div className="form-row">
          <select className="input" value={selectedHost} onChange={e => { setSelectedHost(e.target.value); setUpgradable([]); setPatchResult(null); }}>
            <option value="">-- Select Host --</option>
            {hosts.map(h => <option key={h.id} value={h.ip}>{h.name} ({h.ip})</option>)}
          </select>
          <button className="btn btn-primary" onClick={fetchUpgradable} disabled={loading}>{loading ? 'Checking...' : 'Check Updates'}</button>
        </div>
      </div>

      {upgradable.length > 0 && (
        <div className="card">
          <div className="card-header">
            <h3>Available Updates ({upgradable.length})</h3>
            <div className="btn-group">
              <button className="btn btn-sm btn-primary" onClick={selectAll}>Select All</button>
              <button className="btn btn-sm" onClick={selectNone}>Deselect All</button>
            </div>
          </div>
          <div className="package-list">
            <table className="table">
              <thead><tr><th style={{width:'40px'}}>✓</th><th>Package</th><th>Current Version</th><th>Available Version</th></tr></thead>
              <tbody>{upgradable.map((p, i) => (
                <tr key={i} className={selectedPkgs.includes(p.name) ? 'row-selected' : ''}>
                  <td><input type="checkbox" checked={selectedPkgs.includes(p.name)} onChange={() => togglePkg(p.name)} /></td>
                  <td><strong>{p.name}</strong></td>
                  <td><code>{p.current_version || '—'}</code></td>
                  <td><code className="text-success-inline">{p.available_version}</code></td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        </div>
      )}

      <div className="card">
        <h3>Patch Options</h3>
        <div className="options-grid">
          <label className="toggle-option"><input type="checkbox" checked={autoSnapshot} onChange={e => setAutoSnapshot(e.target.checked)} /> <span>📸 Auto-Snapshot before install</span></label>
          <label className="toggle-option"><input type="checkbox" checked={autoRollback} onChange={e => setAutoRollback(e.target.checked)} /> <span>⏪ Auto-Rollback on failure</span></label>
          <label className="toggle-option"><input type="checkbox" checked={dryRun} onChange={e => setDryRun(e.target.checked)} /> <span>🧪 Dry Run (show what would be downloaded)</span></label>
        </div>
        <div className="form-row" style={{marginTop:'12px'}}>
          <input className="input" placeholder="Hold packages (comma-separated, e.g. linux-kernel,grub)" value={holdPkgs} onChange={e => setHoldPkgs(e.target.value)} style={{flex:1}} />
        </div>
        <div style={{marginTop:'16px'}}>
          <button className="btn btn-lg btn-success" onClick={executePatch} disabled={patchLoading || !selectedHost}>
            {patchLoading ? '⏳ Patching...' : dryRun ? '🧪 Simulate (Dry Run)' : '🚀 Download & Patch'}
          </button>
          {patchPhase && <span style={{marginLeft:'16px', color:'#6b7280', fontStyle:'italic'}}>{patchPhase}</span>}
        </div>
      </div>

      {patchResult && (
        <div className={`card ${patchResult.success ? 'result-success' : 'result-failure'}`}>
          <h3>{patchResult.success ? '✅ Patch Successful' : '❌ Patch Failed'}</h3>

          {patchResult.dry_run && <p><span className="badge badge-info">DRY RUN</span> {patchResult.message || 'No changes were made.'}</p>}
          {patchResult.dry_run && patchResult.packages_to_download && (
            <div style={{margin:'8px 0'}}><strong>Packages that would be downloaded:</strong>
              <ul style={{marginTop:'4px'}}>{patchResult.packages_to_download.map((f, i) => <li key={i}><code>{f}</code></li>)}</ul>
            </div>
          )}

          {!patchResult.dry_run && patchResult.downloaded && patchResult.downloaded.length > 0 && (
            <p>📦 Downloaded: <strong>{patchResult.downloaded.length}</strong> packages on server</p>
          )}
          {!patchResult.dry_run && patchResult.download_failed && patchResult.download_failed.length > 0 && (
            <p className="text-danger">⚠️ Failed to download: {patchResult.download_failed.length} packages</p>
          )}
          {!patchResult.dry_run && patchResult.pushed > 0 && <p>📤 Pushed: <strong>{patchResult.pushed}</strong> .deb files to agent</p>}

          {patchResult.install_result && patchResult.install_result.snapshot && (
            <p>📸 Snapshot: <strong>{patchResult.install_result.snapshot.name}</strong> ({patchResult.install_result.snapshot.success ? 'created' : 'FAILED'})</p>
          )}
          {patchResult.install_result && patchResult.install_result.rollback && (
            <p>⏪ Rollback: <strong>{patchResult.install_result.rollback.success ? 'SUCCESS — System restored' : 'FAILED — Manual intervention needed'}</strong></p>
          )}

          {patchResult.error && <p className="text-danger">Error: {patchResult.error}</p>}
          {patchResult.message && !patchResult.dry_run && <p>{patchResult.message}</p>}

          <details><summary>Full Details</summary><pre className="code-block">{
            patchResult.install_result
              ? (patchResult.install_result.install_output || JSON.stringify(patchResult.install_result, null, 2))
              : JSON.stringify(patchResult, null, 2)
          }</pre></details>
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
    try {
      const r = await fetch(`${API}/api/agent/${selectedHost}/snapshot/list`);
      const d = await r.json();
      setSnapshots(d.snapshots || []);
    } catch { setSnapshots([]); }
    setLoading(false);
  }, [selectedHost]);

  useEffect(() => { fetchSnapshots(); }, [fetchSnapshots]);

  const createSnap = async () => {
    setActionResult(null);
    try {
      const r = await fetch(`${API}/api/agent/${selectedHost}/snapshot/create`, {
        method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ name: snapName || undefined })
      });
      const d = await r.json();
      setActionResult(d);
      setSnapName('');
      fetchSnapshots();
    } catch (e) { setActionResult({ error: e.message }); }
  };

  const rollbackSnap = async (name) => {
    if (!window.confirm(`ROLLBACK to snapshot "${name}" on ${selectedHost}?\n\nThis will revert packages to the snapshot state.`)) return;
    setActionResult(null);
    try {
      const r = await fetch(`${API}/api/agent/${selectedHost}/snapshot/rollback`, {
        method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ name })
      });
      const d = await r.json();
      setActionResult(d);
    } catch (e) { setActionResult({ error: e.message }); }
  };

  const deleteSnap = async (name) => {
    if (!window.confirm(`Delete snapshot "${name}"?`)) return;
    try {
      await fetch(`${API}/api/agent/${selectedHost}/snapshot/delete`, {
        method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ name })
      });
      fetchSnapshots();
    } catch {}
  };

  return (
    <div>
      <div className="card highlight-card">
        <h3>📸 Snapshot Manager</h3>
        <p>Create snapshots of installed packages before patching. Rollback to any snapshot if something goes wrong. <strong>Works offline — no internet needed.</strong></p>
      </div>

      <div className="card">
        <h3>Select Host</h3>
        <div className="form-row">
          <select className="input" value={selectedHost} onChange={e => setSelectedHost(e.target.value)}>
            <option value="">-- Select Host --</option>
            {hosts.map(h => <option key={h.id} value={h.ip}>{h.name} ({h.ip})</option>)}
          </select>
        </div>
      </div>

      {selectedHost && (
        <>
          <div className="card">
            <h3>Create New Snapshot</h3>
            <div className="form-row">
              <input className="input" placeholder="Snapshot name (optional, auto-generated)" value={snapName} onChange={e => setSnapName(e.target.value)} style={{flex:1}} />
              <button className="btn btn-success" onClick={createSnap}>📸 Create Snapshot</button>
            </div>
          </div>

          <div className="card">
            <div className="card-header"><h3>Snapshots ({snapshots.length})</h3><button className="btn btn-sm" onClick={fetchSnapshots}>{loading ? 'Loading...' : 'Refresh'}</button></div>
            {snapshots.length === 0 ? <p className="text-muted">No snapshots found on this host.</p> : (
              <table className="table">
                <thead><tr><th>Name</th><th>Created</th><th>Packages</th><th>Actions</th></tr></thead>
                <tbody>{snapshots.map((s, i) => (
                  <tr key={i}>
                    <td><strong>{s.name}</strong></td>
                    <td>{s.created || '—'}</td>
                    <td>{s.packages_count || '—'}</td>
                    <td>
                      <button className="btn btn-sm btn-warning" onClick={() => rollbackSnap(s.name)}>⏪ Rollback</button>{' '}
                      <button className="btn btn-sm btn-danger" onClick={() => deleteSnap(s.name)}>🗑️ Delete</button>
                    </td>
                  </tr>
                ))}</tbody>
              </table>
            )}
          </div>
        </>
      )}

      {actionResult && (
        <div className={`card ${actionResult.success ? 'result-success' : 'result-failure'}`}>
          <h3>{actionResult.success ? '✅ Operation Successful' : '❌ Operation Failed'}</h3>
          {actionResult.error && <p className="text-danger">{actionResult.error}</p>}
          <details><summary>Details</summary><pre className="code-block">{JSON.stringify(actionResult, null, 2)}</pre></details>
        </div>
      )}
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
  const [refreshing, setRefreshing] = useState(false);
  const [refreshMsg, setRefreshMsg] = useState('');

  const fetchData = async () => {
    if (!selectedHost) return alert('Select a host first');
    setLoading(true); setInstalled([]); setUpgradable([]);
    try {
      const [rI, rU] = await Promise.all([
        fetch(`${API}/api/agent/${selectedHost}/packages/installed`),
        fetch(`${API}/api/agent/${selectedHost}/packages/upgradable`)
      ]);
      const dI = await rI.json();
      const dU = await rU.json();
      setInstalled(dI.packages || []);
      setUpgradable(dU.packages || []);
    } catch (e) { alert('Could not reach agent: ' + e.message); }
    setLoading(false);
  };

  const refreshCache = async () => {
    if (!selectedHost) return alert('Select a host first');
    setRefreshing(true); setRefreshMsg('');
    try {
      const r = await fetch(`${API}/api/agent/${selectedHost}/packages/refresh`, { method: 'POST' });
      const d = await r.json();
      setRefreshMsg(d.success ? '✅ Apt cache refreshed! Click "Scan Packages" to see updates.' : '❌ Refresh failed (agent may have no internet)');
    } catch (e) { setRefreshMsg('❌ Could not reach agent: ' + e.message); }
    setRefreshing(false);
  };

  const upgMap = {};
  upgradable.forEach(p => { upgMap[p.name] = p; });
  const merged = installed.map(p => ({
    name: p.name,
    installed_version: p.version,
    available_version: upgMap[p.name]?.available_version || null,
    has_update: !!upgMap[p.name]
  }));

  const filtered = merged.filter(p => {
    if (view === 'upgradable' && !p.has_update) return false;
    if (view === 'uptodate' && p.has_update) return false;
    if (search && !p.name.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <div>
      <div className="card highlight-card">
        <h3>🔍 Package Comparison — Installed vs Available</h3>
        <p>Compare installed package versions with available updates side-by-side. <strong>Works in air-gapped environments</strong> (compares against local repo if no internet).</p>
      </div>

      <div className="card">
        <div className="form-row">
          <select className="input" value={selectedHost} onChange={e => setSelectedHost(e.target.value)}>
            <option value="">-- Select Host --</option>
            {hosts.map(h => <option key={h.id} value={h.ip}>{h.name} ({h.ip})</option>)}
          </select>
          <button className="btn btn-primary" onClick={fetchData} disabled={loading}>{loading ? 'Scanning...' : '🔍 Scan Packages'}</button>
          <button className="btn" onClick={refreshCache} disabled={refreshing} title="Run apt-get update on agent (requires agent internet)">{refreshing ? '⏳ Refreshing...' : '🔄 Refresh Apt Cache'}</button>
        </div>
        {refreshMsg && <p style={{marginTop:'8px', fontWeight:500}}>{refreshMsg}</p>}
      </div>

      {installed.length > 0 && (
        <>
          <div className="stats-grid">
            <div className="stat-card" onClick={() => setView('all')}><div className="stat-icon">📦</div><div className="stat-info"><span className="stat-number">{installed.length}</span><span className="stat-label">Installed</span></div></div>
            <div className="stat-card warning" onClick={() => setView('upgradable')}><div className="stat-icon">🔄</div><div className="stat-info"><span className="stat-number">{upgradable.length}</span><span className="stat-label">Updates Available</span></div></div>
            <div className="stat-card success" onClick={() => setView('uptodate')}><div className="stat-icon">✅</div><div className="stat-info"><span className="stat-number">{installed.length - upgradable.length}</span><span className="stat-label">Up-to-date</span></div></div>
          </div>

          <div className="card">
            <div className="card-header">
              <h3>Packages ({filtered.length}) — {view === 'all' ? 'All' : view === 'upgradable' ? 'Updates Available' : 'Up-to-date'}</h3>
              <input className="input search-input" placeholder="Search packages..." value={search} onChange={e => setSearch(e.target.value)} />
            </div>
            <div className="package-list">
              <table className="table">
                <thead><tr><th>Package</th><th>Installed Version</th><th>Available Version</th><th>Status</th></tr></thead>
                <tbody>{filtered.slice(0, 200).map((p, i) => (
                  <tr key={i} className={p.has_update ? 'row-update' : ''}>
                    <td><strong>{p.name}</strong></td>
                    <td><code>{p.installed_version}</code></td>
                    <td>{p.available_version ? <code className="text-success-inline">{p.available_version}</code> : <span className="text-muted">—</span>}</td>
                    <td>{p.has_update ? <span className="badge badge-warning">Update Available</span> : <span className="badge badge-success">Up-to-date</span>}</td>
                  </tr>
                ))}</tbody>
              </table>
              {filtered.length > 200 && <p className="text-muted">Showing first 200 of {filtered.length}. Use search to filter.</p>}
            </div>
          </div>
        </>
      )}
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
    try {
      const r = await fetch(`${API}/api/agent/${selectedHost}/offline/list`);
      const d = await r.json();
      setOfflineDebs(d.debs || []);
    } catch { setOfflineDebs([]); }
    setLoading(false);
  }, [selectedHost]);

  useEffect(() => { fetchDebs(); }, [fetchDebs]);

  const toggleFile = (name) => {
    setSelectedFiles(prev => prev.includes(name) ? prev.filter(f => f !== name) : [...prev, name]);
  };

  const installOffline = async () => {
    if (!selectedHost) return;
    if (!window.confirm(`Install ${selectedFiles.length || 'ALL'} .deb files on ${selectedHost}?\n\nAuto-Snapshot: ${autoSnapshot}\nAuto-Rollback: ${autoRollback}`)) return;
    setInstallResult(null); setLoading(true);
    try {
      const r = await fetch(`${API}/api/agent/${selectedHost}/offline/install`, {
        method: 'POST', headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ files: selectedFiles.length > 0 ? selectedFiles : [], auto_snapshot: autoSnapshot, auto_rollback: autoRollback })
      });
      const d = await r.json();
      setInstallResult(d);
      fetchDebs();
    } catch (e) { setInstallResult({ error: e.message }); }
    setLoading(false);
  };

  const clearDebs = async () => {
    if (!window.confirm('Remove all uploaded .deb files from this host?')) return;
    await fetch(`${API}/api/agent/${selectedHost}/offline/clear`, { method: 'POST' });
    fetchDebs();
  };

  return (
    <div>
      <div className="card highlight-card">
        <h3>📦 Offline Patching — No Internet Required</h3>
        <p>For air-gapped / isolated environments. Copy <code>.deb</code> files to the agent's offline directory via USB/SCP, then install with snapshot protection.</p>
      </div>

      <div className="card">
        <h3>Select Host</h3>
        <select className="input" value={selectedHost} onChange={e => setSelectedHost(e.target.value)}>
          <option value="">-- Select Host --</option>
          {hosts.map(h => <option key={h.id} value={h.ip}>{h.name} ({h.ip})</option>)}
        </select>
      </div>

      {selectedHost && (
        <>
          <div className="card">
            <h3>How to Upload .deb Files (Offline)</h3>
            <pre className="code-block">{`# Copy .deb files to the agent's offline directory:
scp *.deb user@${selectedHost}:/var/lib/patch-agent/offline-debs/

# Or use USB / shared drive:
sudo cp /mnt/usb/*.deb /var/lib/patch-agent/offline-debs/

# Then click "Refresh" below to see them.`}</pre>
          </div>

          <div className="card">
            <div className="card-header">
              <h3>Available .deb Files ({offlineDebs.length})</h3>
              <div className="btn-group">
                <button className="btn btn-sm" onClick={fetchDebs}>{loading ? 'Loading...' : 'Refresh'}</button>
                <button className="btn btn-sm btn-danger" onClick={clearDebs}>Clear All</button>
              </div>
            </div>
            {offlineDebs.length === 0 ? <p className="text-muted">No .deb files found in offline directory.</p> : (
              <table className="table">
                <thead><tr><th style={{width:'40px'}}>✓</th><th>Filename</th><th>Size</th></tr></thead>
                <tbody>{offlineDebs.map((d, i) => (
                  <tr key={i} className={selectedFiles.includes(d.name) ? 'row-selected' : ''}>
                    <td><input type="checkbox" checked={selectedFiles.includes(d.name)} onChange={() => toggleFile(d.name)} /></td>
                    <td><strong>{d.name}</strong></td>
                    <td>{d.size_mb} MB</td>
                  </tr>
                ))}</tbody>
              </table>
            )}
          </div>

          <div className="card">
            <h3>Install Options</h3>
            <div className="options-grid">
              <label className="toggle-option"><input type="checkbox" checked={autoSnapshot} onChange={e => setAutoSnapshot(e.target.checked)} /> <span>📸 Auto-Snapshot before install</span></label>
              <label className="toggle-option"><input type="checkbox" checked={autoRollback} onChange={e => setAutoRollback(e.target.checked)} /> <span>⏪ Auto-Rollback on failure</span></label>
            </div>
            <div style={{marginTop:'16px'}}>
              <button className="btn btn-lg btn-success" onClick={installOffline} disabled={loading || offlineDebs.length === 0}>
                {loading ? '⏳ Installing...' : `📦 Install ${selectedFiles.length || 'All'} .deb File(s)`}
              </button>
            </div>
          </div>
        </>
      )}

      {installResult && (
        <div className={`card ${installResult.success ? 'result-success' : 'result-failure'}`}>
          <h3>{installResult.success ? '✅ Installation Successful' : '❌ Installation Failed'}</h3>
          {installResult.snapshot && <p>📸 Snapshot: <strong>{installResult.snapshot.name}</strong></p>}
          {installResult.rollback && <p>⏪ Rollback: <strong>{installResult.rollback.success ? 'System restored to previous state' : 'FAILED'}</strong></p>}
          {installResult.files && <p>Files: {installResult.files.join(', ')}</p>}
          {installResult.error && <p className="text-danger">{installResult.error}</p>}
          <details><summary>Full Output</summary><pre className="code-block">{installResult.install_output || JSON.stringify(installResult, null, 2)}</pre></details>
        </div>
      )}
    </div>
  );
}

/* ─── Jobs ─── */
function JobsPage({ jobs, setJobs }) {
  const [form, setForm] = useState({ name: '', status: 'pending', scheduled_time: '' });
  const [search, setSearch] = useState('');
  const nextId = jobs.length > 0 ? Math.max(...jobs.map(j => j.id)) + 1 : 1;
  const addJob = () => {
    if (!form.name) return alert('Job name is required');
    fetch(`${API}/api/jobs/`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({...form, id: nextId}) })
      .then(r => r.json()).then(j => { setJobs(prev => [...prev, j]); setForm({name:'',status:'pending',scheduled_time:''}); });
  };
  const deleteJob = id => { if (!window.confirm('Delete?')) return; fetch(`${API}/api/jobs/${id}`,{method:'DELETE'}).then(()=>setJobs(prev=>prev.filter(j=>j.id!==id))); };
  const filtered = jobs.filter(j => j.name.toLowerCase().includes(search.toLowerCase()) || j.status.toLowerCase().includes(search.toLowerCase()));
  return (
    <div>
      <div className="card"><h3>Create Job</h3>
        <div className="form-row">
          <input className="input" placeholder="Job Name" value={form.name} onChange={e=>setForm(f=>({...f,name:e.target.value}))} />
          <select className="input" value={form.status} onChange={e=>setForm(f=>({...f,status:e.target.value}))}><option value="pending">Pending</option><option value="scheduled">Scheduled</option><option value="running">Running</option><option value="completed">Completed</option><option value="failed">Failed</option></select>
          <input className="input" type="datetime-local" value={form.scheduled_time} onChange={e=>setForm(f=>({...f,scheduled_time:e.target.value}))} />
          <button className="btn btn-primary" onClick={addJob}>Create</button>
        </div>
      </div>
      <div className="card">
        <div className="card-header"><h3>Jobs ({filtered.length})</h3><input className="input search-input" placeholder="Search..." value={search} onChange={e=>setSearch(e.target.value)} /></div>
        {filtered.length===0 ? <p className="text-muted">No jobs.</p> : <table className="table"><thead><tr><th>ID</th><th>Name</th><th>Status</th><th>Scheduled</th><th>Actions</th></tr></thead><tbody>{filtered.map(j=><tr key={j.id}><td>{j.id}</td><td>{j.name}</td><td><span className={`badge badge-${j.status==='completed'||j.status==='success'?'success':j.status==='running'?'warning':j.status==='failed'?'danger':'info'}`}>{j.status}</span></td><td>{j.scheduled_time||'—'}</td><td><button className="btn btn-sm btn-danger" onClick={()=>deleteJob(j.id)}>Del</button></td></tr>)}</tbody></table>}
      </div>
    </div>
  );
}

/* ─── Onboarding ─── */
function OnboardingPage() {
  const [masterIp, setMasterIp] = useState('');
  const [copied, setCopied] = useState(false);
  useEffect(() => { setMasterIp(window.location.hostname); }, []);
  const installCmd = `curl -sS http://${masterIp||'<master-ip>'}:3000/download/install.sh | sudo bash -s -- ${masterIp||'<master-ip>'}`;
  const copyCmd = () => { navigator.clipboard.writeText(installCmd).then(() => { setCopied(true); setTimeout(()=>setCopied(false),2000); }); };

  return (
    <div>
      <div className="card highlight-card">
        <h3>🚀 Quick Install (One Command)</h3>
        <p>Run this on any <strong>Debian/Ubuntu</strong> machine:</p>
        <div className="install-master-ip">
          <label>Master IP: </label>
          <input type="text" value={masterIp} onChange={e=>setMasterIp(e.target.value)} placeholder="e.g. 192.168.1.100" style={{width:'200px',marginLeft:'8px'}} />
        </div>
        <div className="install-cmd-box">
          <pre className="code-block install-code">{installCmd}</pre>
          <button className="btn btn-primary copy-btn" onClick={copyCmd}>{copied ? '✅ Copied!' : '📋 Copy'}</button>
        </div>
        <p className="hint-text">Downloads, installs, configures, and starts the agent. Host appears in dashboard within 60 seconds.</p>
      </div>
      <div className="card"><h3>📥 Manual Install</h3>
        <div style={{display:'flex',gap:'12px',marginBottom:'16px'}}>
          <a href="/download/agent-latest.deb" download><button className="btn btn-success">Download .deb</button></a>
          <a href="/download/install.sh" download><button className="btn btn-secondary">Download Script</button></a>
        </div>
        <pre className="code-block">{`scp patch-agent.deb user@target:/tmp/
ssh user@target "sudo dpkg -i /tmp/patch-agent.deb"
# Then set CONTROLLER_URL and restart agent`}</pre>
      </div>
      <div className="card"><h3>✅ Verify</h3><pre className="code-block">{`sudo systemctl status patch-agent
sudo journalctl -u patch-agent -f`}</pre></div>
    </div>
  );
}

/* ─── Settings ─── */
function SettingsPage({ health, hosts, jobs }) {
  const masterIp = window.location.hostname;
  const masterPort = window.location.port || '3000';
  const backendUrl = `http://${masterIp}:8000`;
  const frontendUrl = `http://${masterIp}:${masterPort}`;
  return (
    <div>
      <div className="card"><h3>🖥️ System Information</h3>
        <table className="table"><tbody>
          <tr><td><strong>Backend Status</strong></td><td>{health ? <span className="badge badge-success">Online</span> : <span className="badge badge-danger">Offline</span>}</td></tr>
          <tr><td><strong>Master IP</strong></td><td><code>{masterIp}</code></td></tr>
          <tr><td><strong>Backend URL</strong></td><td><a href={backendUrl+'/api/health'} target="_blank" rel="noreferrer">{backendUrl}</a></td></tr>
          <tr><td><strong>Frontend URL</strong></td><td><a href={frontendUrl} target="_blank" rel="noreferrer">{frontendUrl}</a></td></tr>
          <tr><td><strong>Total Hosts</strong></td><td>{hosts.length}</td></tr>
          <tr><td><strong>Total Jobs</strong></td><td>{jobs.length}</td></tr>
          <tr><td><strong>Agent Port</strong></td><td>8080 (target machines)</td></tr>
          <tr><td><strong>Metrics Port</strong></td><td>9100 (Prometheus)</td></tr>
        </tbody></table>
      </div>
      <div className="card"><h3>⚡ Quick Agent Install</h3><pre className="code-block">{`curl -sS ${frontendUrl}/download/install.sh | sudo bash -s -- ${masterIp}`}</pre></div>
      <div className="card"><h3>🔗 API Endpoints</h3>
        <table className="table"><thead><tr><th>Endpoint</th><th>Description</th></tr></thead><tbody>
          <tr><td><code>GET /api/health</code></td><td>Health check</td></tr>
          <tr><td><code>GET /api/hosts/</code></td><td>List hosts</td></tr>
          <tr><td><code>GET /api/jobs/</code></td><td>List jobs</td></tr>
          <tr><td><code>POST /api/register</code></td><td>Agent registration</td></tr>
          <tr><td><code>POST /api/heartbeat</code></td><td>Agent heartbeat</td></tr>
          <tr><td><code>GET /api/agent/{'{ip}'}/packages/installed</code></td><td>Installed packages</td></tr>
          <tr><td><code>GET /api/agent/{'{ip}'}/packages/upgradable</code></td><td>Available updates</td></tr>
          <tr><td><code>POST /api/agent/{'{ip}'}/patch/execute</code></td><td>Execute patch with snapshot</td></tr>
          <tr><td><code>GET /api/agent/{'{ip}'}/snapshot/list</code></td><td>List snapshots</td></tr>
          <tr><td><code>POST /api/agent/{'{ip}'}/snapshot/create</code></td><td>Create snapshot</td></tr>
          <tr><td><code>POST /api/agent/{'{ip}'}/snapshot/rollback</code></td><td>Rollback to snapshot</td></tr>
          <tr><td><code>POST /api/agent/{'{ip}'}/offline/install</code></td><td>Install offline .debs</td></tr>
        </tbody></table>
      </div>
      <div className="card"><h3>🐳 Docker Commands</h3><pre className="code-block">{`docker compose build --no-cache
docker compose up -d
docker compose logs -f backend
docker compose down`}</pre></div>
    </div>
  );
}

export default App;
