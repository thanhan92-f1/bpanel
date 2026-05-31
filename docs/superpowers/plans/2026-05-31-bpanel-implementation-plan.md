# BPanel New Features Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement 4 major features: Docker Management, WordPress Toolkits, FTP Manager, and Node.js Project Management

**Architecture:** FastAPI backend with modular services, React SPA frontend with single-file component pattern, Docker SDK for container management, PM2 for Node.js process management

**Tech Stack:** Python FastAPI, Docker SDK, PM2 CLI, React 18, Ace Editor

---

## Phase 1: Docker Management

### Task 1: Docker Backend - Service Layer

**Files:**
- Create: `backend/app/services/docker.py`
- Create: `backend/app/api/docker.py`
- Modify: `backend/app/main.py` (add router)
- Modify: `backend/app/models/entities.py` (add models)

- [ ] **Step 1: Create migration for Docker tables**

```bash
cd backend
.venv/bin/alembic revision --autogenerate -m "add docker tables"
```

- [ ] **Step 2: Create Docker service layer**

```python
# backend/app/services/docker.py
import docker
from docker.errors import DockerException
from typing import List, Dict, Optional
```

- [ ] **Step 3: Create Docker API router**

```python
# backend/app/api/docker.py
from fastapi import APIRouter, HTTPException
router = APIRouter(prefix="/docker", tags=["docker"])
```

- [ ] **Step 4: Add router to main.py**

```python
from app.api import docker
app.include_router(docker.router, prefix="/api")
```

### Task 2: Docker Frontend Components

**Files:**
- Modify: `frontend/src/App.jsx` (add Docker page)

- [ ] **Step 1: Add Docker navigation item**

```javascript
['docker', 'Docker', Docker],
```

- [ ] **Step 2: Add Docker state variables**

```javascript
const [dockerStatus, setDockerStatus] = useState(null);
const [containers, setContainers] = useState([]);
const [images, setImages] = useState([]);
```

- [ ] **Step 3: Create Docker page render function**

```javascript
function renderDocker() { ... }
```

### Task 3: Docker One-Click Install Templates

**Files:**
- Create: `backend/app/templates/docker/` (50 compose templates)

---

## Phase 2: WordPress Toolkits

### Task 4: WordPress Toolkit Backend

**Files:**
- Modify: `backend/app/services/wordpress.py` (extend)
- Create: `backend/app/api/wordpress_toolkit.py`

- [ ] **Step 1: Add plugin/theme management functions**

```python
def list_plugins(path: str) -> List[Dict]:
    # wp plugin list --format=json --path={path} --allow-root
```

- [ ] **Step 2: Create WordPress toolkit API**

```python
# backend/app/api/wordpress_toolkit.py
@router.get("/wordpress/{website_id}/plugins")
async def list_plugins(website_id: int):
```

### Task 5: WordPress Toolkit Frontend

**Files:**
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Add WP Toolkit tab state**

```javascript
const [wpToolkitTab, setWpToolkitTab] = useState('plugins');
```

---

## Phase 3: FTP Manager

### Task 6: FTP Manager Backend

**Files:**
- Create: `backend/app/services/ftp.py`
- Create: `backend/app/api/ftp.py`
- Modify: `backend/app/models/entities.py`

- [ ] **Step 1: Create migration for FTP accounts**

```bash
cd backend
.venv/bin/alembic revision --autogenerate -m "add ftp accounts"
```

- [ ] **Step 2: Create FTP service**

```python
# backend/app/services/ftp.py
import subprocess
def create_ftp_user(username: str, password: str, home: str):
    # useradd, chpasswd commands
```

### Task 7: FTP Manager Frontend

**Files:**
- Modify: `frontend/src/App.jsx`

---

## Phase 4: Node.js Management

### Task 8: Node.js Backend

**Files:**
- Create: `backend/app/services/nodejs.py`
- Create: `backend/app/api/nodejs.py`
- Modify: `backend/app/models/entities.py`

- [ ] **Step 1: Create migration for Node projects**

```bash
cd backend
.venv/bin/alembic revision --autogenerate -m "add node projects"
```

- [ ] **Step 2: Create Node.js service**

```python
# backend/app/services/nodejs.py
def list_node_versions():
    # nvm list, nvm install
def list_pm2_processes():
    # pm2 list --format=json
```

### Task 9: Node.js Frontend (PM2 Monitor)

**Files:**
- Modify: `frontend/src/App.jsx`

---

## Implementation Sequence

1. **Phase 1.1**: Docker service + API (backend)
2. **Phase 1.2**: Docker frontend components
3. **Phase 2.1**: WordPress toolkit backend extensions
4. **Phase 2.2**: WordPress toolkit frontend
5. **Phase 3.1**: FTP manager backend
6. **Phase 3.2**: FTP manager frontend
7. **Phase 4.1**: Node.js backend
8. **Phase 4.2**: Node.js frontend

---

## Testing Strategy

1. Backend API tests with pytest
2. Frontend component rendering
3. Manual testing on Ubuntu 24.04

