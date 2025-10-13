# 🤖 Scrum Master Agent

An intelligent AI-powered assistant for agile teams that helps manage Jira tickets, generates daily reports, follows up on inactive tasks, and provides scrum guidance through an interactive chatbot.

## ✨ Features

### 1. 📊 Daily Reports
- Automatically generates comprehensive daily reports at 9 PM (configurable)
- Includes completed tickets, new tickets, comments summary, time logged, and blockers
- Sends reports via email (configurable to also save as files)
- Beautiful HTML formatting with charts and statistics

### 2. 📈 Real-time Dashboard
- Web-based dashboard showing all your Jira tickets
- Displays tickets assigned to you and where you're mentioned in comments
- Active sprint statistics with progress tracking
- Auto-refreshes every hour (configurable)
- Clean, modern UI with interactive charts

### 3. ⏰ Automated Follow-ups
- Monitors active sprint tickets for inactivity
- Automatically follows up on tickets with no updates for 24 hours (configurable)
- Sends follow-ups via Jira comments and email (configurable)
- Excludes completed tickets and respects configured statuses

### 4. 💬 AI Chatbot
- Azure OpenAI-powered chatbot for scrum assistance
- Provides real-time context from your Jira workspace
- Answers questions about sprint progress, team velocity, blockers, etc.
- Explains scrum ceremonies and best practices
- Web-based chat interface with conversation history

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Jira Cloud account with API access
- Azure OpenAI account (for chatbot feature)
- SMTP email account (for email features)

### Installation

1. **Clone or navigate to the repository:**
   ```bash
   cd /Users/ameetdeshpande/Documents/codeProjects/2025/Agents/scrum_agent
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure credentials:**
   ```bash
   cp config/credentials.properties.example config/credentials.properties
   ```
   
   Edit `config/credentials.properties` and fill in your credentials:
   - Jira URL, email, and API token
   - Azure OpenAI endpoint and API key
   - Email SMTP settings
   - Your Jira account ID

5. **Configure settings:**
   Edit `config/config.yaml` to customize:
   - Report schedule and content
   - Dashboard refresh interval
   - Follow-up settings
   - Chatbot behavior
   - Scheduler settings

### Getting Your Credentials

#### Jira API Token
1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Give it a name and copy the token

#### Jira Account ID
1. Go to your Jira instance
2. Click on your profile icon → Profile
3. The account ID is in the URL: `https://cogcloud.atlassian.net/jira/people/{ACCOUNT_ID}`

#### Azure OpenAI
1. Go to Azure Portal → Azure OpenAI Service
2. Get your endpoint URL and API key from the "Keys and Endpoint" section
3. Note your deployment name (e.g., "gpt-4")

### Test Your Setup

```bash
python -m src.main test
```

This will verify your Jira connection and credentials.

## 🎯 Usage

### Running the Web Application (Recommended)

Start the web server with scheduler enabled:

```bash
python -m src.main web
```

Then open your browser to: http://localhost:8000

The web interface provides:
- **Dashboard**: View all your tickets and sprint statistics
- **Chatbot**: Interactive AI assistant
- **Manual triggers**: Generate reports and check follow-ups on demand

### Command Line Interface

#### Generate Daily Report
```bash
python -m src.main report
```

#### Check for Follow-ups
```bash
python -m src.main follow-up
```

#### Run with Custom Settings
```bash
python -m src.main web --host 0.0.0.0 --port 8080
```

### Development Mode

Run with auto-reload for development:

```bash
python -m src.main web --reload
```

## ⚙️ Configuration

### Main Configuration (`config/config.yaml`)

#### Application Settings
- `app.port`: Web server port (default: 8000)
- `app.timezone`: Your local timezone for scheduling

#### Daily Report
- `daily_report.time`: When to generate report (24-hour format, e.g., "21:00")
- `daily_report.delivery_methods`: List of delivery methods (`email`, `file`, `console`)
- `daily_report.include`: What to include in the report

#### Dashboard
- `dashboard.refresh_interval_minutes`: How often to refresh (default: 60)
- `dashboard.filters`: Which tickets to show

#### Follow-up
- `follow_up.inactive_threshold_hours`: Hours without update to trigger follow-up (default: 24)
- `follow_up.delivery_methods`: Where to send follow-ups (`jira_comment`, `email`)
- `follow_up.exclude_statuses`: Statuses to skip (e.g., `Done`, `Closed`)

#### Scheduler
- `scheduler.enabled`: Enable/disable daemon mode (default: true)

#### Chatbot
- `chatbot.temperature`: AI creativity level (0.0-1.0)
- `chatbot.max_tokens`: Maximum response length

