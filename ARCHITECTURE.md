# 🏗️ Architecture Overview

This document provides a technical overview of the Scrum Master Agent architecture.

## 📁 Project Structure

```
scrum_agent/
├── config/                          # Configuration files
│   ├── config.yaml                  # Main configuration (application settings)
│   └── credentials.properties       # Sensitive credentials (git-ignored)
│
├── src/                             # Source code
│   ├── __init__.py
│   ├── main.py                      # Entry point and CLI
│   ├── config.py                    # Configuration loader
│   ├── database.py                  # SQLAlchemy models and DB setup
│   ├── jira_client.py               # Jira API wrapper with rate limiting
│   ├── email_service.py             # Email sending service
│   ├── chatbot.py                   # Azure OpenAI chatbot
│   ├── scheduler.py                 # Background job scheduler
│   │
│   ├── services/                    # Business logic services
│   │   ├── daily_report.py          # Daily report generation
│   │   ├── dashboard.py             # Dashboard data aggregation
│   │   └── follow_up.py             # Follow-up automation
│   │
│   └── web/                         # Web application
│       ├── app.py                   # FastAPI application and routes
│       └── static/                  # Frontend assets
│           ├── index.html           # Main UI
│           ├── styles.css           # Styling
│           └── script.js            # Frontend logic
│
├── requirements.txt                 # Python dependencies
├── README.md                        # Main documentation
├── QUICKSTART.md                    # Quick setup guide
├── setup.sh                         # Automated setup script
├── run.sh                           # Application runner
└── test.sh                          # Connection tester
```

## 🔧 Core Components

### 1. Configuration Management (`config.py`)

**Purpose**: Centralized configuration loading and access

**Key Features**:
- Loads YAML configuration from `config/config.yaml`
- Reads credentials from `config/credentials.properties`
- Provides convenient property accessors
- Validates configuration on startup

**Usage**:
```python
from src.config import config

jira_url = config.jira_url
refresh_interval = config.get('dashboard.refresh_interval_minutes', 60)
```

### 2. Database Layer (`database.py`)

**Purpose**: Data persistence and caching

**Technology**: SQLAlchemy with SQLite

**Models**:
- `JiraIssue`: Cached Jira issue data
- `IssueComment`: Cached comments
- `DailyReport`: Generated reports history
- `FollowUp`: Follow-up tracking
- `DashboardCache`: Dashboard data cache

**Key Features**:
- Context manager for session handling
- Automatic schema creation
- Transaction management

**Usage**:
```python
from src.database import db

with db.get_session() as session:
    issues = session.query(JiraIssue).filter_by(assignee=user).all()
```

### 3. Jira Client (`jira_client.py`)

**Purpose**: Interact with Jira Cloud API

**Key Features**:
- Token bucket rate limiting (60/min, 3000/hr)
- Automatic retry logic
- Comprehensive error handling
- Issue querying with JQL
- Comment management
- Worklog retrieval

**Rate Limiting**:
```python
class RateLimiter:
    - Tracks API calls per minute and hour
    - Automatically sleeps when approaching limits
    - Prevents API quota exhaustion
```

**Usage**:
```python
from src.jira_client import jira_client

issues = jira_client.get_my_issues()
jira_client.add_comment(issue_key, "Update message")
```

### 4. Email Service (`email_service.py`)

**Purpose**: Send emails for reports and notifications

**Key Features**:
- SMTP support (Gmail, Office365, etc.)
- HTML and plain text emails
- Template-based formatting
- Configurable delivery

**Email Types**:
- Daily reports (HTML formatted)
- Follow-up notifications
- Custom notifications

### 5. Services Layer

#### a. Daily Report Service (`services/daily_report.py`)

**Workflow**:
1. Query Jira for today's activity
2. Aggregate completed, new, in-progress tickets
3. Collect comments and time logged
4. Identify blockers
5. Generate HTML and text reports
6. Store in database
7. Send via configured channels (email, file)

**Report Sections**:
- Statistics cards
- Completed tickets
- New tickets
- In-progress tickets
- Comments summary
- Time logged by user
- Blockers

