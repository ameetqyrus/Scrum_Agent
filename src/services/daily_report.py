"""Daily report generation service."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
from pathlib import Path

from ..config import config
from ..jira_client import jira_client
from ..email_service import email_service
from ..database import db, DailyReport

logger = logging.getLogger(__name__)


class DailyReportService:
    """Service for generating daily reports."""
    
    def __init__(self):
        self.config = config.get('daily_report', {})
        self.include = self.config.get('include', [])
    
    def generate_report(self) -> Dict[str, str]:
        """Generate daily report with all requested sections."""
        logger.info("Generating daily report...")
        
        report_data = {}
        
        # Fetch data based on configuration
        if 'completed_tickets' in self.include:
            report_data['completed'] = self._get_completed_tickets()
        
        if 'new_tickets' in self.include:
            report_data['new'] = self._get_new_tickets()
        
        if 'in_progress_tickets' in self.include:
            report_data['in_progress'] = self._get_in_progress_tickets()
        
        if 'comments_summary' in self.include:
            report_data['comments'] = self._get_comments_summary()
        
        if 'time_logged' in self.include:
            report_data['time_logged'] = self._get_time_logged()
        
        if 'blockers' in self.include:
            report_data['blockers'] = self._get_blockers()
        
        # Generate HTML and text versions
        html_report = self._generate_html_report(report_data)
        text_report = self._generate_text_report(report_data)
        
        return {
            'html': html_report,
            'text': text_report,
            'data': report_data
        }
    
    def _get_completed_tickets(self) -> List[Dict[str, Any]]:
        """Get tickets completed today."""
        try:
            jql = "status changed to (Done, Resolved, Closed) during (startOfDay(), now()) ORDER BY updated DESC"
            issues = jira_client.search_issues(jql, max_results=50)
            
            result = []
            for issue in issues:
                fields = issue.get('fields', {})
                result.append({
                    'key': issue.get('key', ''),
                    'summary': fields.get('summary', ''),
                    'assignee': fields.get('assignee', {}).get('displayName', 'Unassigned') if fields.get('assignee') else 'Unassigned',
                    'type': fields.get('issuetype', {}).get('name', 'Unknown'),
                    'url': f"{config.jira_url}browse/{issue.get('key', '')}"
                })
            return result
        except Exception as e:
            logger.error(f"Error fetching completed tickets: {e}")
            return []
    
    def _get_new_tickets(self) -> List[Dict[str, Any]]:
        """Get tickets created today."""
        try:
            issues = jira_client.get_issues_created_today()
            
            result = []
            for issue in issues:
                fields = issue.get('fields', {})
                result.append({
                    'key': issue.get('key', ''),
                    'summary': fields.get('summary', ''),
                    'assignee': fields.get('assignee', {}).get('displayName', 'Unassigned') if fields.get('assignee') else 'Unassigned',
                    'type': fields.get('issuetype', {}).get('name', 'Unknown'),
                    'priority': fields.get('priority', {}).get('name', 'None') if fields.get('priority') else 'None',
                    'url': f"{config.jira_url}browse/{issue.get('key', '')}"
                })
            return result
        except Exception as e:
            logger.error(f"Error fetching new tickets: {e}")
            return []
    
    def _get_in_progress_tickets(self) -> List[Dict[str, Any]]:
        """Get tickets currently in progress."""
        try:
            jql = "status = 'In Progress' AND updated >= startOfDay() ORDER BY updated DESC"
            issues = jira_client.search_issues(jql, max_results=50)
            
            result = []
            for issue in issues:
                fields = issue.get('fields', {})
                result.append({
                    'key': issue.get('key', ''),
                    'summary': fields.get('summary', ''),
                    'assignee': fields.get('assignee', {}).get('displayName', 'Unassigned') if fields.get('assignee') else 'Unassigned',
                    'url': f"{config.jira_url}browse/{issue.get('key', '')}"
                })
            return result
        except Exception as e:
            logger.error(f"Error fetching in-progress tickets: {e}")
            return []
    
    def _get_comments_summary(self) -> List[Dict[str, Any]]:
        """Get summary of comments added today."""
        try:
            issues = jira_client.get_issues_updated_today()
            comments_summary = []
            
            for issue in issues:
                try:
                    issue_key = issue.get('key')
                    if not issue_key:
                        continue
                        
                    comments = jira_client.get_comments(issue_key)
                    today_comments = [
                        c for c in comments
                        if c['created'].date() == datetime.now().date()
                    ]
                    
                    if today_comments:
                        fields = issue.get('fields', {})
                        comments_summary.append({
                            'key': issue_key,
                            'summary': fields.get('summary', ''),
                            'comment_count': len(today_comments),
                            'comments': [
                                {
                                    'author': c['author'],
                                    'body': c['body'][:200] + '...' if len(c['body']) > 200 else c['body']
                                }
                                for c in today_comments[:3]  # Limit to 3 most recent
                            ],
                            'url': f"{config.jira_url}browse/{issue_key}"
                        })
                except Exception as e:
                    logger.warning(f"Could not fetch comments for {issue.get('key', 'unknown')}: {e}")
            
            return comments_summary
        except Exception as e:
            logger.error(f"Error fetching comments summary: {e}")
            return []
    
    def _get_time_logged(self) -> Dict[str, Any]:
        """Get time logged today."""
        try:
            issues = jira_client.get_issues_updated_today()
            total_seconds = 0
            by_user = {}
            
            for issue in issues:
                try:
                    issue_key = issue.get('key')
                    if not issue_key:
                        continue
                        
                    worklogs = jira_client.get_issue_worklog(issue_key)
                    today_logs = [
                        wl for wl in worklogs
                        if wl['started'].date() == datetime.now().date()
                    ]
                    
                    for log in today_logs:
                        total_seconds += log['time_spent_seconds']
                        author = log['author']
                        by_user[author] = by_user.get(author, 0) + log['time_spent_seconds']
                except Exception as e:
                    logger.warning(f"Could not fetch worklog for {issue.get('key', 'unknown')}: {e}")
            
            return {
                'total_hours': total_seconds / 3600,
                'by_user': {
                    user: seconds / 3600
                    for user, seconds in sorted(by_user.items(), key=lambda x: x[1], reverse=True)
                }
            }
        except Exception as e:
            logger.error(f"Error fetching time logged: {e}")
            return {'total_hours': 0, 'by_user': {}}
    
    def _get_blockers(self) -> List[Dict[str, Any]]:
        """Get tickets marked as blocked or with blockers."""
        try:
            jql = "status != Done AND (labels = blocked OR labels = blocker) ORDER BY priority DESC"
            issues = jira_client.search_issues(jql, max_results=50)
            
            result = []
            for issue in issues:
                fields = issue.get('fields', {})
                result.append({
                    'key': issue.get('key', ''),
                    'summary': fields.get('summary', ''),
                    'assignee': fields.get('assignee', {}).get('displayName', 'Unassigned') if fields.get('assignee') else 'Unassigned',
                    'priority': fields.get('priority', {}).get('name', 'None') if fields.get('priority') else 'None',
                    'url': f"{config.jira_url}browse/{issue.get('key', '')}"
                })
            return result
        except Exception as e:
            logger.error(f"Error fetching blockers: {e}")
            return []
    
    def _generate_html_report(self, report_data: Dict[str, Any]) -> str:
        """Generate HTML version of the report."""
        today = datetime.now().strftime('%B %d, %Y')
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}
        h1 {{
            color: #0052CC;
            border-bottom: 3px solid #0052CC;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #0052CC;
            margin-top: 30px;
        }}
        .summary-box {{
            background-color: #f4f5f7;
            padding: 15px;
            border-radius: 5px;
            margin: 15px 0;
        }}
        .ticket {{
            background-color: #fff;
            border-left: 4px solid #0052CC;
            padding: 10px;
            margin: 10px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .ticket-key {{
            color: #0052CC;
            font-weight: bold;
            text-decoration: none;
        }}
        .ticket-key:hover {{
            text-decoration: underline;
        }}
        .comment {{
            background-color: #f9f9f9;
            border-left: 3px solid #ddd;
            padding: 8px;
            margin: 5px 0;
            font-size: 0.9em;
        }}
        .author {{
            font-weight: bold;
            color: #555;
        }}
        .stats {{
            display: flex;
            justify-content: space-around;
            margin: 20px 0;
        }}
        .stat-box {{
            text-align: center;
            padding: 15px;
            background-color: #e3fcef;
            border-radius: 5px;
            flex: 1;
            margin: 0 10px;
        }}
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #00875A;
        }}
        .stat-label {{
            color: #666;
            font-size: 0.9em;
        }}
        .blocker {{
            border-left-color: #DE350B;
        }}
    </style>
</head>
<body>
    <h1>📊 Daily Scrum Report - {today}</h1>
"""
        
        # Stats summary
        completed_count = len(report_data.get('completed', []))
        new_count = len(report_data.get('new', []))
        in_progress_count = len(report_data.get('in_progress', []))
        
        html += f"""
    <div class="stats">
        <div class="stat-box">
            <div class="stat-number">{completed_count}</div>
            <div class="stat-label">Completed</div>
        </div>
        <div class="stat-box">
            <div class="stat-number">{new_count}</div>
            <div class="stat-label">New Tickets</div>
        </div>
        <div class="stat-box">
            <div class="stat-number">{in_progress_count}</div>
            <div class="stat-label">In Progress</div>
        </div>
    </div>
"""
        
        # Completed tickets
        if 'completed' in report_data and report_data['completed']:
            html += "<h2>✅ Completed Today</h2>"
            for ticket in report_data['completed']:
                html += f"""
    <div class="ticket">
        <a href="{ticket['url']}" class="ticket-key">{ticket['key']}</a> - {ticket['summary']}<br>
        <small>Assignee: {ticket['assignee']} | Type: {ticket['type']}</small>
    </div>
"""
        
        # New tickets
        if 'new' in report_data and report_data['new']:
            html += "<h2>🆕 New Tickets</h2>"
            for ticket in report_data['new']:
                html += f"""
    <div class="ticket">
        <a href="{ticket['url']}" class="ticket-key">{ticket['key']}</a> - {ticket['summary']}<br>
        <small>Assignee: {ticket['assignee']} | Type: {ticket['type']} | Priority: {ticket['priority']}</small>
    </div>
"""
        
        # In progress tickets
        if 'in_progress' in report_data and report_data['in_progress']:
            html += "<h2>🔄 In Progress</h2>"
            for ticket in report_data['in_progress']:
                html += f"""
    <div class="ticket">
        <a href="{ticket['url']}" class="ticket-key">{ticket['key']}</a> - {ticket['summary']}<br>
        <small>Assignee: {ticket['assignee']}</small>
    </div>
"""
        
        # Comments summary
        if 'comments' in report_data and report_data['comments']:
            html += "<h2>💬 Comments Added</h2>"
            for item in report_data['comments']:
                html += f"""
    <div class="ticket">
        <a href="{item['url']}" class="ticket-key">{item['key']}</a> - {item['summary']}<br>
        <small>{item['comment_count']} comment(s) today</small>
"""
                for comment in item['comments']:
                    html += f"""
        <div class="comment">
            <span class="author">{comment['author']}:</span> {comment['body']}
        </div>
"""
                html += "    </div>\n"
        
        # Time logged
        if 'time_logged' in report_data:
            time_data = report_data['time_logged']
            html += f"<h2>⏱️ Time Logged: {time_data['total_hours']:.1f} hours</h2>"
            if time_data['by_user']:
                html += "<div class='summary-box'>"
                for user, hours in time_data['by_user'].items():
                    html += f"<strong>{user}:</strong> {hours:.1f}h<br>"
                html += "</div>"
        
        # Blockers
        if 'blockers' in report_data and report_data['blockers']:
            html += "<h2>🚫 Blockers</h2>"
            for ticket in report_data['blockers']:
                html += f"""
    <div class="ticket blocker">
        <a href="{ticket['url']}" class="ticket-key">{ticket['key']}</a> - {ticket['summary']}<br>
        <small>Assignee: {ticket['assignee']} | Priority: {ticket['priority']}</small>
    </div>
"""
        
        html += """
</body>
</html>
"""
        return html
    
    def _generate_text_report(self, report_data: Dict[str, Any]) -> str:
        """Generate plain text version of the report."""
        today = datetime.now().strftime('%B %d, %Y')
        
        text = f"📊 DAILY SCRUM REPORT - {today}\n"
        text += "=" * 60 + "\n\n"
        
        # Completed tickets
        if 'completed' in report_data and report_data['completed']:
            text += f"✅ COMPLETED TODAY ({len(report_data['completed'])})\n"
            text += "-" * 60 + "\n"
            for ticket in report_data['completed']:
                text += f"{ticket['key']} - {ticket['summary']}\n"
                text += f"   Assignee: {ticket['assignee']} | Type: {ticket['type']}\n"
                text += f"   {ticket['url']}\n\n"
        
        # New tickets
        if 'new' in report_data and report_data['new']:
            text += f"\n🆕 NEW TICKETS ({len(report_data['new'])})\n"
            text += "-" * 60 + "\n"
            for ticket in report_data['new']:
                text += f"{ticket['key']} - {ticket['summary']}\n"
                text += f"   Assignee: {ticket['assignee']} | Type: {ticket['type']} | Priority: {ticket['priority']}\n"
                text += f"   {ticket['url']}\n\n"
        
        # In progress
        if 'in_progress' in report_data and report_data['in_progress']:
            text += f"\n🔄 IN PROGRESS ({len(report_data['in_progress'])})\n"
            text += "-" * 60 + "\n"
            for ticket in report_data['in_progress']:
                text += f"{ticket['key']} - {ticket['summary']}\n"
                text += f"   Assignee: {ticket['assignee']}\n"
                text += f"   {ticket['url']}\n\n"
        
        # Time logged
        if 'time_logged' in report_data:
            time_data = report_data['time_logged']
            text += f"\n⏱️ TIME LOGGED: {time_data['total_hours']:.1f} hours\n"
            text += "-" * 60 + "\n"
            for user, hours in time_data['by_user'].items():
                text += f"{user}: {hours:.1f}h\n"
        
        # Blockers
        if 'blockers' in report_data and report_data['blockers']:
            text += f"\n🚫 BLOCKERS ({len(report_data['blockers'])})\n"
            text += "-" * 60 + "\n"
            for ticket in report_data['blockers']:
                text += f"{ticket['key']} - {ticket['summary']}\n"
                text += f"   Assignee: {ticket['assignee']} | Priority: {ticket['priority']}\n"
                text += f"   {ticket['url']}\n\n"
        
        return text
    
    def save_and_send_report(self) -> bool:
        """Generate, save, and send the daily report."""
        try:
            logger.info("Starting daily report generation...")
            
            # Generate report
            report = self.generate_report()
            
            # Save to database
            with db.get_session() as session:
                daily_report = DailyReport(
                    report_date=datetime.now(),
                    report_html=report['html'],
                    report_text=report['text']
                )
                session.add(daily_report)
                session.commit()
            
            # Send via configured methods
            delivery_methods = self.config.get('delivery_methods', [])
            
            if 'email' in delivery_methods:
                success = email_service.send_daily_report(
                    report['html'],
                    report['text'],
                    datetime.now()
                )
                
                if success:
                    with db.get_session() as session:
                        daily_report.sent_email = True
                        daily_report.email_sent_date = datetime.now()
                        session.merge(daily_report)
            
            if 'file' in delivery_methods:
                file_path = self.config.get('file_path', 'reports/daily_report_{date}.html')
                file_path = file_path.replace('{date}', datetime.now().strftime('%Y-%m-%d'))
                
                # Create reports directory if it doesn't exist
                Path(file_path).parent.mkdir(parents=True, exist_ok=True)
                
                with open(file_path, 'w') as f:
                    f.write(report['html'])
                logger.info(f"Report saved to {file_path}")
            
            logger.info("Daily report completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error generating daily report: {e}", exc_info=True)
            return False


# Global service instance
daily_report_service = DailyReportService()

