# 🚀 Quick Start Guide

Get your Scrum Master Agent up and running in 5 minutes!

## Step 1: Setup (2 minutes)

Run the automated setup script:

```bash
cd /Users/ameetdeshpande/Documents/codeProjects/2025/Agents/scrum_agent
./setup.sh
```

This will:
- Create a Python virtual environment
- Install all dependencies
- Create a credentials template file

## Step 2: Configure Credentials (2 minutes)

Edit `config/credentials.properties` with your actual credentials:

```bash
nano config/credentials.properties
# or use your preferred editor
```

### Required Credentials:

#### 1. Jira
- **jira.url**: Your Jira instance URL (e.g., `https://cogcloud.atlassian.net/`)
- **jira.email**: Your Jira account email
- **jira.api_token**: [Get from here](https://id.atlassian.com/manage-profile/security/api-tokens)

#### 2. User Info
- **user.email**: Your email for receiving reports
- **user.jira_account_id**: Your Jira account ID (found in your Jira profile URL)

#### 3. Azure OpenAI (for chatbot)
- **azure.openai.endpoint**: Your Azure OpenAI endpoint URL
- **azure.openai.api_key**: Your Azure OpenAI API key
- **azure.openai.deployment_name**: Your deployment name (e.g., `gpt-4`)

#### 4. Email (for sending reports)
- **email.smtp_host**: SMTP server (e.g., `smtp.gmail.com`)
- **email.smtp_port**: Usually `587` for TLS
- **email.from_address**: Sender email address
- **email.password**: Email password or app password

### 💡 Tips:

- **Gmail users**: Use an [App Password](https://support.google.com/accounts/answer/185833)
- **Jira Account ID**: Go to your profile → URL shows `/jira/people/ACCOUNT_ID`

## Step 3: Test Connection (30 seconds)

Verify everything is working:

```bash
./test.sh
```

You should see:
```
✅ Successfully connected to Jira
   User: Your Name
   Email: your.email@example.com
   Account ID: 5a1234567890abcdef
✅ Found X issues assigned to or mentioning you
```

## Step 4: Run the Application (30 seconds)

Start the web application:

```bash
./run.sh
```

Or manually:

```bash
source venv/bin/activate
python -m src.main web
```

## Step 5: Access the Dashboard

Open your browser and go to:

**http://localhost:8000**

You'll see:
- 📈 **Dashboard**: All your tickets and sprint stats
- 💬 **Chatbot**: Ask questions about your work
- 🔘 **Action Buttons**: Generate reports and check follow-ups manually

## 🎉 You're Done!

The agent is now running and will:
- ✅ Generate daily reports at 9 PM
- ✅ Check for follow-ups at 10 AM
- ✅ Refresh dashboard data every hour
- ✅ Provide chatbot assistance anytime

## Common Commands

### Web Application
```bash
./run.sh                    # Start web server
```

### Manual Operations
```bash
source venv/bin/activate

python -m src.main report   # Generate report now
python -m src.main follow-up # Check follow-ups now
python -m src.main test     # Test Jira connection
```

### Custom Port
```bash
python -m src.main web --port 8080
```

## Customization

Edit `config/config.yaml` to customize:
- Report schedule and content
- Dashboard refresh frequency
- Follow-up timing and messages
- Chatbot behavior

## Troubleshooting

### "Failed to connect to Jira"
- Check credentials in `config/credentials.properties`
- Verify API token is valid
- Ensure Jira URL ends with `/`

### "Email not sending"
- Use app password for Gmail (not regular password)
- Check SMTP settings and port
- Look in spam folder

### "Chatbot not responding"
- Verify Azure OpenAI credentials
- Check deployment name matches Azure config
- Ensure API quota is available

## Need More Help?

See the full [README.md](README.md) for:
- Detailed configuration options
- Advanced usage scenarios
- Running as a background service
- Security best practices

---

**Happy Scrum-ing! 🎯**