#### b. Dashboard Service (`services/dashboard.py`)

**Workflow**:
1. Check cache validity (hourly refresh)
2. Fetch my issues from Jira
3. Categorize (assigned, mentioned, watching)
4. Calculate sprint statistics
5. Aggregate recent activity
6. Cache results
7. Return formatted data

**Caching Strategy**:
- Cache duration: 60 minutes (configurable)
- SQLite-based caching
- Force refresh available

#### c. Follow-up Service (`services/follow_up.py`)

**Workflow**:
1. Get active sprint issues
2. Filter by excluded statuses
3. Check for inactivity (24hr threshold)
4. Verify no recent comments or status changes
5. Check if already followed up recently
6. Send via configured methods (Jira comment, email)
7. Record in database

**Inactivity Detection**:
- Last updated date
- Recent comments
- Status changes via changelog
- Configurable threshold

### 6. Chatbot (`chatbot.py`)

**Purpose**: AI-powered scrum assistance

**Technology**: Azure OpenAI (GPT-4)

**Key Features**:
- Contextual responses with Jira data
- Conversation history management
- Suggested questions
- Session-based conversations

**Context Injection**:
```python
def get_context(self):
    - Current assigned tickets
    - Sprint progress
    - Status breakdown
    - Story points completion
```

**Conversation Flow**:
1. User sends message
2. System injects current Jira context
3. Azure OpenAI processes with history
4. Response returned and displayed
5. History updated

### 7. Scheduler (`scheduler.py`)

**Purpose**: Background job automation

**Technology**: APScheduler

**Scheduled Jobs**:
- **Daily Report**: 9 PM daily (configurable)
- **Follow-up Check**: 10 AM daily (configurable)
- **Dashboard Refresh**: Every 60 minutes (configurable)

**Features**:
- Timezone-aware scheduling
- Automatic job recovery
- Configurable enable/disable
- Job status monitoring

### 8. Web Application (`web/app.py`)

**Purpose**: User interface and API endpoints

**Technology**: FastAPI

**API Endpoints**:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/` | Main dashboard page |
| GET | `/api/health` | Health check and status |
| GET | `/api/dashboard` | Get dashboard data |
| POST | `/api/dashboard/refresh` | Force refresh |
| POST | `/api/chat` | Chat with bot |
| GET | `/api/chat/suggestions` | Get suggested questions |
| DELETE | `/api/chat/history/{id}` | Clear chat history |
| POST | `/api/report/generate` | Generate report manually |
| POST | `/api/follow-up/check` | Check follow-ups manually |
| GET | `/api/follow-up/history` | Get follow-up history |

**Frontend**:
- Single-page application
- Vanilla JavaScript (no frameworks)
- Real-time updates via API polling
- Responsive design
- Tab-based navigation

## 🔄 Data Flow

### Daily Report Generation

```
Scheduler (9 PM)
    ↓
DailyReportService.save_and_send_report()
    ↓
├─→ Get completed tickets (JQL: status changed to Done today)
├─→ Get new tickets (JQL: created >= startOfDay)
├─→ Get in-progress tickets (JQL: status = 'In Progress')
├─→ Get comments (fetch all, filter by date)
├─→ Get time logged (worklog entries)
└─→ Get blockers (JQL: labels = blocked)
    ↓
Generate HTML + Text reports
    ↓
├─→ Save to database (DailyReport table)
├─→ Send via email (EmailService)
└─→ Save to file (optional)
```

### Dashboard Request

```
User opens dashboard
    ↓
GET /api/dashboard
    ↓
DashboardService.get_dashboard_data()
    ↓
Check cache (< 60min old?)
    ↓
    YES → Return cached data
    ↓
    NO → Generate fresh data
        ↓
        ├─→ JiraClient.get_my_issues()
        ├─→ JiraClient.get_active_sprint_issues()
        ├─→ Categorize issues (assigned, mentioned, watching)
        ├─→ Calculate statistics (status, priority, type)
        ├─→ Get sprint statistics (completion %, points)
        └─→ Get recent activity
            ↓
        Cache in database
            ↓
        Return data
            ↓
