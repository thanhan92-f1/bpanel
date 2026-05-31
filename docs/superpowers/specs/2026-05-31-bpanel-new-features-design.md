# BPanel New Features Design Specification

**Date:** 2026-05-31
**Author:** Claude
**Status:** Draft

---

## 1. Overview

This document specifies 4 major feature additions to BPanel:
1. **Docker Management** - Container orchestration dashboard
2. **WordPress Toolkits** - Enhanced WordPress management tools
3. **FTP Manager** - FTP account management
4. **Node.js Project Management** - Node.js project deployment with PM2

---

## 2. Docker Management

### 2.1 Features

| Feature | Description |
|---------|-------------|
| Dashboard Overview | System-wide Docker status, container count, image count, volume count, network count |
| Container Management | List, start, stop, restart, remove containers; view logs; exec into container |
| One-Click Install (50 Apps) | Pre-configured Docker Compose templates for popular apps |
| Cloud Image Search | Search Docker Hub for images |
| Local Images | List local images, pull from Docker Hub, upload/import images |
| Docker Compose | Create, edit, deploy, manage Docker Compose stacks |
| Networks | List, create, delete Docker networks |
| Volumes | List, create, delete Docker volumes |
| Settings | Docker daemon configuration, registry settings |

### 2.2 API Endpoints (Backend)

```
GET    /docker/status              - Docker daemon status
GET    /docker/containers         - List all containers
POST   /docker/containers/:id/start
POST   /docker/containers/:id/stop
POST   /docker/containers/:id/restart
DELETE /docker/containers/:id
GET    /docker/containers/:id/logs?lines=100
GET    /docker/images             - List local images
POST   /docker/images/pull        - Pull image from registry
POST   /docker/images/import      - Import image from file
DELETE /docker/images/:id
GET    /docker/networks           - List networks
POST   /docker/networks           - Create network
DELETE /docker/networks/:id
GET    /docker/volumes            - List volumes
POST   /docker/volumes            - Create volume
DELETE /docker/volumes/:id
GET    /docker/compose/list       - List compose projects
POST   /docker/compose/up         - Deploy compose stack
POST   /docker/compose/down       - Stop compose stack
GET    /docker/hub/search?q=      - Search Docker Hub
GET    /docker/hub/tags/:image    - Get image tags
```

### 2.3 Database Models

```python
class DockerContainer(Base):
    __tablename__ = "docker_containers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    container_id: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    image: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime)

class DockerComposeProject(Base):
    __tablename__ = "docker_compose_projects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    compose_content: Mapped[str] = mapped_column(Text)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime)
```

### 2.4 One-Click Install Apps (50)

```
1.  Nginx
2.  Apache
3.  MySQL
4.  PostgreSQL
5.  MongoDB
6.  Redis
7.  Memcached
8.  RabbitMQ
9.  Elasticsearch
10. Prometheus
11. Grafana
12. Jenkins
13. GitLab Runner
14. SonarQube
15. Nexus Repository
16. Portainer
17. Traefik
18. Caddy
19. HaProxy
20. Vault
21. MinIO
22. Watchtower
23. Uptime Kuma
24. Matomo
25. Pi-hole
26. AdGuard Home
27. NextCloud
28. OwnCloud
29. Pydio
30. Jellyfin
31. Plex
32. Emby
33. Radarr
34. Sonarr
35. Lidarr
36. Jackett
37. NZBGet
38. SABnzbd
39. Duplicati
40. Home Assistant
41. OpenHAB
42. Mosquitto
43. Node-RED
44. Grafana Loki
45. AlertManager
46. Cadvisor
47. Blackbox Exporter
48. nginx-proxy
49. phpMyAdmin
50. Adminer
```

### 2.5 Frontend Components

- `DockerDashboard` - Overview statistics
- `DockerContainers` - Container list and actions
- `DockerImages` - Local images management
- `DockerHubSearch` - Docker Hub search interface
- `DockerCompose` - Compose editor and management
- `DockerNetworks` - Network management
- `DockerVolumes` - Volume management
- `DockerOneClick` - One-click install wizard
- `DockerSettings` - Docker configuration

---

## 3. WordPress Toolkits

### 3.1 Features

| Feature | Description |
|---------|-------------|
| WP-CLI Enhanced | Full WP-CLI interface with command builder |
| Plugin Manager | Install, activate, deactivate, delete plugins |
| Theme Manager | Install, activate, switch themes |
| Database Operations | wp db export, import, optimize, repair |
| Cache Management | Object cache, page cache, CDN cache |
| Security Scan | Scan for malware, weak passwords, outdated plugins |
| Performance Monitor | Core Web Vitals, query analysis |
| Staging Environment | Create staging copy of site |
| Auto Updates | Configure auto-update behavior |
| Backup Integration | WP-CLI backup commands |

### 3.2 API Endpoints

```
GET    /wordpress/:id/plugins          - List plugins
POST   /wordpress/:id/plugins/install  - Install plugin
POST   /wordpress/:id/plugins/:plugin/activate
POST   /wordpress/:id/plugins/:plugin/deactivate
DELETE /wordpress/:id/plugins/:plugin
GET    /wordpress/:id/themes           - List themes
POST   /wordpress/:id/themes/install   - Install theme
POST   /wordpress/:id/themes/:theme/activate
DELETE /wordpress/:id/themes/:theme
POST   /wordpress/:id/db/export
POST   /wordpress/:id/db/import
POST   /wordpress/:id/cache/clear
GET    /wordpress/:id/health
POST   /wordpress/:id/staging/create
POST   /wordpress/:id/staging/push
```

### 3.3 Frontend Components