### Credentials (`config/credentials.properties`)

Store all sensitive information here:
- Jira credentials
- Azure OpenAI credentials
- Email credentials
- User information

**⚠️ Never commit this file to version control!**

## 📋 Features in Detail

### Daily Reports

Reports include:
- ✅ Tickets completed today
- 🆕 New tickets created
- 🔄 Tickets in progress
- 💬 Summary of comments
- ⏱️ Time logged by team members
- 🚫 Current blockers

Reports are beautifully formatted with:
- Statistics cards
- Color-coded priorities
- Direct links to tickets
- Team activity summaries

### Dashboard

The dashboard shows:
- Your assigned tickets
- Tickets where you're mentioned
- Active sprint progress
- Recent activity
- Filterable views by status, priority, and type

### Follow-ups

The system automatically:
- Monitors active sprint tickets
- Detects inactivity (no comments, status changes)
- Sends friendly reminders
- Tracks follow-up history to avoid duplicates
- Respects your configured exclusions

### Chatbot

Ask questions like:
- "What's my sprint progress?"
- "Show me my assigned tickets"
- "What are the blockers?"
- "Explain daily standup best practices"
- "How should we run a retrospective?"

The bot has context about your current work and provides relevant, actionable answers.

## 🔧 Advanced Usage

### Running as a Background Service

#### Using systemd (Linux)

Create `/etc/systemd/system/scrum-agent.service`:

```ini
[Unit]
Description=Scrum Master Agent
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/scrum_agent
Environment="PATH=/path/to/scrum_agent/venv/bin"
ExecStart=/path/to/scrum_agent/venv/bin/python -m src.main web
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable scrum-agent
sudo systemctl start scrum-agent
```

#### Using Docker

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["python", "-m", "src.main", "web", "--host", "0.0.0.0"]
```

Build and run:
```bash
docker build -t scrum-agent .
docker run -p 8000:8000 -v $(pwd)/config:/app/config scrum-agent
```

### Customizing the Chatbot

Edit `config.yaml` to customize the chatbot's personality and focus:

```yaml
chatbot:
  system_prompt: |
    You are a specialized Scrum Master assistant focused on...
    [customize as needed]
```

### Rate Limiting

The Jira client includes intelligent rate limiting to respect API limits:
- Default: 60 calls/minute, 3000 calls/hour
- Configurable in `config.yaml` under `jira.rate_limit`
- Automatically waits when approaching limits

## 📊 Database

The application uses SQLite to store:
- Cached Jira issues
- Comments and worklogs
- Generated reports
- Follow-up history
- Dashboard cache

Database file: `scrum_agent.db` (configurable)

## 🐛 Troubleshooting

### Jira Connection Issues

1. Verify credentials: `python -m src.main test`
2. Check your API token is valid
3. Ensure your account has proper permissions
4. Verify the Jira URL format (should include `/` at the end)

### Email Not Sending

1. Check SMTP credentials in `credentials.properties`
2. For Gmail, use an App Password, not your regular password
3. Verify port (587 for TLS, 465 for SSL)
4. Check spam folder

### Chatbot Errors

1. Verify Azure OpenAI credentials
2. Check deployment name matches your Azure configuration
3. Ensure API quota is not exceeded
4. Check network connectivity to Azure

### Scheduler Not Running

1. Verify `scheduler.enabled: true` in `config.yaml`
2. Check logs for errors: `tail -f scrum_agent.log`
3. Verify timezone is set correctly
4. Ensure the application stays running

## 📝 Logs

Logs are written to:
- Console output (stdout)
- `scrum_agent.log` file

Log level is configurable in `config.yaml`:
```yaml
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

## 🔒 Security

- Never commit `credentials.properties` to version control
- Store credentials securely
- Use environment variables for sensitive data in production
- Restrict file permissions: `chmod 600 config/credentials.properties`
- Use HTTPS in production
- Regularly rotate API tokens

## 🤝 Contributing

This is a personal project, but feel free to:
- Report issues
- Suggest features
- Fork and customize for your needs

## 📜 License

MIT License - feel free to use and modify as needed.

## 🙏 Acknowledgments

- Jira API for providing comprehensive REST API
- Azure OpenAI for powerful AI capabilities
- FastAPI for the excellent web framework
- The Python community for amazing libraries

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Review logs in `scrum_agent.log`
3. Test individual components using CLI commands
4. Verify configuration files

## 🗺️ Roadmap

Potential future enhancements:
- Slack integration
- Microsoft Teams integration
- Sprint velocity tracking
- Burndown charts
- Team analytics
- Customizable report templates
- Multi-user support
- Web UI for configuration

---

Made with ❤️ for agile teams everywhere!