Frontend renders dashboard
```

### Follow-up Check

```
Scheduler (10 AM)
    ↓
FollowUpService.check_and_follow_up()
    ↓
Get active sprint issues
    ↓
For each issue:
    ├─→ Skip if status in excluded_statuses
    ├─→ Skip if already followed up in last 24h
    ├─→ Check inactivity:
    │   ├─→ Updated date > threshold?
    │   ├─→ Recent comments?
    │   └─→ Recent status changes?
    └─→ If inactive:
        ├─→ Add Jira comment (if configured)
        ├─→ Send email (if configured)
        └─→ Record in FollowUp table
```

### Chatbot Interaction

```
User types message
    ↓
POST /api/chat
    ↓
Chatbot.chat()
    ↓
├─→ Get conversation history
├─→ Get current Jira context
│   ├─→ My assigned tickets count
│   ├─→ Status breakdown
│   └─→ Sprint statistics
├─→ Build messages array
│   ├─→ System prompt
│   ├─→ Context injection
│   ├─→ Conversation history
│   └─→ Current message
├─→ Call Azure OpenAI API
├─→ Get response
└─→ Update conversation history
    ↓
Return response to frontend
```

## 🔐 Security Considerations

### Credentials Management
- Sensitive data in `credentials.properties` (git-ignored)
- No hardcoded credentials in code
- Environment variable support
- File permission restrictions recommended (chmod 600)

### API Security
- Jira uses Basic Auth (email + API token)
- Azure OpenAI uses API key authentication
- SMTP uses TLS/SSL encryption
- No public API endpoints (localhost only by default)

### Rate Limiting
- Respects Jira API rate limits
- Token bucket algorithm
- Automatic backoff and retry

### Data Storage
- SQLite database for caching only
- No passwords stored in database
- Local file storage (not shared)

## 🚀 Deployment Options

### 1. Local Development
```bash
./setup.sh
./run.sh
```

### 2. Docker Container
```bash
docker-compose up -d
```

### 3. Systemd Service (Linux)
```bash
sudo cp systemd-service.example /etc/systemd/system/scrum-agent.service
sudo systemctl enable scrum-agent
sudo systemctl start scrum-agent
```

### 4. Cloud Deployment
- Deploy to AWS EC2, Azure VM, or Google Cloud
- Use Docker for containerization
- Set up reverse proxy (nginx) for HTTPS
- Configure firewall rules

## 📊 Performance Characteristics

### API Call Efficiency
- **Rate Limiting**: Max 60 calls/minute, 3000 calls/hour
- **Caching**: Dashboard cached for 60 minutes
- **Batch Operations**: Fetch multiple issues in single requests

### Memory Usage
- **Lightweight**: ~100-200 MB typical usage
- **SQLite**: Minimal overhead
- **Conversation History**: Limited to 20 messages per session

### Scalability
- Single-user design (not multi-tenant)
- Can handle 1000+ Jira issues efficiently
- Background jobs don't block web UI
- SQLite sufficient for single-user workload

## 🔧 Extension Points

### Adding New Services
1. Create service in `src/services/`
2. Implement business logic
3. Add route in `web/app.py`
4. Update frontend to consume API

### Custom Reports
1. Add methods to `DailyReportService`
2. Update report templates
3. Configure in `config.yaml`

### New Integrations
1. Create client (e.g., `slack_client.py`)
2. Add credentials to `credentials.properties`
3. Implement delivery method in services
4. Configure in `config.yaml`

## 🐛 Debugging

### Enable Debug Logging
Edit `config/config.yaml`:
```yaml
logging:
  level: "DEBUG"
```

### Check Logs
```bash
tail -f scrum_agent.log
```

### API Testing
Use FastAPI's built-in docs:
```
http://localhost:8000/docs
```

### Database Inspection
```bash
sqlite3 scrum_agent.db
.tables
SELECT * FROM daily_reports;
```

---

For questions or contributions, see [README.md](README.md)

