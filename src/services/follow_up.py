"""Follow-up service for inactive tickets."""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

from ..config import config
from ..jira_client import jira_client
from ..email_service import email_service
from ..database import db, FollowUp

logger = logging.getLogger(__name__)


class FollowUpService:
    """Service for following up on inactive tickets."""
    
    def __init__(self):
        self.config = config.get('follow_up', {})
        self.inactive_threshold = timedelta(
            hours=self.config.get('inactive_threshold_hours', 24)
        )
        self.exclude_statuses = self.config.get('exclude_statuses', ['Done', 'Closed', 'Resolved'])
        self.delivery_methods = self.config.get('delivery_methods', [])
        self.comment_template = self.config.get('comment_template', 'This ticket needs an update.')
    
    def check_and_follow_up(self) -> Dict[str, Any]:
        """Check for inactive tickets and send follow-ups."""
        logger.info("Starting follow-up check...")
        
        try:
            # Get active sprint issues
            sprint_issues = jira_client.get_active_sprint_issues()
            
            inactive_issues = []
            followed_up = []
            errors = []
            
            for issue in sprint_issues:
                fields = issue.get('fields', {})
                issue_key = issue.get('key', '')
                status_name = fields.get('status', {}).get('name', '')
                
                # Skip excluded statuses
                if status_name in self.exclude_statuses:
                    continue
                
                # Check if already followed up recently
                if self._already_followed_up_recently(issue_key):
                    continue
                
                # Check for inactivity
                if self._is_inactive(issue):
                    inactive_issues.append(issue)
                    logger.info(f"Following up on inactive issue: {issue_key}")
                    
                    # Send follow-ups
                    success = self._send_follow_up(issue)
                    
                    if success:
                        assignee = fields.get('assignee', {})
                        followed_up.append({
                            'key': issue_key,
                            'summary': fields.get('summary', ''),
                            'assignee': assignee.get('displayName', 'Unassigned') if assignee else 'Unassigned',
                        })
                    else:
                        errors.append(issue_key)
            
            logger.info(f"Follow-up complete. Sent {len(followed_up)} follow-ups, {len(errors)} errors")
            
            return {
                'total_checked': len(sprint_issues),
                'inactive_found': len(inactive_issues),
                'followed_up': followed_up,
                'errors': errors,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in follow-up check: {e}", exc_info=True)
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _is_inactive(self, issue) -> bool:
        """Check if an issue is inactive."""
        threshold = datetime.now().astimezone() - self.inactive_threshold
        
        fields = issue.get('fields', {})
        issue_key = issue.get('key', '')
        
        # Check updated date
        try:
            updated_str = fields.get('updated', '')
            updated = datetime.fromisoformat(updated_str.replace('Z', '+00:00'))
            if updated > threshold:
                return False
        except Exception as e:
            logger.warning(f"Could not parse updated date for {issue_key}: {e}")
        
        # Check recent comments
        try:
            comments = jira_client.get_comments(issue_key)
            if comments:
                latest_comment = max(comments, key=lambda c: c['created'])
                if latest_comment['created'] > threshold:
                    return False
        except Exception as e:
            logger.warning(f"Could not check comments for {issue_key}: {e}")
        
        # Check status changes from changelog
        try:
            changelog = issue.get('changelog', {})
            histories = changelog.get('histories', [])
            for history in histories:
                history_date_str = history.get('created', '')
                history_date = datetime.fromisoformat(history_date_str.replace('Z', '+00:00'))
                if history_date > threshold:
                    items = history.get('items', [])
                    for item in items:
                        if item.get('field') == 'status':
                            return False
        except Exception as e:
            logger.warning(f"Could not check status changes for {issue_key}: {e}")
        
        return True
    
    def _already_followed_up_recently(self, issue_key: str, days: int = 1) -> bool:
        """Check if we already followed up on this issue recently."""
        try:
            threshold = datetime.now() - timedelta(days=days)
            
            with db.get_session() as session:
                recent_followup = session.query(FollowUp).filter(
                    FollowUp.issue_key == issue_key,
                    FollowUp.follow_up_date >= threshold
                ).first()
                
                return recent_followup is not None
                
        except Exception as e:
            logger.error(f"Error checking follow-up history: {e}")
            return False
    
    def _send_follow_up(self, issue) -> bool:
        """Send follow-up via configured methods."""
        success = True
        reason = f"No activity detected in the last {self.inactive_threshold.total_seconds() / 3600:.0f} hours"
        
        fields = issue.get('fields', {})
        issue_key = issue.get('key', '')
        issue_summary = fields.get('summary', '')
        
        # Send Jira comment
        if 'jira_comment' in self.delivery_methods:
            try:
                comment_result = jira_client.add_comment(
                    issue_key,
                    self.comment_template
                )
                
                # Record in database
                with db.get_session() as session:
                    follow_up = FollowUp(
                        issue_key=issue_key,
                        follow_up_date=datetime.now(),
                        reason=reason,
                        sent_via='jira_comment',
                        comment_id=str(comment_result.get('id', ''))
                    )
                    session.add(follow_up)
                    session.commit()
                
                logger.info(f"Added follow-up comment to {issue_key}")
                
            except Exception as e:
                logger.error(f"Failed to add Jira comment to {issue_key}: {e}")
                success = False
        
        # Send email
        if 'email' in self.delivery_methods:
            try:
                assignee = fields.get('assignee')
                if assignee and assignee.get('emailAddress'):
                    email_sent = email_service.send_follow_up_notification(
                        issue_key,
                        issue_summary,
                        assignee.get('emailAddress'),
                        reason
                    )
                    
                    if email_sent:
                        # Record in database
                        with db.get_session() as session:
                            follow_up = FollowUp(
                                issue_key=issue_key,
                                follow_up_date=datetime.now(),
                                reason=reason,
                                sent_via='email'
                            )
                            session.add(follow_up)
                            session.commit()
                        
                        logger.info(f"Sent follow-up email for {issue_key}")
                    else:
                        success = False
                else:
                    logger.warning(f"No email address for assignee of {issue_key}")
                    
            except Exception as e:
                logger.error(f"Failed to send follow-up email for {issue_key}: {e}")
                success = False
        
        return success
    
    def get_follow_up_history(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get follow-up history for the last N days."""
        try:
            threshold = datetime.now() - timedelta(days=days)
            
            with db.get_session() as session:
                follow_ups = session.query(FollowUp).filter(
                    FollowUp.follow_up_date >= threshold
                ).order_by(FollowUp.follow_up_date.desc()).all()
                
                return [
                    {
                        'issue_key': fu.issue_key,
                        'follow_up_date': fu.follow_up_date.isoformat(),
                        'reason': fu.reason,
                        'sent_via': fu.sent_via,
                    }
                    for fu in follow_ups
                ]
                
        except Exception as e:
            logger.error(f"Error getting follow-up history: {e}")
            return []


# Global service instance
follow_up_service = FollowUpService()

