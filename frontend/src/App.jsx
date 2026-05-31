// Mail module placeholder - renderMail added above
import React, { useEffect, useState, useCallback, useRef } from 'react';
import { createRoot } from 'react-dom/client';
import ace from 'ace-builds/src-noconflict/ace';
import 'ace-builds/src-noconflict/ext-language_tools';
import 'ace-builds/src-noconflict/ext-searchbox';
import 'ace-builds/src-noconflict/mode-css';
import 'ace-builds/src-noconflict/mode-html';
import 'ace-builds/src-noconflict/mode-javascript';
import 'ace-builds/src-noconflict/mode-json';
import 'ace-builds/src-noconflict/mode-php';
import 'ace-builds/src-noconflict/mode-text';
import 'ace-builds/src-noconflict/mode-yaml';
import 'ace-builds/src-noconflict/theme-textmate';
import { Archive, ArrowRightLeft, Bell, Check, Cloud, Clock, Code, Code2, Copy, Cpu, Database, FileText, FolderOpen, Globe, HardDrive, Hexagon, History, Home, Image, KeyRound, Link, Lock, LogIn, LogOut, Mail, Inbox, Palette, Send, Settings as SettingsIcon, Spam, MemoryStick, Menu, MoveRight, Network, Package, Server, Shield, ShieldCheck, Terminal as TerminalIcon, Trash2, Users, Unlock, X, RefreshCw, Plus, Download, Upload, Play, Square, RotateCcw, AlertCircle, Activity, ToggleLeft, ToggleRight, Container, Search, Eye, Edit, Save, ServerCog, AlertTriangle, CheckCircle, XCircle, Wrench, Box } from 'lucide-react';
import { Terminal } from './components/Terminal';
import { Logs } from './components/Logs';
import './style.css';
import './cron.css';
import './brand.css';
import './file-manager.css';

// New page component imports
// These components can be used to replace inline render functions
// See pages/index.js for the full list of available components
// import { Dashboard, Docker, FTP, PHPVersions, NodeJS, GoProject, PythonProject, NginxProxy, WebServer, MailServer, CronJobs, Monitor, Logs, Settings, Update, Backup } from './pages';

// Common components
// import { Modal, Table, Tabs, EmptyState } from './components';

// Hooks
// import { useApi } from './hooks';

const API = import.meta.env.VITE_API_URL || '/api';
const SERVICE_NAMES = ['bpanel-api', 'nginx', 'php8.3-fpm', 'php8.4-fpm', 'mariadb', 'redis-server'];

function editorParamsFromLocation() {
  const params = new URLSearchParams(window.location.search);
  if (params.get('view') !== 'editor') return null;
  const websiteId = params.get('website_id');
  const path = params.get('path') || 'public_html/index.html';
  if (!websiteId) return null;
  return { websiteId: String(websiteId), path };
}

function aceModeName(mode) {
  if (mode === 'PHP') return 'php';
  if (mode === 'JavaScript') return 'javascript';
  if (mode === 'CSS') return 'css';
  if (mode === 'HTML') return 'html';
  if (mode === 'JSON') return 'json';
  if (mode === 'YAML') return 'yaml';
  if (mode === 'Config') return 'ini'; // .env, .htaccess, .ini, .conf -> Ace's ini mode
  return 'text';
}

function CodeEditor({ value, mode, disabled, onChange, onCursorChange }) {
  const hostRef = useRef(null);
  const editorRef = useRef(null);
  const suppressChangeRef = useRef(false);
  const onChangeRef = useRef(onChange);
  const onCursorChangeRef = useRef(onCursorChange);

  useEffect(() => { onChangeRef.current = onChange; }, [onChange]);
  useEffect(() => { onCursorChangeRef.current = onCursorChange; }, [onCursorChange]);

  useEffect(() => {
    if (!hostRef.current) return undefined;
    const editor = ace.edit(hostRef.current, {
      mode: `ace/mode/${aceModeName(mode)}`,
      theme: 'ace/theme/textmate',
      value: value || '',
      readOnly: !!disabled,
      showPrintMargin: false,
      highlightActiveLine: true,
      fontSize: 13,
      tabSize: 2,
      useSoftTabs: true,
      wrap: false,
    });

    editor.setOptions({
      enableBasicAutocompletion: true,
      enableLiveAutocompletion: true,
      enableMatchBrackets: true,
      enableSnippets: false,
      fontFamily: "Consolas, 'SFMono-Regular', 'Liberation Mono', Menlo, monospace",
    });
    editor.session.setUseWorker(false);
    editor.session.setNewLineMode('unix');

    let destroyed = false;
    const reportCursor = () => {
      if (destroyed || !editorRef.current || !onCursorChangeRef.current) return;
      const pos = editorRef.current.getCursorPosition();
      onCursorChangeRef.current({ line: pos.row + 1, column: pos.column + 1 });
    };
    const handleChange = () => {
      if (destroyed || !editorRef.current) return;
      if (!suppressChangeRef.current) {
        if (onChangeRef.current) onChangeRef.current(editorRef.current.getValue());
      }
      // Only report cursor on explicit cursor moves, not on every content change
    };

    editor.session.on('change', handleChange);
    editor.selection.on('changeCursor', reportCursor);
    editorRef.current = editor;
    reportCursor();

    return () => {
      destroyed = true;
      editor.session.off('change', handleChange);
      editor.selection.off('changeCursor', reportCursor);
      editor.destroy();
      editorRef.current = null;
      if (hostRef.current) hostRef.current.textContent = '';
    };
  }, []);

  useEffect(() => {
    const editor = editorRef.current;
    if (!editor) return;
    const nextValue = value || '';
    if (nextValue === editor.getValue()) return;
    const cursor = editor.getCursorPosition();
    suppressChangeRef.current = true;
    editor.setValue(nextValue, -1);
    const newRow = Math.max(0, Math.min(cursor.row, editor.session.getLength() - 1));
    editor.moveCursorTo(newRow, cursor.column);
    suppressChangeRef.current = false;
  }, [value]);

  useEffect(() => {
    const editor = editorRef.current;
    if (!editor) return;
    editor.session.setMode(`ace/mode/${aceModeName(mode)}`);
  }, [mode]);

  useEffect(() => {
    const editor = editorRef.current;
    if (!editor) return;
    editor.setReadOnly(!!disabled);
  }, [disabled]);

  return <div className="code-editor-host" ref={hostRef}></div>;
}

