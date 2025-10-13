"""Dashboard data service."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
from collections import defaultdict

from ..config import config
from ..jira_client import jira_client
from ..database import db, DashboardCache, JiraIssue
import json

logger = logging.getLogger(__name__)


class DashboardService:
    """Service for generating dashboard data."""
    
    def __init__(self):
        self.cache_duration = timedelta(
            minutes=config.get('dashboard.refresh_interval_minutes', 60)
        )
    
    def get_dashboard_data(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Get dashboard data with caching."""
        cache_key = 'main_dashboard'
        
        # Check cache first
        if not force_refresh:
            cached_data = self._get_cached_data(cache_key)
            if cached_data:
                logger.info("Returning cached dashboard data")
                return cached_data
        
        # Generate fresh data
        logger.info("Generating fresh dashboard data...")
        data = self._generate_dashboard_data()
        
        # Cache the data
        self._cache_data(cache_key, data)
        
        return data
    
    def _get_cached_data(self, cache_key: str) -> Dict[str, Any]:
        """Get data from cache if not expired."""
        try:
            with db.get_session() as session:
                cache = session.query(DashboardCache).filter_by(cache_key=cache_key).first()
                
                if cache:
                    age = datetime.utcnow() - cache.last_updated
                    if age < self.cache_duration:
                        return cache.data
        except Exception as e:
            logger.error(f"Error reading cache: {e}")
        
        return None
    
    def _cache_data(self, cache_key: str, data: Dict[str, Any]):
        """Cache dashboard data."""
        try:
            with db.get_session() as session:
                cache = session.query(DashboardCache).filter_by(cache_key=cache_key).first()
                
                if cache:
                    cache.data = data
                    cache.last_updated = datetime.utcnow()
                else:
                    cache = DashboardCache(
                        cache_key=cache_key,
                        data=data,
                        last_updated=datetime.utcnow()
                    )
                    session.add(cache)
                
                session.commit()
        except Exception as e:
            logger.error(f"Error caching data: {e}")
    
    def _generate_dashboard_data(self) -> Dict[str, Any]:
        """Generate dashboard data from Jira."""
        try:
            # Get my issues
            my_issues = jira_client.get_my_issues(include_done=False)
            
            # Categorize issues
            assigned_to_me = []
            mentioned_in_comments = []
            watching = []
            
            for issue in my_issues:
                issue_data = self._format_issue(issue)
                
                # Check if assigned
                assignee = issue.get('fields', {}).get('assignee')
                if assignee and assignee.get('accountId') == config.user_jira_account_id:
                    assigned_to_me.append(issue_data)
                
                # Check if mentioned in comments
                try:
                    issue_key = issue.get('key')
                    if issue_key:
                        # Get raw comment data to check for mentions
                        comments_response = jira_client._api_call('GET', f'/rest/api/3/issue/{issue_key}/comment')
                        user_account_id = config.user_jira_account_id
                        user_email = config.user_email
                        
                        for comment in comments_response.get('comments', []):
                            # Check if user is mentioned in the comment
                            comment_body = comment.get('body', {})
                            comment_text = str(comment_body)
                            
                            # Check for account ID in mentions (ADF format)
                            if user_account_id in comment_text:
                                mentioned_in_comments.append(issue_data)
                                break
                            
                            # Fallback: check for email in text
                            if user_email and user_email.lower() in comment_text.lower():
                                mentioned_in_comments.append(issue_data)
                                break
                except Exception:
                    pass
                
                # Check if watching (add to watching list)
                # Note: Jira API doesn't easily expose watchers, so we'll skip this for now
            
            # Get sprint statistics
            sprint_stats = self._get_sprint_stats()
            
            # Get recent activity
            recent_activity = self._get_recent_activity()
            
            # Generate summary stats
            stats = {
                'total_assigned': len(assigned_to_me),
                'total_mentioned': len(mentioned_in_comments),
                'by_status': self._group_by_status(assigned_to_me),
                'by_priority': self._group_by_priority(assigned_to_me),
                'by_type': self._group_by_type(assigned_to_me),
            }
            
            return {
                'assigned_to_me': assigned_to_me,
                'mentioned_in_comments': mentioned_in_comments,
                'watching': watching,
                'stats': stats,
                'sprint_stats': sprint_stats,
                'recent_activity': recent_activity,
                'last_updated': datetime.utcnow().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Error generating dashboard data: {e}", exc_info=True)
            return {
                'error': str(e),
                'assigned_to_me': [],
                'mentioned_in_comments': [],
                'watching': [],
                'stats': {},
                'sprint_stats': {},
                'recent_activity': [],
                'last_updated': datetime.utcnow().isoformat(),
            }
    
    def _format_issue(self, issue) -> Dict[str, Any]:
        """Format a Jira issue for the dashboard."""
        fields = issue.get('fields', {})
        return {
            'key': issue.get('key', ''),
            'summary': fields.get('summary', ''),
            'status': fields.get('status', {}).get('name', 'Unknown'),
            'priority': fields.get('priority', {}).get('name', 'None') if fields.get('priority') else 'None',
            'assignee': fields.get('assignee', {}).get('displayName', 'Unassigned') if fields.get('assignee') else 'Unassigned',
            'type': fields.get('issuetype', {}).get('name', 'Unknown'),
            'created': fields.get('created', ''),
            'updated': fields.get('updated', ''),
            'url': f"{config.jira_url}browse/{issue.get('key', '')}",
        }
    
    def _group_by_status(self, issues: List[Dict]) -> Dict[str, int]:
        """Group issues by status."""
        groups = defaultdict(int)
        for issue in issues:
            groups[issue['status']] += 1
        return dict(groups)
    
    def _group_by_priority(self, issues: List[Dict]) -> Dict[str, int]:
        """Group issues by priority."""
        groups = defaultdict(int)
        for issue in issues:
            groups[issue['priority']] += 1
        return dict(groups)
    
    def _group_by_type(self, issues: List[Dict]) -> Dict[str, int]:
        """Group issues by type."""
        groups = defaultdict(int)
        for issue in issues:
            groups[issue['type']] += 1
        return dict(groups)
    
    def _get_sprint_stats(self) -> Dict[str, Any]:
        """Get statistics for active sprints."""
        try:
            sprint_issues = jira_client.get_active_sprint_issues()
            
            if not sprint_issues:
                return {}
            
            total = len(sprint_issues)
            by_status = defaultdict(int)
            story_points_total = 0
            story_points_done = 0
            
            for issue in sprint_issues:
                fields = issue.get('fields', {})
                status = fields.get('status', {}).get('name', 'Unknown')
                by_status[status] += 1
                
                # Try to get story points (common custom field)
                points = fields.get('customfield_10016')  # Common story points field
                if points:
                    story_points_total += points
                    if status in ['Done', 'Closed', 'Resolved']:
                        story_points_done += points
            
            return {
                'total_issues': total,
                'by_status': dict(by_status),
                'story_points_total': story_points_total,
                'story_points_completed': story_points_done,
                'completion_percentage': (story_points_done / story_points_total * 100) if story_points_total > 0 else 0,
            }
            
        except Exception as e:
            logger.error(f"Error getting sprint stats: {e}")
            return {}
    
    def _get_recent_activity(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent activity on my issues."""
        try:
            issues = jira_client.get_issues_updated_today()
            
            activities = []
            for issue in issues[:limit]:
                fields = issue.get('fields', {})
                activities.append({
                    'key': issue.get('key', ''),
                    'summary': fields.get('summary', ''),
                    'updated': fields.get('updated', ''),
                    'status': fields.get('status', {}).get('name', 'Unknown'),
                    'url': f"{config.jira_url}browse/{issue.get('key', '')}",
                })
            
            return activities
            
        except Exception as e:
            logger.error(f"Error getting recent activity: {e}")
            return []


# Global service instance
dashboard_service = DashboardService()

