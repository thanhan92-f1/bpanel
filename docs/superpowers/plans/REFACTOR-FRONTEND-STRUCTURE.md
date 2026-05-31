# Frontend Refactoring Plan - Split into Components

## Overview
After all frontend agents complete, split monolithic App.jsx into separate component files for easier maintenance.

## Target Structure

```
frontend/src/
├── App.jsx                 # Main app with routing, auth, state management
├── pages/
│   ├── Dashboard.jsx        # Main dashboard page
│   ├── Websites.jsx         # Website management
│   ├── Databases.jsx         # Database management
│   ├── Docker.jsx           # Docker container management
│   ├── FTP.jsx              # FTP account management
│   ├── PHPVersions.jsx       # Multi-PHP version management
│   ├── phpMyAdmin.jsx       # phpMyAdmin access
│   ├── NodeJS.jsx           # Node.js & PM2 management
│   ├── GoProject.jsx         # Go project management
│   ├── PythonProject.jsx      # Python & venv management
│   ├── NginxProxy.jsx        # Nginx reverse proxy
│   ├── WebServer.jsx         # Multi-webserver (Nginx/Apache/OLS)
│   ├── MailServer.jsx         # Mail domain, mailboxes, emails
│   ├── CronJobs.jsx          # Cron job management
│   ├── Monitor.jsx           # System monitor (CPU, RAM, Disk, Network)
│   ├── Logs.jsx              # All logs (Panel, Website, Audit, SSH)
│   ├── Settings.jsx           # Settings panel
│   ├── Update.jsx            # Auto-update system
│   └── Terminal.jsx           # Terminal feature
├── components/
│   ├── common/
│   │   ├── Modal.jsx         # Reusable modal component
│   │   ├── Table.jsx         # Reusable table component
│   │   ├── Form.jsx          # Reusable form components
│   │   ├── EmptyState.jsx    # Empty state component
│   │   ├── Loading.jsx       # Loading spinner
│   │   ├── Tabs.jsx          # Tab navigation
│   │   └── Badge.jsx          # Status badges
│   ├── forms/
│   │   ├── InputField.jsx
│   │   ├── SelectField.jsx
│   │   ├── ToggleField.jsx
│   │   └── FileUpload.jsx
│   └── charts/
│       ├── ProgressBar.jsx
│       └── Gauge.jsx
├── hooks/
│   ├── useApi.js             # API request hook
│   ├── useAuth.js            # Authentication hook
│   └── useNotification.js    # Notification hook
└── styles/
    ├── variables.css         # CSS variables
    └── components.css         # Shared component styles
```

## Migration Steps

1. **Create directory structure**
2. **Extract common components** to `components/`
3. **Extract each page** to `pages/` directory
4. **Update App.jsx** to import and render pages
5. **Create shared hooks** for API requests
6. **Update imports** in all files

## Benefits
- Easier maintenance
- Better code organization
- Reusable components
- Easier testing
- Team collaboration friendly