- `WordPressToolkits` - Main toolkit container
- `WpPluginManager` - Plugin management UI
- `WpThemeManager` - Theme management UI
- `WpDatabaseTools` - DB operations interface
- `WpCacheManager` - Cache controls
- `WpSecurityScan` - Security scanner UI
- `WpStaging` - Staging environment manager

---

## 4. FTP Manager

### 4.1 Features

| Feature | Description |
|---------|-------------|
| FTP Account List | List all FTP accounts with status |
| Create FTP Account | Create FTP account linked to website |
| Edit FTP Account | Change password, home directory |
| Delete FTP Account | Remove FTP account |
| FTP Client Integration | Generate FTP config for FileZilla |
| Quota Management | Set upload/download limits per account |
| Access Logs | View FTP access history |

### 4.2 API Endpoints

```
GET    /ftp/accounts              - List FTP accounts
POST   /ftp/accounts              - Create FTP account
PATCH  /ftp/accounts/:id          - Update FTP account
DELETE /ftp/accounts/:id          - Delete FTP account
POST   /ftp/accounts/:id/password - Change password
GET    /ftp/accounts/:id/logs     - Get access logs
GET    /ftp/accounts/:id/config   - Generate FileZilla config
```

### 4.3 Database Models

```python
class FtpAccount(Base):
    __tablename__ = "ftp_accounts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    home_directory: Mapped[str] = mapped_column(String(500))
    website_id: Mapped[Optional[int]] = mapped_column(ForeignKey("websites.id"), nullable=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    max_upload_mb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
```

### 4.4 Frontend Components

- `FtpAccounts` - Account list and management
- `FtpAccountForm` - Create/edit form
- `FtpAccessLogs` - Access history viewer

---

## 5. Node.js Project Management

### 5.1 Features

| Feature | Description |
|---------|-------------|
| Node Version Manager | Install, switch Node.js versions (via nvm) |
| Project Creation | Create new Node.js project from templates |
| PM2 Integration | Start, stop, restart, delete PM2 processes |
| PM2 Monitor | Real-time CPU/RAM monitoring per process |
| Log Viewer | View PM2 logs per process |
| Process Management | Scale, reload, graceful restart |
| Environment Variables | Manage env vars per project |
| Auto-restart | Configure auto-start on server boot |

### 5.2 API Endpoints

```
GET    /node/versions              - List installed Node versions
GET    /node/versions/available   - List available versions to install
POST   /node/versions/install     - Install Node version
DELETE /node/versions/:version    - Remove Node version
GET    /node/projects             - List Node.js projects
POST   /node/projects             - Create project
DELETE /node/projects/:id         - Delete project
GET    /node/pm2/list             - List PM2 processes
POST   /node/pm2/start            - Start process
POST   /node/pm2/stop            - Stop process
POST   /node/pm2/restart         - Restart process
DELETE /node/pm2/:name           - Delete process
GET    /node/pm2/:name/logs       - Get PM2 logs
GET    /node/pm2/:name/monitor    - Get CPU/RAM stats
POST   /node/pm2/:name/env        - Update env vars
GET    /node/pm2/startup-config   - Generate startup script
```

### 5.3 Database Models

```python
class NodeProject(Base):
    __tablename__ = "node_projects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    path: Mapped[str] = mapped_column(String(500))
    node_version: Mapped[str] = mapped_column(String(16))
    pm2_name: Mapped[str] = mapped_column(String(100))
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    auto_start: Mapped[bool] = mapped_column(Boolean, default=True)
    env_vars: Mapped[str] = mapped_column(Text, default="{}")  # JSON
    created_at: Mapped[datetime] = mapped_column(DateTime)
```

### 5.4 Frontend Components

- `NodeDashboard` - Overview with version info
- `NodeVersionManager` - Version installation UI
- `NodeProjects` - Project list
- `NodeProjectForm` - Create/edit project
- `Pm2Monitor` - Real-time process monitoring
- `Pm2Logs` - Log viewer
- `NodeEnvEditor` - Environment variable editor

---

## 6. Navigation Structure

### New Nav Items (Frontend)

```javascript
const navItems = [
  // ... existing items ...
  ['docker', 'Docker', Docker],
  ['wordpress-toolkit', 'WP Toolkits', Wrench],
  ['ftp', 'FTP Manager', FolderSync],
  ['nodejs', 'Node.js', Box],
];
```

---

## 7. Implementation Order

1. **Phase 1: Docker Management** (Most complex)
   - Backend API structure
   - Docker service layer
   - Frontend components
   - One-Click Install templates

2. **Phase 2: WordPress Toolkits** (Enhancement)
   - Extend existing WordPress service
   - Add new API endpoints
   - Build toolkit UI

3. **Phase 3: FTP Manager** (Medium)
   - FTP account model
   - vsftpd integration
   - Frontend CRUD

4. **Phase 4: Node.js Management** (PM2 focus)
   - nvm/Node version support
   - PM2 integration
   - Monitoring dashboard

---

## 8. Security Considerations

1. **Docker**: Restrict privileged containers, enforce resource limits
2. **WordPress**: Sanitize all WP-CLI commands, validate paths
3. **FTP**: Use FTPS/SFTP, encrypt passwords, rate limit
4. **Node.js**: Validate project paths, sandbox PM2 processes

---

## 9. Dependencies

### Backend
- `docker` (Python SDK) - For Docker management
- `pyftpdlib` or `pyftpdlib` - For FTP server management

### Frontend
- `lucide-react` - For new icons (already installed)
- Chart.js or Recharts - For monitoring dashboards

---

## 10. Migration Files Required

1. `0012_docker_tables.py` - Docker containers, compose projects
2. `0013_ftp_accounts.py` - FTP accounts table
3. `0014_node_projects.py` - Node.js projects table
