"""Jira API client with rate limiting using direct REST API calls."""

import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import requests
from requests.auth import HTTPBasicAuth
from collections import deque

from .config import config

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter for Jira API calls."""
    
    def __init__(self, calls_per_minute: int, calls_per_hour: int):
        self.calls_per_minute = calls_per_minute
        self.calls_per_hour = calls_per_hour
        self.minute_calls = deque()
        self.hour_calls = deque()
    
    def _clean_old_calls(self):
        """Remove calls older than the time windows."""
        now = time.time()
        
        # Clean minute window
        while self.minute_calls and now - self.minute_calls[0] > 60:
            self.minute_calls.popleft()
        
        # Clean hour window
        while self.hour_calls and now - self.hour_calls[0] > 3600:
            self.hour_calls.popleft()
    
    def wait_if_needed(self):
        """Wait if rate limit would be exceeded."""
        self._clean_old_calls()
        now = time.time()
        
        # Check minute limit
        if len(self.minute_calls) >= self.calls_per_minute:
            sleep_time = 60 - (now - self.minute_calls[0]) + 0.1
            if sleep_time > 0:
                logger.info(f"Rate limit: sleeping {sleep_time:.2f}s (minute limit)")
                time.sleep(sleep_time)
                self._clean_old_calls()
        
        # Check hour limit
        if len(self.hour_calls) >= self.calls_per_hour:
            sleep_time = 3600 - (now - self.hour_calls[0]) + 0.1
            if sleep_time > 0:
                logger.info(f"Rate limit: sleeping {sleep_time:.2f}s (hour limit)")
                time.sleep(sleep_time)
                self._clean_old_calls()
        
        # Record this call
        now = time.time()
        self.minute_calls.append(now)
        self.hour_calls.append(now)


class JiraClient:
    """Direct REST API wrapper for Jira Cloud with rate limiting."""
    
    def __init__(self):
        self.base_url = config.jira_url.rstrip('/')
        self.auth = HTTPBasicAuth(config.jira_email, config.jira_api_token)
        self.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        rate_limit_config = config.get('jira.rate_limit', {})
        self.rate_limiter = RateLimiter(
            calls_per_minute=rate_limit_config.get('calls_per_minute', 60),
            calls_per_hour=rate_limit_config.get('calls_per_hour', 3000)
        )
        
        self.user_account_id = config.user_jira_account_id
        self.batch_size = config.get('jira.batch_size', 50)
    
    def _api_call(self, method: str, endpoint: str, **kwargs):
        """Execute API call with rate limiting and error handling."""
        self.rate_limiter.wait_if_needed()
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.request(
                method,
                url,
                auth=self.auth,
                headers=self.headers,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"Jira API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Jira API error: {e}")
            raise
    
    def search_issues(self, jql: str, max_results: int = 100, expand: str = None) -> List[Dict[str, Any]]:
        """Search for issues using JQL."""
        params = {
            'jql': jql,
            'maxResults': max_results,
            'fields': '*all'
        }
        
        if expand:
            params['expand'] = expand
        
        result = self._api_call('GET', '/rest/api/3/search/jql', params=params)
        return result.get('issues', [])
    
    def get_my_issues(self, include_done: bool = False) -> List[Dict[str, Any]]:
        """Get issues assigned to or mentioning the user."""
        jql_parts = [
            f"(assignee = currentUser() OR comment ~ currentUser() OR watcher = currentUser())"
        ]
        
        if not include_done:
            jql_parts.append("status NOT IN (Done, Closed, Resolved)")
        
        jql = " AND ".join(jql_parts)
        jql += " ORDER BY updated DESC"
        
        logger.info(f"Fetching my issues with JQL: {jql}")
        return self.search_issues(jql, max_results=config.get('jira.max_results', 100), expand='changelog,renderedFields')
    
    def get_active_sprint_issues(self) -> List[Dict[str, Any]]:
        """Get all issues in active sprints."""
        jql = "sprint in openSprints() ORDER BY updated DESC"
        
        logger.info(f"Fetching active sprint issues")
        return self.search_issues(jql, max_results=config.get('jira.max_results', 100), expand='changelog')
    
    def get_issues_updated_today(self) -> List[Dict[str, Any]]:
        """Get issues updated today."""
        jql = "updated >= startOfDay() ORDER BY updated DESC"
        
        logger.info(f"Fetching issues updated today")
        return self.search_issues(jql, max_results=config.get('jira.max_results', 100))
    
    def get_issues_created_today(self) -> List[Dict[str, Any]]:
        """Get issues created today."""
        jql = "created >= startOfDay() ORDER BY created DESC"
        
        logger.info(f"Fetching issues created today")
        return self.search_issues(jql, max_results=config.get('jira.max_results', 100))
    
    def get_issue(self, issue_key: str) -> Dict[str, Any]:
        """Get a specific issue by key."""
        logger.info(f"Fetching issue: {issue_key}")
        return self._api_call('GET', f'/rest/api/3/issue/{issue_key}', params={'expand': 'changelog,renderedFields'})
    
    def get_comments(self, issue_key: str) -> List[Dict[str, Any]]:
        """Get all comments for an issue."""
        logger.info(f"Fetching comments for: {issue_key}")
        comments_data = self._api_call('GET', f'/rest/api/3/issue/{issue_key}/comment')
        
        comments = []
        for comment in comments_data.get('comments', []):
            try:
                created = datetime.fromisoformat(comment['created'].replace('Z', '+00:00'))
                updated = datetime.fromisoformat(comment.get('updated', comment['created']).replace('Z', '+00:00')) if comment.get('updated') else created
                
                comments.append({
                    'id': comment['id'],
                    'author': comment.get('author', {}).get('displayName', 'Unknown'),
                    'body': comment.get('body', ''),
                    'created': created,
                    'updated': updated
                })
            except Exception as e:
                logger.warning(f"Error parsing comment: {e}")
                continue
        
        return comments
    
    def add_comment(self, issue_key: str, comment: str) -> Dict[str, Any]:
        """Add a comment to an issue."""
        logger.info(f"Adding comment to: {issue_key}")
        data = {
            'body': comment
        }
        result = self._api_call('POST', f'/rest/api/3/issue/{issue_key}/comment', json=data)
        
        return {
            'id': result.get('id'),
            'created': result.get('created')
        }
    
    def get_issue_worklog(self, issue_key: str) -> List[Dict[str, Any]]:
        """Get worklog entries for an issue."""
        logger.info(f"Fetching worklog for: {issue_key}")
        try:
            worklogs_data = self._api_call('GET', f'/rest/api/3/issue/{issue_key}/worklog')
            
            worklogs = []
            for wl in worklogs_data.get('worklogs', []):
                try:
                    started = datetime.fromisoformat(wl['started'].replace('Z', '+00:00'))
                    
                    worklogs.append({
                        'author': wl.get('author', {}).get('displayName', 'Unknown'),
                        'time_spent': wl.get('timeSpent', ''),
                        'time_spent_seconds': wl.get('timeSpentSeconds', 0),
                        'started': started,
                        'comment': wl.get('comment', '')
                    })
                except Exception as e:
                    logger.warning(f"Error parsing worklog: {e}")
                    continue
            
            return worklogs
        except Exception as e:
            logger.warning(f"Could not fetch worklog for {issue_key}: {e}")
            return []
    
    def issue_has_recent_activity(self, issue: Dict[str, Any], hours: int = 24) -> bool:
        """Check if an issue has had activity in the last N hours."""
        threshold = datetime.now().astimezone() - timedelta(hours=hours)
        
        # Check updated date
        try:
            updated_str = issue.get('fields', {}).get('updated', '')
            updated = datetime.fromisoformat(updated_str.replace('Z', '+00:00'))
            if updated > threshold:
                return True
        except Exception:
            pass
        
        # Check comments
        try:
            issue_key = issue.get('key')
            if issue_key:
                comments = self.get_comments(issue_key)
                if comments:
                    latest_comment = max(comments, key=lambda c: c['created'])
                    if latest_comment['created'] > threshold:
                        return True
        except Exception:
            pass
        
        return False
    
    def get_user_info(self) -> Dict[str, Any]:
        """Get current user information."""
        logger.info("Fetching current user info")
        user = self._api_call('GET', '/rest/api/3/myself')
        
        return {
            'account_id': user['accountId'],
            'display_name': user['displayName'],
            'email': user['emailAddress'],
            'timezone': user.get('timeZone', 'UTC')
        }


# Global Jira client instance
jira_client = JiraClient()