function App() {
  // Auth is now cookie-based (HttpOnly bpanel_session). The SPA does not see
  // the JWT at all. We track only whether the user is authenticated in memory.
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const [bootstrapping, setBootstrapping] = useState(true);
  const [standaloneEditor] = useState(() => editorParamsFromLocation());
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [needsTwoFactor, setNeedsTwoFactor] = useState(false);
  const [page, setPage] = useState('dashboard');
  const [domain, setDomain] = useState('');
  const [adminEmail, setAdminEmail] = useState('');
  const [wpAdminUser, setWpAdminUser] = useState('admin');
  const [wpAdminPassword, setWpAdminPassword] = useState('');
  const [phpVersion, setPhpVersion] = useState('8.3');
  const [siteType, setSiteType] = useState('wordpress');
  const [installSslAfterCreate, setInstallSslAfterCreate] = useState(false);
  const [installWordPress, setInstallWordPress] = useState(true);
  const [nginxCustomEditing, setNginxCustomEditing] = useState(null); // {id, domain, content}
  const [logViewer, setLogViewer] = useState(null); // {id, domain, kind, lines, path, content, exists}
  const [terminalViewer, setTerminalViewer] = useState(null); // {id, domain}
  const [websites, setWebsites] = useState([]);
  const [databases, setDatabases] = useState([]);
  const [newDatabase, setNewDatabase] = useState({ website_id: '', db_name: '' });
  const [users, setUsers] = useState([]);
  const [resourceUsage, setResourceUsage] = useState(null);
  const [serviceStates, setServiceStates] = useState({});
  const [backups, setBackups] = useState([]);
  const [userBackups, setUserBackups] = useState([]);
  const [restoreBackups, setRestoreBackups] = useState([]);
  const [restoreBackupDir, setRestoreBackupDir] = useState('');
  const [selectedBackupUserId, setSelectedBackupUserId] = useState('');
  const [backupSchedules, setBackupSchedules] = useState([]);
  const [newBackupSchedule, setNewBackupSchedule] = useState({ user_ids: [], all_users: false, schedule: '0 2 * * *', target_id: '', retention: 7 });
  const [sftpTargets, setSftpTargets] = useState([]);
  const [selectedSftpTargetId, setSelectedSftpTargetId] = useState('');
  const [newSftpTarget, setNewSftpTarget] = useState({ name: '', host: '', port: 22, username: '', password: '', private_key: '', remote_path: '/backups/bpanel' });
  const [selectedWebsiteId, setSelectedWebsiteId] = useState(() => standaloneEditor?.websiteId || '');
  const [cronSchedule, setCronSchedule] = useState('0 2 * * *');
  const [cronCommand, setCronCommand] = useState('wp cron event run --due-now --allow-root');
  // Cron jobs state
  const [cronJobs, setCronJobs] = useState([]);
  const [showCronModal, setShowCronModal] = useState(false);
  const [editingCron, setEditingCron] = useState(null);
  const [cronForm, setCronForm] = useState({ command: '', schedule: '', description: '' });
  const [selectedPreset, setSelectedPreset] = useState('');
  const [cronPresets, setCronPresets] = useState([]);
  const [scheduleTypes, setScheduleTypes] = useState({});
  const [cronPreview, setCronPreview] = useState({ expression: '', human_readable: '', next_runs: [] });
  const [cronMinute, setCronMinute] = useState('*');
  const [cronHour, setCronHour] = useState('*');
  const [cronDayOfMonth, setCronDayOfMonth] = useState('*');
  const [cronMonth, setCronMonth] = useState('*');
  const [cronDayOfWeek, setCronDayOfWeek] = useState('*');
  const [filePath, setFilePath] = useState(() => standaloneEditor?.path || 'public_html/index.html');
  const [fileListPath, setFileListPath] = useState('public_html');
  const [fileUploadDir, setFileUploadDir] = useState('public_html');
  const [files, setFiles] = useState([]);
  const [fileJobs, setFileJobs] = useState([]);
  const [fileContent, setFileContent] = useState('');
  const [selectedFilePaths, setSelectedFilePaths] = useState([]);
  const [archiveFormat, setArchiveFormat] = useState('zip');
  const [editorCursor, setEditorCursor] = useState({ line: 1, column: 1 });
  const [newUser, setNewUser] = useState({ username: '', email: '', password: '', role: 'end_user', website_limit: 5, storage_limit_mb: 1024 });
  const [phpConfig, setPhpConfig] = useState({ php_version: '8.3', display_errors: 'Off', max_execution_time: 300, max_input_time: 600, max_input_vars: 10000, memory_limit: '512M', post_max_size: '1024M', upload_max_filesize: '1024M' });
  const [firewallStatus, setFirewallStatus] = useState(null);
  const [firewallPort, setFirewallPort] = useState('80');
  const [firewallProtocol, setFirewallProtocol] = useState('tcp');
  const [firewallAllowIp, setFirewallAllowIp] = useState('');
  const [firewallAllowPort, setFirewallAllowPort] = useState('');
  const [firewallAllowProtocol, setFirewallAllowProtocol] = useState('tcp');
  const [firewallBlockIp, setFirewallBlockIp] = useState('');
  const [firewallBlockPort, setFirewallBlockPort] = useState('');
  const [firewallBlockProtocol, setFirewallBlockProtocol] = useState('tcp');
  const [firewallDeleteNumber, setFirewallDeleteNumber] = useState('');
  const [websitePhpVersions, setWebsitePhpVersions] = useState({});
  const [assignUserId, setAssignUserId] = useState('');
  const [assignWebsiteId, setAssignWebsiteId] = useState('');
  const [twoFactorStatus, setTwoFactorStatus] = useState(null);
  const [twoFactorSetup, setTwoFactorSetup] = useState(null);
  const [twoFactorCode, setTwoFactorCode] = useState('');
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState('');
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [panelSettings, setPanelSettings] = useState({ app_name: 'BPanel', panel_url: '', logo_url: '', favicon_url: '/favicon.png', ssl_enabled: false });
  const [panelSettingsForm, setPanelSettingsForm] = useState({ app_name: 'BPanel', panel_url: '' });
  const [panelLogoFile, setPanelLogoFile] = useState(null);
  const [panelFaviconFile, setPanelFaviconFile] = useState(null);
  const [panelSslEmail, setPanelSslEmail] = useState('');
  const [updatesStatus, setUpdatesStatus] = useState(null);
  const [osAutoUpdate, setOsAutoUpdate] = useState({ enabled: true, mode: 'security', auto_reboot: false });
  const [panelAutoUpdate, setPanelAutoUpdate] = useState({ enabled: true, time: '03:30' });
  // WordPress Toolkit state
  const [wpToolkitViewer, setWpToolkitViewer] = useState(null); // { id, domain }
  const [wpPlugins, setWpPlugins] = useState([]);
  const [wpThemes, setWpThemes] = useState([]);
  const [wpHealth, setWpHealth] = useState(null);
  const [wpStagingStatus, setWpStagingStatus] = useState(null);
  const [wpActiveTab, setWpActiveTab] = useState('plugins');
  // Monitor state
  const [monitorData, setMonitorData] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState(2000); // 2 seconds
  // PHP Management state
  const [phpVersions, setPhpVersions] = useState([]);
  const [phpAvailableVersions, setPhpAvailableVersions] = useState([]);
  const [selectedPhpVersion, setSelectedPhpVersion] = useState('8.3');
  const [phpExtensions, setPhpExtensions] = useState([]);
  const [phpConfig, setPhpConfig] = useState({ php_version: '8.3', display_errors: 'Off', max_execution_time: 300, max_input_time: 600, max_input_vars: 10000, memory_limit: '512M', post_max_size: '1024M', upload_max_filesize: '1024M', disable_functions: '', opcache_enable: true, opcache_memory: '128', opcache_max_files: 10000, session_save_path: '/var/lib/php/sessions', session_name: 'PHPSESSID' });
  const [phpInfo, setPhpInfo] = useState(null);
  const [phpSlowlog, setPhpSlowlog] = useState(null);
  const [phpFpmPools, setPhpFpmPools] = useState([]);
  const [phpActiveTab, setPhpActiveTab] = useState('versions');
  // FTP Manager state
  const [ftpUsers, setFtpUsers] = useState([]);
  const [ftpStatus, setFtpStatus] = useState(null);
  const [newFtpUser, setNewFtpUser] = useState({ username: '', website_id: '', auto_password: true, password: '' });
  // Mail state
  const [mailDomains, setMailDomains] = useState([]);
  const [selectedDomain, setSelectedDomain] = useState('');
  const [mailboxes, setMailboxes] = useState([]);
  const [selectedMailbox, setSelectedMailbox] = useState('');
  const [emails, setEmails] = useState([]);
  const [mailSettings, setMailSettings] = useState(null);
  const [mailActiveTab, setMailActiveTab] = useState('domains');
  const [mailFolder, setMailFolder] = useState('inbox');
  const [selectedEmail, setSelectedEmail] = useState(null);
  const [newMailDomain, setNewMailDomain] = useState({ domain: '', quota_gb: 10 });
  const [newMailbox, setNewMailbox] = useState({ username: '', password: '', quota_gb: 1 });
  // Python state
  const [pythonVersion, setPythonVersion] = useState(null);
  const [pythonVersions, setPythonVersions] = useState([]);
  const [venvs, setVenvs] = useState([]);
  const [selectedVenv, setSelectedVenv] = useState(null);
  const [venvPackages, setVenvPackages] = useState([]);
  const [pythonProcesses, setPythonProcesses] = useState([]);
  const [newVenvName, setNewVenvName] = useState('');
  const [newVenvVersion, setNewVenvVersion] = useState('');
  const [installPackageName, setInstallPackageName] = useState('');
  // Nginx Proxy state
  const [proxyConfigs, setProxyConfigs] = useState([]);
  const [proxyTemplates, setProxyTemplates] = useState([]);
  const [proxyStatus, setProxyStatus] = useState(null);
  const [showProxyModal, setShowProxyModal] = useState(false);
  const [editingProxy, setEditingProxy] = useState(null);
  const [newProxyConfig, setNewProxyConfig] = useState({
    domain: '',
    target_url: '',
    template: 'default',
    ssl_enabled: false,
    connect_timeout: 60,
    send_timeout: 60,
    read_timeout: 60,
  });
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [previewConfig, setPreviewConfig] = useState(null);
  // Node.js state
  const [nodeVersion, setNodeVersion] = useState(null);
  const [nodeVersions, setNodeVersions] = useState([]);
  const [pm2Processes, setPm2Processes] = useState([]);
  const [selectedPm2Process, setSelectedPm2Process] = useState(null);
  const [pm2Logs, setPm2Logs] = useState({ content: '', lines: 100 });
  const [pm2LogModal, setPm2LogModal] = useState(null);
  // WebServer state
  const [webEngines, setWebEngines] = useState([]);
  const [currentEngine, setCurrentEngine] = useState(null);
  const [webserverStatus, setWebserverStatus] = useState({});
  const [safetyCheck, setSafetyCheck] = useState(null);
  const [websitesWithEngines, setWebsitesWithEngines] = useState([]);
  // Docker state
  const [dockerStatus, setDockerStatus] = useState(null);
  const [containers, setContainers] = useState([]);
  const [images, setImages] = useState([]);
  const [selectedContainer, setSelectedContainer] = useState(null);
  const [containerLogs, setContainerLogs] = useState('');
  // Auto Update state
  const [updateStatus, setUpdateStatus] = useState(null);
  const [availableUpdate, setAvailableUpdate] = useState(null);
  const [updateBackups, setUpdateBackups] = useState([]);
  const [updateSettings, setUpdateSettings] = useState(null);
  const [updateLogs, setUpdateLogs] = useState([]);
  // Logs state
  const [activeLogTab, setActiveLogTab] = useState('panel');
  const [panelLogsContent, setPanelLogsContent] = useState('');
  const [websiteLogsContent, setWebsiteLogsContent] = useState('');
  const [selectedWebsiteLogId, setSelectedWebsiteLogId] = useState(null);
  const [selectedLogType, setSelectedLogType] = useState('access');
  const [auditLogs, setAuditLogs] = useState([]);
  const [auditStats, setAuditStats] = useState(null);
  const [sshLogs, setSshLogs] = useState('');
  const [sshStats, setSshStats] = useState(null);
  const [softLogs, setSoftLogs] = useState('');
  const [softLogType, setSoftLogType] = useState('updates');
  const [selectedService, setSelectedService] = useState('nginx');
  const [logLines, setLogLines] = useState(100);
  const [logSearch, setLogSearch] = useState('');
  const [logLevel, setLogLevel] = useState('all');
  const [logAutoRefresh, setLogAutoRefresh] = useState(false);
  // Backup Enhanced state
  const [backupJobs, setBackupJobs] = useState([]);
  const [backupHistory, setBackupHistory] = useState([]);
  const [storageConfigs, setStorageConfigs] = useState([]);
  const [selectedBackupJob, setSelectedBackupJob] = useState(null);
  const [excludePatterns, setExcludePatterns] = useState([
    { pattern: "node_modules/*", description: "Node.js dependencies" },
    { pattern: ".git/*", description: "Git repository" },
    { pattern: "*.log", description: "Log files" },
    { pattern: "tmp/*", description: "Temporary files" },
    { pattern: "cache/*", description: "Cache files" },
    { pattern: "__pycache__/*", description: "Python cache" },
    { pattern: ".DS_Store", description: "macOS system files" },
    { pattern: "Thumbs.db", description: "Windows system files" },
    { pattern: "*.bak", description: "Backup files" },
    { pattern: "*.swp", description: "Vim swap files" },
  ]);
  const [backupActiveTab, setBackupActiveTab] = useState('jobs');
  const [showBackupJobModal, setShowBackupJobModal] = useState(false);
  const [editingBackupJob, setEditingBackupJob] = useState(null);
  const [showStorageModal, setShowStorageModal] = useState(false);
  const [storageModalType, setStorageModalType] = useState(null);
  const noticeTimer = useRef(null);

  // Auto-dismiss notices after 6 seconds
  useEffect(() => {
    if (notice) {
      if (noticeTimer.current) clearTimeout(noticeTimer.current);
      noticeTimer.current = setTimeout(() => setNotice(''), 6000);
    }
    return () => { if (noticeTimer.current) clearTimeout(noticeTimer.current); };
  }, [notice]);

  function readCookie(name) {
    const match = document.cookie.match(new RegExp('(?:^|; )' + name.replace(/[$()*+./?[\\\]^{|}]/g, '\\$&') + '=([^;]*)'));
    return match ? decodeURIComponent(match[1]) : '';
  }

  function clearSession(message = 'Your session expired. Please log in again.') {
    // Old localStorage token from a previous deploy: nuke it for safety.
    try { localStorage.removeItem('token'); } catch {}
    setIsAuthenticated(false);
    setCurrentUser(null);
    setNeedsTwoFactor(false);
    setOtpCode('');
    setWebsites([]);
    setDatabases([]);
    setUsers([]);
    setResourceUsage(null);
    setServiceStates({});
    setBackups([]);
    setUserBackups([]);
    setRestoreBackups([]);
    setRestoreBackupDir('');
    setSelectedBackupUserId('');
    setBackupSchedules([]);
    setSftpTargets([]);
    setSelectedSftpTargetId('');
    setTwoFactorStatus(null);
    setTwoFactorSetup(null);
    setTwoFactorCode('');
    setUpdatesStatus(null);
    setLogViewer(null);
    setSelectedWebsiteId('');
    setMobileMenuOpen(false);
    setPage('dashboard');
    setError('');
    setNotice(message);
  }

  function handleAuthExpired(status, detail = '') {
    if (status === 401 || detail === 'Could not validate credentials' || detail === 'Not authenticated') {
      clearSession();
      return true;
    }
    return false;
  }

  async function request(path, options = {}, label = '') {
    try {
      setError('');
      if (label) setLoading(label);
      const method = (options.method || 'GET').toUpperCase();
      const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData;
      const headers = isFormData ? { ...(options.headers || {}) } : {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      };
      // CSRF: echo the bpanel_csrf cookie back in a header for mutating
      // requests. The backend rejects mismatches when the request was
      // authenticated via cookie.
      if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
        const csrf = readCookie('bpanel_csrf');
        if (csrf) headers['X-CSRF-Token'] = csrf;
      }
      const res = await fetch(`${API}${path}`, {
        ...options,
        credentials: 'include',
        headers,
      });
      const text = await res.text();
      let data;
      try { data = text ? JSON.parse(text) : {}; } catch { data = { detail: text || `HTTP ${res.status}` }; }
      if (!res.ok && handleAuthExpired(res.status, data.detail)) return null;
      if (!res.ok) setError(data.detail || `Request failed with status ${res.status}`);
      if (res.ok && data?.message) setNotice(data.message);
      return res.ok ? data : null;
    } catch (err) {
      setError(`Cannot connect to the ${panelSettings.app_name || 'BPanel'} API at ${API}. Check bpanel-api and the panel port.`);
      return null;
    } finally {
      if (label) setLoading('');
    }
  }

  async function login() {
    try {
      setError('');
      setLoading('Logging in...');
      const body = new URLSearchParams({ username, password });
      if (needsTwoFactor || otpCode) body.set('otp', otpCode);
      const res = await fetch(`${API}/auth/login`, {
        method: 'POST',
        body,
        credentials: 'include',
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok && data.requires_2fa) {
        setNeedsTwoFactor(true);
        setNotice('Enter your authentication code.');
      } else if (res.ok && data.access_token) {
        // Don't keep the token anywhere: the HttpOnly cookie just got set by
        // the response. JS code MUST NOT touch the JWT.
        setIsAuthenticated(true);
        setNeedsTwoFactor(false);
        setOtpCode('');
        setNotice('Login successful.');
        await loadCurrentUser();
      } else {
        setError(data.detail || `Login failed with status ${res.status}`);
      }
    } catch (err) {
      setError(`Cannot connect to the ${panelSettings.app_name || 'BPanel'} API at ${API}. Check bpanel-api and the panel port.`);
    } finally {
      setLoading('');
    }
  }

  async function logout() {
    try {
      // Best-effort server logout: clears cookies and bumps token_version.
      await fetch(`${API}/auth/logout`, {
        method: 'POST',
        credentials: 'include',
        headers: (() => {
          const csrf = readCookie('bpanel_csrf');
          return csrf ? { 'X-CSRF-Token': csrf } : {};
        })(),
      });
    } catch {}
    clearSession('Logged out.');
  }

  async function loadCurrentUser() {
    try {
      const res = await fetch(`${API}/users/me`, { credentials: 'include' });
      if (!res.ok) {
        if (res.status === 401) clearSession('Session expired.');
        return;
      }
      const data = await res.json();
      setCurrentUser(data);
      setIsAuthenticated(true);
    } catch {
      setCurrentUser(null);
    }
  }

  async function loadPanelSettings() {
    try {
      const res = await fetch(`${API}/panel-settings/public`, { credentials: 'include' });
      if (!res.ok) return null;
      const data = await res.json();
      const panelUrl = data.panel_url || `${window.location.protocol}//${window.location.host}`;
      setPanelSettings(data);
      setPanelSettingsForm({ app_name: data.app_name || 'BPanel', panel_url: panelUrl });
      return data;
    } catch {
      return null;
    }
  }

  async function savePanelSettings() {
    const data = await request('/panel-settings', {
      method: 'PATCH',
      body: JSON.stringify(panelSettingsForm),
    }, 'Saving panel settings...');
    if (data) {
      setPanelSettings(data);
      setPanelSettingsForm({ app_name: data.app_name || 'BPanel', panel_url: data.panel_url || `${window.location.protocol}//${window.location.host}` });
      setNotice('Panel settings updated. The panel may restart if the URL changed.');
    }
  }

  async function uploadPanelAsset(kind) {
    const file = kind === 'logo' ? panelLogoFile : panelFaviconFile;
    if (!file) return;
    const body = new FormData();
    body.append('file', file);
    const data = await request(`/panel-settings/${kind}`, { method: 'POST', body }, `Uploading ${kind}...`);
    if (data) {
      setPanelSettings(data);
      setPanelSettingsForm({ app_name: data.app_name || 'BPanel', panel_url: data.panel_url || `${window.location.protocol}//${window.location.host}` });
      if (kind === 'logo') setPanelLogoFile(null);
      if (kind === 'favicon') setPanelFaviconFile(null);
    }
  }

  async function installPanelSsl() {
    const data = await request('/panel-settings/ssl', {
      method: 'POST',
      body: JSON.stringify({ panel_url: panelSettingsForm.panel_url, email: panelSslEmail }),
    }, 'Installing panel SSL...');
    if (data) {
      setPanelSettings(data);
      setPanelSettingsForm({ app_name: data.app_name || 'BPanel', panel_url: data.panel_url || `${window.location.protocol}//${window.location.host}` });
      setNotice(data.message || 'Panel SSL installed. The panel may restart in a moment.');
    }
  }

  function brandInitials(value = panelSettings.app_name) {
    const words = String(value || 'BPanel').trim().split(/\s+/).filter(Boolean);
    const initials = words.length > 1 ? `${words[0][0]}${words[1][0]}` : words[0]?.slice(0, 2);
    return (initials || 'BP').toUpperCase();
  }

  function renderBrandMark(extraClass = '') {
    const classes = ['brand-mark', panelSettings.logo_url ? 'has-logo' : '', extraClass].filter(Boolean).join(' ');
    return <span className={classes}>{panelSettings.logo_url ? <img src={panelSettings.logo_url} alt="" /> : brandInitials()}</span>;
  }

  // Bootstrap: try to restore session from the HttpOnly cookie (set previously
  // and still valid). If /users/me returns 200 we are authenticated.
  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API}/users/me`, { credentials: 'include' });
        if (res.ok) {
          const data = await res.json();
          setCurrentUser(data);
          setIsAuthenticated(true);
        }
      } catch {}
      finally { setBootstrapping(false); }
    })();
  }, []);

  useEffect(() => { loadPanelSettings(); }, []);

  useEffect(() => {
    const appName = panelSettings.app_name || 'BPanel';
    document.title = appName;
    let link = document.querySelector('link[rel="icon"]');
    if (!link) {
      link = document.createElement('link');
      link.rel = 'icon';
      document.head.appendChild(link);
    }
    link.href = panelSettings.favicon_url || '/favicon.png';
  }, [panelSettings]);

  useEffect(() => {
    if (!panelSslEmail && currentUser?.email) setPanelSslEmail(currentUser.email);
  }, [currentUser?.email, panelSslEmail]);

  async function refreshAll() {
    await loadCurrentUser();
    const siteData = await request('/websites');
    if (siteData) {
      setWebsites(siteData);
      if (!selectedWebsiteId && siteData[0]) setSelectedWebsiteId(String(siteData[0].id));
      if (!newDatabase.website_id && siteData[0]) setNewDatabase(prev => ({ ...prev, website_id: String(siteData[0].id) }));
    }
    const dbData = await request('/databases');
    if (dbData) setDatabases(dbData);
  }

  async function loadUsers() {
    const data = await request('/users');
    if (data) {
      setUsers(data);
      if (!selectedBackupUserId && data[0]) setSelectedBackupUserId(String(data[0].id));
      setNewBackupSchedule(prev => (!prev.all_users && (!prev.user_ids || prev.user_ids.length === 0) && data[0]) ? ({ ...prev, user_ids: [String(data[0].id)] }) : prev);
    }
  }

  async function loadResourceUsage() {
    const data = await request('/services/resource-usage');
    if (data) setResourceUsage(data);
  }

  async function createUser() {
    const data = await request('/users', { method: 'POST', body: JSON.stringify({ ...newUser, website_limit: Number(newUser.website_limit), storage_limit_mb: Number(newUser.storage_limit_mb) }) }, 'Creating user...');
    if (data) {
      setNotice(`Created user ${data.username}`);
      setNewUser({ username: '', email: '', password: '', role: 'end_user', website_limit: 5, storage_limit_mb: 1024 });
      await loadUsers();
    }
  }

  async function changeUserPassword(user) {
    const password = prompt(`Enter a new password for ${user.username} (minimum 12 characters):`);
    if (!password) return;
    if (password.length < 12) { setError('Password must be at least 12 characters.'); return; }
    const data = await request(`/users/${user.id}/password`, { method: 'POST', body: JSON.stringify({ password }) }, `Changing password for ${user.username}...`);
    if (data?.message) setNotice(data.message);
  }

  async function deletePanelUser(user) {
    if (!user || user.id === currentUser?.id) return;
    if (!confirm(`Delete panel user ${user.username} and permanently delete all owned websites, files, databases, and Linux user data?`)) return;
    const data = await request(`/users/${user.id}`, { method: 'DELETE' }, `Deleting user ${user.username}...`);
    if (data) {
      const count = data.deleted_websites?.length || 0;
      setNotice(`Deleted user ${user.username}${count ? ` and ${count} website(s)` : ''}`);
      await loadUsers();
      await loadWebsites();
    }
  }

  async function quickLoginUser(user) {
    if (!user) return;
    if (!confirm(`Login as ${user.username}? New websites will belong to this user.`)) return;
    // Impersonation re-prompts TOTP when the calling admin has 2FA enabled.
    // Try without the code first; if the backend says one is required, ask
    // and resend. Sending the OTP via FormData keeps it out of the URL.
    let body;
    if (currentUser?.totp_enabled) {
      const code = prompt(`Enter the 6-digit code from your authenticator to confirm impersonation of ${user.username}:`);
      if (!code) return;
      body = new URLSearchParams({ otp: code.trim() });
    }
    const data = await request(
      `/auth/impersonate/${user.id}`,
      body
        ? { method: 'POST', body, headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
        : { method: 'POST' },
      `Logging in as ${user.username}...`,
    );
    // Handle case where backend says 2FA is required (e.g., stale user object).
    if (data?.requires_2fa) {
      const code = prompt(`Enter the 6-digit code from your authenticator to confirm impersonation of ${user.username}:`);
      if (!code) return;
      const retryBody = new URLSearchParams({ otp: code.trim() });
      const retryData = await request(
        `/auth/impersonate/${user.id}`,
        { method: 'POST', body: retryBody, headers: { 'Content-Type': 'application/x-www-form-urlencoded' } },
        `Logging in as ${user.username}...`,
      );
      if (retryData?.access_token) {
        setNotice(`Logged in as ${user.username}.`);
        await loadCurrentUser();
        setPage('websites');
        await refreshAll();
      }
      return;
    }
    if (data?.access_token) {
      setNotice(`Logged in as ${user.username}.`);
      await loadCurrentUser();
      setPage('websites');
      await refreshAll();
    }
  }

  async function changeMyPassword() { if (!currentUser) return; await changeUserPassword(currentUser); }

  async function loadTwoFactorStatus() {
    const data = await request('/auth/2fa/status');
    if (data) setTwoFactorStatus(data);
  }

  async function setupTwoFactorAuth() {
    const data = await request('/auth/2fa/setup', { method: 'POST' }, 'Preparing 2FA...');
    if (data) {
      setTwoFactorSetup(data);
      setTwoFactorStatus({ enabled: false });
    }
  }

  async function enableTwoFactorAuth() {
    const data = await request('/auth/2fa/enable', { method: 'POST', body: JSON.stringify({ code: twoFactorCode }) }, 'Enabling 2FA...');
    if (data) {
      setTwoFactorStatus(data);
      setTwoFactorSetup(null);
      setTwoFactorCode('');
      await loadCurrentUser();
      setNotice('2FA enabled.');
    }
  }

  async function disableTwoFactorAuth() {
    const data = await request('/auth/2fa/disable', { method: 'POST', body: JSON.stringify({ code: twoFactorCode }) }, 'Disabling 2FA...');
    if (data) {
      setTwoFactorStatus(data);
      setTwoFactorCode('');
      await loadCurrentUser();
      setNotice('2FA disabled.');
    }
  }

  async function resetUserTwoFactor(user) {
    if (!confirm(`Reset 2FA for ${user.username}?`)) return;
    const data = await request(`/users/${user.id}/2fa/reset`, { method: 'POST' }, `Resetting 2FA for ${user.username}...`);
    if (data?.message) { setNotice(data.message); await loadUsers(); }
  }

  async function assignDomainToUser() {
    if (!assignWebsiteId || !assignUserId) return;
    const data = await request(`/websites/${assignWebsiteId}`, { method: 'PATCH', body: JSON.stringify({ owner_id: Number(assignUserId) }) }, 'Assigning domain to user...');
    if (data) { setNotice(`Assigned domain ${data.domain} to user ID ${assignUserId}`); await refreshAll(); }
  }

  async function createWordPress() {
    if (!domain) { setError('Please enter a domain name.'); return; }
    const installWp = siteType === 'wordpress' && installWordPress;
    const body = {
      domain,
      php_version: phpVersion,
      app_type: siteType,
      install_wordpress: installWp,
      title: domain,
      admin_user: wpAdminUser,
      admin_email: adminEmail || `admin@${domain}`,
      admin_password: wpAdminPassword || (installWp ? 'StrongPass123!' : ''),
    };
    const data = await request('/websites', { method: 'POST', body: JSON.stringify(body) },
      installWp ? 'Creating WordPress website...' : 'Creating website...');
    if (data) {
      if (installWp) {
        setNotice(`Created WordPress site: https://${domain}\nAdmin: ${wpAdminUser} | Password: ${wpAdminPassword || 'StrongPass123!'}`);
      } else {
        setNotice(`Created site ${domain}. Upload your files to public_html/ folder.`);
      }
      if (installSslAfterCreate) await enableSsl(data.id);
      refreshAll();
    }
  }

  async function deleteWebsite(id) {
    if (!confirm('Delete this website including files, vhost, and database?')) return;
    const data = await request(`/websites/${id}?delete_files=true&delete_database=true`, { method: 'DELETE' }, 'Deleting website...');
    if (data) refreshAll();
  }

  async function enableSsl(id) {
    const data = await request(`/websites/${id}/ssl`, { method: 'POST' }, "Installing Let's Encrypt SSL...");
    if (data) refreshAll();
  }

  async function openNginxCustom(site) {
    const data = await request(`/websites/${site.id}/nginx-config`, {}, 'Loading Nginx config...');
    if (data !== null) {
      setNginxCustomEditing({ id: site.id, domain: site.domain, content: data?.nginx_config || '' });
    }
  }

  async function saveNginxCustom() {
    if (!nginxCustomEditing) return;
    const data = await request(`/websites/${nginxCustomEditing.id}/nginx-config`, {
      method: 'PUT',
      body: JSON.stringify({ nginx_config: nginxCustomEditing.content }),
    }, 'Applying Nginx config and reloading...');
    if (data) {
      setNotice(`Updated Nginx config for ${nginxCustomEditing.domain}`);
      setNginxCustomEditing(null);
      refreshAll();
    }
  }

  async function resetNginxDefault() {
    if (!nginxCustomEditing) return;
    if (!confirm(`Reset Nginx config for ${nginxCustomEditing.domain} to the BPanel default template?`)) return;
    const data = await request(`/websites/${nginxCustomEditing.id}/nginx-config/reset`, { method: 'POST' }, 'Resetting Nginx config...');
    if (data) {
      setNotice(`Reset Nginx config for ${nginxCustomEditing.domain}.`);
      setNginxCustomEditing(null);
      await refreshAll();
    }
  }

  async function loadWebsiteLog(siteOrId = logViewer?.id, kind = logViewer?.kind || 'access', lines = logViewer?.lines || 200, domainLabel = logViewer?.domain || '') {
    const websiteId = typeof siteOrId === 'object' ? siteOrId.id : siteOrId;
    const domainName = typeof siteOrId === 'object' ? siteOrId.domain : domainLabel;
    if (!websiteId) return;
    const data = await request(`/websites/${websiteId}/logs?kind=${encodeURIComponent(kind)}&lines=${encodeURIComponent(lines)}`, {}, `Loading ${kind} log...`);
    if (data) {
      setLogViewer({
        id: websiteId,
        domain: data.domain || domainName,
        kind: data.kind || kind,
        lines: data.lines || lines,
        path: data.path || '',
        content: data.content || '',
        exists: !!data.exists,
      });
    }
  }

  async function openWebsiteLogs(site) {
    setLogViewer({ id: site.id, domain: site.domain, kind: 'access', lines: 200, path: '', content: '', exists: true });
    await loadWebsiteLog(site, 'access', 200, site.domain);
  }

  function openWebsiteTerminal(site) {
    setTerminalViewer({ id: site.id, domain: site.domain });
  }

  // WordPress Toolkit functions
  function openWpToolkit(site) {
    setWpToolkitViewer({ id: site.id, domain: site.domain });
    setWpActiveTab('plugins');
    loadWpPlugins(site.id);
  }

  async function loadWpPlugins(websiteId) {
    const data = await request(`/wordpress/${websiteId}/plugins`);
    if (data?.plugins) setWpPlugins(data.plugins);
  }

  async function loadWpThemes(websiteId) {
    const data = await request(`/wordpress/${websiteId}/themes`);
    if (data?.themes) setWpThemes(data.themes);
  }

  async function loadWpHealth(websiteId) {
    const data = await request(`/wordpress/${websiteId}/health`);
    if (data?.health) setWpHealth(data.health);
  }

  async function loadWpStagingStatus(websiteId) {
    const data = await request(`/wordpress/${websiteId}/staging/status`);
    if (data?.staging) setWpStagingStatus(data.staging);
  }

  async function toggleWpPlugin(websiteId, plugin, action) {
    const data = await request(`/wordpress/${websiteId}/plugins/${plugin}/${action}`, { method: 'POST' });
    if (data) {
      setNotice(data.message);
      await loadWpPlugins(websiteId);
    }
  }

  async function deleteWpPlugin(websiteId, plugin) {
    if (!confirm(`Delete plugin '${plugin}'? This cannot be undone.`)) return;
    const data = await request(`/wordpress/${websiteId}/plugins/${plugin}/delete`, { method: 'POST' });
    if (data) {
      setNotice(data.message);
      await loadWpPlugins(websiteId);
    }
  }

  async function toggleWpTheme(websiteId, theme) {
    const data = await request(`/wordpress/${websiteId}/themes/${theme}/activate`, { method: 'POST' });
    if (data) {
      setNotice(data.message);
      await loadWpThemes(websiteId);
    }
  }

  async function createWpStaging(websiteId) {
    const data = await request(`/wordpress/${websiteId}/staging/create`, { method: 'POST' });
    if (data) {
      setNotice(data.message);
      await loadWpStagingStatus(websiteId);
    }
  }

  async function pushWpStagingToProduction(websiteId) {
    if (!confirm('Push staging to production? This will overwrite the production files.')) return;
    const data = await request(`/wordpress/${websiteId}/staging/push-to-production`, { method: 'POST' });
    if (data) setNotice(data.message);
  }

  function renderWpToolkit() {
    if (!wpToolkitViewer) return null;
    const websiteId = wpToolkitViewer.id;
    const tabs = [
      { key: 'plugins', label: 'Plugins' },
      { key: 'themes', label: 'Themes' },
      { key: 'health', label: 'Health' },
      { key: 'staging', label: 'Staging' },
    ];
    return <section className="section wp-toolkit-modal">
      <div className="section-title">
        <div>
          <h2>WordPress Toolkit - {wpToolkitViewer.domain}</h2>
        </div>
        <button className="secondary-light" onClick={() => setWpToolkitViewer(null)}><X size={14}/> Close</button>
      </div>
      <div className="segmented-control">
        {tabs.map(tab => (
          <button key={tab.key} className={wpActiveTab === tab.key ? 'active' : ''} onClick={() => {
            setWpActiveTab(tab.key);
            if (tab.key === 'plugins') loadWpPlugins(websiteId);
            else if (tab.key === 'themes') loadWpThemes(websiteId);
            else if (tab.key === 'health') loadWpHealth(websiteId);
            else if (tab.key === 'staging') loadWpStagingStatus(websiteId);
          }}>{tab.label}</button>
        ))}
      </div>
      {wpActiveTab === 'plugins' && <div className="wp-toolkit-content">
        {wpPlugins.length === 0 ? <p className="hint">No plugins found or loading...</p> : (
          <div className="table">
            {wpPlugins.map(plugin => (
              <div className="row" key={plugin.name}>
                <span><strong>{plugin.name}</strong><small>{plugin.description?.substring(0, 80) || ''}</small></span>
                <span className={`badge ${plugin.status === 'active' ? 'ok' : ''}`}>{plugin.status}</span>
                <span>Version {plugin.version}</span>
                <div className="row-actions">
                  {plugin.status === 'active' ? (
                    <button className="mini secondary-light" disabled={!!loading} onClick={() => toggleWpPlugin(websiteId, plugin.name, 'deactivate')}>Deactivate</button>
                  ) : (
                    <button className="mini secondary-light" disabled={!!loading} onClick={() => toggleWpPlugin(websiteId, plugin.name, 'activate')}>Activate</button>
                  )}
                  {plugin.status !== 'active' && (
                    <button className="mini danger" disabled={!!loading} onClick={() => deleteWpPlugin(websiteId, plugin.name)}>Delete</button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>}
      {wpActiveTab === 'themes' && <div className="wp-toolkit-content">
        {wpThemes.length === 0 ? <p className="hint">No themes found or loading...</p> : (
          <div className="table">
            {wpThemes.map(theme => (
              <div className="row" key={theme.name}>
                <span><strong>{theme.name}</strong><small>{theme.description?.substring(0, 80) || ''}</small></span>
                <span className={`badge ${theme.status === 'active' ? 'ok' : ''}`}>{theme.status}</span>
                <span>Version {theme.version}</span>
                <div className="row-actions">
                  {theme.status !== 'active' && (
                    <button className="mini secondary-light" disabled={!!loading} onClick={() => toggleWpTheme(websiteId, theme.name)}>Activate</button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>}
      {wpActiveTab === 'health' && <div className="wp-toolkit-content">
        {!wpHealth ? <button disabled={!!loading} onClick={() => loadWpHealth(websiteId)}>Run Health Check</button> : (
          <div className="info-box">
            <pre>{wpHealth.output || 'Health check completed'}</pre>
            <button disabled={!!loading} onClick={() => loadWpHealth(websiteId)} style={{marginTop: 8}}>Refresh</button>
          </div>
        )}
      </div>}
      {wpActiveTab === 'staging' && <div className="wp-toolkit-content">
        {!wpStagingStatus ? <p className="hint">Loading...</p> : (
          <div className="info-box">
            <p><strong>Staging Environment Status:</strong></p>
            <p>Exists: {wpStagingStatus.exists ? 'Yes' : 'No'}</p>
            {wpStagingStatus.exists && <p>Has WordPress: {wpStagingStatus.has_wordpress ? 'Yes' : 'No'}</p>}
            <div className="actions" style={{marginTop: 8}}>
              {!wpStagingStatus.exists && <button disabled={!!loading || !isAdmin} onClick={() => createWpStaging(websiteId)}>Create Staging</button>}
              {wpStagingStatus.exists && <button disabled={!!loading || !isAdmin} onClick={() => pushWpStagingToProduction(websiteId)} className="danger">Push to Production</button>}
            </div>
            {!isAdmin && <p className="hint">Only admins can create or push staging environments.</p>}
          </div>
        )}
      </div>}
    </section>;
  }

  async function toggleWebsiteWaf(site) {
    const next = !site.waf_enabled;
    const data = await request(`/websites/${site.id}/waf`, {
      method: 'PATCH',
      body: JSON.stringify({ waf_enabled: next }),
    }, `${next ? 'Enabling' : 'Disabling'} WAF for ${site.domain}...`);
    if (data) {
      setNotice(`${next ? 'Enabled' : 'Disabled'} WAF for ${site.domain}.`);
      await refreshAll();
    }
  }

  async function fixWordPressPermissions(id) {
    const data = await request(`/maintenance/wordpress/${id}/fix-permissions`, { method: 'POST' }, 'Fixing permissions...');
    if (data?.message) setNotice(data.message);
  }

  async function fixNginxSecurity(id) {
    const data = await request(`/websites/${id}/fix-nginx-security`, { method: 'POST' }, 'Rewriting Nginx security template...');
    if (data?.message) setNotice(data.message);
  }

  async function changeWebsitePhpVersion(site) {
    const next = websitePhpVersions[site.id] || site.php_version || '8.3';
    if (next === site.php_version) return;
    const data = await request(`/websites/${site.id}`, { method: 'PATCH', body: JSON.stringify({ php_version: next }) }, `Changing ${site.domain} to PHP ${next}...`);
    if (data) { setNotice(`Changed ${site.domain} to PHP ${next} and reloaded Nginx.`); await refreshAll(); }
  }

  async function changeDbPassword(id) {
    const newPass = prompt('Enter a new database password, minimum 12 characters:');
    if (!newPass) return;
    await request(`/databases/${id}/password`, { method: 'POST', body: JSON.stringify({ password: newPass }) }, 'Changing database password...');
  }

  async function createDatabase() {
    if (!newDatabase.website_id) { setError('Please select a website.'); return; }
    const body = {
      website_id: Number(newDatabase.website_id),
      db_name: newDatabase.db_name.trim() || null,
    };
    const data = await request('/databases', { method: 'POST', body: JSON.stringify(body) }, 'Creating database...');
    if (data) {
      setNotice(`Created database ${data.db_name}\nUser: ${data.db_user}${data.db_password ? ` | Password: ${data.db_password}` : ''}`);
      setNewDatabase(prev => ({ ...prev, db_name: '' }));
      await refreshAll();
    }
  }

  // Cron job functions
  async function loadCronJobs() {
    const data = await request('/cron/jobs');
    if (data) setCronJobs(data);
  }

  async function loadCronPresets() {
    const data = await request('/cron/presets');
    if (data) setCronPresets(data);
  }

  async function loadScheduleTypes() {
    const data = await request('/cron/schedule-types');
    if (data) setScheduleTypes(data);
  }

  async function generateSchedulePreview() {
    const schedule = `${cronMinute} ${cronHour} ${cronDayOfMonth} ${cronMonth} ${cronDayOfWeek}`;
    const data = await request('/cron/schedules/generate', {
      method: 'POST',
      body: JSON.stringify({ expression: schedule }),
    });
    if (data) setCronPreview(data);
  }

  function openCronModal(cron = null) {
    if (cron) {
      setEditingCron(cron);
      setCronForm({
        command: cron.command || '',
        schedule: cron.schedule || '',
        description: cron.description || '',
      });
      const parts = (cron.schedule || '* * * * *').split(' ');
      if (parts.length === 5) {
        setCronMinute(parts[0]);
        setCronHour(parts[1]);
        setCronDayOfMonth(parts[2]);
        setCronMonth(parts[3]);
        setCronDayOfWeek(parts[4]);
      }
      setSelectedPreset('');
    } else {
      setEditingCron(null);
      setCronForm({ command: '', schedule: '', description: '' });
      setCronMinute('*');
      setCronHour('*');
      setCronDayOfMonth('*');
      setCronMonth('*');
      setCronDayOfWeek('*');
      setSelectedPreset('');
    }
    setShowCronModal(true);
    generateSchedulePreview();
  }

  function closeCronModal() {
    setShowCronModal(false);
    setEditingCron(null);
    setCronForm({ command: '', schedule: '', description: '' });
    setSelectedPreset('');
  }

  function applyPreset(preset) {
    setSelectedPreset(preset);
    if (preset) {
      const parts = preset.split(' ');
      if (parts.length === 5) {
        setCronMinute(parts[0]);
        setCronHour(parts[1]);
        setCronDayOfMonth(parts[2]);
        setCronMonth(parts[3]);
        setCronDayOfWeek(parts[4]);
      }
    }
  }

  async function createCronJob() {
    const schedule = `${cronMinute} ${cronHour} ${cronDayOfMonth} ${cronMonth} ${cronDayOfWeek}`;
    const data = await request('/cron/jobs', {
      method: 'POST',
      body: JSON.stringify({
        command: cronForm.command,
        schedule: schedule,
        description: cronForm.description,
      }),
    }, 'Creating cron job...');
    if (data) {
      setNotice('Cron job created successfully.');
      closeCronModal();
      await loadCronJobs();
    }
  }

  async function updateCronJob() {
    if (!editingCron) return;
    const schedule = `${cronMinute} ${cronHour} ${cronDayOfMonth} ${cronMonth} ${cronDayOfWeek}`;
    const data = await request(`/cron/jobs/${editingCron.id}`, {
      method: 'PUT',
      body: JSON.stringify({
        command: cronForm.command,
        schedule: schedule,
        description: cronForm.description,
      }),
    }, 'Updating cron job...');
    if (data) {
      setNotice('Cron job updated successfully.');
      closeCronModal();
      await loadCronJobs();
    }
  }

  async function deleteCronJob(cron) {
    if (!confirm(`Delete cron job "${cron.description || cron.command}"?`)) return;
    const data = await request(`/cron/jobs/${cron.id}`, { method: 'DELETE' }, 'Deleting cron job...');
    if (data) {
      setNotice('Cron job deleted.');
      await loadCronJobs();
    }
  }

  async function toggleCronJob(cron) {
    const data = await request(`/cron/jobs/${cron.id}/toggle`, { method: 'POST' }, `${cron.enabled ? 'Disabling' : 'Enabling'} cron job...`);
    if (data) {
      await loadCronJobs();
    }
  }

  async function runCronJobNow(cron) {
    const data = await request(`/cron/jobs/${cron.id}/run`, { method: 'POST' }, 'Running cron job...');
    if (data?.message) {
      setNotice(data.message);
    }
  }

  async function listFiles(path = fileListPath, websiteId = selectedWebsiteId) {
    if (!websiteId) return;
    const data = await request(`/maintenance/files/${websiteId}?path=${encodeURIComponent(path)}`, {}, 'Loading file list...');
    if (data?.items) { setFiles(data.items); setFileListPath(path); setFileUploadDir(path || ''); setSelectedFilePaths([]); }
  }

  async function readFile(pathOverride = filePath, websiteId = selectedWebsiteId) {
    const targetPath = pathOverride || filePath;
    if (!websiteId || !targetPath) return;
    if (pathOverride) setFilePath(pathOverride);
    const data = await request(`/maintenance/files/${websiteId}/read?path=${encodeURIComponent(targetPath)}`, {}, 'Reading file...');
    if (data?.content !== undefined) {
      setFileContent(data.content);
      setEditorCursor({ line: 1, column: 1 });
    }
  }

  async function writeFile() {
    const data = await request('/maintenance/files/write', { method: 'POST', body: JSON.stringify({ website_id: Number(selectedWebsiteId), path: filePath, content: fileContent }) }, 'Saving file...');
    if (data) { await listFiles(fileListPath); await loadCurrentUser(); }
  }

  async function deleteFileAction(path) {
    if (!confirm(`Delete file ${path}?`)) return;
    const data = await request('/maintenance/files/delete', { method: 'POST', body: JSON.stringify({ website_id: Number(selectedWebsiteId), paths: [path] }) }, 'Deleting file...');
    if (data) { await listFiles(fileListPath); await loadCurrentUser(); }
  }

  async function downloadFile(path) {
    if (!selectedWebsiteId || !path) return;
    try {
      setError(''); setLoading('Downloading file...');
      const res = await fetch(`${API}/maintenance/files/${selectedWebsiteId}/download?path=${encodeURIComponent(path)}`, { credentials: 'include' });
      if (!res.ok) { const data = await res.json().catch(() => ({})); if (handleAuthExpired(res.status, data.detail)) return; setError(data.detail || 'Download failed.'); return; }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url; link.download = path.split('/').pop() || 'download';
      document.body.appendChild(link); link.click(); link.remove();
      URL.revokeObjectURL(url);
    } catch (err) { setError('File download failed.'); }
    finally { setLoading(''); }
  }

  function fileEditorUrl(websiteId, path) {
    const url = new URL(window.location.href);
    url.search = '';
    url.hash = '';
    url.searchParams.set('view', 'editor');
    url.searchParams.set('website_id', String(websiteId));
    url.searchParams.set('path', path);
    return url.toString();
  }

  function openFileEditorTab(path, websiteId = selectedWebsiteId) {
    if (!websiteId || !path) return;
    window.open(fileEditorUrl(websiteId, path), '_blank', 'noopener,noreferrer');
  }

  async function makeFileDirectory() {
    if (!selectedWebsiteId) return;
    const name = prompt('Folder name:');
    if (!name) return;
    const data = await request('/maintenance/files/mkdir', { method: 'POST', body: JSON.stringify({ website_id: Number(selectedWebsiteId), path: fileListPath || '', name }) }, 'Creating folder...');
    if (data) await listFiles(fileListPath);
  }

  async function makeFile() {
    if (!selectedWebsiteId) return;
    const name = prompt('File name:', 'new-file.txt');
    if (!name) return;
    const data = await request('/maintenance/files/create', { method: 'POST', body: JSON.stringify({ website_id: Number(selectedWebsiteId), path: fileListPath || '', name }) }, 'Creating file...');
    if (data) {
      await listFiles(fileListPath);
      const newPath = [fileListPath, name].filter(Boolean).join('/');
      openFileEditorTab(newPath);
    }
  }

  async function renameFileItem(item) {
    if (!item) return;
    const newName = prompt('New name:', item.name);
    if (!newName || newName === item.name) return;
    const data = await request('/maintenance/files/rename', { method: 'POST', body: JSON.stringify({ website_id: Number(selectedWebsiteId), path: item.path, new_name: newName }) }, 'Renaming...');
    if (data) await listFiles(fileListPath);
  }

  async function chmodFileItem(item) {
    if (!item) return;
    const currentMode = item.mode || (item.is_dir ? '755' : '644');
    const mode = prompt('Mode (octal, e.g. 644 or 755):', currentMode);
    if (!mode || mode === currentMode) return;
    const data = await request('/maintenance/files/chmod', { method: 'POST', body: JSON.stringify({ website_id: Number(selectedWebsiteId), path: item.path, mode }) }, 'Changing permissions...');
    if (data) await listFiles(fileListPath);
  }

  async function deleteSelectedFiles() {
    if (selectedFilePaths.length === 0) return;
    if (!confirm(`Delete ${selectedFilePaths.length} selected item(s)?`)) return;
    const data = await request('/maintenance/files/delete', { method: 'POST', body: JSON.stringify({ website_id: Number(selectedWebsiteId), paths: selectedFilePaths }) }, 'Deleting selected files...');
    if (data) { await listFiles(fileListPath); await loadCurrentUser(); }
  }

  async function transferFileItems(action, paths) {
    if (!selectedWebsiteId || !paths?.length) return;
    const verb = action === 'copy' ? 'Copy' : 'Move';
    const destination = prompt(`${verb} to folder:`, fileListPath || 'public_html');
    if (destination === null) return;
    const targetPath = destination.trim() || fileListPath || 'public_html';
    const data = await request(`/maintenance/files/${action}`, {
      method: 'POST',
      body: JSON.stringify({ website_id: Number(selectedWebsiteId), paths, destination_path: targetPath }),
    }, `${verb}ing files...`);
    if (data) { await listFiles(fileListPath); await loadCurrentUser(); }
  }

  async function copySelectedFiles() {
    await transferFileItems('copy', selectedFilePaths);
  }

  async function moveSelectedFiles() {
    await transferFileItems('move', selectedFilePaths);
  }

  async function copyFileItem(item) {
    if (!item) return;
    await transferFileItems('copy', [item.path]);
  }

  async function moveFileItem(item) {
    if (!item) return;
    await transferFileItems('move', [item.path]);
  }

  async function archiveSelectedFiles() {
    if (selectedFilePaths.length === 0) return;
    const ext = archiveFormat === 'tar.gz' ? 'tar.gz' : 'zip';
    const outputName = prompt('Archive file name:', `archive-${Date.now()}.${ext}`);
    if (!outputName) return;
    const data = await request('/maintenance/files/archive', {
      method: 'POST',
      body: JSON.stringify({ website_id: Number(selectedWebsiteId), base_path: fileListPath || '', paths: selectedFilePaths, output_name: outputName, format: archiveFormat }),
    }, 'Creating archive...');
    if (data) { await listFiles(fileListPath); await loadCurrentUser(); }
  }

  function upsertFileJob(job) {
    if (!job?.job_id) return;
    setFileJobs(prev => [job, ...prev.filter(item => item.job_id !== job.job_id)].slice(0, 6));
  }

  async function loadFileJob(jobId) {
    try {
      const res = await fetch(`${API}/maintenance/files/jobs/${jobId}`, { credentials: 'include' });
      const text = await res.text();
      let data;
      try { data = text ? JSON.parse(text) : {}; } catch { data = { detail: text || `HTTP ${res.status}` }; }
      if (!res.ok && handleAuthExpired(res.status, data.detail)) return null;
      if (!res.ok) return null;
      return data;
    } catch {
      return null;
    }
  }

  async function loadFileJobs(websiteId = selectedWebsiteId) {
    if (!websiteId) return;
    const data = await request(`/maintenance/files/jobs?website_id=${encodeURIComponent(websiteId)}`);
    if (data?.jobs) {
      setFileJobs(prev => [
        ...data.jobs,
        ...prev.filter(job => String(job.website_id) !== String(websiteId)),
      ].slice(0, 6));
    }
  }

  async function extractArchiveFile(path) {
    if (!path) return;
    const destination = prompt('Extract to folder:', fileListPath || '.');
    if (destination === null) return;
    const targetPath = destination || fileListPath || '.';
    const data = await request('/maintenance/files/extract', { method: 'POST', body: JSON.stringify({ website_id: Number(selectedWebsiteId), archive_path: path, destination_path: targetPath }) }, 'Starting extraction...');
    if (data?.job_id) upsertFileJob(data);
    else if (data) { await listFiles(targetPath === '.' ? '' : targetPath); await loadCurrentUser(); }
  }

  useEffect(() => {
    const activeJobs = fileJobs.filter(job => ['queued', 'running'].includes(job.status));
    if (activeJobs.length === 0) return undefined;

    const poll = async () => {
      for (const job of activeJobs) {
        const data = await loadFileJob(job.job_id);
        if (!data) continue;
        upsertFileJob(data);
        if (data.status === 'done') {
          setNotice(data.message || 'Extraction completed');
          await listFiles(data.destination_path || fileListPath);
          await loadCurrentUser();
        } else if (data.status === 'error') {
          setError(data.error || 'Extraction failed');
        }
      }
    };

    const timer = window.setInterval(poll, 3000);
    return () => window.clearInterval(timer);
  }, [fileJobs]);

  useEffect(() => {
    if (page === 'files' && selectedWebsiteId) loadFileJobs(selectedWebsiteId);
  }, [page, selectedWebsiteId]);

  async function openWebsiteFileManager(site) {
    setSelectedWebsiteId(String(site.id));
    setPage('files');
    setFileListPath('public_html');
    setFileUploadDir('public_html');
    await listFiles('public_html', site.id);
  }

  async function uploadSiteFile(file) {
    if (!file) return;
    if (!selectedWebsiteId) { setError('Please select a website first.'); return; }
    const uploadDir = fileUploadDir.trim();
    const form = new FormData();
    form.append('file', file);
    try {
      setError('');
      setLoading('Uploading file...');
      const csrfToken = readCookie('bpanel_csrf');
      const headers = csrfToken ? { 'X-CSRF-Token': csrfToken } : {};
      const res = await fetch(`${API}/maintenance/files/${selectedWebsiteId}/upload?path=${encodeURIComponent(uploadDir)}`, {
        method: 'POST',
        credentials: 'include',
        headers,
        body: form,
      });
      const responseText = await res.text();
      let data;
      try { data = responseText ? JSON.parse(responseText) : {}; } catch { data = { detail: responseText || `HTTP ${res.status}` }; }
      if (!res.ok) { if (handleAuthExpired(res.status, data.detail)) return; setError(data.detail || 'Upload failed.'); return; }
      setNotice(`Uploaded ${file.name} to ${uploadDir || 'site root'}.`);
      if (String(fileListPath || '') === uploadDir) await listFiles(uploadDir);
      await loadCurrentUser();
    } catch (err) { setError('File upload failed.'); }
    finally { setLoading(''); }
  }

  async function createBackup() {
    const data = await request('/maintenance/backup', { method: 'POST', body: JSON.stringify({ website_id: Number(selectedWebsiteId) }) }, 'Creating backup...');
    if (data?.backup_file) { setNotice(`Created backup: ${data.backup_file}`); await listBackups(); }
  }

  async function listBackups() {
    const data = await request(`/maintenance/backups/${selectedWebsiteId}`);
    if (data?.items) setBackups(data.items);
  }

  async function listUserBackups(userId = selectedBackupUserId) {
    if (!userId) return;
    const data = await request(`/maintenance/user-backups/${userId}`);
    if (data?.items) setUserBackups(data.items);
  }

  async function createUserBackup() {
    if (!selectedBackupUserId) return;
    const body = {
      user_id: Number(selectedBackupUserId),
      target_id: selectedSftpTargetId ? Number(selectedSftpTargetId) : null,
    };
    const data = await request('/maintenance/user-backup', { method: 'POST', body: JSON.stringify(body) }, 'Creating full user backup...');
    if (data?.backup_file) {
      setNotice(data.remote_file ? `Full user backup uploaded: ${data.remote_file}` : `Created full user backup: ${data.backup_file}`);
      await listUserBackups();
    }
  }

  async function loadBackupSchedules() {
    const data = await request('/maintenance/backup-schedules');
    if (data) setBackupSchedules(data);
  }

  async function loadRestoreBackups() {
    const data = await request('/maintenance/user-restore-backups');
    if (data?.items) setRestoreBackups(data.items);
    if (data?.directory) setRestoreBackupDir(data.directory);
  }

  async function createBackupSchedule() {
    const selectedUserIds = (newBackupSchedule.user_ids || []).map(Number).filter(Boolean);
    if (!newBackupSchedule.all_users && selectedUserIds.length === 0) return;
    const body = {
      user_id: selectedUserIds[0] || null,
      user_ids: newBackupSchedule.all_users ? [] : selectedUserIds,
      all_users: !!newBackupSchedule.all_users,
      schedule: newBackupSchedule.schedule,
      target_id: newBackupSchedule.target_id ? Number(newBackupSchedule.target_id) : null,
      retention: Number(newBackupSchedule.retention || 7),
      is_active: true,
    };
    const data = await request('/maintenance/backup-schedules', { method: 'POST', body: JSON.stringify(body) }, 'Saving backup schedule...');
    if (data) {
      setNotice('Backup schedule saved.');
      await loadBackupSchedules();
    }
  }

  async function deleteBackupSchedule(id) {
    if (!confirm('Delete this backup schedule?')) return;
    const data = await request(`/maintenance/backup-schedules/${id}`, { method: 'DELETE' }, 'Deleting backup schedule...');
    if (data) await loadBackupSchedules();
  }

  async function loadSftpTargets() {
    const data = await request('/maintenance/sftp-targets');
    if (data) {
      setSftpTargets(data);
      if (!selectedSftpTargetId && data[0]) setSelectedSftpTargetId(String(data[0].id));
    }
  }

  async function createSftpTarget() {
    const body = {
      ...newSftpTarget,
      port: Number(newSftpTarget.port || 22),
      password: newSftpTarget.password || null,
      private_key: newSftpTarget.private_key || null,
    };
    const data = await request('/maintenance/sftp-targets', { method: 'POST', body: JSON.stringify(body) }, 'Saving SFTP target...');
    if (data) {
      setNotice(`Saved SFTP target ${data.name}`);
      setNewSftpTarget({ name: '', host: '', port: 22, username: '', password: '', private_key: '', remote_path: '/backups/bpanel' });
      await loadSftpTargets();
    }
  }

  async function deleteSftpTarget(id) {
    if (!confirm('Delete this SFTP target?')) return;
    const data = await request(`/maintenance/sftp-targets/${id}`, { method: 'DELETE' }, 'Deleting SFTP target...');
    if (data) await loadSftpTargets();
  }

  async function createSftpBackup() {
    if (!selectedWebsiteId || !selectedSftpTargetId) return;
    const data = await request('/maintenance/backup-sftp', {
      method: 'POST',
      body: JSON.stringify({ website_id: Number(selectedWebsiteId), target_id: Number(selectedSftpTargetId) }),
    }, 'Creating and uploading SFTP backup...');
    if (data?.remote_file) {
      setNotice(`SFTP backup uploaded: ${data.remote_file}`);
      await listBackups();
    }
  }

  async function restoreBackup(file) {
    if (!confirm(`Restore this backup to the current website?\n${file}`)) return;
    await request('/maintenance/restore', { method: 'POST', body: JSON.stringify({ website_id: Number(selectedWebsiteId), backup_file: file }) }, 'Restoring backup...');
  }

  async function downloadBackup(file) {
    if (!selectedWebsiteId) return;
    try {
      setError(''); setLoading('Downloading backup...');
      const res = await fetch(`${API}/maintenance/backups/${selectedWebsiteId}/download?backup_file=${encodeURIComponent(file)}`, { credentials: 'include' });
      if (!res.ok) { const data = await res.json().catch(() => ({})); if (handleAuthExpired(res.status, data.detail)) return; setError(data.detail || 'Download failed.'); return; }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url; link.download = file.split('/').pop() || 'backup.tar.gz';
      document.body.appendChild(link); link.click(); link.remove();
      URL.revokeObjectURL(url);
      setNotice('Backup downloaded.');
    } catch (err) { setError('Backup download failed.'); }
    finally { setLoading(''); }
  }

  async function downloadUserBackup(file) {
    try {
      setError(''); setLoading('Downloading full user backup...');
      const res = await fetch(`${API}/maintenance/user-backups-download?backup_file=${encodeURIComponent(file)}`, { credentials: 'include' });
      if (!res.ok) { const data = await res.json().catch(() => ({})); if (handleAuthExpired(res.status, data.detail)) return; setError(data.detail || 'Download failed.'); return; }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url; link.download = file.split('/').pop() || 'user-backup.tar.gz';
      document.body.appendChild(link); link.click(); link.remove();
      URL.revokeObjectURL(url);
      setNotice('Full user backup downloaded.');
    } catch (err) { setError('Full user backup download failed.'); }
    finally { setLoading(''); }
  }

  async function restoreUserBackup(file) {
    if (!confirm(`Restore this full user backup? Missing panel user and websites will be created.\n${file}`)) return;
    const data = await request('/maintenance/user-restore', { method: 'POST', body: JSON.stringify({ backup_file: file }) }, 'Restoring full user backup...');
    if (data) {
      setNotice(`Restored user ${data.username}. Websites: ${data.websites?.length || 0}`);
      await refreshAll();
      await loadUsers();
      await listUserBackups();
      await loadRestoreBackups();
    }
  }

  async function deleteUserBackup(file) {
    if (!confirm(`Delete this full user backup?\n${file}`)) return;
    const data = await request(`/maintenance/user-backups?backup_file=${encodeURIComponent(file)}`, { method: 'DELETE' }, 'Deleting full user backup...');
    if (data) {
      await listUserBackups();
      await loadRestoreBackups();
    }
  }

  async function deleteRestoreBackup(file) {
    if (!confirm(`Delete this restore backup?\n${file}`)) return;
    const data = await request(`/maintenance/user-restore-backups?backup_file=${encodeURIComponent(file)}`, { method: 'DELETE' }, 'Deleting restore backup...');
    if (data) {
      await loadRestoreBackups();
      await listUserBackups();
    }
  }

  async function uploadUserBackups(files) {
    const selectedFiles = Array.from(files || []);
    if (selectedFiles.length === 0) return;
    const form = new FormData();
    selectedFiles.forEach(file => form.append('files', file));
    try {
      setError(''); setLoading('Uploading full user backups...');
      const csrfToken = readCookie('bpanel_csrf');
      const headers = csrfToken ? { 'X-CSRF-Token': csrfToken } : {};
      const res = await fetch(`${API}/maintenance/user-restore-backups/upload`, {
        method: 'POST',
        credentials: 'include',
        headers,
        body: form,
      });
      const responseText = await res.text();
      let data;
      try { data = responseText ? JSON.parse(responseText) : {}; } catch { data = { detail: responseText || `HTTP ${res.status}` }; }
      if (!res.ok) { if (handleAuthExpired(res.status, data.detail)) return; setError(data.detail || 'Upload failed.'); return; }
      setNotice(`Uploaded ${data.items?.length || selectedFiles.length} full user backup file(s).`);
      await loadRestoreBackups();
      await listUserBackups();
    } catch (err) { setError('Full user backup upload failed.'); }
    finally { setLoading(''); }
  }

  // =============================================================================
  // Enhanced Backup Functions
  // =============================================================================

  async function loadBackupJobs() {
    const data = await request('/backup/jobs');
    if (data) setBackupJobs(data);
  }

  async function createBackupJob(jobData) {
    const data = await request('/backup/jobs', {
      method: 'POST',
      body: JSON.stringify(jobData),
    }, 'Creating backup job...');
    if (data) {
      setNotice('Backup job created successfully.');
      setShowBackupJobModal(false);
      setEditingBackupJob(null);
      await loadBackupJobs();
    }
  }

  async function updateBackupJob(jobId, jobData) {
    const data = await request(`/backup/jobs/${jobId}`, {
      method: 'PUT',
      body: JSON.stringify(jobData),
    }, 'Updating backup job...');
    if (data) {
      setNotice('Backup job updated successfully.');
      setShowBackupJobModal(false);
      setEditingBackupJob(null);
      await loadBackupJobs();
    }
  }

  async function deleteBackupJob(jobId) {
    if (!confirm('Delete this backup job?')) return;
    const data = await request(`/backup/jobs/${jobId}`, { method: 'DELETE' }, 'Deleting backup job...');
    if (data) {
      setNotice('Backup job deleted.');
      await loadBackupJobs();
    }
  }

  async function runBackupJob(jobId) {
    const data = await request(`/backup/jobs/${jobId}/run`, { method: 'POST' }, 'Running backup...');
    if (data) {
      setNotice('Backup job started.');
      await loadBackupHistory();
    }
  }

  async function loadBackupHistory(page = 1) {
    const data = await request(`/backup/history?page=${page}`);
    if (data) {
      setBackupHistory(data.items || []);
    }
  }

  async function loadStorageConfigs() {
    const data = await request('/backup/storage');
    if (data) setStorageConfigs(data);
  }

  async function configureStorage(type, config) {
    let endpoint;
    switch (type) {
      case 'ftp': endpoint = '/backup/storage/ftp'; break;
      case 's3': endpoint = '/backup/storage/s3'; break;
      case 'ssh': endpoint = '/backup/storage/ssh'; break;
      case 'onedrive': endpoint = '/backup/storage/onedrive'; break;
      case 'google-drive': endpoint = '/backup/storage/google-drive'; break;
      case 'webdav': endpoint = '/backup/storage/webdav'; break;
      case 'b2': endpoint = '/backup/storage/b2'; break;
      default: return;
    }
    const data = await request(endpoint, { method: 'POST', body: JSON.stringify(config) }, 'Configuring storage...');
    if (data) {
      setNotice('Storage configured successfully.');
      setShowStorageModal(false);
      await loadStorageConfigs();
    }
  }

  async function testStorageConnection(configId) {
    const data = await request(`/backup/storage/${configId}/test`, { method: 'POST' }, 'Testing connection...');
    if (data) {
      if (data.ok) {
        setNotice(data.message || 'Connection successful.');
      } else {
        setError(data.message || 'Connection failed.');
      }
    }
  }

  async function deleteStorageConfig(configId) {
    if (!confirm('Delete this storage configuration?')) return;
    const data = await request(`/backup/storage/${configId}`, { method: 'DELETE' }, 'Deleting storage...');
    if (data) {
      setNotice('Storage configuration deleted.');
      await loadStorageConfigs();
    }
  }

  async function backupWebsite(websiteId, options) {
    const { destinations = ['local'], exclude_paths = [] } = options || {};
    const data = await request(`/backup/website/${websiteId}/full`, {
      method: 'POST',
      body: JSON.stringify({ destinations, exclude_paths }),
    }, 'Creating website backup...');
    if (data) {
      setNotice('Website backup created successfully.');
      await loadBackupHistory();
    }
  }

  async function backupDatabase(databaseId, destination) {
    const data = await request(`/backup/database/${databaseId}`, {
      method: 'POST',
      body: JSON.stringify({ destination: destination || 'local' }),
    }, 'Creating database backup...');
    if (data) {
      setNotice('Database backup created successfully.');
      await loadBackupHistory();
    }
  }

  async function backupPath(path, destination) {
    const data = await request('/backup/path', {
      method: 'POST',
      body: JSON.stringify({ path, destination: destination || 'local' }),
    }, 'Creating path backup...');
    if (data) {
      setNotice('Path backup created successfully.');
      await loadBackupHistory();
    }
  }

  async function restoreBackup(backupId, targetId) {
    if (!confirm('Restore from this backup?')) return;
    const data = await request(`/backup/restore/${backupId}?target_database_id=${targetId}`, { method: 'POST' }, 'Restoring backup...');
    if (data) {
      setNotice('Backup restored successfully.');
    }
  }

  async function downloadBackupAction(backupId) {
    try {
      setError(''); setLoading('Downloading backup...');
      const res = await fetch(`${API}/backup/${backupId}/download`, { credentials: 'include' });
      if (!res.ok) { const data = await res.json().catch(() => ({})); if (handleAuthExpired(res.status, data.detail)) return; setError(data.detail || 'Download failed.'); return; }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url; link.download = `backup-${backupId}.tar.gz`;
      document.body.appendChild(link); link.click(); link.remove();
      URL.revokeObjectURL(url);
      setNotice('Backup downloaded.');
    } catch (err) { setError('Backup download failed.'); }
    finally { setLoading(''); }
  }

  async function verifyBackupAction(backupId) {
    const data = await request(`/backup/${backupId}/verify`, { method: 'POST' }, 'Verifying backup...');
    if (data) {
      if (data.verified) {
        setNotice(data.message || 'Backup verified successfully.');
      } else {
        setError(data.message || 'Backup verification failed.');
      }
    }
  }

  async function deleteBackupAction(backupId) {
    if (!confirm('Delete this backup?')) return;
    const data = await request(`/backup/${backupId}`, { method: 'DELETE' }, 'Deleting backup...');
    if (data) {
      setNotice('Backup deleted.');
      await loadBackupHistory();
    }
  }

  async function openPhpMyAdmin(databaseId) {
    try {
      setError(''); setLoading('Opening phpMyAdmin...');
      const csrfToken = readCookie('bpanel_csrf');
      const headers = csrfToken ? { 'X-CSRF-Token': csrfToken } : {};
      const res = await fetch(`${API}/databases/${databaseId}/phpmyadmin-sso`, {
        method: 'POST',
        credentials: 'include',
        headers,
      });
      const data = await res.json().catch(() => ({}));
      if (handleAuthExpired(res.status, data.detail)) return;
      if (!res.ok || !data.url) { setError(data.detail || 'Cannot open phpMyAdmin.'); return; }
      window.open(data.url, '_blank', 'noopener,noreferrer');
    } catch (err) { setError('Cannot open phpMyAdmin.'); }
    finally { setLoading(''); }
  }

  async function downloadDatabase(databaseId, databaseName) {
    try {
      setError(''); setLoading('Downloading database...');
      const res = await fetch(`${API}/databases/${databaseId}/download`, { credentials: 'include' });
      if (!res.ok) { const data = await res.json().catch(() => ({})); if (handleAuthExpired(res.status, data.detail)) return; setError(data.detail || 'Download failed.'); return; }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url; link.download = `${databaseName || 'database'}.sql`;
      document.body.appendChild(link); link.click(); link.remove();
      URL.revokeObjectURL(url);
      setNotice('Database SQL downloaded.');
    } catch (err) { setError('Database download failed.'); }
    finally { setLoading(''); }
  }

  async function deleteBackup(file) {
    if (!confirm(`Delete this backup?\n${file}`)) return;
    const data = await request(`/maintenance/backups/${selectedWebsiteId}?backup_file=${encodeURIComponent(file)}`, { method: 'DELETE' }, 'Deleting backup...');
    if (data) await listBackups();
  }

  async function uploadBackup(file) {
    if (!file || !selectedWebsiteId) return;
    const form = new FormData();
    form.append('file', file);
    try {
      setError(''); setLoading('Uploading backup...');
      const csrfToken = readCookie('bpanel_csrf');
      const headers = csrfToken ? { 'X-CSRF-Token': csrfToken } : {};
      const res = await fetch(`${API}/maintenance/backups/${selectedWebsiteId}/upload`, {
        method: 'POST',
        credentials: 'include',
        headers,
        body: form,
      });
      const responseText = await res.text();
      let data;
      try { data = responseText ? JSON.parse(responseText) : {}; } catch { data = { detail: responseText || `HTTP ${res.status}` }; }
      if (!res.ok) { if (handleAuthExpired(res.status, data.detail)) return; setError(data.detail || 'Upload failed.'); return; }
      if (data.backup_file) { setNotice(`Uploaded backup: ${data.backup_file}`); await listBackups(); }
    } catch (err) { setError('Upload backup failed.'); }
    finally { setLoading(''); }
  }

  async function checkService(name) {
    const data = await request('/services/action', { method: 'POST', body: JSON.stringify({ name, action: 'status' }) });
    setServiceStates(prev => ({ ...prev, [name]: data || { stdout: '', stderr: error || 'Cannot check', returncode: 1 } }));
    return data;
  }

  async function checkAllServices() {
    setLoading('Checking services...');
    for (const name of SERVICE_NAMES) { await checkService(name); }
    setLoading('');
  }

  async function runServiceAction(name, action) {
    await request('/services/action', { method: 'POST', body: JSON.stringify({ name, action }) }, `${action} ${name}...`);
    await checkService(name);
  }

  async function loadPhpConfig(version = phpConfig.php_version) {
    const data = await request(`/maintenance/php-config?php_version=${encodeURIComponent(version)}`, {}, 'Loading PHP config...');
    if (data) setPhpConfig(prev => ({ ...prev, ...data, php_version: version }));
  }

  async function updatePhpConfig() {
    const data = await request('/maintenance/php-config', {
      method: 'POST',
      body: JSON.stringify({ ...phpConfig, max_execution_time: Number(phpConfig.max_execution_time), max_input_time: Number(phpConfig.max_input_time), max_input_vars: Number(phpConfig.max_input_vars) }),
    }, 'Updating PHP config...');
    if (data?.target) { setNotice(`Updated PHP config: ${data.target}`); await loadPhpConfig(phpConfig.php_version); }
  }

  async function loadFirewall() {
    const data = await request('/firewall/status', {}, 'Loading firewall...');
    if (data) setFirewallStatus(data);
  }

  async function runFirewallAction(path, options = {}, label = 'Updating firewall...') {
    const data = await request(path, options, label);
    if (data) { setNotice((data.stdout || data.stderr || 'Firewall updated.').trim()); await loadFirewall(); }
  }

  async function enableFirewall() {
    if (!confirm('Enable UFW firewall now? Make sure SSH and web ports are allowed.')) return;
    await runFirewallAction('/firewall/enable', { method: 'POST' }, 'Enabling firewall...');
  }
  async function disableFirewall() {
    if (!confirm('Disable UFW firewall?')) return;
    await runFirewallAction('/firewall/disable', { method: 'POST' }, 'Disabling firewall...');
  }
  async function reloadFirewall() { await runFirewallAction('/firewall/reload', { method: 'POST' }, 'Reloading firewall...'); }
  async function openFirewallPort() { await runFirewallAction('/firewall/allow-port', { method: 'POST', body: JSON.stringify({ port: firewallPort, protocol: firewallProtocol }) }, 'Opening port...'); }
  async function allowFirewallIp() { await runFirewallAction('/firewall/allow-ip', { method: 'POST', body: JSON.stringify({ ip: firewallAllowIp, port: firewallAllowPort || null, protocol: firewallAllowProtocol }) }, 'Allowing IP...'); }
  async function blockFirewallIp() {
    if (!confirm(`Block ${firewallBlockIp || 'this IP'}?`)) return;
    await runFirewallAction('/firewall/block-ip', { method: 'POST', body: JSON.stringify({ ip: firewallBlockIp, port: firewallBlockPort || null, protocol: firewallBlockProtocol }) }, 'Blocking IP...');
  }
  async function deleteFirewallRule() {
    if (!firewallDeleteNumber) return;
    if (!confirm(`Delete UFW rule #${firewallDeleteNumber}?`)) return;
    await runFirewallAction(`/firewall/rules/${encodeURIComponent(firewallDeleteNumber)}`, { method: 'DELETE' }, 'Deleting rule...');
    setFirewallDeleteNumber('');
  }

  async function loadUpdates() {
    const data = await request('/updates/status', {}, 'Loading update status...');
    if (data) setUpdatesStatus(data);
  }

  async function runOsUpdate() {
    if (!confirm('Run apt-get update && apt-get upgrade now?')) return;
    const data = await request('/updates/os/run', { method: 'POST' }, 'Updating OS packages...');
    if (data) { setNotice((data.stdout || data.stderr || 'OS update finished.').trim()); await loadUpdates(); }
  }

  async function saveOsAutoUpdate() {
    const data = await request('/updates/os/auto', { method: 'POST', body: JSON.stringify(osAutoUpdate) }, 'Saving OS auto update...');
    if (data) { setNotice((data.stdout || data.stderr || 'OS auto update saved.').trim()); await loadUpdates(); }
  }

  async function runPanelUpdate() {
    if (!confirm('Update BPanel from GitHub now? The API may restart.')) return;
    const data = await request('/updates/panel/run', { method: 'POST' }, 'Updating BPanel...');
    if (data) setNotice((data.stdout || data.stderr || 'Panel update finished.').trim());
  }

  async function savePanelAutoUpdate() {
    const data = await request('/updates/panel/auto', { method: 'POST', body: JSON.stringify(panelAutoUpdate) }, 'Saving panel auto update...');
    if (data) { setNotice((data.stdout || data.stderr || 'Panel auto update saved.').trim()); await loadUpdates(); }
  }

  // Auto Update functions
  async function loadUpdateStatus() {
    const data = await request('/update/current');
    if (data) setUpdateStatus(data);
  }

  async function checkForUpdates() {
    const data = await request('/update/available');
    if (data) setAvailableUpdate(data);
  }

  async function downloadUpdate(version) {
    const data = await request(`/update/download/${encodeURIComponent(version)}`, { method: 'POST' }, `Downloading update ${version}...`);
    if (data?.success) {
      setNotice(`Downloaded update ${version}`);
      await checkForUpdates();
    }
    return data;
  }

  async function installUpdate(version) {
    if (!confirm(`Install update ${version}? A backup will be created first.`)) return;
    const data = await request(`/update/install/${encodeURIComponent(version)}`, { method: 'POST' }, `Installing update ${version}...`);
    if (data?.success) {
      setNotice(data.message || `Successfully installed ${version}`);
      await loadUpdateStatus();
    }
    return data;
  }

  async function createUpdateBackup() {
    const data = await request('/update/backup', { method: 'POST' }, 'Creating backup...');
    if (data?.success) {
      setNotice(`Backup created: ${data.backup_id}`);
      await loadUpdateBackups();
    }
    return data;
  }

  async function loadUpdateBackups() {
    const data = await request('/update/backups');
    if (data?.backups) setUpdateBackups(data.backups);
  }

  async function restoreUpdateBackup(backupId) {
    if (!confirm(`Restore from backup ${backupId}?`)) return;
    const data = await request(`/update/restore/${encodeURIComponent(backupId)}`, { method: 'POST' }, `Restoring from backup ${backupId}...`);
    if (data?.success) {
      setNotice('Successfully restored from backup');
      await loadUpdateStatus();
    }
    return data;
  }

  async function deleteUpdateBackup(backupId) {
    if (!confirm(`Delete backup ${backupId}? This cannot be undone.`)) return;
    const data = await request(`/update/backup/${encodeURIComponent(backupId)}`, { method: 'DELETE' }, 'Deleting backup...');
    if (data?.success) {
      setNotice('Backup deleted');
      await loadUpdateBackups();
    }
  }

  async function rollbackUpdate() {
    if (!confirm('Rollback to previous version? This will use the most recent backup.')) return;
    const data = await request('/update/rollback', { method: 'POST' }, 'Rolling back...');
    if (data?.success) {
      setNotice('Successfully rolled back');
      await loadUpdateStatus();
    }
    return data;
  }

  async function loadUpdateSettings() {
    const data = await request('/update/settings');
    if (data) setUpdateSettings(data);
  }

  async function saveUpdateSettings(settings) {
    const data = await request('/update/settings', { method: 'PUT', body: JSON.stringify(settings) }, 'Saving update settings...');
    if (data?.success) {
      setNotice('Update settings saved');
      await loadUpdateSettings();
    }
    return data;
  }

  async function loadUpdateLogs() {
    const data = await request('/update/logs');
    if (data?.logs) setUpdateLogs(data.logs);
  }

  async function loadMonitorData() {
    const data = await request('/monitor/all');
    if (data) setMonitorData(data);
  }

  // WebServer functions
  async function loadWebEngines() {
    const [enginesData, currentData] = await Promise.all([
      request('/webserver/engines'),
      request('/webserver/current'),
    ]);
    if (enginesData) setWebEngines(enginesData);
    if (currentData) setCurrentEngine(currentData);
  }

  async function switchWebEngine(engine) {
    if (!engine) return;
    const data = await request('/webserver/switch', { method: 'POST', body: JSON.stringify({ engine }) }, `Switching to ${engine}...`);
    if (data) { setNotice(`Switched to ${engine}. Service restarted.`); await loadWebEngines(); await checkAllServices(); }
  }

  async function checkSafety() {
    const data = await request('/webserver/safety-check', {}, 'Running safety check...');
    if (data) setSafetyCheck(data);
  }

  async function restoreConfig() {
    const data = await request('/webserver/restore', { method: 'POST' }, 'Restoring config...');
    if (data) { setNotice('Original config restored. Web server reloaded.'); await checkSafety(); }
  }

  async function loadWebsiteEngines() {
    const data = await request('/webserver/websites');
    if (data) setWebsitesWithEngines(Array.isArray(data) ? data : []);
  }

  async function setWebsiteEngine(websiteId, engine) {
    const data = await request(`/webserver/websites/${websiteId}/engine`, { method: 'PUT', body: JSON.stringify({ engine }) }, `Setting ${engine} for site...`);
    if (data) { setNotice(`Updated web engine for site.`); await loadWebsiteEngines(); }
  }

  async function loadEngineStatus(engine) {
    const data = await request(`/webserver/${engine}/status`);
    if (data) setWebserverStatus(prev => ({ ...prev, [engine]: data }));
  }

  async function repairEngine(engine) {
    const data = await request(`/webserver/${engine}/repair`, { method: 'POST' }, `Repairing ${engine}...`);
    if (data) { setNotice(data.message || `Repair completed for ${engine}.`); await loadEngineStatus(engine); }
  }

  // PHP Management functions
  async function loadPhpVersions() {
    const data = await request('/php/versions');
    if (data) setPhpVersions(Array.isArray(data) ? data : []);
  }

  async function loadPhpAvailableVersions() {
    const data = await request('/php/versions/available');
    if (data) setPhpAvailableVersions(Array.isArray(data) ? data : []);
  }

  async function installPhpVersion(version) {
    if (!version) return;
    if (!confirm(`Install PHP ${version}?`)) return;
    const data = await request(`/php/versions/${version}/install`, { method: 'POST' }, `Installing PHP ${version}...`);
    if (data) {
      setNotice(data.message || `PHP ${version} installation started.`);
      await loadPhpVersions();
      await loadPhpAvailableVersions();
    }
  }

  async function loadPhpExtensions() {
    const data = await request(`/php/${selectedPhpVersion}/extensions`);
    if (data) setPhpExtensions(Array.isArray(data) ? data : []);
  }

  async function installPhpExtension(ext) {
    if (!ext || !selectedPhpVersion) return;
    const data = await request(`/php/${selectedPhpVersion}/extensions/${ext}/install`, { method: 'POST' }, `Installing ${ext}...`);
    if (data) {
      setNotice(data.message || `Extension ${ext} installation started.`);
      await loadPhpExtensions();
    }
  }

  async function loadPhpConfig() {
    const data = await request(`/php/${selectedPhpVersion}/config`);
    if (data) setPhpConfig(prev => ({ ...prev, ...data, php_version: selectedPhpVersion }));
  }

  async function updatePhpConfig() {
    const data = await request(`/php/${selectedPhpVersion}/config`, {
      method: 'PUT',
      body: JSON.stringify({
        ...phpConfig,
        max_execution_time: Number(phpConfig.max_execution_time),
        max_input_time: Number(phpConfig.max_input_time),
        max_input_vars: Number(phpConfig.max_input_vars),
        opcache_max_files: Number(phpConfig.opcache_max_files),
      }),
    }, 'Updating PHP config...');
    if (data) {
      setNotice(data.message || 'PHP config updated.');
      await loadPhpConfig();
    }
  }

  async function loadPhpInfo() {
    const data = await request(`/php/${selectedPhpVersion}/phpinfo`);
    if (data) setPhpInfo(data);
  }

  async function loadPhpSlowlog() {
    const data = await request(`/php/${selectedPhpVersion}/slowlog`);
    if (data) setPhpSlowlog(data);
  }

  async function loadPhpFpmPools() {
    const data = await request(`/php/${selectedPhpVersion}/fpm/pools`);
    if (data) setPhpFpmPools(Array.isArray(data) ? data : []);
  }

  async function restartPhpFpm() {
    if (!confirm(`Restart PHP ${selectedPhpVersion}-FPM?`)) return;
    const data = await request(`/php/${selectedPhpVersion}/fpm/restart`, { method: 'POST' }, `Restarting PHP ${selectedPhpVersion}-FPM...`);
    if (data) {
      setNotice(data.message || `PHP ${selectedPhpVersion}-FPM restarted.`);
    }
  }

  async function optimizePhp() {
    const data = await request(`/php/${selectedPhpVersion}/optimize`, { method: 'POST' }, 'Optimizing PHP...');
    if (data) {
      setNotice(data.message || 'PHP optimized.');
      await loadPhpConfig();
    }
  }

  // Mail Server functions
  async function loadMailDomains() {
    const data = await request('/mail/domains');
    if (data) setMailDomains(Array.isArray(data) ? data : []);
  }

  async function loadMailSettings() {
    const data = await request('/mail/settings');
    if (data) setMailSettings(data);
  }

  async function loadMailStatus() {
    const data = await request('/mail/status');
    if (data) setMailSettings(prev => ({ ...prev, status: data }));
  }

  async function addMailDomain() {
    if (!newMailDomain.domain) { setError('Please enter a domain name.'); return; }
    const data = await request('/mail/domains', {
      method: 'POST',
      body: JSON.stringify({ domain: newMailDomain.domain, quota_gb: Number(newMailDomain.quota_gb) || 10 }),
    }, 'Adding mail domain...');
    if (data) {
      setNotice(`Added mail domain ${newMailDomain.domain}`);
      setNewMailDomain({ domain: '', quota_gb: 10 });
      await loadMailDomains();
    }
  }

  async function deleteMailDomain(domain) {
    if (!confirm(`Delete mail domain ${domain}? This will delete all mailboxes and emails.`)) return;
    const data = await request(`/mail/domains/${encodeURIComponent(domain)}`, { method: 'DELETE' }, 'Deleting mail domain...');
    if (data) {
      setNotice(`Deleted mail domain ${domain}`);
      if (selectedDomain === domain) setSelectedDomain('');
      await loadMailDomains();
    }
  }

  async function saveMailSettings(settings) {
    const data = await request('/mail/settings', {
      method: 'PUT',
      body: JSON.stringify(settings),
    }, 'Saving mail settings...');
    if (data) {
      setMailSettings(data);
      setNotice('Mail settings saved.');
    }
  }

  async function loadMailboxes(domain = selectedDomain) {
    if (!domain) return;
    const data = await request(`/mail/domains/${encodeURIComponent(domain)}/mailboxes`);
    if (data) setMailboxes(Array.isArray(data) ? data : []);
  }

  async function addMailbox() {
    if (!selectedDomain) { setError('Please select a domain first.'); return; }
    if (!newMailbox.username) { setError('Please enter a username.'); return; }
    const body = {
      username: newMailbox.username,
      password: newMailbox.password,
      quota_gb: Number(newMailbox.quota_gb) || 1,
    };
    const data = await request(`/mail/domains/${encodeURIComponent(selectedDomain)}/mailboxes`, {
      method: 'POST',
      body: JSON.stringify(body),
    }, 'Creating mailbox...');
    if (data) {
      setNotice(`Created mailbox ${newMailbox.username}@${selectedDomain}`);
      setNewMailbox({ username: '', password: '', quota_gb: 1 });
      await loadMailboxes();
    }
  }

  async function deleteMailbox(username) {
    if (!confirm(`Delete mailbox ${username}@${selectedDomain}?`)) return;
    const data = await request(`/mail/domains/${encodeURIComponent(selectedDomain)}/mailboxes/${encodeURIComponent(username)}`, { method: 'DELETE' }, 'Deleting mailbox...');
    if (data) {
      setNotice(`Deleted mailbox ${username}@${selectedDomain}`);
      if (selectedMailbox === username) setSelectedMailbox('');
      await loadMailboxes();
    }
  }

  async function changeMailboxPassword(username) {
    const password = prompt(`Enter a new password for ${username}:`);
    if (!password) return;
    const data = await request(`/mail/domains/${encodeURIComponent(selectedDomain)}/mailboxes/${encodeURIComponent(username)}/password`, {
      method: 'PUT',
      body: JSON.stringify({ password }),
    }, 'Changing password...');
    if (data?.message) setNotice(data.message);
  }

  async function batchCreateMailboxes() {
    const csv = prompt('Enter mailboxes in CSV format (username,password,quota_gb per line):\nExample:\njohn,password123,1\njane,password456,2');
    if (!csv) return;
    const lines = csv.trim().split('\n').filter(Boolean);
    const mailboxes_list = lines.map(line => {
      const [username, password, quota_gb] = line.split(',').map(s => s.trim());
      return { username, password, quota_gb: Number(quota_gb) || 1 };
    });
    const data = await request(`/mail/domains/${encodeURIComponent(selectedDomain)}/mailboxes/batch`, {
      method: 'POST',
      body: JSON.stringify({ mailboxes: mailboxes_list }),
    }, 'Batch creating mailboxes...');
    if (data?.message) {
      setNotice(data.message);
      await loadMailboxes();
    }
  }

  async function loadEmails(domain = selectedDomain, username = selectedMailbox, folder = mailFolder) {
    if (!domain || !username) return;
    const data = await request(`/mail/domains/${encodeURIComponent(domain)}/mailboxes/${encodeURIComponent(username)}/emails?folder=${encodeURIComponent(folder)}`);
    if (data) setEmails(Array.isArray(data) ? data : []);
  }

  async function moveEmail(emailId, toFolder) {
    const data = await request(`/mail/domains/${encodeURIComponent(selectedDomain)}/mailboxes/${encodeURIComponent(selectedMailbox)}/emails/${emailId}/move`, {
      method: 'POST',
      body: JSON.stringify({ folder: toFolder }),
    }, 'Moving email...');
    if (data?.message) {
      setNotice(data.message);
      await loadEmails();
    }
  }

  async function deleteEmail(emailId) {
    if (!confirm('Delete this email?')) return;
    await moveEmail(emailId, 'trash');
  }

  // FTP Manager functions
  async function loadFtpStatus() {
    const data = await request('/ftp/status');
    if (data) setFtpStatus(data);
  }

  async function loadFtpUsers() {
    const data = await request('/ftp/users');
    if (data) setFtpUsers(Array.isArray(data) ? data : []);
  }

  async function createFtpUser() {
    if (!newFtpUser.username) { setError('Please enter a username.'); return; }
    if (!newFtpUser.website_id) { setError('Please select a website.'); return; }
    const body = {
      username: newFtpUser.username.toLowerCase(),
      website_id: Number(newFtpUser.website_id),
    };
    if (!newFtpUser.auto_password && newFtpUser.password) {
      body.password = newFtpUser.password;
    }
    const data = await request('/ftp/users', { method: 'POST', body: JSON.stringify(body) }, 'Creating FTP user...');
    if (data) {
      setNotice(data.password ? `Created FTP user: ${data.username}\nPassword: ${data.password}` : `Created FTP user: ${data.username}`);
      setNewFtpUser({ username: '', website_id: '', auto_password: true, password: '' });
      await loadFtpUsers();
    }
  }

  async function deleteFtpUser(username) {
    if (!confirm(`Delete FTP user ${username}?`)) return;
    const data = await request(`/ftp/users/${encodeURIComponent(username)}`, { method: 'DELETE' }, `Deleting FTP user ${username}...`);
    if (data) {
      setNotice(`Deleted FTP user ${username}`);
      await loadFtpUsers();
    }
  }

  async function changeFtpPassword(username) {
    const password = prompt(`Enter a new password for FTP user ${username}:`);
    if (!password) return;
    const data = await request(`/ftp/users/${encodeURIComponent(username)}/password`, {
      method: 'PUT',
      body: JSON.stringify({ password }),
    }, `Changing password for ${username}...`);
    if (data?.message) setNotice(data.message);
  }

  async function configureFtp() {
    const data = await request('/ftp/configure', { method: 'POST' }, 'Configuring FTP server...');
    if (data?.message) {
      setNotice(data.message);
      await loadFtpStatus();
    }
  }

  // Nginx Proxy functions
  async function loadProxyConfigs() {
    const data = await request('/nginx-proxy/configs');
    if (data) setProxyConfigs(Array.isArray(data) ? data : []);
  }

  async function loadProxyTemplates() {
    const data = await request('/nginx-proxy/templates');
    if (data) setProxyTemplates(Array.isArray(data) ? data : []);
  }

  async function loadProxyStatus() {
    const data = await request('/nginx-proxy/status');
    if (data) setProxyStatus(data);
  }

  async function createProxyConfig() {
    if (!newProxyConfig.domain) { setError('Please enter a domain name.'); return; }
    if (!newProxyConfig.target_url) { setError('Please enter a target URL.'); return; }
    const body = {
      domain: newProxyConfig.domain,
      target_url: newProxyConfig.target_url,
      template: newProxyConfig.template,
      ssl_enabled: newProxyConfig.ssl_enabled,
      connect_timeout: Number(newProxyConfig.connect_timeout) || 60,
      send_timeout: Number(newProxyConfig.send_timeout) || 60,
      read_timeout: Number(newProxyConfig.read_timeout) || 60,
    };
    const data = await request('/nginx-proxy/configs', { method: 'POST', body: JSON.stringify(body) }, 'Creating proxy config...');
    if (data) {
      setNotice(`Created proxy config for ${data.domain || newProxyConfig.domain}`);
      resetProxyForm();
      await loadProxyConfigs();
    }
  }

  async function updateProxyConfig() {
    if (!editingProxy || !newProxyConfig.domain) return;
    const body = {
      target_url: newProxyConfig.target_url,
      template: newProxyConfig.template,
      ssl_enabled: newProxyConfig.ssl_enabled,
      connect_timeout: Number(newProxyConfig.connect_timeout) || 60,
      send_timeout: Number(newProxyConfig.send_timeout) || 60,
      read_timeout: Number(newProxyConfig.read_timeout) || 60,
    };
    const data = await request(`/nginx-proxy/configs/${encodeURIComponent(newProxyConfig.domain)}`, {
      method: 'PUT',
      body: JSON.stringify(body),
    }, 'Updating proxy config...');
    if (data) {
      setNotice(`Updated proxy config for ${newProxyConfig.domain}`);
      resetProxyForm();
      await loadProxyConfigs();
    }
  }

  async function deleteProxyConfig(domain) {
    if (!confirm(`Delete proxy config for ${domain}?`)) return;
    const data = await request(`/nginx-proxy/configs/${encodeURIComponent(domain)}`, { method: 'DELETE' }, `Deleting proxy config for ${domain}...`);
    if (data) {
      setNotice(`Deleted proxy config for ${domain}`);
      await loadProxyConfigs();
    }
  }

  async function toggleProxyConfig(config) {
    const data = await request(`/nginx-proxy/configs/${encodeURIComponent(config.domain)}`, {
      method: 'PATCH',
      body: JSON.stringify({ enabled: !config.enabled }),
    }, `${config.enabled ? 'Disabling' : 'Enabling'} proxy for ${config.domain}...`);
    if (data) {
      setNotice(`${config.enabled ? 'Disabled' : 'Enabled'} proxy for ${config.domain}`);
      await loadProxyConfigs();
    }
  }

  async function setupSsl(domain) {
    const data = await request(`/nginx-proxy/ssl/${encodeURIComponent(domain)}`, { method: 'POST' }, `Setting up SSL for ${domain}...`);
    if (data) {
      setNotice(data.message || `SSL setup initiated for ${domain}`);
      await loadProxyConfigs();
    }
  }

  async function renewSsl(domain) {
    const data = await request(`/nginx-proxy/ssl/${encodeURIComponent(domain)}/renew`, { method: 'POST' }, `Renewing SSL for ${domain}...`);
    if (data) {
      setNotice(data.message || `SSL renewal initiated for ${domain}`);
      await loadProxyConfigs();
    }
  }

  async function reloadNginx() {
    const data = await request('/nginx-proxy/reload', { method: 'POST' }, 'Reloading Nginx...');
    if (data) {
      setNotice(data.message || 'Nginx reloaded');
      await loadProxyStatus();
    }
  }

  async function restartNginx() {
    if (!confirm('Restart Nginx? Active connections may be interrupted.')) return;
    const data = await request('/nginx-proxy/restart', { method: 'POST' }, 'Restarting Nginx...');
    if (data) {
      setNotice(data.message || 'Nginx restarted');
      await loadProxyStatus();
    }
  }

  async function previewProxyConfig() {
    const data = await request('/nginx-proxy/configs/preview', {
      method: 'POST',
      body: JSON.stringify({
        domain: newProxyConfig.domain,
        target_url: newProxyConfig.target_url,
        template: newProxyConfig.template,
        ssl_enabled: newProxyConfig.ssl_enabled,
        connect_timeout: Number(newProxyConfig.connect_timeout) || 60,
        send_timeout: Number(newProxyConfig.send_timeout) || 60,
        read_timeout: Number(newProxyConfig.read_timeout) || 60,
      }),
    });
    if (data) {
      setPreviewConfig(data.config || data);
    }
  }

  function openProxyModal(config = null) {
    if (config) {
      setEditingProxy(config);
      setNewProxyConfig({
        domain: config.domain,
        target_url: config.target_url || '',
        template: config.template || 'default',
        ssl_enabled: config.ssl_enabled || false,
        connect_timeout: config.connect_timeout || 60,
        send_timeout: config.send_timeout || 60,
        read_timeout: config.read_timeout || 60,
      });
    } else {
      resetProxyForm();
    }
    setShowProxyModal(true);
  }

  function resetProxyForm() {
    setShowProxyModal(false);
    setEditingProxy(null);
    setNewProxyConfig({
      domain: '',
      target_url: '',
      template: 'default',
      ssl_enabled: false,
      connect_timeout: 60,
      send_timeout: 60,
      read_timeout: 60,
    });
    setShowAdvanced(false);
    setPreviewConfig(null);
  }

  // Python functions
  async function loadPythonVersion() {
    const data = await request('/python/version');
    if (data) setPythonVersion(data.version);
  }

  async function loadPythonVersions() {
    const data = await request('/python/versions');
    if (data?.versions) setPythonVersions(data.versions);
  }

  async function loadVenvs() {
    const data = await request('/python/venvs');
    if (data?.venvs) setVenvs(data.venvs);
  }

  async function createVenv() {
    if (!newVenvName) { setError('Please enter a venv name.'); return; }
    const data = await request('/python/venv', {
      method: 'POST',
      body: JSON.stringify({ name: newVenvName, python_version: newVenvVersion || undefined }),
    }, 'Creating virtual environment...');
    if (data) {
      setNotice(data.message || `Created virtual environment: ${newVenvName}`);
      setNewVenvName('');
      setNewVenvVersion('');
      await loadVenvs();
    }
  }

  async function deleteVenv(venvId) {
    if (!confirm(`Delete this virtual environment?`)) return;
    const data = await request(`/python/venv/${venvId}`, { method: 'DELETE' }, 'Deleting virtual environment...');
    if (data) {
      setNotice(data.message || 'Virtual environment deleted');
      if (selectedVenv?.id === venvId) setSelectedVenv(null);
      await loadVenvs();
    }
  }

  async function loadVenvPackages(venvId) {
    const data = await request(`/python/venv/${venvId}/packages`);
    if (data?.packages) {
      setVenvPackages(data.packages);
      const venv = venvs.find(v => v.id === venvId);
      setSelectedVenv(venv || { id: venvId, name: 'Unknown' });
    }
  }

  async function installVenvPackage(venvId) {
    if (!installPackageName) { setError('Please enter a package name.'); return; }
    const data = await request(`/python/venv/${venvId}/packages`, {
      method: 'POST',
      body: JSON.stringify({ package: installPackageName }),
    }, 'Installing package...');
    if (data?.message) setNotice(data.message);
    setInstallPackageName('');
    await loadVenvPackages(venvId);
  }

  async function uninstallVenvPackage(venvId, packageName) {
    if (!confirm(`Uninstall package '${packageName}'?`)) return;
    const data = await request(`/python/venv/${venvId}/packages/${encodeURIComponent(packageName)}`, { method: 'DELETE' }, 'Uninstalling package...');
    if (data?.message) setNotice(data.message);
    await loadVenvPackages(venvId);
  }

  async function loadPythonProcesses() {
    const data = await request('/python/processes');
    if (data?.processes) setPythonProcesses(data.processes);
  }

  // Go Project state
  const [goVersion, setGoVersion] = useState('');
  const [goVersions, setGoVersions] = useState([]);
  const [goProcesses, setGoProcesses] = useState([]);
  const [selectedProcess, setSelectedProcess] = useState(null);
  const [goLogs, setGoLogs] = useState('');
  const [goBuildPath, setGoBuildPath] = useState('');
  const [goRunPath, setGoRunPath] = useState('');
  const [goModulePath, setGoModulePath] = useState('');
  const [goModules, setGoModules] = useState([]);
  const [installingVersion, setInstallingVersion] = useState('');

  // Go Project functions
  async function loadGoVersion() {
    const data = await request('/golang/version');
    if (data?.version) setGoVersion(data.version);
  }

  async function loadGoVersions() {
    const data = await request('/golang/versions');
    if (data?.versions) setGoVersions(data.versions);
  }

  async function installGoVersion(version) {
    setInstallingVersion(version);
    const data = await request(`/golang/versions/${encodeURIComponent(version)}/install`, { method: 'POST' }, `Installing Go ${version}...`);
    if (data?.message) setNotice(data.message);
    await loadGoVersion();
    await loadGoVersions();
    setInstallingVersion('');
  }

  async function loadGoProcesses() {
    const data = await request('/golang/processes');
    if (data?.processes) setGoProcesses(data.processes);
  }

  async function stopGoProcess(name) {
    const data = await request(`/golang/processes/${encodeURIComponent(name)}/stop`, { method: 'POST' }, `Stopping ${name}...`);
    if (data?.message) setNotice(data.message);
    await loadGoProcesses();
  }

  async function restartGoProcess(name) {
    const data = await request(`/golang/processes/${encodeURIComponent(name)}/restart`, { method: 'POST' }, `Restarting ${name}...`);
    if (data?.message) setNotice(data.message);
    await loadGoProcesses();
  }

  async function viewGoProcessLogs(name) {
    setSelectedProcess(name);
    const data = await request(`/golang/processes/${encodeURIComponent(name)}/logs`);
    if (data?.logs) setGoLogs(data.logs);
    else setGoLogs(data?.message || 'No logs available');
  }

  async function buildGoProject() {
    if (!goBuildPath) { setError('Please enter the project path.'); return; }
    const data = await request('/golang/build', {
      method: 'POST',
      body: JSON.stringify({ path: goBuildPath }),
    }, 'Building Go project...');
    if (data?.message) setNotice(data.message);
  }

  async function runGoProject() {
    if (!goRunPath) { setError('Please enter the project path.'); return; }
    const data = await request('/golang/run', {
      method: 'POST',
      body: JSON.stringify({ path: goRunPath }),
    }, 'Running Go project...');
    if (data?.message) setNotice(data.message);
    await loadGoProcesses();
  }

  async function loadGoModules(path) {
    if (!path) return;
    const data = await request(`/golang/modules?path=${encodeURIComponent(path)}`);
    if (data?.modules) setGoModules(data.modules);
  }

  async function setupGoForWebsite(websiteId) {
    if (!websiteId) { setError('Please select a website.'); return; }
    const data = await request(`/golang/setup/${encodeURIComponent(websiteId)}`, { method: 'POST' }, 'Setting up Go for website...');
    if (data?.message) setNotice(data.message);
  }

  // Node.js functions
  async function loadNodeVersion() {
    const data = await request('/nodejs/version');
    if (data) setNodeVersion(data.version || data);
  }

  async function loadNodeVersions() {
    const data = await request('/nodejs/versions');
    if (data?.versions) setNodeVersions(data.versions);
    else if (Array.isArray(data)) setNodeVersions(data);
  }

  async function installNodeVersion(version) {
    setInstallingVersion(version);
    const data = await request(`/nodejs/versions/${encodeURIComponent(version)}/install`, { method: 'POST' }, `Installing Node.js ${version}...`);
    if (data?.message) setNotice(data.message);
    await loadNodeVersion();
    await loadNodeVersions();
    setInstallingVersion('');
  }

  async function loadPm2Processes() {
    const data = await request('/nodejs/pm2/processes');
    if (data?.processes) setPm2Processes(data.processes);
    else if (Array.isArray(data)) setPm2Processes(data);
  }

  async function restartPm2Process(name) {
    const data = await request(`/nodejs/pm2/processes/${encodeURIComponent(name)}/restart`, { method: 'POST' }, `Restarting ${name}...`);
    if (data?.message) setNotice(data.message);
    await loadPm2Processes();
  }

  async function stopPm2Process(name) {
    const data = await request(`/nodejs/pm2/processes/${encodeURIComponent(name)}/stop`, { method: 'POST' }, `Stopping ${name}...`);
    if (data?.message) setNotice(data.message);
    await loadPm2Processes();
  }

  async function deletePm2Process(name) {
    if (!confirm(`Delete PM2 process '${name}'?`)) return;
    const data = await request(`/nodejs/pm2/processes/${encodeURIComponent(name)}`, { method: 'DELETE' }, `Deleting ${name}...`);
    if (data?.message) setNotice(data.message);
    await loadPm2Processes();
  }

  async function loadPm2Logs(name, lines = 100) {
    setPm2LogModal(name);
    setPm2Logs({ content: '', lines });
    const data = await request(`/nodejs/pm2/processes/${encodeURIComponent(name)}/logs?lines=${encodeURIComponent(lines)}`);
    if (data?.logs) setPm2Logs({ content: data.logs, lines });
    else if (typeof data === 'string') setPm2Logs({ content: data, lines });
    else setPm2Logs({ content: data?.message || 'No logs available', lines });
  }

  async function refreshPm2Logs() {
    if (pm2LogModal) {
      await loadPm2Logs(pm2LogModal, pm2Logs.lines);
    }
  }

  async function setupPm2ForWebsite(websiteId) {
    if (!websiteId) { setError('Please select a website.'); return; }
    const data = await request(`/nodejs/pm2/setup/${encodeURIComponent(websiteId)}`, { method: 'POST' }, 'Setting up PM2 for website...');
    if (data?.message) setNotice(data.message);
    await loadPm2Processes();
  }

  useEffect(() => {
    if (isAuthenticated) {
      refreshAll();
    }
  }, [isAuthenticated]);

  useEffect(() => {
    if (!isAuthenticated || !standaloneEditor) return;
    setSelectedWebsiteId(standaloneEditor.websiteId);
    setFilePath(standaloneEditor.path);
    readFile(standaloneEditor.path, standaloneEditor.websiteId);
  }, [isAuthenticated, standaloneEditor]);

  useEffect(() => {
    if (!standaloneEditor || !isAuthenticated) return undefined;
    const handler = event => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
        event.preventDefault();
        writeFile();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [standaloneEditor, isAuthenticated, selectedWebsiteId, filePath, fileContent]);

  useEffect(() => {
    if (!isAuthenticated || page !== 'dashboard') return undefined;
    loadResourceUsage();
    const timer = setInterval(loadResourceUsage, 5000);
    return () => clearInterval(timer);
  }, [isAuthenticated, page]);

  useEffect(() => {
    if (!isAuthenticated || page !== 'services') return undefined;
    checkAllServices();
    const timer = setInterval(checkAllServices, 10000);
    return () => clearInterval(timer);
  }, [isAuthenticated, page]);

  useEffect(() => { if (selectedWebsiteId && page === 'backups') listBackups(); }, [selectedWebsiteId, page]);

  useEffect(() => { if (selectedWebsiteId && page === 'files') listFiles('public_html'); }, [selectedWebsiteId, page]);

  useEffect(() => { if (selectedBackupUserId && page === 'backups') listUserBackups(selectedBackupUserId); }, [selectedBackupUserId, page]);

  useEffect(() => {
    if (isAuthenticated && page === 'users') loadUsers();
    if (isAuthenticated && page === 'php') loadPhpConfig();
    if (isAuthenticated && page === 'firewall') loadFirewall();
    if (isAuthenticated && page === 'security') loadTwoFactorStatus();
    if (isAuthenticated && page === 'settings') loadPanelSettings();
    if (isAuthenticated && page === 'updates' && currentUser?.role === 'admin') loadUpdates();
    if (isAuthenticated && page === 'update' && currentUser?.role === 'admin') { loadUpdateStatus(); loadUpdateSettings(); loadUpdateBackups(); loadUpdateLogs(); }
    if (isAuthenticated && page === 'backups' && currentUser?.role === 'admin') { loadUsers(); loadSftpTargets(); loadBackupSchedules(); loadRestoreBackups(); }
    if (isAuthenticated && page === 'monitor') loadMonitorData();
    if (isAuthenticated && page === 'ftp') { loadFtpStatus(); loadFtpUsers(); }
    if (isAuthenticated && page === 'mail' && currentUser?.role === 'admin') { loadMailDomains(); loadMailSettings(); }
    if (isAuthenticated && page === 'python') { loadPythonVersion(); loadPythonVersions(); loadVenvs(); loadPythonProcesses(); }
    if (isAuthenticated && page === 'docker') { loadDockerStatus(); loadContainers(); loadImages(); }
    if (isAuthenticated && page === 'golang') { loadGoVersion(); loadGoVersions(); loadGoProcesses(); }
    if (isAuthenticated && page === 'nodejs') { loadNodeVersion(); loadNodeVersions(); loadPm2Processes(); }
    if (isAuthenticated && page === 'webserver' && currentUser?.role === 'admin') { loadWebEngines(); loadWebsiteEngines(); }
    if (isAuthenticated && page === 'proxy') { loadProxyConfigs(); loadProxyTemplates(); loadProxyStatus(); }
  }, [isAuthenticated, page, currentUser?.role]);

  useEffect(() => {
    if (!isAuthenticated || page !== 'monitor' || !autoRefresh) return undefined;
    loadMonitorData();
    const timer = setInterval(loadMonitorData, refreshInterval);
    return () => clearInterval(timer);
  }, [isAuthenticated, page, autoRefresh, refreshInterval]);

  useEffect(() => { setMobileMenuOpen(false); }, [page]);

  const isAdmin = currentUser?.role === 'admin';

  function roleLabel(role) {
    return role === 'admin' ? 'Admin' : 'End user';
  }

  const navItems = [
    ['dashboard', 'Dashboard', Home],
    ['websites', 'Websites', Globe],
    ['ssl', 'SSL', Lock],
    ['databases', 'Database', Database],
    ['cron', 'Cron', Clock],
    ['files', 'File manager', FolderOpen],
    ['backups', 'Backups', Archive],
    ['security', 'Security', Shield],
    ...(isAdmin ? [['php', 'PHP', Code]] : []),
    ...(isAdmin ? [['firewall', 'Firewall', Shield]] : []),
    ...(isAdmin ? [['proxy', 'Proxy', Globe]] : []),
    ...(isAdmin ? [['webserver', 'WebServer', ServerCog]] : []),
    ...(isAdmin ? [['updates', 'Updates', RefreshCw]] : []),
    ...(isAdmin ? [['update', 'Auto Update', Download]] : []),
    ['services', 'Services Status', Server],
    ...(isAdmin ? [['ftp', 'FTP Manager', Server]] : []),
    ...(isAdmin ? [['mail', 'Mail', Mail]] : []),
    ['docker', 'Docker', Container],
    ...(isAdmin ? [['golang', 'Go', Hexagon]] : []),
    ...(isAdmin ? [['nodejs', 'Node.js', Box]] : []),
    ...(isAdmin ? [['python', 'Python', TerminalIcon]] : []),
    ...(isAdmin ? [['users', 'Panel users', Users]] : []),
    ...(isAdmin ? [['settings', 'Settings', SettingsIcon]] : []),
    ['monitor', 'Monitor', Activity],
    ['logs', 'Logs', FileText],
    ...(isAdmin ? [['backup', 'Backup', Package]] : []),
  ];

  const currentSite = websites.find(site => String(site.id) === String(selectedWebsiteId));
  const activeNavItem = navItems.find(([key]) => key === page) || navItems[0];

  function websiteUrl(site) {
    const value = (site?.domain || '').trim();
    if (/^https?:\/\//i.test(value)) return value;
    return `${site?.ssl_enabled ? 'https' : 'http'}://${value}`;
  }

  function parentFilePath(path) {
    const parts = String(path || '').split('/').filter(Boolean);
    parts.pop();
    return parts.join('/');
  }

  function fileBreadcrumbs(path) {
    const parts = String(path || '').split('/').filter(Boolean);
    let current = '';
    return parts.map(part => {
      current = current ? `${current}/${part}` : part;
      return { label: part, path: current };
    });
  }

  function isArchiveFile(item) {
    const name = (item?.name || '').toLowerCase();
    return !item?.is_dir && (name.endsWith('.zip') || name.endsWith('.tar.gz') || name.endsWith('.tgz'));
  }

  function isTextEditable(item) {
    if (!item || item.is_dir) return false;
    const name = (item.name || '').toLowerCase();
    const editableDotfiles = new Set(['.env', '.env.example', '.htaccess', '.user.ini', '.gitignore', '.gitattributes']);
    return editableDotfiles.has(name) || /\.(txt|md|json|css|js|jsx|ts|tsx|html|htm|xml|yml|yaml|ini|conf|log|php|env|htaccess)$/.test(name) || !name.includes('.');
  }

  function toggleFileSelection(path) {
    setSelectedFilePaths(prev => prev.includes(path) ? prev.filter(item => item !== path) : [...prev, path]);
  }

  function toggleAllFiles() {
    setSelectedFilePaths(prev => prev.length === files.length ? [] : files.map(item => item.path));
  }

  function editorLanguage(path) {
    const name = String(path || '').toLowerCase();
    if (/\.php\d?$/.test(name) || name.endsWith('.phtml')) return 'PHP';
    if (/\.(js|jsx|ts|tsx)$/.test(name)) return 'JavaScript';
    if (/\.css$/.test(name)) return 'CSS';
    if (/\.html?$/.test(name)) return 'HTML';
    if (/\.json$/.test(name)) return 'JSON';
    if (/\.ya?ml$/.test(name)) return 'YAML';
    if (/\.(conf|ini|env|htaccess)$/.test(name)) return 'Config';
    return 'Text';
  }

  function WebsiteSelect() {
    return <select value={selectedWebsiteId} onChange={e => setSelectedWebsiteId(e.target.value)}>
      <option value="">-- Select website --</option>
      {websites.map(site => <option key={site.id} value={site.id}>{site.domain}</option>)}
    </select>;
  }

  function EmptyState({ icon: Icon = AlertCircle, message = 'No data yet' }) {
    return <div className="empty-state"><Icon size={40} /><p>{message}</p></div>;
  }

  function formatBytes(value) {
    const amount = Number(value);
    if (!Number.isFinite(amount) || amount < 0) return '--';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let size = amount;
    let unit = 0;
    while (size >= 1024 && unit < units.length - 1) { size /= 1024; unit += 1; }
    return `${size >= 10 || unit === 0 ? size.toFixed(0) : size.toFixed(1)} ${units[unit]}`;
  }

  function formatPercent(value) {
    const amount = Number(value);
    if (!Number.isFinite(amount)) return '--';
    return `${Math.round(amount)}%`;
  }

  function clampPercent(value) {
    const amount = Number(value);
    if (!Number.isFinite(amount)) return 0;
    return Math.max(0, Math.min(100, amount));
  }

  function storageLimitBytes(user) {
    if (!user) return null;
    if (user.storage_limit_bytes === null) return null;
    if (user.storage_limit_bytes !== undefined) return user.storage_limit_bytes;
    return Number(user.storage_limit_mb || 0) * 1024 * 1024;
  }

  function storageUsageText(user) {
    const used = Number(user?.storage_used_bytes || 0);
    const limit = storageLimitBytes(user);
    return limit === null ? `${formatBytes(used)} / Unlimited` : `${formatBytes(used)} / ${formatBytes(limit)}`;
  }

  function ResourceCard({ icon: Icon, label, value, detail, percent }) {
    const safePercent = percent == null ? null : clampPercent(percent);
    return <article className="resource-card">
      <div className="resource-head"><span className="resource-icon"><Icon size={16}/></span><span>{label}</span></div>
      <strong>{value}</strong>
      {safePercent !== null && <div className="resource-track"><span style={{ width: `${safePercent}%` }}></span></div>}
      <small>{detail}</small>
    </article>;
  }

  function renderDashboard() {
    const cpu = resourceUsage?.cpu || {};
    const memory = resourceUsage?.memory || {};
    const disk = resourceUsage?.disk || {};
    const network = resourceUsage?.network || {};
    const networkTotal = (Number(network.rx_per_sec) || 0) + (Number(network.tx_per_sec) || 0);
    return <>
      <section className="resource-grid">
        <ResourceCard icon={Cpu} label="CPU" value={formatPercent(cpu.percent)} percent={cpu.percent} detail={cpu.load?.length ? `Load ${cpu.load.join(' / ')}` : `${cpu.cores || '--'} cores`} />
        <ResourceCard icon={MemoryStick} label="RAM" value={formatPercent(memory.percent)} percent={memory.percent} detail={`${formatBytes(memory.used)} / ${formatBytes(memory.total)}`} />
        <ResourceCard icon={HardDrive} label="Disk" value={formatPercent(disk.percent)} percent={disk.percent} detail={`${formatBytes(disk.used)} / ${formatBytes(disk.total)}`} />
        <ResourceCard icon={Network} label="Network" value={`${formatBytes(networkTotal)}/s`} detail={`Down ${formatBytes(network.rx_per_sec)}/s / Up ${formatBytes(network.tx_per_sec)}/s`} />
      </section>
      <section className="stats-grid">
        <div className="stat-card"><strong>{websites.length}</strong><span>Websites</span></div>
        <div className="stat-card"><strong>{databases.length}</strong><span>Databases</span></div>
        <div className="stat-card"><strong>{websites.filter(s => s.ssl_enabled).length}</strong><span>SSL active</span></div>
        {currentUser && !isAdmin && <div className="stat-card"><strong>{formatBytes(currentUser.storage_used_bytes)}</strong><span>Storage / {formatBytes(storageLimitBytes(currentUser))}</span></div>}
      </section>
      {websites.length > 0 && <section className="section">
        <h2>Quick overview</h2>
        <div className="site-grid">
          {websites.slice(0, 4).map(site => <article className="site-card" key={site.id}>
            <div className="site-head">
              <div><a className="site-link" href={websiteUrl(site)} target="_blank" rel="noopener noreferrer">{site.domain}</a></div>
            </div>
            <div className="site-meta">
              <span className={`badge site-ssl-badge ${site.ssl_enabled ? 'ok' : ''}`}>{site.ssl_enabled ? 'SSL' : 'No SSL'}</span>
              <span>PHP <strong>{site.php_version}</strong></span>
              <span>Status <strong>{site.status}</strong></span>
            </div>
          </article>)}
        </div>
        {websites.length > 4 && <p className="hint" style={{marginTop:8}}>Showing 4 of {websites.length} websites. Go to Websites for full list.</p>}
      </section>}
      {websites.length === 0 && <section className="section">
        <EmptyState icon={Globe} message="No websites yet. Create your first WordPress site from the Websites menu." />
      </section>}
    </>;
  }

  function renderWebsites() {
    const wpFieldsEnabled = siteType === 'wordpress' && installWordPress;
    return <>
      <section className="section">
        <h2>Create website</h2>
        <div className="form-row create-site-row">
          <input value={domain} onChange={e => setDomain(e.target.value)} placeholder="domain.com" />
          <select value={siteType} onChange={e => setSiteType(e.target.value)}>
            <option value="wordpress">WordPress</option>
            <option value="php">Static/PHP</option>
            <option value="static">Static only</option>
          </select>
          <select value={phpVersion} onChange={e => setPhpVersion(e.target.value)}>
            <option value="8.3">PHP 8.3</option>
            <option value="8.4">PHP 8.4</option>
          </select>
          <input value={adminEmail} onChange={e => setAdminEmail(e.target.value)} placeholder="admin@domain.com" disabled={!wpFieldsEnabled} />
          <input value={wpAdminUser} onChange={e => setWpAdminUser(e.target.value)} placeholder="WP admin user" disabled={!wpFieldsEnabled} />
          <input value={wpAdminPassword} onChange={e => setWpAdminPassword(e.target.value)} placeholder="WP admin password" type="password" disabled={!wpFieldsEnabled} />
          <button disabled={!!loading || !domain} onClick={createWordPress}><Plus size={15}/> Create</button>
        </div>
        {siteType === 'wordpress' && <label className="check-line">
          <input type="checkbox" checked={installWordPress} onChange={e => setInstallWordPress(e.target.checked)} />
          Install WordPress (creates database, downloads WP, configures vhost)
        </label>}
        <label className="check-line">
          <input type="checkbox" checked={installSslAfterCreate} onChange={e => setInstallSslAfterCreate(e.target.checked)} />
          Install SSL after creating
        </label>
        <p className="hint">{wpFieldsEnabled
          ? 'WordPress will be installed and the panel will show the URL, admin account, and password after creation.'
          : siteType === 'php'
            ? 'A PHP-FPM vhost will be created with public_html/ folder. Upload your PHP or static files via File Manager.'
            : 'A static-only Nginx vhost will be created. PHP files can be uploaded but will not execute.'}</p>
      </section>
      <section className="section">
        <div className="section-title">
          <h2>Website list</h2>
          <button disabled={!!loading} onClick={refreshAll}><RefreshCw size={15}/> Refresh</button>
        </div>
        {websites.length === 0 && <EmptyState icon={Globe} message="No websites yet." />}
        <div className="site-grid">
          {websites.map(site => <article className="site-card" key={site.id}>
            <div className="site-head">
              <div>
                <a className="site-link" href={websiteUrl(site)} target="_blank" rel="noopener noreferrer">{site.domain}</a>
                <small>{site.root_path}</small>
              </div>
            </div>
            <div className="site-meta">
              <span className={`badge site-ssl-badge ${site.ssl_enabled ? 'ok' : ''}`}>{site.ssl_enabled ? 'SSL OK' : 'No SSL'}</span>
              <span>Type <strong>{site.app_type || 'wordpress'}</strong></span>
              <span>PHP <strong>{site.php_version}</strong></span>
              <span>Status <strong>{site.status}</strong></span>
              {site.nginx_custom && <span className="badge ok">Custom Nginx</span>}
              {site.waf_enabled && <span className="badge ok">WAF</span>}
            </div>
            <div className="actions">
              {site.app_type !== 'static' && <select value={websitePhpVersions[site.id] || site.php_version || '8.3'} onChange={e => setWebsitePhpVersions(prev => ({ ...prev, [site.id]: e.target.value }))}>
                <option value="8.3">PHP 8.3</option><option value="8.4">PHP 8.4</option>
              </select>}
              {site.app_type !== 'static' && <button disabled={!!loading || (websitePhpVersions[site.id] || site.php_version) === site.php_version} onClick={() => changeWebsitePhpVersion(site)}>Change PHP</button>}
              <button disabled={!!loading} onClick={() => openWebsiteFileManager(site)}><FolderOpen size={14}/> Files</button>
              <button disabled={!!loading} onClick={() => openWebsiteLogs(site)}><FileText size={14}/> Logs</button>
              <button disabled={!!loading} onClick={() => openWebsiteTerminal(site)}><TerminalIcon size={14}/> Terminal</button>
              {isAdmin && <button disabled={!!loading} onClick={() => openNginxCustom(site)}><Code2 size={14}/> Nginx</button>}
              {isAdmin && <button disabled={!!loading} onClick={() => toggleWebsiteWaf(site)}><Shield size={14}/> {site.waf_enabled ? 'WAF off' : 'WAF on'}</button>}
              {site.app_type === 'wordpress' && <button disabled={!!loading} onClick={() => fixWordPressPermissions(site.id)}>Fix permissions</button>}
              {site.app_type === 'wordpress' && <button disabled={!!loading} onClick={() => openWpToolkit(site)}><Globe size={14}/> WP Toolkit</button>}
              <button className="danger" disabled={!!loading} onClick={() => deleteWebsite(site.id)}><Trash2 size={14}/> Delete</button>
            </div>
          </article>)}
        </div>
      </section>
      {nginxCustomEditing && <section className="section nginx-modal">
        <div className="section-title">
          <div className="nginx-config-title">
            <h2>Nginx config - {nginxCustomEditing.domain}</h2>
            <h2>Custom Nginx — {nginxCustomEditing.domain}</h2>
            <p className="hint">Edit the full vhost file. BPanel tests Nginx and rolls back if validation fails.</p>
          </div>
          <button className="secondary-light" onClick={() => setNginxCustomEditing(null)}><X size={14}/> Close</button>
        </div>
        <textarea
          className="code-editor"
          value={nginxCustomEditing.content}
          onChange={e => setNginxCustomEditing(prev => ({ ...prev, content: e.target.value }))}
          placeholder={`server {\n    listen 80;\n    server_name ${nginxCustomEditing.domain};\n}`}
          spellCheck={false}
          rows={14}
        />
        <p className="hint">Use care with <code>listen</code>, <code>root</code>, SSL paths, and upstream directives; this editor writes the production vhost.</p>
        <div className="actions">
          <button disabled={!!loading} onClick={saveNginxCustom}>Save and reload Nginx</button>
          <button className="secondary-light" disabled={!!loading} onClick={resetNginxDefault}><RotateCcw size={14}/> Reset default</button>
          <button className="secondary-light" disabled={!!loading} onClick={() => setNginxCustomEditing(null)}>Cancel</button>
        </div>
      </section>}
      {logViewer && <section className="section nginx-modal log-viewer">
        <div className="section-title">
          <div className="nginx-config-title">
            <h2>Nginx logs - {logViewer.domain}</h2>
            <p className="hint">{logViewer.path || `/var/log/nginx/${logViewer.domain}.${logViewer.kind}.log`}</p>
          </div>
          <button className="secondary-light" onClick={() => setLogViewer(null)}><X size={14}/> Close</button>
        </div>
        <div className="log-toolbar">
          <div className="segmented-control">
            <button className={logViewer.kind === 'access' ? 'active' : ''} disabled={!!loading} onClick={() => loadWebsiteLog(logViewer.id, 'access', logViewer.lines, logViewer.domain)}>Access</button>
            <button className={logViewer.kind === 'error' ? 'active' : ''} disabled={!!loading} onClick={() => loadWebsiteLog(logViewer.id, 'error', logViewer.lines, logViewer.domain)}>Error</button>
          </div>
          <select value={logViewer.lines} onChange={e => loadWebsiteLog(logViewer.id, logViewer.kind, Number(e.target.value), logViewer.domain)} disabled={!!loading}>
            <option value={100}>100 lines</option>
            <option value={200}>200 lines</option>
            <option value={500}>500 lines</option>
            <option value={1000}>1000 lines</option>
            <option value={2000}>2000 lines</option>
          </select>
          <button disabled={!!loading} onClick={() => loadWebsiteLog(logViewer.id, logViewer.kind, logViewer.lines, logViewer.domain)}><RefreshCw size={14}/> Refresh</button>
        </div>
        <pre className="log-output">{logViewer.exists ? (logViewer.content || 'Log is empty.') : 'Log file has not been created yet.'}</pre>
      </section>}
      {terminalViewer && <section className="section terminal-modal">
        <div className="section-title">
          <h2>Terminal - {terminalViewer.domain}</h2>
          <button className="secondary-light" onClick={() => setTerminalViewer(null)}><X size={14}/> Close</button>
        </div>
        <div style={{ height: '500px', marginTop: '8px' }}>
          <Terminal websiteId={terminalViewer.id} />
        </div>
      </section>}
      {wpToolkitViewer && renderWpToolkit()}
    </>;
  }

  function renderSsl() {
    return <section className="section">
      <h2>SSL Certificate</h2>
      <WebsiteSelect />
      {currentSite && <div className="info-box" style={{marginTop:8}}>
        <strong>{currentSite.domain}</strong>
        <span className={currentSite.ssl_enabled ? 'badge ok' : 'badge'} style={{justifySelf:'start'}}>{currentSite.ssl_enabled ? 'SSL Enabled' : 'SSL Disabled'}</span>
      </div>}
      <button disabled={!selectedWebsiteId || !!loading} onClick={() => enableSsl(selectedWebsiteId)} style={{marginTop:8}}><Lock size={15}/> Install / Renew SSL</button>
      <p className="hint">The domain must point to the correct VPS IP before issuing SSL.</p>
    </section>;
  }

  function renderDatabases() {
    return <section className="section">
      <div className="section-title">
        <h2>Databases</h2>
        <button disabled={!!loading} onClick={refreshAll}><RefreshCw size={15}/> Refresh</button>
      </div>
      <div className="form-row">
        <select value={newDatabase.website_id} onChange={e => setNewDatabase(prev => ({ ...prev, website_id: e.target.value }))}>
          <option value="">Select website</option>
          {websites.map(site => <option key={site.id} value={site.id}>{site.domain}</option>)}
        </select>
        <input value={newDatabase.db_name} onChange={e => setNewDatabase(prev => ({ ...prev, db_name: e.target.value }))} placeholder="database_name (optional)" />
        <button disabled={!!loading || !newDatabase.website_id} onClick={createDatabase}><Plus size={15}/> Create database</button>
      </div>
      {databases.length === 0 && <EmptyState icon={Database} message="No databases found." />}
      <div className="table">
        {databases.map(db => {
          const site = websites.find(item => item.id === db.website_id);
          return <div className="row db-row" key={db.id}>
          <span><strong>{db.db_name}</strong>{site && <small>{site.domain}</small>}</span>
          <span style={{color:'var(--text-muted)'}}>{db.db_user}</span>
          <button disabled={!!loading} onClick={() => openPhpMyAdmin(db.id)}>phpMyAdmin</button>
          <button disabled={!!loading} onClick={() => downloadDatabase(db.id, db.db_name)}><Download size={14}/> SQL</button>
          <button disabled={!!loading} onClick={() => changeDbPassword(db.id)}><KeyRound size={14}/> Password</button>
        </div>})}
      </div>
      <p className="hint">Click phpMyAdmin to sign in directly. Token expires after 60s.</p>
    </section>;
  }

  function renderCron() {
    const presets = [
      { label: 'Every 5 minutes', value: '*/5 * * * *' },
      { label: 'Every 10 minutes', value: '*/10 * * * *' },
      { label: 'Every 15 minutes', value: '*/15 * * * *' },
      { label: 'Every 30 minutes', value: '*/30 * * * *' },
      { label: 'Every hour', value: '0 * * * *' },
      { label: 'Daily at midnight', value: '0 0 * * *' },
      { label: 'Daily at 6 AM', value: '0 6 * * *' },
      { label: 'Weekly on Monday', value: '0 0 * * 1' },
      { label: 'Monthly on 1st', value: '0 0 1 * *' },
    ];

    const minuteOptions = ['*', '*/5', '*/10', '*/15', '*/30', '0', '15', '30', '45'];
    const hourOptions = ['*', '*/2', '*/4', '*/6', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23'];
    const dayOfMonthOptions = ['*', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23', '24', '25', '26', '27', '28', '29', '30', '31'];
    const monthOptions = ['*', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12'];
    const dayOfWeekOptions = ['*', '0', '1', '2', '3', '4', '5', '6'];

    return <section className="section cron-page">
      <div className="section-title">
        <div>
          <h2>Cron Jobs</h2>
          <p className="hint">Schedule and manage automated tasks</p>
        </div>
        <div className="cron-actions-header">
          <button disabled={!!loading} onClick={() => { loadCronJobs(); loadCronPresets(); loadScheduleTypes(); }}><RefreshCw size={14}/> Refresh</button>
          <button disabled={!!loading} onClick={() => openCronModal()}><Plus size={14}/> Create Job</button>
        </div>
      </div>

      {cronJobs.length === 0 ? (
        <EmptyState icon={Clock} message="No cron jobs configured. Create your first job to schedule automated tasks." />
      ) : (
        <div className="table cron-table">
          <div className="row header-row">
            <span>Command</span>
            <span>Schedule</span>
            <span>Next Run</span>
            <span>Enabled</span>
            <span>Last Run</span>
            <span>Actions</span>
          </div>
          {cronJobs.map(cron => (
            <div className="row" key={cron.id}>
              <span className="cron-command"><strong>{cron.description || 'Untitled'}</strong><small>{cron.command}</small></span>
              <span className="cron-schedule">{cron.schedule}</span>
              <span className="cron-next-run">{cron.next_run || '--'}</span>
              <span>
                <button className="mini" onClick={() => toggleCronJob(cron)} disabled={!!loading}>
                  {cron.enabled ? <ToggleRight size={18} color="var(--color-success)" /> : <ToggleLeft size={18} />}
                </button>
              </span>
              <span className="cron-last-run">{cron.last_run || 'Never'}</span>
              <span className="row-actions">
                <button className="mini secondary-light" onClick={() => runCronJobNow(cron)} disabled={!!loading} title="Run now"><Play size={14}/></button>
                <button className="mini secondary-light" onClick={() => openCronModal(cron)} disabled={!!loading} title="Edit"><Edit size={14}/></button>
                <button className="mini danger" onClick={() => deleteCronJob(cron)} disabled={!!loading} title="Delete"><Trash2 size={14}/></button>
              </span>
            </div>
          ))}
        </div>
      )}

      {showCronModal && (
        <div className="modal-overlay" onClick={(e) => { if (e.target === e.currentTarget) closeCronModal(); }}>
          <div className="modal cron-modal">
            <div className="modal-header">
              <h3>{editingCron ? 'Edit Cron Job' : 'Create Cron Job'}</h3>
              <button className="close-btn" onClick={closeCronModal}><X size={18}/></button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>Command</label>
                <textarea
                  value={cronForm.command}
                  onChange={e => setCronForm(prev => ({ ...prev, command: e.target.value }))}
                  placeholder="wp cron event run --due-now --allow-root"
                  rows={3}
                />
              </div>

              <div className="form-group">
                <label>Description</label>
                <input
                  type="text"
                  value={cronForm.description}
                  onChange={e => setCronForm(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="Run WordPress cron events"
                />
              </div>

              <div className="form-group">
                <label>Schedule Preset</label>
                <select value={selectedPreset} onChange={e => { applyPreset(e.target.value); generateSchedulePreview(); }}>
                  <option value="">Custom schedule...</option>
                  {presets.map(preset => (
                    <option key={preset.value} value={preset.value}>{preset.label}</option>
                  ))}
                </select>
              </div>

              <div className="form-group schedule-builder">
                <label>Custom Schedule</label>
                <div className="schedule-fields">
                  <div className="schedule-field">
                    <span className="field-label">Minute</span>
                    <select value={cronMinute} onChange={e => { setCronMinute(e.target.value); setSelectedPreset(''); generateSchedulePreview(); }}>
                      {minuteOptions.map(opt => <option key={opt} value={opt}>{opt}</option>)}
                    </select>
                  </div>
                  <div className="schedule-field">
                    <span className="field-label">Hour</span>
                    <select value={cronHour} onChange={e => { setCronHour(e.target.value); setSelectedPreset(''); generateSchedulePreview(); }}>
                      {hourOptions.map(opt => <option key={opt} value={opt}>{opt}</option>)}
                    </select>
                  </div>
                  <div className="schedule-field">
                    <span className="field-label">Day (Month)</span>
                    <select value={cronDayOfMonth} onChange={e => { setCronDayOfMonth(e.target.value); setSelectedPreset(''); generateSchedulePreview(); }}>
                      {dayOfMonthOptions.map(opt => <option key={opt} value={opt}>{opt}</option>)}
                    </select>
                  </div>
                  <div className="schedule-field">
                    <span className="field-label">Month</span>
                    <select value={cronMonth} onChange={e => { setCronMonth(e.target.value); setSelectedPreset(''); generateSchedulePreview(); }}>
                      {monthOptions.map(opt => <option key={opt} value={opt}>{opt}</option>)}
                    </select>
                  </div>
                  <div className="schedule-field">
                    <span className="field-label">Day (Week)</span>
                    <select value={cronDayOfWeek} onChange={e => { setCronDayOfWeek(e.target.value); setSelectedPreset(''); generateSchedulePreview(); }}>
                      {dayOfWeekOptions.map(opt => <option key={opt} value={opt}>{opt}</option>)}
                    </select>
                  </div>
                </div>
              </div>

              <div className="form-group cron-preview">
                <label>Schedule Preview</label>
                <div className="preview-box">
                  <div className="preview-expression">
                    <code>{cronPreview.expression || `${cronMinute} ${cronHour} ${cronDayOfMonth} ${cronMonth} ${cronDayOfWeek}`}</code>
                  </div>
                  <div className="preview-human">
                    {cronPreview.human_readable || 'Custom schedule'}
                  </div>
                  {cronPreview.next_runs && cronPreview.next_runs.length > 0 && (
                    <div className="preview-next-runs">
                      <strong>Next 5 runs:</strong>
                      <ul>
                        {cronPreview.next_runs.slice(0, 5).map((run, idx) => (
                          <li key={idx}>{run}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            </div>
            <div className="modal-footer">
              <button className="secondary-light" onClick={closeCronModal}><X size={14}/> Cancel</button>
              <button disabled={!cronForm.command || !!loading} onClick={editingCron ? updateCronJob : createCronJob}>
                <Save size={14}/> {editingCron ? 'Update' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>;
  }

  function renderFiles() {
    const allSelected = files.length > 0 && selectedFilePaths.length === files.length;
    const visibleFileJobs = fileJobs.filter(job => String(job.website_id) === String(selectedWebsiteId)).slice(0, 4);
    return <section className="section">
      <div className="section-title">
        <div><h2>File manager</h2></div>
        <button disabled={!selectedWebsiteId || !!loading} onClick={() => listFiles(fileListPath)}><RefreshCw size={14}/> Refresh</button>
      </div>
      <div className="file-manager">
        <div className="file-panel">
          <div className="file-controls">
            <WebsiteSelect />
            {currentSite && <div className="file-meta">
              <span>Website: <strong>{currentSite.domain}</strong></span>
              <span>Root: <strong>{currentSite.root_path}{fileListPath ? `/${fileListPath}` : ''}</strong></span>
              {currentUser && !isAdmin && <span>Storage: <strong>{storageUsageText(currentUser)}</strong></span>}
            </div>}
            <div className="path-pill breadcrumb-line">
              <button className="crumb" disabled={!selectedWebsiteId || fileListPath === ''} onClick={() => listFiles('')}>root</button>
              {fileBreadcrumbs(fileListPath).map(crumb => <button className="crumb" key={crumb.path} onClick={() => listFiles(crumb.path)}>{crumb.label}</button>)}
            </div>
            <div className="file-toolbar">
              <button disabled={!selectedWebsiteId || fileListPath === '' || !!loading} onClick={() => listFiles(parentFilePath(fileListPath))}>Up</button>
              <button disabled={!selectedWebsiteId || !!loading} onClick={makeFileDirectory}><Plus size={14}/> Folder</button>
              <button disabled={!selectedWebsiteId || !!loading} onClick={makeFile}><FileText size={14}/> File</button>
              <label className={`upload-button ${(!selectedWebsiteId || !!loading) ? 'disabled' : ''}`}>
                <Upload size={14}/> Upload
                <input type="file" disabled={!selectedWebsiteId || !!loading} onChange={e => { uploadSiteFile(e.target.files?.[0]); e.target.value = ''; }} />
              </label>
              <select value={archiveFormat} onChange={e => setArchiveFormat(e.target.value)} disabled={!selectedWebsiteId || !!loading}>
                <option value="zip">zip</option>
                <option value="tar.gz">tar.gz</option>
              </select>
              <button disabled={selectedFilePaths.length === 0 || !!loading} onClick={copySelectedFiles}><Copy size={14}/> Copy</button>
              <button disabled={selectedFilePaths.length === 0 || !!loading} onClick={moveSelectedFiles}><MoveRight size={14}/> Move</button>
              <button disabled={selectedFilePaths.length === 0 || !!loading} onClick={archiveSelectedFiles}><Archive size={14}/> Archive</button>
              <button className="danger" disabled={selectedFilePaths.length === 0 || !!loading} onClick={deleteSelectedFiles}><Trash2 size={14}/> Delete</button>
            </div>
            {visibleFileJobs.length > 0 && <div className="file-job-list">
              {visibleFileJobs.map(job => <div className={`file-job ${job.status}`} key={job.job_id}>
                <Clock size={14}/>
                <span><strong>{job.archive_path?.split('/').pop() || 'Archive'}</strong> {job.status === 'done' ? 'completed' : job.status === 'error' ? 'failed' : job.status}</span>
                {job.error && <small>{job.error}</small>}
              </div>)}
            </div>}
          </div>
          <div className="file-list-header">
            <label><input type="checkbox" checked={allSelected} onChange={toggleAllFiles} disabled={files.length === 0} /> Select</label>
            <span>{files.length} item(s)</span>
          </div>
          <div className="file-list">
            {files.length === 0 && <div className="empty-box">No files in this folder.</div>}
            {files.map(item => <div className={`file-item ${selectedFilePaths.includes(item.path) ? 'selected' : ''}`} key={item.path}>
              <input type="checkbox" checked={selectedFilePaths.includes(item.path)} onChange={() => toggleFileSelection(item.path)} />
              <button className="file-name" onClick={() => item.is_dir ? listFiles(item.path) : (isTextEditable(item) ? openFileEditorTab(item.path) : downloadFile(item.path))}>
                {item.is_dir ? <FolderOpen size={16}/> : <FileText size={16}/>} <strong>{item.name}</strong>
              </button>
              <span className="file-mode">{item.mode || '---'}</span>
              <span className="file-size">{item.is_dir ? 'Folder' : formatBytes(item.size)}</span>
              <div className="file-row-actions">
                {!item.is_dir && isTextEditable(item) && <button className="mini secondary-light" disabled={!!loading} onClick={() => openFileEditorTab(item.path)}>Edit</button>}
                {!item.is_dir && <button className="mini secondary-light" disabled={!!loading} onClick={() => downloadFile(item.path)}><Download size={13}/></button>}
                {isArchiveFile(item) && <button className="mini secondary-light" disabled={!!loading} onClick={() => extractArchiveFile(item.path)}>Extract</button>}
                <button className="mini secondary-light" disabled={!!loading} onClick={() => chmodFileItem(item)}>Chmod</button>
                <button className="mini secondary-light" title="Copy" aria-label="Copy" disabled={!!loading} onClick={() => copyFileItem(item)}><Copy size={13}/></button>
                <button className="mini secondary-light" title="Move" aria-label="Move" disabled={!!loading} onClick={() => moveFileItem(item)}><MoveRight size={13}/></button>
                <button className="mini secondary-light" disabled={!!loading} onClick={() => renameFileItem(item)}>Rename</button>
                <button className="mini danger" disabled={!!loading} onClick={() => deleteFileAction(item.path)}><Trash2 size={13}/></button>
              </div>
            </div>)}
          </div>
        </div>
      </div>
    </section>;
  }

  function renderBackups() {
    const selectedBackupUser = users.find(user => String(user.id) === String(selectedBackupUserId));
    const userNameById = id => users.find(user => String(user.id) === String(id))?.username || `User #${id}`;
    const scheduleUserLabel = item => {
      if (item.all_users) return 'All users';
      const ids = (item.user_ids && item.user_ids.length > 0) ? item.user_ids : (item.user_id ? [item.user_id] : []);
      return ids.length ? ids.map(userNameById).join(', ') : 'No users';
    };
    return <section className="section backups-page">
      <h2>Backups</h2>
      <WebsiteSelect />
      <p className="hint">Backups include website source files and a database SQL export.</p>
      <div className="actions backup-toolbar">
        <button disabled={!selectedWebsiteId || !!loading} onClick={createBackup}><Plus size={14}/> Create backup</button>
        <button disabled={!selectedWebsiteId || !!loading} onClick={listBackups}><RefreshCw size={14}/> Refresh</button>
        <label className="upload-button">
          <Upload size={14}/> Upload backup
          <input type="file" accept=".tar.gz,application/gzip" onChange={e => { uploadBackup(e.target.files?.[0]); e.target.value = ''; }} />
        </label>
      </div>
      {backups.length === 0 && selectedWebsiteId && <EmptyState icon={Archive} message="No backups found for this website." />}
      <div className="backup-list">
        {backups.map(file => <div className="backup-item" key={file}>
          <span>{file.split('/').pop()}</span>
          <div className="actions">
            <button disabled={!!loading} onClick={() => downloadBackup(file)}><Download size={14}/> Download</button>
            <button disabled={!!loading} onClick={() => restoreBackup(file)}><RotateCcw size={14}/> Restore</button>
            <button className="danger" disabled={!!loading} onClick={() => deleteBackup(file)}><Trash2 size={14}/></button>
          </div>
        </div>)}
      </div>
      {isAdmin && <div className="sftp-panel backup-admin-panel">
        <div className="section-title backup-panel-heading">
          <div><h2>Full user backup</h2><p className="hint">Includes the panel user, all owned websites, source files, database dumps, and restore metadata.</p></div>
          <button disabled={!!loading} onClick={() => { loadUsers(); loadBackupSchedules(); loadRestoreBackups(); }}><RefreshCw size={14}/> Refresh</button>
        </div>
        <div className="sftp-run-row user-backup-row backup-run-row">
          <select value={selectedBackupUserId} onChange={e => setSelectedBackupUserId(e.target.value)}>
            <option value="">Select user</option>
            {users.map(user => <option key={user.id} value={user.id}>{user.username}</option>)}
          </select>
          <select value={selectedSftpTargetId} onChange={e => setSelectedSftpTargetId(e.target.value)}>
            <option value="">Local only</option>
            {sftpTargets.map(target => <option key={target.id} value={target.id}>{target.name}</option>)}
          </select>
          <button disabled={!selectedBackupUserId || !!loading} onClick={createUserBackup}><Archive size={14}/> Full backup</button>
        </div>
        {selectedBackupUser && <p className="hint">Current user: <strong>{selectedBackupUser.username}</strong></p>}
        <div className="actions backup-subactions">
          <button disabled={!selectedBackupUserId || !!loading} onClick={() => listUserBackups()}><RefreshCw size={14}/> Backups</button>
        </div>
        <div className="backup-list">
          {userBackups.map(file => <div className="backup-item" key={file}>
            <span>{file.split('/').pop()}</span>
            <div className="actions">
              <button disabled={!!loading} onClick={() => downloadUserBackup(file)}><Download size={14}/> Download</button>
              <button disabled={!!loading} onClick={() => restoreUserBackup(file)}><RotateCcw size={14}/> Restore user</button>
              <button className="danger" disabled={!!loading} onClick={() => deleteUserBackup(file)}><Trash2 size={14}/></button>
            </div>
          </div>)}
        </div>
        <div className="section-title restore-title backup-panel-heading">
          <div><h2>Restore folder</h2><p className="hint">{restoreBackupDir || '/var/backups/bpanel/users/restore'}</p></div>
          <div className="actions">
            <button disabled={!!loading} onClick={loadRestoreBackups}><RefreshCw size={14}/> Refresh</button>
            <label className="upload-button">
              <Upload size={14}/> Upload backups
              <input type="file" multiple accept=".tar.gz,application/gzip" onChange={e => { uploadUserBackups(e.target.files); e.target.value = ''; }} />
            </label>
          </div>
        </div>
        <div className="backup-list">
          {restoreBackups.map(item => <div className="backup-item" key={item.backup_file}>
            <span>{item.filename || item.backup_file.split('/').pop()}<small>{item.valid ? `${item.username || 'unknown user'} - ${item.websites || 0} website(s)` : (item.error || 'Invalid backup')}</small></span>
            <div className="actions">
              <button disabled={!!loading} onClick={() => downloadUserBackup(item.backup_file)}><Download size={14}/> Download</button>
              <button disabled={!!loading || !item.valid} onClick={() => restoreUserBackup(item.backup_file)}><RotateCcw size={14}/> Restore user</button>
              <button className="danger" disabled={!!loading} onClick={() => deleteRestoreBackup(item.backup_file)}><Trash2 size={14}/></button>
            </div>
          </div>)}
        </div>
        <div className="sftp-form schedule-form backup-schedule-form">
          <label className="schedule-toggle">
            <input type="checkbox" checked={!!newBackupSchedule.all_users} onChange={e => setNewBackupSchedule(prev => ({ ...prev, all_users: e.target.checked }))} />
            <span>All users</span>
          </label>
          <select multiple value={newBackupSchedule.user_ids || []} disabled={!!newBackupSchedule.all_users} onChange={e => setNewBackupSchedule(prev => ({ ...prev, user_ids: Array.from(e.target.selectedOptions, option => option.value) }))}>
            {users.map(user => <option key={user.id} value={String(user.id)}>{user.username}</option>)}
          </select>
          <input value={newBackupSchedule.schedule} onChange={e => setNewBackupSchedule(prev => ({ ...prev, schedule: e.target.value }))} placeholder="0 2 * * *" />
          <select value={newBackupSchedule.target_id} onChange={e => setNewBackupSchedule(prev => ({ ...prev, target_id: e.target.value }))}>
            <option value="">Local only</option>
            {sftpTargets.map(target => <option key={target.id} value={target.id}>{target.name}</option>)}
          </select>
          <input value={newBackupSchedule.retention} onChange={e => setNewBackupSchedule(prev => ({ ...prev, retention: e.target.value }))} placeholder="7" inputMode="numeric" />
          <button disabled={(!newBackupSchedule.all_users && (!newBackupSchedule.user_ids || newBackupSchedule.user_ids.length === 0)) || !!loading} onClick={createBackupSchedule}><Clock size={14}/> Schedule</button>
        </div>
        <div className="backup-list">
          {backupSchedules.map(item => {
            const scheduleTarget = sftpTargets.find(target => target.id === item.target_id);
            return <div className="backup-item" key={item.id}>
              <span>{scheduleUserLabel(item)} - {item.schedule} - keep {item.retention}{scheduleTarget ? ` - ${scheduleTarget.name}` : ''}<small>{item.last_status}: {item.last_message || 'not run yet'}</small></span>
              <button className="danger" disabled={!!loading} onClick={() => deleteBackupSchedule(item.id)}><Trash2 size={14}/></button>
            </div>;
          })}
        </div>
      </div>}
      {isAdmin && <div className="sftp-panel backup-admin-panel">
        <div className="section-title backup-panel-heading">
          <div><h2>SFTP backup</h2><p className="hint">Create a local archive and upload it to an SFTP target.</p></div>
          <button disabled={!!loading} onClick={loadSftpTargets}><RefreshCw size={14}/> Targets</button>
        </div>
        <div className="sftp-run-row backup-run-row">
          <select value={selectedSftpTargetId} onChange={e => setSelectedSftpTargetId(e.target.value)}>
            <option value="">Select SFTP target</option>
            {sftpTargets.map(target => <option key={target.id} value={target.id}>{target.name} - {target.host}</option>)}
          </select>
          <button disabled={!selectedWebsiteId || !selectedSftpTargetId || !!loading} onClick={createSftpBackup}><Upload size={14}/> Backup to SFTP</button>
        </div>
        <div className="sftp-form sftp-target-form">
          <input value={newSftpTarget.name} onChange={e => setNewSftpTarget(prev => ({ ...prev, name: e.target.value }))} placeholder="Target name" />
          <input value={newSftpTarget.host} onChange={e => setNewSftpTarget(prev => ({ ...prev, host: e.target.value }))} placeholder="Host" />
          <input value={newSftpTarget.port} onChange={e => setNewSftpTarget(prev => ({ ...prev, port: e.target.value }))} placeholder="22" inputMode="numeric" />
          <input value={newSftpTarget.username} onChange={e => setNewSftpTarget(prev => ({ ...prev, username: e.target.value }))} placeholder="Username" />
          <input value={newSftpTarget.password} onChange={e => setNewSftpTarget(prev => ({ ...prev, password: e.target.value }))} placeholder="Password" type="password" />
          <input value={newSftpTarget.remote_path} onChange={e => setNewSftpTarget(prev => ({ ...prev, remote_path: e.target.value }))} placeholder="/backups/bpanel" />
          <textarea value={newSftpTarget.private_key} onChange={e => setNewSftpTarget(prev => ({ ...prev, private_key: e.target.value }))} placeholder="Private key (optional)" rows={4} />
          <button disabled={!!loading || !newSftpTarget.name || !newSftpTarget.host || !newSftpTarget.username || (!newSftpTarget.password && !newSftpTarget.private_key)} onClick={createSftpTarget}><Plus size={14}/> Save target</button>
        </div>
        <div className="backup-list">
          {sftpTargets.map(target => <div className="backup-item" key={target.id}>
            <span>{target.name} - {target.username}@{target.host}:{target.remote_path}</span>
            <button className="danger" disabled={!!loading} onClick={() => deleteSftpTarget(target.id)}><Trash2 size={14}/></button>
          </div>)}
        </div>
      </div>}
    </section>;
  }

  function renderServices() {
    return <section className="section">
      <div className="section-title">
        <h2>Services Status</h2>
        <button disabled={!!loading} onClick={checkAllServices}><RefreshCw size={15}/> Refresh</button>
      </div>
      <div className="service-grid">
        {SERVICE_NAMES.map(name => {
          const state = serviceStates[name];
          const text = `${state?.stdout || ''} ${state?.stderr || ''}`;
          const active = text.includes('active (running)');
          const inactive = text.includes('inactive') || text.includes('failed');
          return <div className="service-card" key={name}>
            <div><strong>{name}</strong><span className={active ? 'badge ok' : inactive ? 'badge bad' : 'badge'}>{active ? 'Running' : inactive ? 'Stopped' : '...'}</span></div>
            <small>Auto-refreshes every 10s</small>
            {isAdmin && <div className="service-actions">
              <button onClick={() => runServiceAction(name, 'start')}><Play size={13}/> Start</button>
              {name !== 'bpanel-api' && <button onClick={() => runServiceAction(name, 'stop')}><Square size={13}/> Stop</button>}
              <button onClick={() => runServiceAction(name, 'restart')}><RotateCcw size={13}/> Restart</button>
            </div>}
          </div>;
        })}
      </div>
    </section>;
  }

  function renderPhp() {
    if (!isAdmin) return <section className="section"><h2>PHP Management</h2><p className="hint">You do not have permission to manage PHP.</p></section>;
    return <section className="section">
      <div className="section-title">
        <div><h2>PHP Management</h2><p className="hint">Manage PHP versions, extensions, configuration, and FPM pools.</p></div>
      </div>
      <div className="user-create-card">
        <label><span>PHP version</span><select value={phpConfig.php_version} onChange={e => { const v = e.target.value; setPhpConfig(prev => ({ ...prev, php_version: v })); loadPhpConfig(v); }}>
          <option value="8.3">PHP 8.3</option><option value="8.4">PHP 8.4</option>
        </select></label>
        <label><span>display_errors</span><select value={phpConfig.display_errors} onChange={e => setPhpConfig(prev => ({ ...prev, display_errors: e.target.value }))}>
          <option value="Off">Off (production)</option><option value="On">On (debug)</option>
        </select></label>
        <label><span>max_execution_time</span><input type="number" value={phpConfig.max_execution_time} onChange={e => setPhpConfig(prev => ({ ...prev, max_execution_time: e.target.value }))} /></label>
        <label><span>max_input_time</span><input type="number" value={phpConfig.max_input_time} onChange={e => setPhpConfig(prev => ({ ...prev, max_input_time: e.target.value }))} /></label>
        <label><span>max_input_vars</span><input type="number" value={phpConfig.max_input_vars} onChange={e => setPhpConfig(prev => ({ ...prev, max_input_vars: e.target.value }))} /></label>
        <label><span>memory_limit</span><input value={phpConfig.memory_limit} onChange={e => setPhpConfig(prev => ({ ...prev, memory_limit: e.target.value }))} placeholder="512M" /></label>
        <label><span>post_max_size</span><input value={phpConfig.post_max_size} onChange={e => setPhpConfig(prev => ({ ...prev, post_max_size: e.target.value }))} placeholder="1024M" /></label>
        <label><span>upload_max_filesize</span><input value={phpConfig.upload_max_filesize} onChange={e => setPhpConfig(prev => ({ ...prev, upload_max_filesize: e.target.value }))} placeholder="1024M" /></label>
        <button disabled={!!loading} onClick={updatePhpConfig}>Save PHP config</button>
      </div>
      <p className="hint">Note: <code>post_max_size</code> should be ≥ <code>upload_max_filesize</code>.</p>
    </section>;
  }

  function renderFirewall() {
    if (!isAdmin) return <section className="section"><h2>Firewall</h2><p className="hint">No permission.</p></section>;
    return <>
      <section className="section">
        <div className="section-title">
          <div><h2>Firewall (UFW)</h2><p className="hint">Keep SSH and web ports allowed before enabling.</p></div>
        </div>
        <div className="actions">
          <button disabled={!!loading} onClick={loadFirewall}><RefreshCw size={14}/> Refresh</button>
          <button disabled={!!loading} onClick={enableFirewall}><Shield size={14}/> Enable</button>
          <button disabled={!!loading} onClick={disableFirewall}>Disable</button>
          <button disabled={!!loading} onClick={reloadFirewall}>Reload</button>
        </div>
        <div className="info-box firewall-status">
          <strong>UFW status</strong>
          <pre>{firewallStatus?.stdout || firewallStatus?.stderr || 'Click Refresh to load status.'}</pre>
        </div>
      </section>
      <section className="section">
        <h2>Open port</h2>
        <div className="firewall-form">
          <label><span>Port</span><input value={firewallPort} onChange={e => setFirewallPort(e.target.value)} placeholder="80" inputMode="numeric" /></label>
          <label><span>Protocol</span><select value={firewallProtocol} onChange={e => setFirewallProtocol(e.target.value)}><option value="tcp">TCP</option><option value="udp">UDP</option></select></label>
          <button disabled={!!loading || !firewallPort} onClick={openFirewallPort}>Open port</button>
        </div>
      </section>
      <section className="section">
        <h2>Allow IP</h2>
        <div className="firewall-form">
          <label><span>IP / CIDR</span><input value={firewallAllowIp} onChange={e => setFirewallAllowIp(e.target.value)} placeholder="1.2.3.4" /></label>
          <label><span>Port (optional)</span><input value={firewallAllowPort} onChange={e => setFirewallAllowPort(e.target.value)} placeholder="22" inputMode="numeric" /></label>
          <label><span>Protocol</span><select value={firewallAllowProtocol} onChange={e => setFirewallAllowProtocol(e.target.value)}><option value="tcp">TCP</option><option value="udp">UDP</option></select></label>
          <button disabled={!!loading || !firewallAllowIp} onClick={allowFirewallIp}>Allow</button>
        </div>
      </section>
      <section className="section">
        <h2>Block IP</h2>
        <div className="firewall-form">
          <label><span>IP / CIDR</span><input value={firewallBlockIp} onChange={e => setFirewallBlockIp(e.target.value)} placeholder="5.6.7.8" /></label>
          <label><span>Port (optional)</span><input value={firewallBlockPort} onChange={e => setFirewallBlockPort(e.target.value)} placeholder="All ports" inputMode="numeric" /></label>
          <label><span>Protocol</span><select value={firewallBlockProtocol} onChange={e => setFirewallBlockProtocol(e.target.value)}><option value="tcp">TCP</option><option value="udp">UDP</option></select></label>
          <button className="danger" disabled={!!loading || !firewallBlockIp} onClick={blockFirewallIp}>Block</button>
        </div>
      </section>
      <section className="section">
        <h2>Delete rule</h2>
        <div className="firewall-form">
          <label><span>Rule #</span><input value={firewallDeleteNumber} onChange={e => setFirewallDeleteNumber(e.target.value)} placeholder="1" inputMode="numeric" /></label>
          <button className="danger" disabled={!!loading || !firewallDeleteNumber} onClick={deleteFirewallRule}>Delete rule</button>
        </div>
        <p className="hint">Rule numbers change after each delete. Refresh status first.</p>
      </section>
    </>;
  }

  function renderUpdates() {
    if (!isAdmin) return <section className="section"><h2>Updates</h2><p className="hint">No permission.</p></section>;
    const statusText = updatesStatus?.stdout || updatesStatus?.stderr || 'Click Refresh to load update status.';
    return <>
      <section className="section">
        <div className="section-title">
          <div><h2>Updates</h2><p className="hint">OS packages use apt; panel updates use <code>installer/update.sh</code>.</p></div>
          <button disabled={!!loading} onClick={loadUpdates}><RefreshCw size={14}/> Refresh</button>
        </div>
        <div className="actions">
          <button disabled={!!loading} onClick={runOsUpdate}><RefreshCw size={14}/> Update OS now</button>
          <button disabled={!!loading} onClick={runPanelUpdate}><RotateCcw size={14}/> Update panel now</button>
        </div>
        <div className="info-box firewall-status"><strong>Status</strong><pre>{statusText}</pre></div>
      </section>
      <section className="section">
        <h2>Auto Update OS</h2>
        <div className="firewall-form">
          <label><span>Enabled</span><select value={osAutoUpdate.enabled ? 'on' : 'off'} onChange={e => setOsAutoUpdate(prev => ({ ...prev, enabled: e.target.value === 'on' }))}><option value="on">On</option><option value="off">Off</option></select></label>
          <label><span>Mode</span><select value={osAutoUpdate.mode} onChange={e => setOsAutoUpdate(prev => ({ ...prev, mode: e.target.value }))}><option value="security">Security</option><option value="all">All packages</option></select></label>
          <label><span>Auto reboot</span><select value={osAutoUpdate.auto_reboot ? 'on' : 'off'} onChange={e => setOsAutoUpdate(prev => ({ ...prev, auto_reboot: e.target.value === 'on' }))}><option value="off">Off</option><option value="on">On</option></select></label>
          <button disabled={!!loading} onClick={saveOsAutoUpdate}>Save OS auto update</button>
        </div>
      </section>
      <section className="section">
        <h2>Auto Update Panel</h2>
        <div className="firewall-form">
          <label><span>Enabled</span><select value={panelAutoUpdate.enabled ? 'on' : 'off'} onChange={e => setPanelAutoUpdate(prev => ({ ...prev, enabled: e.target.value === 'on' }))}><option value="on">On</option><option value="off">Off</option></select></label>
          <label><span>Daily time</span><input value={panelAutoUpdate.time} onChange={e => setPanelAutoUpdate(prev => ({ ...prev, time: e.target.value }))} placeholder="03:30" /></label>
          <button disabled={!!loading} onClick={savePanelAutoUpdate}>Save panel auto update</button>
        </div>
      </section>
    </>;
  }

  function renderUpdate() {
    if (!isAdmin) return <section className="section"><h2>Auto Update</h2><p className="hint">No permission.</p></section>;

    const scheduleOptions = [
      { value: 'disabled', label: 'Disabled - Never' },
      { value: 'daily', label: 'Daily at 3 AM' },
      { value: 'weekly', label: 'Weekly on Sunday' },
      { value: 'monthly', label: 'Monthly on 1st' },
      { value: 'security_only', label: 'Security updates only' },
    ];

    return (
      <section className="section">
        <div className="section-title">
          <div><h2>Auto Update</h2><p className="hint">Automatically update BPanel from GitHub releases.</p></div>
          <button disabled={!!loading} onClick={() => { loadUpdateStatus(); loadUpdateSettings(); loadUpdateBackups(); loadUpdateLogs(); }}><RefreshCw size={14}/> Refresh</button>
        </div>

        {/* Update Status Section */}
        <div className="info-box">
          <div className="update-status">
            <div className="update-version">
              <span className="label">Current Version:</span>
              <strong>{updateStatus?.version || 'Loading...'}</strong>
            </div>
            <div className="update-commit">
              <span className="label">Commit:</span>
              <code>{updateStatus?.commit || '--'}</code>
            </div>
          </div>
        </div>

        {/* Check for Updates */}
        <div className="actions" style={{ marginTop: 16, marginBottom: 16 }}>
          <button disabled={!!loading} onClick={checkForUpdates}><RefreshCw size={14}/> Check for Updates</button>
        </div>

        {/* Available Update Info */}
        {availableUpdate?.available ? (
          <div className="info-box" style={{ borderColor: 'var(--accent)', marginBottom: 16 }}>
            <h3>Update Available</h3>
            <div className="update-info">
              <p><strong>Version:</strong> {availableUpdate.version}</p>
              {availableUpdate.release_name && <p><strong>Release:</strong> {availableUpdate.release_name}</p>}
              {availableUpdate.release_notes && (
                <div className="release-notes">
                  <strong>Release Notes:</strong>
                  <pre style={{ maxHeight: 200, overflow: 'auto', whiteSpace: 'pre-wrap' }}>{availableUpdate.release_notes}</pre>
                </div>
              )}
              {availableUpdate.prerelease && <span className="badge" style={{ backgroundColor: 'orange' }}>Pre-release</span>}
            </div>
            <div className="actions" style={{ marginTop: 12 }}>
              <button disabled={!!loading} onClick={() => downloadUpdate(availableUpdate.version)}><Download size={14}/> Download</button>
              <button disabled={!!loading} onClick={() => installUpdate(availableUpdate.version)} className="primary"><Play size={14}/> Install Now</button>
            </div>
          </div>
        ) : availableUpdate && !availableUpdate.available ? (
          <div className="info-box" style={{ borderColor: 'var(--success)', marginBottom: 16 }}>
            <p><CheckCircle size={16}/> You are running the latest version ({availableUpdate.current_version})</p>
          </div>
        ) : null}

        {/* Auto Update Settings */}
        <div className="settings-section">
          <h3>Auto Update Settings</h3>
          <div className="settings-form">
            <label className="check-line">
              <input
                type="checkbox"
                checked={updateSettings?.auto_update_enabled || false}
                onChange={e => saveUpdateSettings({ ...updateSettings, auto_update_enabled: e.target.checked })}
              />
              <span>Enable Auto Update</span>
            </label>
            <label className="setting-row">
              <span>Update Schedule:</span>
              <select
                value={updateSettings?.schedule || 'disabled'}
                onChange={e => saveUpdateSettings({ ...updateSettings, schedule: e.target.value })}
              >
                {scheduleOptions.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </label>
            <label className="check-line">
              <input
                type="checkbox"
                checked={updateSettings?.include_beta || false}
                onChange={e => saveUpdateSettings({ ...updateSettings, include_beta: e.target.checked })}
              />
              <span>Include Beta Versions</span>
            </label>
            <label className="check-line">
              <input
                type="checkbox"
                checked={updateSettings?.auto_backup !== false}
                onChange={e => saveUpdateSettings({ ...updateSettings, auto_backup: e.target.checked })}
              />
              <span>Auto Backup Before Update</span>
            </label>
            <label className="check-line">
              <input
                type="checkbox"
                checked={updateSettings?.notify_on_update !== false}
                onChange={e => saveUpdateSettings({ ...updateSettings, notify_on_update: e.target.checked })}
              />
              <span>Notify on Update Available</span>
            </label>
          </div>
        </div>

        {/* Backup Section */}
        <div className="settings-section">
          <h3>Backups</h3>
          <div className="actions" style={{ marginBottom: 12 }}>
            <button disabled={!!loading} onClick={createUpdateBackup}><Archive size={14}/> Create Backup</button>
          </div>
          {updateBackups.length > 0 ? (
            <div className="backup-list">
              {updateBackups.map(backup => (
                <div className="backup-item" key={backup.id}>
                  <div className="backup-info">
                    <strong>{backup.created_at || backup.id}</strong>
                    <small>Version: {backup.version || 'unknown'}</small>
                    <small>Size: {formatBytes(backup.size)}</small>
                  </div>
                  <div className="actions">
                    <button disabled={!!loading} onClick={() => restoreUpdateBackup(backup.id)}><RotateCcw size={14}/> Restore</button>
                    <button disabled={!!loading} className="danger" onClick={() => deleteUpdateBackup(backup.id)}><Trash2 size={14}/></button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="hint">No backups available. Create a backup before updating.</p>
          )}
        </div>

        {/* Rollback Section */}
        <div className="settings-section">
          <h3>Rollback</h3>
          <p className="hint">Rollback to the previous version using the most recent backup.</p>
          <button disabled={!!loading || updateBackups.length === 0} onClick={rollbackUpdate} className="danger"><RotateCcw size={14}/> Rollback to Previous Version</button>
        </div>

        {/* Update Logs */}
        <div className="settings-section">
          <div className="section-title">
            <h3>Update Logs</h3>
            <button disabled={!!loading} onClick={loadUpdateLogs}><RefreshCw size={14}/> Refresh</button>
          </div>
          {updateLogs.length > 0 ? (
            <div className="log-output" style={{ maxHeight: 300, overflow: 'auto' }}>
              {updateLogs.map((log, idx) => (
                <div key={idx} className="log-entry">
                  <span className="log-time">{log.timestamp}</span>
                  <span className={`log-level ${log.level}`}>{log.level}</span>
                  <span className="log-message">{log.message}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="hint">No update logs available.</p>
          )}
        </div>
      </section>
    );
  }

  function renderSecurity() {
    const enabled = Boolean(twoFactorStatus?.enabled || currentUser?.totp_enabled);
    return <section className="section">
      <div className="section-title">
        <div><h2>Google Authenticator 2FA</h2><p className="hint">Current status: <strong>{enabled ? 'Enabled' : 'Disabled'}</strong></p></div>
        <button disabled={!!loading} onClick={loadTwoFactorStatus}><RefreshCw size={14}/> Refresh</button>
      </div>
      {!enabled && <div className="security-grid">
        <div className="info-box">
          <strong>Setup</strong>
          {twoFactorSetup?.qr_data_url ? <img className="qr-code" src={twoFactorSetup.qr_data_url} alt="2FA QR code" /> : <p className="hint">No setup code generated.</p>}
          {twoFactorSetup?.secret && <code className="secret-text">{twoFactorSetup.secret}</code>}
          <div className="actions">
            <button disabled={!!loading} onClick={setupTwoFactorAuth}><Shield size={14}/> Generate QR</button>
          </div>
        </div>
        <div className="info-box">
          <strong>Verify</strong>
          <input value={twoFactorCode} onChange={e => setTwoFactorCode(e.target.value)} placeholder="123456" inputMode="numeric" />
          <button disabled={!!loading || !twoFactorSetup || !twoFactorCode} onClick={enableTwoFactorAuth}><Lock size={14}/> Enable 2FA</button>
        </div>
      </div>}
      {enabled && <div className="security-grid one">
        <div className="info-box">
          <strong>Disable 2FA</strong>
          <input value={twoFactorCode} onChange={e => setTwoFactorCode(e.target.value)} placeholder="123456" inputMode="numeric" />
          <button className="danger" disabled={!!loading || !twoFactorCode} onClick={disableTwoFactorAuth}>Disable 2FA</button>
        </div>
      </div>}
    </section>;
  }

  function renderPanelSettings() {
    if (!isAdmin) return <section className="section"><h2>Settings</h2><p className="hint">No permission.</p></section>;

    // Settings state
    const [activeSettingsTab, setActiveSettingsTab] = useState('general');
    const [settingsData, setSettingsData] = useState({});
    const [sslStatus, setSslStatus] = useState(null);
    const [apiKey, setApiKey] = useState(null);
    const [alarmTasks, setAlarmTasks] = useState([]);
    const [backupList, setBackupList] = useState([]);
    const [services, setServices] = useState([]);
    const [showApiKey, setShowApiKey] = useState(false);
    const [phpVersionsInstalled, setPhpVersionsInstalled] = useState([]);
    const [webServersInstalled, setWebServersInstalled] = useState([]);
    const [installingPhp, setInstallingPhp] = useState(false);
    const [installingWebServer, setInstallingWebServer] = useState(false);

    // Load settings data
    async function loadSettingsData() {
      const data = await request('/settings');
      if (data) setSettingsData(data);
    }

    async function loadSslStatus() {
      const data = await request('/settings/ssl');
      if (data) setSslStatus(data);
    }

    async function loadApiKey() {
      const data = await request('/settings/api/key');
      if (data) setApiKey(data);
    }

    async function loadAlarmTasks() {
      const data = await request('/settings/alarm/tasks');
      if (data) setAlarmTasks(Array.isArray(data) ? data : []);
    }

    async function loadBackupList() {
      const data = await request('/settings/backup/list');
      if (data) setBackupList(Array.isArray(data) ? data : []);
    }

    async function loadAllServices() {
      const data = await request('/settings/services/all');
      if (data) setServices(Array.isArray(data) ? data : []);
    }

    async function loadPhpVersionsInstalled() {
      const data = await request('/php/versions');
      if (data) setPhpVersionsInstalled(data.versions || []);
    }

    async function loadWebServersInstalled() {
      const data = await request('/webserver/engines');
      if (data) setWebServersInstalled(data.engines || []);
    }

    async function installPhpVersion(version) {
      setInstallingPhp(true);
      const result = await request(`/php/versions/${version}/install`, { method: 'POST' }, `Installing PHP ${version}...`);
      setInstallingPhp(false);
      if (result?.success) {
        setNotice(`PHP ${version} installed successfully`);
        loadPhpVersionsInstalled();
      }
    }

    async function installWebServer(engine) {
      setInstallingWebServer(true);
      const result = await request(`/webserver/install/${engine}`, { method: 'POST' }, `Installing ${engine}...`);
      setInstallingWebServer(false);
      if (result?.success) {
        setNotice(`${engine} installed successfully`);
        loadWebServersInstalled();
      }
    }

    // Save settings
    async function saveSettings(key, value) {
      const data = await request('/settings', {
        method: 'PUT',
        body: JSON.stringify({ [key]: value }),
      });
      if (data) {
        setSettingsData(prev => ({ ...prev, [key]: value }));
        setNotice(`${key} updated`);
      }
    }

    // Toggle functions
    async function toggleSetting(key) {
      await saveSettings(key, !settingsData[key]);
    }

    // API key functions
    async function resetApiKey() {
      if (!confirm('Generate a new API key? The old key will stop working.')) return;
      const data = await request('/settings/api/reset-key', { method: 'POST' });
      if (data?.api_key) {
        setApiKey(data);
        setNotice('API key reset successfully');
      }
    }

    // Backup functions
    async function createPanelBackup() {
      const data = await request('/settings/backup/create', { method: 'POST' }, 'Creating backup...');
      if (data?.success) {
        setNotice('Panel backup created');
        await loadBackupList();
      }
    }

    async function restoreBackup(backupId) {
      if (!confirm('Restore this backup? Current settings will be overwritten.')) return;
      const data = await request(`/settings/backup/restore/${backupId}`, { method: 'POST' }, 'Restoring backup...');
      if (data?.success) {
        setNotice('Backup restored');
        await loadSettingsData();
      }
    }

    async function deleteBackup(backupId) {
      if (!confirm('Delete this backup?')) return;
      const data = await request(`/settings/backup/${backupId}`, { method: 'DELETE' }, 'Deleting backup...');
      if (data?.success) {
        setNotice('Backup deleted');
        await loadBackupList();
      }
    }

    async function clearAllBackups() {
      if (!confirm('Delete ALL panel backups? This cannot be undone.')) return;
      const data = await request('/settings/backup/clear', { method: 'POST' }, 'Clearing backups...');
      if (data?.success) {
        setNotice(`${data.deleted_count} backups deleted`);
        setBackupList([]);
      }
    }

    // Service functions
    async function serviceAction(name, action) {
      const data = await request(`/settings/services/${name}/${action}`, { method: 'POST' }, `${action} ${name}...`);
      if (data?.success) {
        setNotice(data.message);
        await loadAllServices();
      }
    }

    // Alarm functions
    async function deleteAlarmTask(id) {
      if (!confirm('Delete this alarm task?')) return;
      const data = await request(`/settings/alarm/tasks/${id}`, { method: 'DELETE' }, 'Deleting task...');
      if (data?.success) {
        setNotice('Alarm task deleted');
        await loadAlarmTasks();
      }
    }

    // Load data on tab change
    useEffect(() => {
      if (page === 'settings') {
        loadSettingsData();
        loadSslStatus();
        loadApiKey();
        loadAlarmTasks();
        loadBackupList();
        loadAllServices();
      }
    }, [page]);

    const SETTINGS_TABS = [
      { key: 'general', label: 'General', icon: SettingsIcon },
      { key: 'network', label: 'Network', icon: Globe },
      { key: 'ssl', label: 'SSL', icon: Shield },
      { key: 'developer', label: 'Developer', icon: Code },
      { key: 'security', label: 'Security', icon: Lock },
      { key: 'interface', label: 'Interface', icon: Palette },
      { key: 'software', label: 'Software', icon: Package },
      { key: 'backup', label: 'Backup', icon: Database },
      { key: 'alarm', label: 'Alarm', icon: Bell },
      { key: 'migrate', label: 'Migrate', icon: ArrowRightLeft },
      { key: 'service', label: 'Service', icon: Server },
    ];

    // PHP Module options
    const PHP_MODULES = [
      { key: 'mysql', label: 'MySQLi', desc: 'MySQL database support' },
      { key: 'gd', label: 'GD', desc: 'Image processing' },
      { key: 'xml', label: 'XML', desc: 'XML parsing' },
      { key: 'mbstring', label: 'MBString', desc: 'Multibyte string support' },
      { key: 'curl', label: 'cURL', desc: 'HTTP requests' },
      { key: 'zip', label: 'Zip', desc: 'ZIP archive support' },
      { key: 'opcache', label: 'OPcache', desc: 'PHP caching' },
      { key: 'intl', label: 'Intl', desc: 'Internationalization' },
      { key: 'bcmath', label: 'BCMath', desc: 'Arbitrary precision math' },
      { key: 'redis', label: 'Redis', desc: 'Redis session/cache' },
      { key: 'imagick', label: 'Imagick', desc: 'ImageMagick PHP extension' },
      { key: 'soap', label: 'SOAP', desc: 'SOAP web services' },
      { key: 'ldap', label: 'LDAP', desc: 'Directory services' },
      { key: 'pgsql', label: 'PostgreSQL', desc: 'PostgreSQL support' },
      { key: 'sqlite3', label: 'SQLite3', desc: 'SQLite database' },
    ];

    // Web Server options
    const WEB_SERVERS = [
      { key: 'nginx', label: 'Nginx', desc: 'Web server & reverse proxy', port: '80/443' },
      { key: 'apache', label: 'Apache', desc: 'Apache HTTP server', port: '8188/8189' },
      { key: 'openlitespeed', label: 'OpenLiteSpeed', desc: 'High-performance server', port: '8190/8288' },
      { key: 'litespeed', label: 'LiteSpeed Enterprise', desc: 'Premium server (license required)', port: '8290/8291' },
    ];

    const THEMES = [
      { key: 'fresh', label: 'Fresh', color: '#0084FF' },
      { key: 'dark', label: 'Dark', color: '#18181b' },
      { key: 'light', label: 'Light', color: '#ffffff' },
    ];

    const THEME_COLORS = [
      { key: 'default', label: 'Default', color: '#0084FF' },
      { key: 'mint', label: 'Mint', color: '#10B981' },
      { key: 'violet', label: 'Violet', color: '#8B5CF6' },
      { key: 'sky', label: 'Sky Blue', color: '#0EA5E9' },
      { key: 'sakura', label: 'Sakura', color: '#EC4899' },
      { key: 'gold', label: 'Black Gold', color: '#F59E0B' },
    ];

    const THEME_STYLES = [
      { key: 'auto', label: 'Auto' },
      { key: 'light', label: 'Light' },
      { key: 'dark', label: 'Dark' },
    ];

    // Render content based on active tab
    function renderSettingsContent() {
      switch (activeSettingsTab) {
        case 'general':
          return (
            <>
              <div className="settings-section">
                <h3>Panel Information</h3>
                <div className="settings-grid two-col">
                  <div className="settings-field">
                    <label>Panel Alias</label>
                    <input value={settingsData.panel_alias || ''} onChange={e => setSettingsData(prev => ({ ...prev, panel_alias: e.target.value }))} placeholder="My Server" />
                  </div>
                  <div className="settings-field">
                    <label>Session Timeout</label>
                    <select value={settingsData.session_timeout || '24h'} onChange={e => saveSettings('session_timeout', e.target.value)}>
                      <option value="1h">1 Hour</option>
                      <option value="6h">6 Hours</option>
                      <option value="12h">12 Hours</option>
                      <option value="24h">24 Hours</option>
                      <option value="48h">48 Hours</option>
                      <option value="7d">7 Days</option>
                    </select>
                  </div>
                  <div className="settings-field">
                    <label>Default Site Folder</label>
                    <input value={settingsData.default_site_folder || 'public_html'} onChange={e => setSettingsData(prev => ({ ...prev, default_site_folder: e.target.value }))} placeholder="public_html" />
                  </div>
                  <div className="settings-field">
                    <label>Default Backup Folder</label>
                    <input value={settingsData.default_backup_folder || '/var/backups/bpanel'} onChange={e => setSettingsData(prev => ({ ...prev, default_backup_folder: e.target.value }))} placeholder="/var/backups/bpanel" />
                  </div>
                </div>
              </div>
              <div className="settings-section">
                <h3>Server Information</h3>
                <div className="settings-info-box">
                  <p><strong>Server IP:</strong> {settingsData.server_ip || 'Loading...'}</p>
                  <p><strong>Server Time:</strong> {settingsData.server_time ? new Date(settingsData.server_time).toLocaleString() : 'Loading...'}</p>
                </div>
              </div>
              <div className="settings-section">
                <h3>Network Options</h3>
                <div className="settings-toggle" onClick={() => toggleSetting('ipv6_enabled')}>
                  <div className="settings-toggle-label">
                    <strong>IPv6 Support</strong>
                    <span>Enable IPv6 for panel access</span>
                  </div>
                  <div className={`toggle-switch ${settingsData.ipv6_enabled ? 'active' : ''}`}></div>
                </div>
                <div className="settings-toggle" onClick={() => toggleSetting('offline_mode')}>
                  <div className="settings-toggle-label">
                    <strong>Offline Mode</strong>
                    <span>Disable external connections and updates</span>
                  </div>
                  <div className={`toggle-switch ${settingsData.offline_mode ? 'active' : ''}`}></div>
                </div>
                <div className="settings-toggle" onClick={() => toggleSetting('cdn_proxy_enabled')}>
                  <div className="settings-toggle-label">
                    <strong>CDN Proxy</strong>
                    <span>Use CDN for static assets</span>
                  </div>
                  <div className={`toggle-switch ${settingsData.cdn_proxy_enabled ? 'active' : ''}`}></div>
                </div>
              </div>
            </>
          );

        case 'network':
          return (
            <>
              <div className="settings-section">
                <h3>Network Configuration</h3>
                <div className="settings-grid two-col">
                  <div className="settings-field">
                    <label>Domain</label>
                    <input value={settingsData.panel_domain || ''} onChange={e => setSettingsData(prev => ({ ...prev, panel_domain: e.target.value }))} placeholder="panel.example.com" />
                  </div>
                  <div className="settings-field">
                    <label>Port (8888-65535)</label>
                    <input type="number" value={settingsData.panel_port || 2222} onChange={e => setSettingsData(prev => ({ ...prev, panel_port: parseInt(e.target.value) }))} min="8888" max="65535" />
                  </div>
                </div>
              </div>
              <div className="settings-section">
                <h3>Security Entrance</h3>
                <div className="settings-field">
                  <label>Entrance Path</label>
                  <input value={settingsData.security_entrance || ''} onChange={e => setSettingsData(prev => ({ ...prev, security_entrance: e.target.value }))} placeholder="/secure" />
                </div>
                <div className="settings-toggle" onClick={() => toggleSetting('security_entrance_enabled')} style={{ marginTop: 12 }}>
                  <div className="settings-toggle-label">
                    <strong>Enable Security Entrance</strong>
                    <span>Require special path to access panel</span>
                  </div>
                  <div className={`toggle-switch ${settingsData.security_entrance_enabled ? 'active' : ''}`}></div>
                </div>
              </div>
            </>
          );

        case 'ssl':
          return (
            <>
              <div className="settings-section">
                <h3>SSL Status</h3>
                <div className="settings-info-box">
                  <p>Status: {sslStatus?.ssl_enabled ? <span className="badge ok">Enabled</span> : <span className="badge">Disabled</span>}</p>
                  {sslStatus?.domain && <p><strong>Domain:</strong> {sslStatus.domain}</p>}
                  {sslStatus?.issuer && <p><strong>Issuer:</strong> {sslStatus.issuer}</p>}
                  {sslStatus?.expiry_date && <p><strong>Expires:</strong> {sslStatus.expiry_date}</p>}
                  {sslStatus?.days_remaining !== undefined && <p><strong>Days Remaining:</strong> {sslStatus.days_remaining}</p>}
                </div>
              </div>
              <div className="settings-section">
                <h3>SSL Actions</h3>
                <div className="settings-grid two-col">
                  <button disabled={!!loading} onClick={loadSslStatus}><RefreshCw size={14}/> Refresh Status</button>
                  <button disabled={!!loading} onClick={async () => { await request('/settings/ssl/renew', { method: 'POST' }); loadSslStatus(); }}><Shield size={14}/> Renew Certificate</button>
                </div>
              </div>
            </>
          );

        case 'developer':
          return (
            <>
              <div className="settings-section">
                <h3>Developer Mode</h3>
                <div className="settings-toggle" onClick={() => toggleSetting('developer_mode')}>
                  <div className="settings-toggle-label">
                    <strong>Enable Developer Mode</strong>
                    <span>Show debug tools and advanced options</span>
                  </div>
                  <div className={`toggle-switch ${settingsData.developer_mode ? 'active' : ''}`}></div>
                </div>
              </div>
              <div className="settings-section">
                <h3>API Access</h3>
                <div className="settings-toggle" onClick={() => toggleSetting('api_enabled')}>
                  <div className="settings-toggle-label">
                    <strong>Enable API</strong>
                    <span>Allow programmatic access to panel</span>
                  </div>
                  <div className={`toggle-switch ${settingsData.api_enabled ? 'active' : ''}`}></div>
                </div>
              </div>
              <div className="settings-section">
                <h3>API Key</h3>
                <div className="settings-info-box">
                  <p><strong>API Key:</strong> {apiKey?.api_key ? (showApiKey ? apiKey.api_key : '••••••••••••••••••••') : 'Not generated'}</p>
                  <p><strong>Created:</strong> {apiKey?.created_at ? new Date(apiKey.created_at).toLocaleString() : 'N/A'}</p>
                </div>
                <div className="actions">
                  <button disabled={!!loading} onClick={() => setShowApiKey(!showApiKey)}>{showApiKey ? <EyeOff size={14}/> : <Eye size={14}/>} {showApiKey ? 'Hide' : 'Show'}</button>
                  <button disabled={!!loading} onClick={resetApiKey}><RefreshCw size={14}/> Reset Key</button>
                </div>
              </div>
              <div className="settings-section">
                <h3>IP Whitelist</h3>
                <div className="settings-list">
                  {(settingsData.api_whitelist || []).map(ip => (
                    <div key={ip} className="settings-list-item">
                      <span>{ip}</span>
                      <div className="actions">
                        <button className="mini danger" disabled={!!loading} onClick={async () => { await request(`/settings/api/whitelist/${ip}`, { method: 'DELETE' }); loadSettingsData(); }}><Trash2 size={13}/></button>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="settings-field" style={{ marginTop: 12 }}>
                  <label>Add IP Address</label>
                  <div className="actions">
                    <input placeholder="192.168.1.1" onKeyDown={async e => { if (e.key === 'Enter') { await request('/settings/api/whitelist', { method: 'POST', body: JSON.stringify({ ip: e.target.value }) }); e.target.value = ''; loadSettingsData(); }}} />
                    <button disabled={!!loading}><Plus size={14}/> Add</button>
                  </div>
                </div>
              </div>
            </>
          );

        case 'security':
          return (
            <>
              <div className="settings-section">
                <h3>Basic Authentication</h3>
                <div className="settings-toggle" onClick={() => toggleSetting('basic_auth_enabled')}>
                  <div className="settings-toggle-label">
                    <strong>Enable Basic Auth</strong>
                    <span>Additional login barrier before panel login</span>
                  </div>
                  <div className={`toggle-switch ${settingsData.basic_auth_enabled ? 'active' : ''}`}></div>
                </div>
              </div>
              <div className="settings-section">
                <h3>Password Security</h3>
                <div className="settings-toggle" onClick={() => toggleSetting('strong_password_enabled')}>
                  <div className="settings-toggle-label">
                    <strong>Strong Password Required</strong>
                    <span>Require complex passwords for users</span>
                  </div>
                  <div className={`toggle-switch ${settingsData.strong_password_enabled ? 'active' : ''}`}></div>
                </div>
                <div className="settings-field" style={{ marginTop: 12 }}>
                  <label>Password Expiration (days, 0 = never)</label>
                  <select value={settingsData.password_expire_days || 0} onChange={e => saveSettings('password_expire_days', parseInt(e.target.value))}>
                    <option value="0">Never</option>
                    <option value="30">30 Days</option>
                    <option value="60">60 Days</option>
                    <option value="90">90 Days</option>
                    <option value="180">180 Days</option>
                  </select>
                </div>
              </div>
              <div className="settings-section">
                <h3>Authorized IPs</h3>
                <div className="settings-info-box">
                  <p>Comma-separated IP addresses that are allowed to access the panel</p>
                </div>
                <div className="settings-field">
                  <textarea value={(settingsData.authorized_ips || []).join(', ')} onChange={(e) => saveSettings('authorized_ips', e.target.value.split(',').map((ip) => ip.trim()).filter(Boolean))} placeholder="192.168.1.1, 10.0.0.0/8" rows={3} />
                </div>
              </div>
            </>
          );

        case 'interface':
          return (
            <>
              <div className="settings-section">
                <h3>Theme</h3>
                <div className="settings-grid">
                  {THEMES.map(theme => (
                    <div key={theme.key} className={`theme-preset ${settingsData.theme === theme.key ? 'selected' : ''}`} onClick={() => saveSettings('theme', theme.key)}>
                      <div style={{ width: 24, height: 24, borderRadius: 4, background: theme.color }}></div>
                      <span>{theme.label}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="settings-section">
                <h3>Theme Style</h3>
                <div className="settings-grid">
                  {THEME_STYLES.map(style => (
                    <div key={style.key} className={`theme-preset ${settingsData.theme_style === style.key ? 'selected' : ''}`} onClick={() => saveSettings('theme_style', style.key)}>
                      <span>{style.label}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="settings-section">
                <h3>Theme Color</h3>
                <div className="color-picker">
                  {THEME_COLORS.map(color => (
                    <div key={color.key} className={`color-swatch ${settingsData.theme_color === color.key ? 'selected' : ''}`} style={{ background: color.color }} onClick={() => saveSettings('theme_color', color.key)} title={color.label}></div>
                  ))}
                </div>
              </div>
              <div className="settings-section">
                <h3>Background Opacity</h3>
                <div className="slider-field">
                  <div className="range-labels"><span>0%</span><span>100%</span></div>
                  <input type="range" min="0" max="100" value={settingsData.sidebar_bg_opacity || 100} onChange={e => saveSettings('sidebar_bg_opacity', parseInt(e.target.value))} />
                </div>
              </div>
            </>
          );

        case 'backup':
          return (
            <>
              <div className="settings-section">
                <h3>Backup Settings</h3>
                <div className="settings-toggle" onClick={() => toggleSetting('auto_backup_enabled')}>
                  <div className="settings-toggle-label">
                    <strong>Auto Backup</strong>
                    <span>Automatically backup panel settings</span>
                  </div>
                  <div className={`toggle-switch ${settingsData.auto_backup_enabled ? 'active' : ''}`}></div>
                </div>
                <div className="settings-field" style={{ marginTop: 12 }}>
                  <label>Retention Count</label>
                  <input type="number" value={settingsData.backup_retention_count || 7} onChange={e => saveSettings('backup_retention_count', parseInt(e.target.value))} min="1" max="100" />
                </div>
              </div>
              <div className="settings-section">
                <h3>Backup Actions</h3>
                <div className="actions" style={{ marginBottom: 16 }}>
                  <button disabled={!!loading} onClick={createPanelBackup}><Plus size={14}/> Create Backup</button>
                  <button className="danger" disabled={!!loading} onClick={clearAllBackups}><Trash2 size={14}/> Clear All</button>
                </div>
              </div>
              <div className="settings-section">
                <h3>Backup History</h3>
                <div className="settings-list">
                  {backupList.map(backup => (
                    <div key={backup.backup_id} className="settings-list-item">
                      <span>{backup.filename} <small>({(backup.size / 1024 / 1024).toFixed(2)} MB)</small></span>
                      <div className="actions">
                        <button className="mini secondary-light" disabled={!!loading} onClick={() => restoreBackup(backup.backup_id)}><Download size={13}/> Restore</button>
                        <button className="mini danger" disabled={!!loading} onClick={() => deleteBackup(backup.backup_id)}><Trash2 size={13}/></button>
                      </div>
                    </div>
                  ))}
                  {backupList.length === 0 && <p className="hint">No backups yet.</p>}
                </div>
              </div>
            </>
          );

        case 'alarm':
          return (
            <>
              <div className="settings-section">
                <h3>Alarm Tasks</h3>
                <div className="settings-info-box info">
                  <p>Configure monitoring alerts for CPU, memory, disk, and services.</p>
                </div>
                <div className="settings-list">
                  {alarmTasks.map(task => (
                    <div key={task.id} className="settings-list-item">
                      <div>
                        <strong>{task.title}</strong>
                        <br /><small>{task.alarm_type} - {task.notification_method}</small>
                      </div>
                      <div className="actions">
                        <span className={`badge ${task.enabled ? 'ok' : ''}`}>{task.enabled ? 'Active' : 'Disabled'}</span>
                        <button className="mini danger" disabled={!!loading} onClick={() => deleteAlarmTask(task.id)}><Trash2 size={13}/></button>
                      </div>
                    </div>
                  ))}
                  {alarmTasks.length === 0 && <p className="hint">No alarm tasks configured.</p>}
                </div>
              </div>
            </>
          );

        case 'migrate':
          return (
            <>
              <div className="settings-section">
                <h3>Migrate from aaPanel</h3>
                <div className="settings-info-box warning">
                  <p>Migrate websites, databases, and settings from an existing aaPanel installation.</p>
                </div>
                <div className="settings-form-card">
                  <h4>Server Connection</h4>
                  <div className="settings-grid">
                    <div className="settings-field">
                      <label>Server IP</label>
                      <input placeholder="192.168.1.100" />
                    </div>
                    <div className="settings-field">
                      <label>SSH User</label>
                      <input placeholder="root" />
                    </div>
                    <div className="settings-field">
                      <label>SSH Password</label>
                      <input type="password" placeholder="••••••••" />
                    </div>
                  </div>
                  <div className="actions" style={{ marginTop: 16 }}>
                    <button disabled={!!loading}><Globe size={14}/> Test Connection</button>
                    <button disabled={!!loading}><ArrowRightLeft size={14}/> Start Migration</button>
                  </div>
                </div>
              </div>
              <div className="settings-section">
                <h3>Migration Steps</h3>
                <div className="migrate-steps">
                  <div className="migrate-step">
                    <div className="migrate-step-number">1</div>
                    <div className="migrate-step-content">
                      <h4>Connect</h4>
                      <p>Establish SSH connection to remote server</p>
                    </div>
                  </div>
                  <div className="migrate-step">
                    <div className="migrate-step-number">2</div>
                    <div className="migrate-step-content">
                      <h4>Export</h4>
                      <p>Export aaPanel data and configurations</p>
                    </div>
                  </div>
                  <div className="migrate-step">
                    <div className="migrate-step-number">3</div>
                    <div className="migrate-step-content">
                      <h4>Transfer</h4>
                      <p>Transfer data to this BPanel server</p>
                    </div>
                  </div>
                  <div className="migrate-step">
                    <div className="migrate-step-number">4</div>
                    <div className="migrate-step-content">
                      <h4>Import</h4>
                      <p>Import and configure websites, databases</p>
                    </div>
                  </div>
                </div>
              </div>
            </>
          );

        case 'software':
          return (
            <>
              <div className="settings-section">
                <h3>PHP Versions</h3>
                <p className="hint">Install additional PHP versions or modules. Select the modules you need.</p>
                <div className="settings-grid">
                  {PHP_MODULES.map(mod => (
                    <div key={mod.key} className="software-card">
                      <div className="software-info">
                        <strong>{mod.label}</strong>
                        <small>{mod.desc}</small>
                      </div>
                      <label className="checkbox-label">
                        <input type="checkbox" defaultChecked />
                      </label>
                    </div>
                  ))}
                </div>
                <div className="settings-section" style={{ marginTop: 24 }}>
                  <h4>Install PHP Version</h4>
                  <div className="form-row">
                    <select onChange={e => e.target.value && installPhpVersion(e.target.value)} disabled={installingPhp}>
                      <option value="">Select PHP version to install...</option>
                      {['8.1', '8.2', '8.3', '8.4', '8.5'].map(v => (
                        <option key={v} value={v}>PHP {v}</option>
                      ))}
                    </select>
                    <button disabled={installingPhp} onClick={loadPhpVersionsInstalled}>
                      <RefreshCw size={14}/> Refresh
                    </button>
                  </div>
                </div>
              </div>

              <div className="settings-section">
                <h3>Web Servers</h3>
                <p className="hint">Install additional web servers for Multi-WebServer hosting.</p>
                <div className="settings-info-box">
                  <p><strong>Port Assignments:</strong></p>
                  <small>Nginx: 80/443 | Apache: 8188/8189 | OpenLiteSpeed: 8190/8288 | LiteSpeed: 8290/8291</small>
                </div>
                <div className="settings-grid">
                  {WEB_SERVERS.map(ws => {
                    const installed = webServersInstalled.some(e => e.name === ws.key);
                    return (
                      <div key={ws.key} className="software-card">
                        <div className="software-info">
                          <strong>{ws.label}</strong>
                          <small>{ws.desc}</small>
                          <small>Ports: {ws.port}</small>
                        </div>
                        <div className="software-actions">
                          {installed ? (
                            <span className="badge ok">Installed</span>
                          ) : (
                            <button className="secondary" disabled={installingWebServer} onClick={() => installWebServer(ws.key)}>
                              Install
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </>
          );

        case 'service':
          return (
            <>
              <div className="settings-section">
                <h3>System Services</h3>
                <div className="settings-list">
                  {services.map(service => (
                    <div key={service.name} className="settings-list-item">
                      <div>
                        <strong>{service.name}</strong>
                        <br /><small>{service.version || 'N/A'}</small>
                      </div>
                      <div className="actions">
                        <span className={`badge ${service.active ? 'ok' : 'bad'}`}>{service.status}</span>
                        <button className="mini" disabled={!!loading || service.active} onClick={() => serviceAction(service.name, 'start')}><Play size={13}/></button>
                        <button className="mini" disabled={!!loading || !service.active} onClick={() => serviceAction(service.name, 'stop')}><Square size={13}/></button>
                        <button className="mini" disabled={!!loading} onClick={() => serviceAction(service.name, 'restart')}><RefreshCw size={13}/></button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          );

        default:
          return null;
      }
    }

    return (
      <>
        <div className="settings-tabs">
          {SETTINGS_TABS.map(tab => (
            <button
              key={tab.key}
              className={`settings-tab ${activeSettingsTab === tab.key ? 'active' : ''}`}
              onClick={() => setActiveSettingsTab(tab.key)}
            >
              <tab.icon size={16} />
              {tab.label}
            </button>
          ))}
        </div>
        <div className="settings-content">
          {renderSettingsContent()}
        </div>
        <div className="actions" style={{ marginTop: 16 }}>
          <button disabled={!!loading} onClick={loadSettingsData}><RefreshCw size={14}/> Refresh All</button>
        </div>
      </>
    );
  }

  function renderMonitor() {
    const sysInfo = monitorData?.system_info || {};
    const cpuInfo = monitorData?.cpu_info || {};
    const load = monitorData?.load || {};
    const cpu = monitorData?.cpu || {};
    const memory = monitorData?.memory || {};
    const swap = monitorData?.swap || {};
    const diskUsage = monitorData?.disk_usage || {};
    const diskIo = monitorData?.disk_io || {};
    const networkIo = monitorData?.network_io || {};
    const processes = monitorData?.processes || [];

    return <>
      <section className="section">
        <div className="section-title">
          <div>
            <h2>System Monitor</h2>
            <p className="hint">{sysInfo.hostname} - {sysInfo.os}</p>
          </div>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <label className="check-line" style={{ margin: 0 }}>
              <input type="checkbox" checked={autoRefresh} onChange={e => setAutoRefresh(e.target.checked)} />
              <span>Auto-refresh</span>
            </label>
            <select value={refreshInterval} onChange={e => setRefreshInterval(Number(e.target.value))} disabled={!autoRefresh}>
              <option value={1000}>1s</option>
              <option value={2000}>2s</option>
              <option value={5000}>5s</option>
              <option value={10000}>10s</option>
            </select>
            <button disabled={!!loading} onClick={loadMonitorData}><RefreshCw size={15}/> Refresh</button>
          </div>
        </div>
      </section>

      <section className="section">
        <h2>System Information</h2>
        <div className="monitor-info-grid">
          <div className="monitor-info-item">
            <span className="monitor-info-label">Hostname</span>
            <span className="monitor-info-value">{sysInfo.hostname || '--'}</span>
          </div>
          <div className="monitor-info-item">
            <span className="monitor-info-label">Operating System</span>
            <span className="monitor-info-value">{sysInfo.os || '--'}</span>
          </div>
          <div className="monitor-info-item">
            <span className="monitor-info-label">Kernel</span>
            <span className="monitor-info-value">{sysInfo.kernel || '--'}</span>
          </div>
          <div className="monitor-info-item">
            <span className="monitor-info-label">Uptime</span>
            <span className="monitor-info-value">{sysInfo.uptime || '--'}</span>
          </div>
          <div className="monitor-info-item">
            <span className="monitor-info-label">CPU Model</span>
            <span className="monitor-info-value">{cpuInfo.model || '--'}</span>
          </div>
          <div className="monitor-info-item">
            <span className="monitor-info-label">CPU Cores / Threads</span>
            <span className="monitor-info-value">{cpuInfo.cores || '--'} / {cpuInfo.threads || '--'}</span>
          </div>
        </div>
      </section>

      <section className="section">
        <h2>Load Average</h2>
        <div className="resource-grid">
          <div className="resource-card">
            <div className="resource-head"><span className="resource-icon"><Activity size={16}/></span><span>1 min</span></div>
            <strong>{load['1min']?.toFixed(2) || '--'}</strong>
            <small>Load average</small>
          </div>
          <div className="resource-card">
            <div className="resource-head"><span className="resource-icon"><Activity size={16}/></span><span>5 min</span></div>
            <strong>{load['5min']?.toFixed(2) || '--'}</strong>
            <small>Load average</small>
          </div>
          <div className="resource-card">
            <div className="resource-head"><span className="resource-icon"><Activity size={16}/></span><span>15 min</span></div>
            <strong>{load['15min']?.toFixed(2) || '--'}</strong>
            <small>Load average</small>
          </div>
          <div className="resource-card">
            <div className="resource-head"><span className="resource-icon"><Cpu size={16}/></span><span>CPUs</span></div>
            <strong>{load.cpus || '--'}</strong>
            <small>Logical cores</small>
          </div>
        </div>
      </section>

      <section className="section">
        <h2>CPU Usage</h2>
        <div className="resource-grid">
          <div className="resource-card">
            <div className="resource-head"><span className="resource-icon"><Cpu size={16}/></span><span>User</span></div>
            <strong>{formatPercent(cpu.user)}</strong>
            <div className="resource-track"><span style={{ width: `${clampPercent(cpu.user)}%` }}></span></div>
            <small>{cpu.user?.toFixed(1) || 0}%</small>
          </div>
          <div className="resource-card">
            <div className="resource-head"><span className="resource-icon"><Cpu size={16}/></span><span>System</span></div>
            <strong>{formatPercent(cpu.system)}</strong>
            <div className="resource-track"><span style={{ width: `${clampPercent(cpu.system)}%` }}></span></div>
            <small>{cpu.system?.toFixed(1) || 0}%</small>
          </div>
          <div className="resource-card">
            <div className="resource-head"><span className="resource-icon"><Cpu size={16}/></span><span>Idle</span></div>
            <strong>{formatPercent(cpu.idle)}</strong>
            <div className="resource-track"><span style={{ width: `${clampPercent(cpu.idle)}%` }}></span></div>
            <small>{cpu.idle?.toFixed(1) || 0}%</small>
          </div>
          <div className="resource-card">
            <div className="resource-head"><span className="resource-icon"><Cpu size={16}/></span><span>I/O Wait</span></div>
            <strong>{formatPercent(cpu.iowait)}</strong>
            <div className="resource-track"><span style={{ width: `${clampPercent(cpu.iowait)}%` }}></span></div>
            <small>{cpu.iowait?.toFixed(1) || 0}%</small>
          </div>
        </div>
      </section>

      <section className="section">
        <h2>Memory Usage</h2>
        <div className="resource-grid">
          <div className="resource-card">
            <div className="resource-head"><span className="resource-icon"><MemoryStick size={16}/></span><span>Used</span></div>
            <strong>{formatBytes(memory.used)}</strong>
            <div className="resource-track"><span style={{ width: `${clampPercent(memory.percent)}%` }}></span></div>
            <small>{memory.percent?.toFixed(1) || 0}% of {formatBytes(memory.total)}</small>
          </div>
          <div className="resource-card">
            <div className="resource-head"><span className="resource-icon"><MemoryStick size={16}/></span><span>Free</span></div>
            <strong>{formatBytes(memory.free)}</strong>
            <small>{formatBytes(memory.free)}</small>
          </div>
          <div className="resource-card">
            <div className="resource-head"><span className="resource-icon"><MemoryStick size={16}/></span><span>Available</span></div>
            <strong>{formatBytes(memory.available)}</strong>
            <small>{formatBytes(memory.available)}</small>
          </div>
          <div className="resource-card">
            <div className="resource-head"><span className="resource-icon"><MemoryStick size={16}/></span><span>Cached</span></div>
            <strong>{formatBytes(memory.cached)}</strong>
            <small>{formatBytes(memory.buffers)} buffers</small>
          </div>
        </div>
      </section>

      <section className="section">
        <h2>Swap Usage</h2>
        <div className="resource-grid">
          <div className="resource-card">
            <div className="resource-head"><span className="resource-icon"><HardDrive size={16}/></span><span>Swap</span></div>
            <strong>{formatPercent(swap.percent)}</strong>
            <div className="resource-track"><span style={{ width: `${clampPercent(swap.percent)}%` }}></span></div>
            <small>{formatBytes(swap.used)} / {formatBytes(swap.total)}</small>
          </div>
          <div className="resource-card">
            <div className="resource-head"><span className="resource-icon"><HardDrive size={16}/></span><span>Free</span></div>
            <strong>{formatBytes(swap.free)}</strong>
            <small>Swap free</small>
          </div>
        </div>
      </section>

      <section className="section">
        <h2>Disk Usage</h2>
        {Object.keys(diskUsage).length === 0 ? <p className="hint">No disk data available</p> : (
          <div className="resource-grid">
            {Object.entries(diskUsage).map(([mount, info]) => (
              <div className="resource-card" key={mount}>
                <div className="resource-head"><span className="resource-icon"><HardDrive size={16}/></span><span>{mount}</span></div>
                <strong>{formatPercent(info.percent)}</strong>
                <div className="resource-track"><span style={{ width: `${clampPercent(info.percent)}%` }}></span></div>
                <small>{formatBytes(info.used)} / {formatBytes(info.total)}</small>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="section">
        <h2>Disk I/O</h2>
        {Object.keys(diskIo).length === 0 ? <p className="hint">No disk I/O data available</p> : (
          <div className="table">
            <div className="row header-row">
              <span>Device</span>
              <span>Reads</span>
              <span>Writes</span>
              <span>Read Bytes</span>
              <span>Write Bytes</span>
            </div>
            {Object.entries(diskIo).map(([device, stats]) => (
              <div className="row" key={device}>
                <span><strong>{device}</strong></span>
                <span>{formatNumber(stats.reads)}</span>
                <span>{formatNumber(stats.writes)}</span>
                <span>{formatBytes(stats.read_bytes)}</span>
                <span>{formatBytes(stats.write_bytes)}</span>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="section">
        <h2>Network I/O</h2>
        {Object.keys(networkIo).length === 0 ? <p className="hint">No network data available</p> : (
          <div className="table">
            <div className="row header-row">
              <span>Interface</span>
              <span>RX Bytes</span>
              <span>RX Packets</span>
              <span>TX Bytes</span>
              <span>TX Packets</span>
            </div>
            {Object.entries(networkIo).map(([iface, stats]) => (
              <div className="row" key={iface}>
                <span><strong>{iface}</strong></span>
                <span>{formatBytes(stats.rx_bytes)}</span>
                <span>{formatNumber(stats.rx_packets)}</span>
                <span>{formatBytes(stats.tx_bytes)}</span>
                <span>{formatNumber(stats.tx_packets)}</span>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="section">
        <h2>Top Processes</h2>
        {processes.length === 0 ? <p className="hint">No process data available</p> : (
          <div className="table">
            <div className="row header-row">
              <span>PID</span>
              <span>Name</span>
              <span>CPU %</span>
              <span>MEM %</span>
            </div>
            {processes.slice(0, 10).map(proc => (
              <div className="row" key={proc.pid}>
                <span>{proc.pid}</span>
                <span title={proc.name}>{proc.name.length > 30 ? proc.name.substring(0, 30) + '...' : proc.name}</span>
                <span className={proc.cpu > 50 ? 'badge bad' : ''}>{proc.cpu?.toFixed(1)}</span>
                <span>{proc.mem?.toFixed(1)}</span>
              </div>
            ))}
          </div>
        )}
      </section>
    </>;
  }

  function formatNumber(value) {
    const amount = Number(value);
    if (!Number.isFinite(amount)) return '--';
    return amount.toLocaleString();
  }

  // Nginx Proxy render function
  function renderProxy() {
    const templates = proxyTemplates.length > 0 ? proxyTemplates : [
      { name: 'default', description: 'Default' },
      { name: 'websocket', description: 'WebSocket' },
      { name: 'nodejs', description: 'Node.js' },
      { name: 'php', description: 'PHP' },
      { name: 'python', description: 'Python' },
      { name: 'go', description: 'Go' },
      { name: 'static', description: 'Static' },
      { name: 'java', description: 'Java' },
    ];
    return <>
      <section className="section">
        <div className="section-title">
          <div>
            <h2>Nginx Proxy</h2>
            <p className="hint">Configure reverse proxy rules for custom backend applications.</p>
          </div>
          <button disabled={!!loading} onClick={() => { loadProxyConfigs(); loadProxyTemplates(); loadProxyStatus(); }}><RefreshCw size={14}/> Refresh</button>
        </div>
      </section>
      <section className="section">
        <div className="section-title">
          <h3>Proxy Configs</h3>
          <button disabled={!!loading} onClick={() => openProxyModal(null)}><Plus size={14}/> Create</button>
        </div>
        {proxyConfigs.length === 0 ? (
          <div className="empty-state"><Globe size={40}/><p>No proxy configs yet. Create one to get started.</p></div>
        ) : (
          <div className="table">
            <div className="row header-row">
              <span>Domain</span><span>Target URL</span><span>Template</span><span>SSL</span><span>Status</span><span>Actions</span>
            </div>
            {proxyConfigs.map(config => (
              <div className="row" key={config.domain}>
                <span><strong>{config.domain}</strong></span>
                <span>{config.target_url}</span>
                <span>{config.template || 'default'}</span>
                <span>{config.ssl_enabled ? <span className="badge ok"><ShieldCheck size={13}/> SSL</span> : <span className="badge"><Unlock size={13}/> No SSL</span>}</span>
                <span>{config.enabled ? <span className="badge ok">Active</span> : <span className="badge bad">Disabled</span>}</span>
                <div className="row-actions">
                  <button className="mini secondary-light" disabled={!!loading} onClick={() => toggleProxyConfig(config)}>{config.enabled ? <Unlock size={13}/> : <Lock size={13}/>}{config.enabled ? 'Disable' : 'Enable'}</button>
                  {!config.ssl_enabled && <button className="mini secondary-light" disabled={!!loading} onClick={() => setupSsl(config.domain)}><Shield size={13}/> SSL</button>}
                  {config.ssl_enabled && <button className="mini secondary-light" disabled={!!loading} onClick={() => renewSsl(config.domain)}><RefreshCw size={13}/> Renew</button>}
                  <button className="mini secondary-light" disabled={!!loading} onClick={() => openProxyModal(config)}><Edit size={13}/> Edit</button>
                  <button className="mini danger" disabled={!!loading} onClick={() => deleteProxyConfig(config.domain)}><Trash2 size={13}/></button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
      <section className="section">
        <div className="section-title"><h3>Nginx Status</h3></div>
        <div className="info-box">
          <div className="proxy-status-row"><span>Status:</span><span className={proxyStatus?.running ? 'badge ok' : 'badge'}>{proxyStatus?.running ? 'Running' : 'Stopped'}</span></div>
          {proxyStatus?.version && <div className="proxy-status-row"><span>Nginx Version:</span><span>{proxyStatus.version}</span></div>}
        </div>
        <div className="actions">
          <button disabled={!!loading} onClick={reloadNginx}><RefreshCw size={14}/> Reload</button>
          <button disabled={!!loading} onClick={restartNginx}><RotateCcw size={14}/> Restart</button>
        </div>
      </section>
      {showProxyModal && (
        <section className="section nginx-modal">
          <div className="section-title">
            <h2>{editingProxy ? 'Edit Proxy Config' : 'Create Proxy Config'}</h2>
            <button className="secondary-light" onClick={resetProxyForm}><X size={14}/> Close</button>
          </div>
          <div className="proxy-form">
          </div>
        </section>
      )}
    </>;
  }
  function renderNodeJS() {
    if (!isAdmin) return <section className="section"><h2>Node.js</h2><p className="hint">No permission.</p></section>;
    return <>
      <section className="section">
        <div className="section-title">
          <div>
            <h2>Node.js Management</h2>
            <p className="hint">Current version: <strong>{nodeVersion || 'Loading...'}</strong></p>
          </div>
          <button disabled={!!loading} onClick={() => { loadNodeVersion(); loadNodeVersions(); loadPm2Processes(); }}><RefreshCw size={15}/> Refresh</button>
        </div>
      </section>
      <section className="section">
        <h2>Node.js Versions</h2>
        <p className="hint">Install and manage Node.js versions using nvm.</p>
        {nodeVersions.length === 0 ? <p className="hint">Loading...</p> : (
          <div className="table">
            <div className="row header-row"><span>Version</span><span>Actions</span></div>
            {nodeVersions.map(version => (
              <div className="row" key={version}>
                <span><strong>{version}</strong></span>
                <div className="row-actions">
                  {nodeVersion === version ? <span className="badge ok">Current</span> : (
                    <button className="mini" disabled={!!loading || installingVersion === version} onClick={() => installNodeVersion(version)}>
                      <Download size={13}/> Install
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
      <section className="section">
        <h2>PM2 Process Manager</h2>
        <p className="hint">Manage Node.js applications with PM2 process manager.</p>
        <div className="form-row">
          <select value={selectedWebsiteId} onChange={e => setSelectedWebsiteId(e.target.value)}>
            <option value="">Select website</option>
            {websites.map(site => <option key={site.id} value={site.id}>{site.domain}</option>)}
          </select>
          <button disabled={!!loading || !selectedWebsiteId} onClick={() => setupPm2ForWebsite(selectedWebsiteId)}><Plus size={14}/> Setup PM2</button>
        </div>
        {pm2Processes.length === 0 ? <EmptyState icon={Box} message="No PM2 processes found." /> : (
          <div className="table">
            <div className="row header-row"><span>Name</span><span>Status</span><span>CPU</span><span>Memory</span><span>Uptime</span><span>Actions</span></div>
            {pm2Processes.map(proc => (
              <div className="row" key={proc.name}>
                <span><strong>{proc.name}</strong></span>
                <span className={`badge ${proc.status === 'online' ? 'ok' : proc.status === 'errored' ? 'bad' : ''}`}>{proc.status || 'unknown'}</span>
                <span>{proc.cpu !== undefined ? `${proc.cpu}%` : '-'}</span>
                <span>{proc.memory ? formatBytes(proc.memory) : '-'}</span>
                <span>{proc.uptime ? formatNodeUptime(proc.uptime) : '-'}</span>
                <div className="row-actions">
                  <button className="mini" disabled={!!loading} onClick={() => restartPm2Process(proc.name)}><RotateCcw size={13}/> Restart</button>
                  {proc.status !== 'stopped' && proc.status !== 'errored' && (
                    <button className="mini" disabled={!!loading} onClick={() => stopPm2Process(proc.name)}><Square size={13}/> Stop</button>
                  )}
                  <button className="mini secondary-light" disabled={!!loading} onClick={() => loadPm2Logs(proc.name)}><FileText size={13}/> Logs</button>
                  <button className="mini danger" disabled={!!loading} onClick={() => deletePm2Process(proc.name)}><Trash2 size={13}/></button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
      {pm2LogModal && (
        <section className="section log-viewer">
          <div className="section-title">
            <div><h2>PM2 Logs - {pm2LogModal}</h2></div>
            <button className="secondary-light" onClick={() => setPm2LogModal(null)}><X size={14}/> Close</button>
          </div>
          <div className="log-toolbar">
            <select value={pm2Logs.lines} onChange={e => loadPm2Logs(pm2LogModal, Number(e.target.value))} disabled={!!loading}>
              <option value={50}>50 lines</option><option value={100}>100 lines</option><option value={200}>200 lines</option><option value={500}>500 lines</option>
            </select>
            <button disabled={!!loading} onClick={refreshPm2Logs}><RefreshCw size={14}/> Refresh</button>
          </div>
          <pre className="log-output">{pm2Logs.content || 'Loading...'}</pre>
        </section>
      )}
    </>;
  }
  function formatNodeUptime(seconds) {
    if (!seconds || seconds < 0) return '-';
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${mins}m`;
    return `${mins}m`;
  }
  function renderProxy() {
    return (
      <section className="section">
        <div className="section-title">
          <div>
            <h2>Nginx Proxy</h2>
            <p className="hint">Manage reverse proxy configurations</p>
          </div>
          <button disabled={!!loading} onClick={loadProxyConfigs}><RefreshCw size={15}/> Refresh</button>
        </div>
        {proxyConfigs.length > 0 && (
          <div className="table">
            <div className="row header-row">
              <span>Domain</span><span>Template</span><span>SSL</span><span>Status</span><span>Actions</span>
            </div>
            {proxyConfigs.map(c => (
              <div key={c.domain} className="row">
                <span><strong>{c.domain}</strong><small>{c.target_url}</small></span>
                <span>{c.template}</span>
                <span>{c.ssl_enabled ? <Badge className="ok">Enabled</Badge> : <Badge>Disabled</Badge>}</span>
                <span>{c.enabled ? <Badge className="ok">Active</Badge> : <Badge className="muted">Inactive</Badge>}</span>
                <div className="row-actions">
                  <button className="mini" disabled={!!loading} onClick={() => toggleProxyConfig(c)}>{c.enabled ? 'Disable' : 'Enable'}</button>
                  <button className="mini secondary-light" disabled={!!loading} onClick={() => c.ssl_enabled ? renewSsl(c.domain) : setupSsl(c.domain)}>{c.ssl_enabled ? 'Renew SSL' : 'Setup SSL'}</button>
                  <button className="mini secondary-light" disabled={!!loading} onClick={() => openProxyModal(c)}>Edit</button>
                  <button className="mini danger" disabled={!!loading} onClick={() => deleteProxyConfig(c.domain)}>Delete</button>
                </div>
              </div>
            ))}
          </div>
        )}
        {proxyConfigs.length === 0 && <EmptyState icon={Globe} message="No proxy configs" />}
        <div className="actions" style={{ marginTop: 16 }}>
          <button disabled={!!loading} onClick={() => openProxyModal(null)}><Plus size={14}/> Add Proxy Config
        </button>
        <button disabled={!!loading} onClick={reloadNginx}>Reload Nginx</button>
        <button disabled={!!loading} onClick={restartNginx}>Restart Nginx</button>
        <button disabled={!!loading} onClick={loadProxyStatus}>Status</button>
        </div>
        {showProxyModal && (
          <div className="modal-overlay" onClick={closeProxyModal}>
            <div className="modal-content" onClick={e => e.stopPropagation()}>
              <h3>{editingProxy ? 'Edit Proxy Config' : 'New Proxy Config'}</h3>
              <label>Domain<input value={newProxyConfig.domain} onChange={e => setNewProxyConfig(prev => ({ ...prev, domain: e.target.value })} placeholder="proxy.example.com" disabled={!!editingProxy}/></label>
              <label>Target URL<input value={newProxyConfig.target_url} onChange={e => setNewProxyConfig(prev => ({ ...prev, target_url: e.target.value })} placeholder="http://localhost:3000"/></label>
              <label>Template<select value={newProxyConfig.template} onChange={e => setNewProxyConfig(prev => ({ ...prev, template: e.target.value })}>{templates.map(t => <option key={t.name} value={t.name}>{t.name}</option>)}</select></label>
              <label className="check-line"><input type="checkbox" checked={newProxyConfig.ssl_enabled} onChange={e => setNewProxyConfig(prev => ({ ...prev, ssl_enabled: e.target.checked })}/>Enable SSL</label>
              <div className="modal-actions">
                <button disabled={!!loading} onClick={editingProxy ? updateProxyConfig : createProxyConfig}>{editingProxy ? 'Update' : 'Create'}</button>
                <button className="secondary-light" onClick={closeProxyModal}>Cancel</button>
              </div>
            </div>
          </div>
        )}
      </section>
    );
  }

  // Docker functions
  async function loadDockerStatus() {
    const data = await request('/docker/status');
    if (data) setDockerStatus(data);
  }

  async function loadContainers() {
    const data = await request('/docker/containers');
    if (data) setContainers(data);
  }

  async function loadImages() {
    const data = await request('/docker/images');
    if (data) setImages(data);
  }

  async function startContainer(id) {
    const data = await request(`/docker/containers/${id}/start`, { method: 'POST' }, 'Starting container...');
    if (data) {
      setNotice(data.message || 'Container started');
      await loadContainers();
    }
  }

  async function stopContainer(id) {
    const data = await request(`/docker/containers/${id}/stop`, { method: 'POST' }, 'Stopping container...');
    if (data) {
      setNotice(data.message || 'Container stopped');
      await loadContainers();
    }
  }

  async function restartContainer(id) {
    const data = await request(`/docker/containers/${id}/restart`, { method: 'POST' }, 'Restarting container...');
    if (data) {
      setNotice(data.message || 'Container restarted');
      await loadContainers();
    }
  }

  async function getContainerLogs(id) {
    const data = await request(`/docker/containers/${id}/logs`);
    if (data) {
      setSelectedContainer(id);
      setContainerLogs(data.logs || data.content || '');
    }
  }

  async function deleteContainerAction(id) {
    if (!confirm('Delete this container? This cannot be undone.')) return;
    const data = await request(`/docker/containers/${id}`, { method: 'DELETE' }, 'Deleting container...');
    if (data) {
      setNotice(data.message || 'Container deleted');
      await loadContainers();
    }
  }

  async function pullImage() {
    const imageName = prompt('Enter image name to pull (e.g., nginx:latest):');
    if (!imageName) return;
    const data = await request('/docker/images/pull', { method: 'POST', body: JSON.stringify({ name: imageName }) }, 'Pulling image...');
    if (data) {
      setNotice(data.message || 'Image pulled successfully');
      await loadImages();
    }
  }

  async function deleteImageAction(id) {
    if (!confirm('Delete this image? This cannot be undone.')) return;
    const data = await request(`/docker/images/${id}`, { method: 'DELETE' }, 'Deleting image...');
    if (data) {
      setNotice(data.message || 'Image deleted');
      await loadImages();
    }
  }

  function renderPython() {
    return <section className="section">
      <div className="section-title">
        <h2>Python</h2>
        <button disabled={!!loading} onClick={() => { loadPythonVersion(); loadPythonVersions(); loadVenvs(); loadPythonProcesses(); }}><RefreshCw size={15}/> Refresh</button>
      </div>

      {/* Python Version Section */}
      <section className="subsection">
        <h3>Python Version</h3>
        <div className="info-box">
          <p><strong>Current Python:</strong> {pythonVersion || 'Loading...'}</p>
          <p><strong>Available versions:</strong> {pythonVersions.length > 0 ? pythonVersions.join(', ') : 'Loading...'}</p>
        </div>
      </section>

      {/* Virtual Environments Section */}
      <section className="subsection">
        <h3>Virtual Environments</h3>
        <div className="form-row">
          <input value={newVenvName} onChange={e => setNewVenvName(e.target.value)} placeholder="venv name" />
          <select value={newVenvVersion} onChange={e => setNewVenvVersion(e.target.value)}>
            <option value="">Default Python</option>
            {pythonVersions.map(v => <option key={v} value={v}>Python {v}</option>)}
          </select>
          <button disabled={!!loading || !newVenvName} onClick={createVenv}><Plus size={14}/> Create venv</button>
        </div>

        {venvs.length === 0 ? <p className="hint">No virtual environments found.</p> : (
          <div className="table">
            <div className="row header-row">
              <span>Name</span><span>Python</span><span>Path</span><span>Actions</span>
            </div>
            {venvs.map(venv => (
              <div className="row" key={venv.id}>
                <span><strong>{venv.name}</strong></span>
                <span>{venv.python_version || 'default'}</span>
                <span><small>{venv.path}</small></span>
                <div className="row-actions">
                  <button className="mini secondary-light" disabled={!!loading} onClick={() => loadVenvPackages(venv.id)}><Package size={13}/> Packages</button>
                  <button className="mini danger" disabled={!!loading} onClick={() => deleteVenv(venv.id)}><Trash2 size={13}/> Delete</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Packages Section */}
      {selectedVenv && (
        <section className="subsection">
          <h3>Packages - {selectedVenv.name}</h3>
          <div className="form-row">
            <input value={installPackageName} onChange={e => setInstallPackageName(e.target.value)} placeholder="package name (e.g., requests)" />
            <button disabled={!!loading || !installPackageName} onClick={() => installVenvPackage(selectedVenv.id)}><Download size={14}/> Install</button>
            <button className="secondary-light" onClick={() => { setSelectedVenv(null); setVenvPackages([]); }}><X size={14}/> Close</button>
          </div>

          {venvPackages.length === 0 ? <p className="hint">No packages installed or loading...</p> : (
            <div className="table">
              <div className="row header-row">
                <span>Package</span><span>Version</span><span>Actions</span>
              </div>
              {venvPackages.map(pkg => (
                <div className="row" key={pkg.name}>
                  <span><strong>{pkg.name}</strong></span>
                  <span>{pkg.version}</span>
                  <div className="row-actions">
                    <button className="mini danger" disabled={!!loading} onClick={() => uninstallVenvPackage(selectedVenv.id, pkg.name)}><Trash2 size={13}/> Uninstall</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {/* Python Processes Section */}
      <section className="subsection">
        <h3>Python Processes</h3>
        <button className="mini" disabled={!!loading} onClick={loadPythonProcesses}><RefreshCw size={13}/> Refresh</button>

        {pythonProcesses.length === 0 ? <p className="hint">No Python processes running.</p> : (
          <div className="table">
            <div className="row header-row">
              <span>Name</span><span>PID</span><span>Status</span><span>Actions</span>
            </div>
            {pythonProcesses.map(proc => (
              <div className="row" key={proc.pid}>
                <span><strong>{proc.name}</strong></span>
                <span>{proc.pid}</span>
                <span className="badge ok">{proc.status}</span>
                <div className="row-actions">
                  <button className="mini danger" disabled={!!loading}><Square size={13}/> Stop</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </section>;
  }

  function renderEnhancedBackup() {
    const BACKUP_TABS = [
      { key: 'jobs', label: 'Backup Jobs', icon: Package },
      { key: 'history', label: 'History', icon: History },
      { key: 'storage', label: 'Storage', icon: HardDrive },
      { key: 'restore', label: 'Restore', icon: RotateCcw },
    ];

    useEffect(() => {
      if (page === 'backup') {
        loadBackupJobs();
        loadBackupHistory();
        loadStorageConfigs();
      }
    }, [page]);

    function formatSize(bytes) {
      if (!bytes) return '0 B';
      for (const unit of ['B', 'KB', 'MB', 'GB', 'TB']) {
        if (bytes < 1024) return `${bytes.toFixed(2)} ${unit}`;
        bytes /= 1024;
      }
      return `${bytes.toFixed(2)} PB`;
    }

    function getDestinationIcon(type) {
      const icons = {
        local: HardDrive,
        ftp: Upload,
        ssh: Server,
        s3: Cloud,
        minio: Cloud,
        onedrive: Cloud,
        google_drive: Cloud,
        webdav: Link,
        b2: HardDrive,
      };
      return icons[type] || HardDrive;
    }

    function openCreateJobModal() {
      setEditingBackupJob(null);
      setShowBackupJobModal(true);
    }

    function openEditJobModal(job) {
      setEditingBackupJob(job);
      setShowBackupJobModal(true);
    }

    function openStorageModal(type) {
      setStorageModalType(type);
      setShowStorageModal(true);
    }

    function closeBackupJobModal() {
      setShowBackupJobModal(false);
      setEditingBackupJob(null);
    }

    function closeStorageModal() {
      setShowStorageModal(false);
      setStorageModalType(null);
    }

    async function saveBackupJob(jobData) {
      if (editingBackupJob) {
        await updateBackupJob(editingBackupJob.id, jobData);
      } else {
        await createBackupJob(jobData);
      }
    }

    async function toggleJobEnabled(job) {
      await updateBackupJob(job.id, { ...job, enabled: !job.enabled });
    }

    // Render Jobs Tab
    function renderJobsTab() {
      return (
        <div className="backup-jobs-tab">
          <div className="section-actions">
            <button disabled={!!loading} onClick={openCreateJobModal}>
              <Plus size={14}/> Create Job
            </button>
          </div>

          {backupJobs.length === 0 ? (
            <EmptyState icon={Package} message="No backup jobs configured." />
          ) : (
            <div className="jobs-grid">
              {backupJobs.map(job => (
                <div key={job.id} className="job-card">
                  <div className="job-header">
                    <h3>{job.name}</h3>
                    <span className={`badge ${job.job_type === 'full' ? 'ok' : job.job_type === 'incremental' ? 'info' : 'warning'}`}>
                      {job.job_type}
                    </span>
                  </div>
                  <div className="job-destinations">
                    <span className="label">Destinations:</span>
                    {(job.destinations || []).map(dest => {
                      const Icon = getDestinationIcon(dest);
                      return <span key={dest} className="destination-badge" title={dest}><Icon size={14}/></span>;
                    })}
                  </div>
                  <div className="job-meta">
                    <span><Clock size={12}/> {job.schedule || 'Manual'}</span>
                    <span><Shield size={12}/> {job.retention_days || 30} days</span>
                  </div>
                  <div className="job-stats">
                    <span>Compression: {job.compression_level || 6}</span>
                    {job.encryption_enabled && <span><Shield size={12}/> Encrypted</span>}
                  </div>
                  <div className="job-actions">
                    <label className="toggle">
                      <input
                        type="checkbox"
                        checked={job.enabled}
                        onChange={() => toggleJobEnabled(job)}
                      />
                      <span>{job.enabled ? 'Enabled' : 'Disabled'}</span>
                    </label>
                    <button className="mini" disabled={!!loading} onClick={() => runBackupJob(job.id)}>
                      <Play size={13}/> Run Now
                    </button>
                    <button className="mini secondary-light" disabled={!!loading} onClick={() => openEditJobModal(job)}>
                      <Edit size={13}/>
                    </button>
                    <button className="mini danger" disabled={!!loading} onClick={() => deleteBackupJob(job.id)}>
                      <Trash2 size={13}/>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      );
    }

    // Render History Tab
    function renderHistoryTab() {
      return (
        <div className="backup-history-tab">
          <div className="stats-row">
            <div className="stat-card">
              <span className="stat-value">{backupHistory.filter(b => b.status === 'completed').length}</span>
              <span className="stat-label">Completed</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">{backupHistory.filter(b => b.status === 'failed').length}</span>
              <span className="stat-label">Failed</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">{formatSize(backupHistory.reduce((sum, b) => sum + (b.file_size || 0), 0))}</span>
              <span className="stat-label">Total Size</span>
            </div>
          </div>

          {backupHistory.length === 0 ? (
            <EmptyState icon={History} message="No backup history yet." />
          ) : (
            <div className="table">
              <div className="row header-row">
                <span>Date</span>
                <span>Type</span>
                <span>Size</span>
                <span>Status</span>
                <span>Actions</span>
              </div>
              {backupHistory.map(backup => (
                <div className="row" key={backup.id}>
                  <span>{new Date(backup.started_at).toLocaleString()}</span>
                  <span className="badge">{backup.backup_type}</span>
                  <span>{formatSize(backup.file_size)}</span>
                  <span className={`badge ${backup.status === 'completed' ? 'ok' : backup.status === 'failed' ? 'bad' : ''}`}>
                    {backup.status}
                  </span>
                  <div className="row-actions">
                    <button className="mini" disabled={!!loading || backup.status !== 'completed'} onClick={() => downloadBackupAction(backup.id)}>
                      <Download size={13}/>
                    </button>
                    <button className="mini" disabled={!!loading} onClick={() => verifyBackupAction(backup.id)}>
                      <Shield size={13}/>
                    </button>
                    <button className="mini danger" disabled={!!loading} onClick={() => deleteBackupAction(backup.id)}>
                      <Trash2 size={13}/>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      );
    }

    // Render Storage Tab
    function renderStorageTab() {
      const storageTypes = [
        { type: 'local', name: 'Local', icon: HardDrive, description: 'Store backups locally on server' },
        { type: 'ftp', name: 'FTP', icon: Upload, description: 'Upload to FTP server' },
        { type: 'ssh', name: 'SSH/SFTP', icon: Server, description: 'Upload via SSH/SFTP' },
        { type: 's3', name: 'AWS S3', icon: Cloud, description: 'Store in Amazon S3' },
        { type: 'minio', name: 'MinIO', icon: Cloud, description: 'Store in MinIO server' },
        { type: 'onedrive', name: 'OneDrive', icon: Cloud, description: 'Upload to Microsoft OneDrive' },
        { type: 'google-drive', name: 'Google Drive', icon: Cloud, description: 'Upload to Google Drive' },
        { type: 'webdav', name: 'WebDAV', icon: Link, description: 'Store via WebDAV' },
        { type: 'b2', name: 'Backblaze B2', icon: HardDrive, description: 'Store in Backblaze B2' },
      ];

      return (
        <div className="backup-storage-tab">
          <div className="storage-grid">
            {storageTypes.map(storage => (
              <div key={storage.type} className="storage-card" onClick={() => openStorageModal(storage.type)}>
                <storage.icon size={32}/>
                <h4>{storage.name}</h4>
                <p>{storage.description}</p>
              </div>
            ))}
          </div>

          {storageConfigs.length > 0 && (
            <div className="configured-storages">
              <h3>Configured Storage</h3>
              <div className="table">
                <div className="row header-row">
                  <span>Name</span>
                  <span>Type</span>
                  <span>Default</span>
                  <span>Actions</span>
                </div>
                {storageConfigs.map(config => {
                  const Icon = getDestinationIcon(config.storage_type);
                  return (
                    <div className="row" key={config.id}>
                      <span><strong>{config.name}</strong></span>
                      <span><Icon size={14}/> {config.storage_type}</span>
                      <span>{config.is_default ? 'Yes' : 'No'}</span>
                      <div className="row-actions">
                        <button className="mini" disabled={!!loading} onClick={() => testStorageConnection(config.id)}>
                          <Check size={13}/> Test
                        </button>
                        <button className="mini danger" disabled={!!loading} onClick={() => deleteStorageConfig(config.id)}>
                          <Trash2 size={13}/>
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      );
    }

    // Render Restore Tab
    function renderRestoreTab() {
      return (
        <div className="backup-restore-tab">
          <div className="info-box">
            <p><AlertTriangle size={16}/> Select a backup from the History tab to restore.</p>
            <button disabled={!!loading} onClick={() => setBackupActiveTab('history')}>
              <History size={14}/> Go to History
            </button>
          </div>

          <div className="restore-options">
            <h3>Restore Options</h3>
            <p className="hint">Choose what to restore and where to restore it.</p>
            <div className="form-row">
              <label>Restore to:</label>
              <select>
                <option value="website">Website</option>
                <option value="database">Database</option>
                <option value="path">Custom Path</option>
              </select>
            </div>
          </div>
        </div>
      );
    }

    // Render Backup Job Modal
    function renderBackupJobModal() {
      const [formData, setFormData] = useState({
        name: editingBackupJob?.name || '',
        job_type: editingBackupJob?.job_type || 'full',
        destinations: editingBackupJob?.destinations || ['local'],
        include_websites: editingBackupJob?.include_websites || [],
        include_databases: editingBackupJob?.include_databases || [],
        exclude_paths: editingBackupJob?.exclude_paths || [],
        schedule: editingBackupJob?.schedule || '',
        retention_days: editingBackupJob?.retention_days || 30,
        encryption_enabled: editingBackupJob?.encryption_enabled || false,
        compression_level: editingBackupJob?.compression_level || 6,
      });

      function toggleDestination(dest) {
        const dests = formData.destinations.includes(dest)
          ? formData.destinations.filter(d => d !== dest)
          : [...formData.destinations, dest];
        setFormData({ ...formData, destinations: dests });
      }

      function toggleWebsite(id) {
        const sites = formData.include_websites.includes(id)
          ? formData.include_websites.filter(w => w !== id)
          : [...formData.include_websites, id];
        setFormData({ ...formData, include_websites: sites });
      }

      function toggleDatabase(id) {
        const dbs = formData.include_databases.includes(id)
          ? formData.include_databases.filter(d => d !== id)
          : [...formData.include_databases, id];
        setFormData({ ...formData, include_databases: dbs });
      }

      function toggleExclude(pattern) {
        const paths = formData.exclude_paths.includes(pattern)
          ? formData.exclude_paths.filter(p => p !== pattern)
          : [...formData.exclude_paths, pattern];
        setFormData({ ...formData, exclude_paths: paths });
      }

      function handleSubmit(e) {
        e.preventDefault();
        saveBackupJob(formData);
      }

      return (
        <div className="modal-backdrop" onClick={closeBackupJobModal}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{editingBackupJob ? 'Edit Backup Job' : 'Create Backup Job'}</h2>
              <button className="secondary-light" onClick={closeBackupJobModal}><X size={14}/></button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                <label>
                  <span>Job Name</span>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={e => setFormData({ ...formData, name: e.target.value })}
                    required
                    placeholder="e.g., Daily Website Backup"
                  />
                </label>

                <label>
                  <span>Backup Type</span>
                  <select value={formData.job_type} onChange={e => setFormData({ ...formData, job_type: e.target.value })}>
                    <option value="full">Full - Complete backup</option>
                    <option value="incremental">Incremental - Changes since last backup</option>
                    <option value="differential">Differential - Changes since last full backup</option>
                  </select>
                </label>

                <label>
                  <span>Select Websites</span>
                  <div className="checkbox-grid">
                    {websites.map(site => (
                      <label key={site.id} className="checkbox-item">
                        <input
                          type="checkbox"
                          checked={formData.include_websites.includes(site.id)}
                          onChange={() => toggleWebsite(site.id)}
                        />
                        {site.domain}
                      </label>
                    ))}
                  </div>
                </label>

                <label>
                  <span>Select Databases</span>
                  <div className="checkbox-grid">
                    {databases.map(db => (
                      <label key={db.id} className="checkbox-item">
                        <input
                          type="checkbox"
                          checked={formData.include_databases.includes(db.id)}
                          onChange={() => toggleDatabase(db.id)}
                        />
                        {db.db_name}
                      </label>
                    ))}
                  </div>
                </label>

                <label>
                  <span>Exclude Patterns</span>
                  <div className="checkbox-grid">
                    {excludePatterns.map(pat => (
                      <label key={pat.pattern} className="checkbox-item">
                        <input
                          type="checkbox"
                          checked={formData.exclude_paths.includes(pat.pattern)}
                          onChange={() => toggleExclude(pat.pattern)}
                        />
                        {pat.description}
                      </label>
                    ))}
                  </div>
                </label>

                <label>
                  <span>Destinations</span>
                  <div className="checkbox-grid">
                    {['local', 'ftp', 'ssh', 's3', 'minio', 'onedrive', 'google_drive', 'webdav', 'b2'].map(dest => (
                      <label key={dest} className="checkbox-item">
                        <input
                          type="checkbox"
                          checked={formData.destinations.includes(dest)}
                          onChange={() => toggleDestination(dest)}
                        />
                        {dest}
                      </label>
                    ))}
                  </div>
                </label>

                <label>
                  <span>Schedule (Cron Expression)</span>
                  <input
                    type="text"
                    value={formData.schedule}
                    onChange={e => setFormData({ ...formData, schedule: e.target.value })}
                    placeholder="e.g., 0 2 * * * (daily at 2 AM)"
                  />
                </label>

                <label>
                  <span>Retention (Days)</span>
                  <input
                    type="number"
                    value={formData.retention_days}
                    onChange={e => setFormData({ ...formData, retention_days: parseInt(e.target.value) || 30 })}
                    min="1"
                    max="365"
                  />
                </label>

                <label>
                  <span>Compression Level (1-9)</span>
                  <input
                    type="range"
                    min="1"
                    max="9"
                    value={formData.compression_level}
                    onChange={e => setFormData({ ...formData, compression_level: parseInt(e.target.value) })}
                  />
                  <span>{formData.compression_level}</span>
                </label>

                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={formData.encryption_enabled}
                    onChange={e => setFormData({ ...formData, encryption_enabled: e.target.checked })}
                  />
                  <span>Enable Encryption</span>
                </label>
              </div>
              <div className="modal-footer">
                <button type="button" className="secondary-light" onClick={closeBackupJobModal}>Cancel</button>
                <button type="submit" disabled={!!loading || !formData.name}>{editingBackupJob ? 'Update' : 'Create'}</button>
              </div>
            </form>
          </div>
        </div>
      );
    }

    // Render Storage Modal
    function renderStorageModal() {
      const [formData, setFormData] = useState({});

      function handleSubmit(e) {
        e.preventDefault();
        configureStorage(storageModalType, formData);
      }

      const modalTitles = {
        local: 'Configure Local Storage',
        ftp: 'Configure FTP Storage',
        ssh: 'Configure SSH/SFTP Storage',
        s3: 'Configure AWS S3 Storage',
        minio: 'Configure MinIO Storage',
        onedrive: 'Configure OneDrive Storage',
        'google-drive': 'Configure Google Drive Storage',
        webdav: 'Configure WebDAV Storage',
        b2: 'Configure Backblaze B2 Storage',
      };

      const renderFormFields = () => {
        switch (storageModalType) {
          case 'local':
            return (
              <label>
                <span>Path</span>
                <input type="text" value={formData.path || ''} onChange={e => setFormData({ ...formData, path: e.target.value })} placeholder="/var/backups" />
              </label>
            );
          case 'ftp':
            return (
              <>
                <label><span>Name</span><input type="text" value={formData.name || ''} onChange={e => setFormData({ ...formData, name: e.target.value })} placeholder="My FTP" /></label>
                <label><span>Host</span><input type="text" value={formData.host || ''} onChange={e => setFormData({ ...formData, host: e.target.value })} placeholder="ftp.example.com" /></label>
                <label><span>Port</span><input type="number" value={formData.port || 21} onChange={e => setFormData({ ...formData, port: parseInt(e.target.value) })} /></label>
                <label><span>Username</span><input type="text" value={formData.username || ''} onChange={e => setFormData({ ...formData, username: e.target.value })} /></label>
                <label><span>Password</span><input type="password" value={formData.password || ''} onChange={e => setFormData({ ...formData, password: e.target.value })} /></label>
                <label><span>Base Path</span><input type="text" value={formData.base_path || ''} onChange={e => setFormData({ ...formData, base_path: e.target.value })} placeholder="/backups" /></label>
              </>
            );
          case 'ssh':
            return (
              <>
                <label><span>Name</span><input type="text" value={formData.name || ''} onChange={e => setFormData({ ...formData, name: e.target.value })} placeholder="My SSH" /></label>
                <label><span>Host</span><input type="text" value={formData.host || ''} onChange={e => setFormData({ ...formData, host: e.target.value })} placeholder="server.example.com" /></label>
                <label><span>Port</span><input type="number" value={formData.port || 22} onChange={e => setFormData({ ...formData, port: parseInt(e.target.value) })} /></label>
                <label><span>Username</span><input type="text" value={formData.username || ''} onChange={e => setFormData({ ...formData, username: e.target.value })} /></label>
                <label><span>Password (optional)</span><input type="password" value={formData.password || ''} onChange={e => setFormData({ ...formData, password: e.target.value })} /></label>
                <label><span>Private Key</span><textarea value={formData.private_key || ''} onChange={e => setFormData({ ...formData, private_key: e.target.value })} placeholder="Paste private key content..." rows={4} /></label>
                <label><span>Base Path</span><input type="text" value={formData.base_path || ''} onChange={e => setFormData({ ...formData, base_path: e.target.value })} placeholder="/backups" /></label>
              </>
            );
          case 's3':
            return (
              <>
                <label><span>Name</span><input type="text" value={formData.name || ''} onChange={e => setFormData({ ...formData, name: e.target.value })} placeholder="My S3" /></label>
                <label><span>Bucket</span><input type="text" value={formData.bucket || ''} onChange={e => setFormData({ ...formData, bucket: e.target.value })} /></label>
                <label><span>Region</span><input type="text" value={formData.region || ''} onChange={e => setFormData({ ...formData, region: e.target.value })} placeholder="us-east-1" /></label>
                <label><span>Access Key</span><input type="text" value={formData.access_key || ''} onChange={e => setFormData({ ...formData, access_key: e.target.value })} /></label>
                <label><span>Secret Key</span><input type="password" value={formData.secret_key || ''} onChange={e => setFormData({ ...formData, secret_key: e.target.value })} /></label>
                <label><span>Path Prefix (optional)</span><input type="text" value={formData.path_prefix || ''} onChange={e => setFormData({ ...formData, path_prefix: e.target.value })} placeholder="backups/" /></label>
              </>
            );
          case 'minio':
            return (
              <>
                <label><span>Name</span><input type="text" value={formData.name || ''} onChange={e => setFormData({ ...formData, name: e.target.value })} placeholder="My MinIO" /></label>
                <label><span>Endpoint</span><input type="text" value={formData.endpoint || ''} onChange={e => setFormData({ ...formData, endpoint: e.target.value })} placeholder="localhost:9000" /></label>
                <label><span>Bucket</span><input type="text" value={formData.bucket || ''} onChange={e => setFormData({ ...formData, bucket: e.target.value })} /></label>
                <label><span>Access Key</span><input type="text" value={formData.access_key || ''} onChange={e => setFormData({ ...formData, access_key: e.target.value })} /></label>
                <label><span>Secret Key</span><input type="password" value={formData.secret_key || ''} onChange={e => setFormData({ ...formData, secret_key: e.target.value })} /></label>
              </>
            );
          case 'onedrive':
            return (
              <>
                <label><span>Name</span><input type="text" value={formData.name || ''} onChange={e => setFormData({ ...formData, name: e.target.value })} placeholder="My OneDrive" /></label>
                <label><span>Folder Path</span><input type="text" value={formData.folder_path || ''} onChange={e => setFormData({ ...formData, folder_path: e.target.value })} placeholder="/Backups" /></label>
                <p className="hint">OAuth2 authentication will be required. Configure via Settings.</p>
              </>
            );
          case 'google-drive':
            return (
              <>
                <label><span>Name</span><input type="text" value={formData.name || ''} onChange={e => setFormData({ ...formData, name: e.target.value })} placeholder="My Google Drive" /></label>
                <label><span>Folder Path</span><input type="text" value={formData.folder_path || ''} onChange={e => setFormData({ ...formData, folder_path: e.target.value })} placeholder="/Backups" /></label>
                <p className="hint">OAuth2 authentication will be required. Configure via Settings.</p>
              </>
            );
          case 'webdav':
            return (
              <>
                <label><span>Name</span><input type="text" value={formData.name || ''} onChange={e => setFormData({ ...formData, name: e.target.value })} placeholder="My WebDAV" /></label>
                <label><span>URL</span><input type="text" value={formData.url || ''} onChange={e => setFormData({ ...formData, url: e.target.value })} placeholder="https://webdav.example.com" /></label>
                <label><span>Username</span><input type="text" value={formData.username || ''} onChange={e => setFormData({ ...formData, username: e.target.value })} /></label>
                <label><span>Password</span><input type="password" value={formData.password || ''} onChange={e => setFormData({ ...formData, password: e.target.value })} /></label>
              </>
            );
          case 'b2':
            return (
              <>
                <label><span>Name</span><input type="text" value={formData.name || ''} onChange={e => setFormData({ ...formData, name: e.target.value })} placeholder="My B2" /></label>
                <label><span>Account ID</span><input type="text" value={formData.account_id || ''} onChange={e => setFormData({ ...formData, account_id: e.target.value })} /></label>
                <label><span>Application Key</span><input type="password" value={formData.application_key || ''} onChange={e => setFormData({ ...formData, application_key: e.target.value })} /></label>
                <label><span>Bucket</span><input type="text" value={formData.bucket || ''} onChange={e => setFormData({ ...formData, bucket: e.target.value })} /></label>
                <label><span>Path Prefix (optional)</span><input type="text" value={formData.path_prefix || ''} onChange={e => setFormData({ ...formData, path_prefix: e.target.value })} placeholder="backups/" /></label>
              </>
            );
          default:
            return null;
        }
      };

      return (
        <div className="modal-backdrop" onClick={closeStorageModal}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{modalTitles[storageModalType] || 'Configure Storage'}</h2>
              <button className="secondary-light" onClick={closeStorageModal}><X size={14}/></button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                {renderFormFields()}
                <label className="checkbox-label">
                  <input type="checkbox" checked={formData.is_default || false} onChange={e => setFormData({ ...formData, is_default: e.target.checked })} />
                  <span>Set as default destination</span>
                </label>
              </div>
              <div className="modal-footer">
                <button type="button" className="secondary-light" onClick={closeStorageModal}>Cancel</button>
                <button type="submit" disabled={!!loading}>Save</button>
              </div>
            </form>
          </div>
        </div>
      );
    }

    // Main render
    return (
      <section className="section backup-section">
        <div className="section-title">
          <h2>Enhanced Backup</h2>
          <button disabled={!!loading} onClick={() => { loadBackupJobs(); loadBackupHistory(); loadStorageConfigs(); }}>
            <RefreshCw size={15}/> Refresh
          </button>
        </div>

        <div className="segmented-control">
          {BACKUP_TABS.map(tab => (
            <button key={tab.key} className={backupActiveTab === tab.key ? 'active' : ''} onClick={() => setBackupActiveTab(tab.key)}>
              <tab.icon size={15}/> {tab.label}
            </button>
          ))}
        </div>

        <div className="tab-content">
          {backupActiveTab === 'jobs' && renderJobsTab()}
          {backupActiveTab === 'history' && renderHistoryTab()}
          {backupActiveTab === 'storage' && renderStorageTab()}
          {backupActiveTab === 'restore' && renderRestoreTab()}
        </div>

        {showBackupJobModal && renderBackupJobModal()}
        {showStorageModal && renderStorageModal()}
      </section>
    );
  }

  function renderDocker() {
    const isRunning = dockerStatus?.running || dockerStatus?.status === 'running';
    return <>
      <section className="section">
        <div className="section-title">
          <div>
            <h2>Docker Management</h2>
            <p className="hint">Status: {isRunning ? <span className="badge ok">Running</span> : <span className="badge bad">Not Running</span>}</p>
          </div>
          <button disabled={!!loading} onClick={() => { loadDockerStatus(); loadContainers(); loadImages(); }}><RefreshCw size={15}/> Refresh</button>
        </div>
        {!isRunning && <div className="info-box"><p>Docker is not running. Start the Docker service to manage containers and images.</p></div>}
      </section>

      <section className="section">
        <h2>Containers</h2>
        {containers.length === 0 ? <EmptyState icon={Container} message="No containers found." /> : (
          <div className="table">
            <div className="row header-row">
              <span>Name</span>
              <span>Image</span>
              <span>Status</span>
              <span>Ports</span>
              <span>Actions</span>
            </div>
            {containers.map(container => (
              <div className="row" key={container.id}>
                <span><strong>{container.name || container.names?.[0] || container.id?.substring(0, 12)}</strong></span>
                <span>{container.image}</span>
                <span className={`badge ${container.state === 'running' ? 'ok' : ''}`}>{container.state || container.status}</span>
                <span>{container.ports || '-'}</span>
                <div className="row-actions">
                  {container.state !== 'running' && <button className="mini" disabled={!!loading} onClick={() => startContainer(container.id)}><Play size={13}/> Start</button>}
                  {container.state === 'running' && <button className="mini" disabled={!!loading} onClick={() => stopContainer(container.id)}><Square size={13}/> Stop</button>}
                  <button className="mini" disabled={!!loading} onClick={() => restartContainer(container.id)}><RotateCcw size={13}/> Restart</button>
                  <button className="mini secondary-light" disabled={!!loading} onClick={() => getContainerLogs(container.id)}><Eye size={13}/> Logs</button>
                  <button className="mini danger" disabled={!!loading} onClick={() => deleteContainerAction(container.id)}><Trash2 size={13}/></button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="section">
        <h2>Images</h2>
        <div className="actions" style={{marginBottom: 12}}>
          <button disabled={!!loading} onClick={pullImage}><Download size={15}/> Pull Image</button>
        </div>
        {images.length === 0 ? <EmptyState icon={Image} message="No images found." /> : (
          <div className="table">
            <div className="row header-row">
              <span>Repository</span>
              <span>Tag</span>
              <span>Size</span>
              <span>Actions</span>
            </div>
            {images.map(image => (
              <div className="row" key={image.id}>
                <span><strong>{image.repository || image.repo}</strong></span>
                <span>{image.tag}</span>
                <span>{image.size}</span>
                <div className="row-actions">
                  <button className="mini danger" disabled={!!loading} onClick={() => deleteImageAction(image.id)}><Trash2 size={13}/></button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {selectedContainer && (
        <section className="section docker-logs-modal">
          <div className="section-title">
            <div>
              <h2>Container Logs</h2>
              <p className="hint">Container: {containers.find(c => c.id === selectedContainer)?.name || selectedContainer}</p>
            </div>
            <button className="secondary-light" onClick={() => { setSelectedContainer(null); setContainerLogs(''); }}><X size={14}/> Close</button>
          </div>
          <div className="log-toolbar">
            <button disabled={!!loading} onClick={() => getContainerLogs(selectedContainer)}><RefreshCw size={14}/> Refresh</button>
          </div>
          <textarea
            className="code-editor"
            value={containerLogs}
            readOnly
            rows={20}
            style={{ fontFamily: 'monospace', background: '#1e1e1e', color: '#d4d4d4' }}
          />
        </section>
      )}
    </>;
  }

  function renderGo() {
    if (!isAdmin) return <section className="section"><h2>Go</h2><p className="hint">No permission.</p></section>;
    return <section className="section">
    <div className="section-title">
      <h2>Go Project</h2>
      <button disabled={!!loading} onClick={() => { loadGoVersion(); loadGoVersions(); loadGoProcesses(); }}><RefreshCw size={15}/> Refresh</button>
    </div>
    <div className="go-section">
      <h3>Go Version</h3>
      <div className="info-box"><p><strong>Current Version:</strong> {goVersion || 'Loading...'}</p></div>
      <div className="form-row">
        <select value={installingVersion} onChange={e => setInstallingVersion(e.target.value)} disabled={!!loading}>
          <option value="">Select version to install</option>
          {goVersions.filter(v => v !== goVersion).map(v => <option key={v} value={v}>Go {v}</option>)}
        </select>
        <button disabled={!!loading || !installingVersion} onClick={() => installGoVersion(installingVersion)}><Plus size={15}/> Install</button>
      </div>
    </div>
    <div className="go-section">
      <h3>Build &amp; Run</h3>
      <div className="form-row">
        <input value={goBuildPath} onChange={e => setGoBuildPath(e.target.value)} placeholder="Project path" />
        <button disabled={!!loading || !goBuildPath} onClick={buildGoProject}><Play size={15}/> Build</button>
      </div>
      <div className="form-row">
        <input value={goRunPath} onChange={e => setGoRunPath(e.target.value)} placeholder="Project path to run" />
        <button disabled={!!loading || !goRunPath} onClick={runGoProject}><Play size={15}/> Run</button>
      </div>
    </div>
    <div className="go-section">
      <h3>Go Modules</h3>
      <div className="form-row">
        <input value={goModulePath} onChange={e => setGoModulePath(e.target.value)} placeholder="Project path" />
        <button disabled={!!loading || !goModulePath} onClick={() => loadGoModules(goModulePath)}><Search size={15}/> Check</button>
      </div>
      {goModules.length > 0 && (
        <div className="table">
          <div className="row header-row"><span>Module</span><span>Version</span></div>
          {goModules.map((mod, idx) => <div className="row" key={idx}><span><strong>{mod.path}</strong></span><span>{mod.version}</span></div>)}
        </div>
      )}
    </div>
    <div className="go-section">
      <h3>Go Services</h3>
      {goProcesses.length === 0 ? <p className="hint">No Go processes running.</p> : (
        <div className="table">
          <div className="row header-row"><span>Name</span><span>Status</span><span>PID</span><span>Actions</span></div>
          {goProcesses.map(proc => (
            <div className="row" key={proc.name}>
              <span><strong>{proc.name}</strong></span>
              <span className={`badge ${proc.status === 'running' ? 'ok' : ''}`}>{proc.status}</span>
              <span>{proc.pid || '-'}</span>
              <div className="row-actions">
                <button className="mini secondary-light" disabled={!!loading} onClick={() => restartGoProcess(proc.name)}><RotateCcw size={13}/> Restart</button>
                <button className="mini secondary-light" disabled={!!loading} onClick={() => viewGoProcessLogs(proc.name)}><FileText size={13}/> Logs</button>
                <button className="mini danger" disabled={!!loading} onClick={() => stopGoProcess(proc.name)}><Square size={13}/> Stop</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
    {selectedProcess && (
      <div className="go-logs-modal">
        <div className="section-title">
          <h3>Logs - {selectedProcess}</h3>
          <button className="secondary-light" onClick={() => { setSelectedProcess(null); setGoLogs(''); }}><X size={14}/> Close</button>
        </div>
        <button className="mini secondary-light" onClick={() => viewGoProcessLogs(selectedProcess)}><RefreshCw size={13}/> Refresh</button>
        <pre className="log-output">{goLogs || 'Loading...'}</pre>
      </div>
    )}
    <div className="go-section">
      <h3>Setup Go for Website</h3>
      <div className="form-row">
        <select value={selectedWebsiteId} onChange={e => setSelectedWebsiteId(e.target.value)}>
          <option value="">Select website</option>
          {websites.map(site => <option key={site.id} value={site.id}>{site.domain}</option>)}
        </select>
        <button disabled={!!loading || !selectedWebsiteId} onClick={() => setupGoForWebsite(selectedWebsiteId)}><Wrench size={15}/> Setup</button>
      </div>
    </div>
  </section>;
  }

  function renderUsers() {
    if (!isAdmin) return <section className="section"><h2>Users</h2><p className="hint">No permission.</p></section>;
    return <>
      <section className="section">
        <div className="section-title">
          <div><h2>Add panel user</h2><p className="hint">Panel username is also the Linux user. Login as a user before creating websites for that account.</p></div>
        </div>
        <div className="user-create-card">
          <label><span>Username</span><input value={newUser.username} onChange={e => setNewUser(prev => ({ ...prev, username: e.target.value.toLowerCase() }))} placeholder="johndoe" /></label>
          <label><span>Email</span><input value={newUser.email} onChange={e => setNewUser(prev => ({ ...prev, email: e.target.value }))} placeholder="user@domain.com" /></label>
          <label><span>Password</span><input value={newUser.password} onChange={e => setNewUser(prev => ({ ...prev, password: e.target.value }))} placeholder="Min 12 characters" type="password" /></label>
          <label><span>Role</span><select value={newUser.role} onChange={e => setNewUser(prev => ({ ...prev, role: e.target.value }))}>
            <option value="end_user">End user</option><option value="admin">Admin</option>
          </select></label>
          <label><span>Site limit</span><input type="number" value={newUser.website_limit} onChange={e => setNewUser(prev => ({ ...prev, website_limit: e.target.value }))} /></label>
          <label><span>Storage MB</span><input type="number" value={newUser.storage_limit_mb} onChange={e => setNewUser(prev => ({ ...prev, storage_limit_mb: e.target.value }))} /></label>
          <button disabled={!!loading || !newUser.username || !newUser.password} onClick={createUser}><Plus size={14}/> Create user</button>
        </div>
      </section>
      <section className="section">
        <h2>Assign domain to user</h2>
        <div className="assign-row">
          <select value={assignWebsiteId} onChange={e => setAssignWebsiteId(e.target.value)}>
            <option value="">Select domain</option>
            {websites.map(site => <option key={site.id} value={site.id}>{site.domain}</option>)}
          </select>
          <select value={assignUserId} onChange={e => setAssignUserId(e.target.value)}>
            <option value="">Select user</option>
            {users.map(user => <option key={user.id} value={user.id}>{user.username} ({roleLabel(user.role)})</option>)}
          </select>
          <button disabled={!assignWebsiteId || !assignUserId || !!loading} onClick={assignDomainToUser}>Assign</button>
        </div>
      </section>
      <section className="section">
        <div className="section-title">
          <h2>Panel user list</h2>
          <button disabled={!!loading} onClick={loadUsers}><RefreshCw size={14}/> Refresh</button>
        </div>
        {users.length === 0 && <EmptyState icon={Users} message="No users found." />}
        <div className="table">
          {users.map(user => <div className="row user-row" key={user.id}>
            <div className="user-main"><strong>{user.username}</strong><small>{user.email}</small></div>
            <span className="badge">{roleLabel(user.role)}</span>
            <span className={user.totp_enabled ? 'badge ok' : 'badge'}>{user.totp_enabled ? '2FA' : 'No 2FA'}</span>
            <span className="user-metric"><Globe size={13}/>{user.website_limit} sites</span>
            <span className="user-metric"><HardDrive size={13}/>{storageUsageText(user)}</span>
            <div className="row-actions">
              <button className="mini secondary-light" disabled={!!loading} onClick={() => quickLoginUser(user)}><LogIn size={14}/> Login as</button>
              <button className="mini secondary-light" disabled={!!loading} onClick={() => changeUserPassword(user)}><KeyRound size={14}/> Password</button>
              {user.totp_enabled && user.id !== currentUser?.id && <button className="mini secondary-light" disabled={!!loading} onClick={() => resetUserTwoFactor(user)}>Reset 2FA</button>}
              {user.id !== currentUser?.id && <button className="mini danger" disabled={!!loading} onClick={() => deletePanelUser(user)}><Trash2 size={14}/></button>}
            </div>
          </div>)}
        </div>
      </section>
    </>;
  }

  function renderStandaloneEditor() {
    const editorLineCount = Math.max(1, String(fileContent || '').split('\n').length);
    const editorMode = editorLanguage(filePath);
    const siteLabel = currentSite?.domain || (selectedWebsiteId ? `Website #${selectedWebsiteId}` : 'Website');
    return <main className="standalone-editor-page">
      <header className="standalone-editor-top">
        <div className="standalone-editor-title">
          <strong>{filePath || 'No file selected'}</strong>
          <span>{siteLabel}</span>
        </div>
        <div className="standalone-editor-actions">
          <span className="editor-chip">{editorMode}</span>
          <span className="editor-chip">{editorLineCount} line(s)</span>
          <span className="editor-chip">Ln {editorCursor.line}, Col {editorCursor.column}</span>
          <button disabled={!selectedWebsiteId || !!loading} onClick={() => readFile(filePath)}><RefreshCw size={14}/> Reload</button>
          <button disabled={!selectedWebsiteId || !!loading} onClick={writeFile}>Save</button>
          <button disabled={!selectedWebsiteId || !filePath || !!loading} onClick={() => downloadFile(filePath)}><Download size={14}/></button>
          <button className="secondary-light" onClick={() => window.close()}><X size={14}/> Close</button>
        </div>
      </header>
      {loading && <div className="loading">{loading}</div>}
      {error && <div className="error"><AlertCircle size={16} style={{display:'inline',verticalAlign:'middle',marginRight:6}}/>{error}</div>}
      {notice && <div className="notice">{notice}</div>}
      <section className="standalone-editor-body">
        <CodeEditor
          value={fileContent}
          mode={editorMode}
          disabled={!selectedWebsiteId}
          onChange={setFileContent}
          onCursorChange={setEditorCursor}
        />
      </section>
    </main>;
  }

  function renderPage() {
    if (page === 'websites') return renderWebsites();
    if (page === 'ssl') return renderSsl();
    if (page === 'databases') return renderDatabases();
    if (page === 'cron') return renderCron();
    if (page === 'files') return renderFiles();
    if (page === 'backups') return renderBackups();
    if (page === 'security') return renderSecurity();
    if (page === 'php') return renderPhp();
    if (page === 'firewall') return renderFirewall();
    if (page === 'updates') return renderUpdates();
    if (page === 'update') return renderUpdate();
    if (page === 'services') return renderServices();
    if (page === 'settings') return renderPanelSettings();
    if (page === 'monitor') return renderMonitor();
    if (page === 'users') return renderUsers();
    if (page === 'docker') return renderDocker();
    if (page === 'golang') return renderGo();
    if (page === 'nodejs') return renderNodeJS();
    if (page === 'webserver') return renderWebserver({ isAdmin, loading, currentEngine, webEngines, webserverStatus, safetyCheck, websitesWithEngines, loadWebEngines, loadWebsiteEngines, switchWebEngine, loadEngineStatus, repairEngine, checkSafety, restoreConfig, setWebsiteEngine, runServiceAction, EmptyState });
    if (page === 'mail') return renderMail();
    if (page === 'python') return renderPython();
    if (page === 'proxy') return renderProxy();
    if (page === 'backup') return renderEnhancedBackup();
    if (page === 'logs') return <Logs
      websites={websites}
      auditLogs={auditLogs}
      setAuditLogs={setAuditLogs}
      auditStats={auditStats}
      setAuditStats={setAuditStats}
      sshLogs={sshLogs}
      setSshLogs={setSshLogs}
      sshStats={sshStats}
      setSshStats={setSshStats}
      softLogs={softLogs}
      setSoftLogs={setSoftLogs}
      softLogType={softLogType}
      setSoftLogType={setSoftLogType}
      selectedService={selectedService}
      setSelectedService={setSelectedService}
      logLines={logLines}
      setLogLines={setLogLines}
      logLevel={logLevel}
      setLogLevel={setLogLevel}
      logAutoRefresh={logAutoRefresh}
      setLogAutoRefresh={setLogAutoRefresh}
      activeLogTab={activeLogTab}
      setActiveLogTab={setActiveLogTab}
      panelLogsContent={panelLogsContent}
      setPanelLogsContent={setPanelLogsContent}
      websiteLogsContent={websiteLogsContent}
      setWebsiteLogsContent={setWebsiteLogsContent}
      selectedWebsiteLogId={selectedWebsiteLogId}
      setSelectedWebsiteLogId={setSelectedWebsiteLogId}
      selectedLogType={selectedLogType}
      setSelectedLogType={setSelectedLogType}
      loading={loading}
      setNotice={setNotice}
      setError={setError}
    />;
    return renderDashboard();
  }

  // Login screen
  if (bootstrapping) {
    return <main className="login-page">
      <section className="login-card">
        <div className="login-brand">{renderBrandMark('login-brand-mark')}<div><p className="eyebrow">{panelSettings.app_name || 'BPanel'}</p><h1>Loading…</h1></div></div>
      </section>
    </main>;
  }

  if (!isAuthenticated) {
    return <main className="login-page">
      <section className="login-card">
        <div className="login-brand">
          {renderBrandMark('login-brand-mark')}
          <div>
            <p className="eyebrow">Server Management Panel</p>
            <h1>{panelSettings.app_name || 'BPanel'}</h1>
            <p className="hint">Manage websites, databases, backups, SSL, and services.</p>
          </div>
        </div>
        <div className="login-form">
          <input value={username} onChange={e => setUsername(e.target.value)} placeholder="Username" autoComplete="username" />
          <input value={password} onChange={e => setPassword(e.target.value)} placeholder="Password" type="password" autoComplete="current-password" onKeyDown={e => { if (e.key === 'Enter') login(); }} />
          {needsTwoFactor && <input value={otpCode} onChange={e => setOtpCode(e.target.value)} placeholder="Authentication code" inputMode="numeric" autoComplete="one-time-code" onKeyDown={e => { if (e.key === 'Enter') login(); }} />}
          <button disabled={!!loading || !username || !password} onClick={login}>{loading ? 'Logging in...' : 'Login'}</button>
        </div>
        {error && <div className="error"><AlertCircle size={16} style={{display:'inline',verticalAlign:'middle',marginRight:6}}/>{error}</div>}
        {notice && <div className="notice">{notice}</div>}
      </section>
    </main>;
  }

  if (standaloneEditor) return renderStandaloneEditor();

  const ActiveIcon = activeNavItem?.[2] || Home;

  return <main className="app-shell">
    <section className="layout">
      {mobileMenuOpen && <div className="mobile-nav-backdrop" onClick={() => setMobileMenuOpen(false)} aria-hidden="true"></div>}
      <aside className={`sidebar ${mobileMenuOpen ? 'open' : ''}`} role="navigation" aria-label="Main navigation">
        <div className="sidebar-head">
          <div className="sidebar-brand">
            {renderBrandMark()}
            <div>
              <strong>{panelSettings.app_name || 'BPanel'}</strong>
              <small>Server Panel</small>
            </div>
          </div>
          <button className="sidebar-close" onClick={() => setMobileMenuOpen(false)} aria-label="Close menu"><X size={18}/></button>
        </div>
        <nav className="sidebar-nav">
          {navItems.map(([key, label, Icon]) => <button key={key} className={page === key ? 'active' : ''} onClick={() => { setPage(key); setMobileMenuOpen(false); }} aria-current={page === key ? 'page' : undefined}>
            <Icon size={17}/>{label}
          </button>)}
        </nav>
      </aside>
      <div className="content">
        <section className="topbar">
          <button className="mobile-nav-toggle" onClick={() => setMobileMenuOpen(o => !o)} aria-expanded={mobileMenuOpen} aria-label="Toggle navigation">
            <Menu size={20}/><span><ActiveIcon size={17}/>{activeNavItem?.[1] || 'Menu'}</span>
          </button>
          <div className="page-title">
            <p className="eyebrow">Server Management Panel</p>
            <h1>{activeNavItem?.[1] || panelSettings.app_name || 'BPanel'}</h1>
          </div>
          <div className="login logged-in">
            <div className="account-pill"><span>Logged in as</span><strong>{currentUser?.username || username}</strong></div>
            <div className="top-actions">
              <button className="secondary compact-btn" onClick={changeMyPassword} aria-label="Change password" title="Change password"><KeyRound size={15}/><span className="btn-label">Password</span></button>
              <button className="secondary compact-btn" onClick={logout} aria-label="Logout" title="Logout"><LogOut size={15}/><span className="btn-label">Logout</span></button>
            </div>
          </div>
        </section>
        <div className="content-body">
          {renderPage()}
          {loading && <div className="loading"><span></span>{loading}</div>}
          {error && <div className="error">{error}</div>}
          {notice && <div className="notice">{notice}</div>}
        </div>
      </div>
    </section>
  </main>;
}

createRoot(document.getElementById('root')).render(<App />);
