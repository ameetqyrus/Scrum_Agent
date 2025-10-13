"""Scheduler service for background jobs."""

import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from .config import config
from .services.daily_report import daily_report_service
from .services.follow_up import follow_up_service

logger = logging.getLogger(__name__)


class SchedulerService:
    """Background scheduler for automated tasks."""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.timezone = pytz.timezone(config.get('scheduler.timezone', 'UTC'))
        self.enabled = config.get('scheduler.enabled', True)
    
    def setup_jobs(self):
        """Set up all scheduled jobs."""
        if not self.enabled:
            logger.info("Scheduler is disabled in configuration")
            return
        
        # Daily report job
        if config.get('daily_report.enabled', True):
            report_time = config.get('daily_report.time', '21:00')
            hour, minute = report_time.split(':')
            
            self.scheduler.add_job(
                func=self._run_daily_report,
                trigger=CronTrigger(
                    hour=int(hour),
                    minute=int(minute),
                    timezone=self.timezone
                ),
                id='daily_report',
                name='Daily Scrum Report',
                replace_existing=True
            )
            logger.info(f"Scheduled daily report at {report_time} {self.timezone}")
        
        # Follow-up job
        if config.get('follow_up.enabled', True):
            follow_up_time = config.get('follow_up.check_time', '10:00')
            hour, minute = follow_up_time.split(':')
            
            self.scheduler.add_job(
                func=self._run_follow_up,
                trigger=CronTrigger(
                    hour=int(hour),
                    minute=int(minute),
                    timezone=self.timezone
                ),
                id='follow_up',
                name='Follow-up Check',
                replace_existing=True
            )
            logger.info(f"Scheduled follow-up check at {follow_up_time} {self.timezone}")
        
        # Dashboard cache refresh (every hour)
        if config.get('dashboard.enabled', True):
            refresh_interval = config.get('dashboard.refresh_interval_minutes', 60)
            
            self.scheduler.add_job(
                func=self._refresh_dashboard,
                trigger='interval',
                minutes=refresh_interval,
                id='dashboard_refresh',
                name='Dashboard Cache Refresh',
                replace_existing=True
            )
            logger.info(f"Scheduled dashboard refresh every {refresh_interval} minutes")
    
    def _run_daily_report(self):
        """Execute daily report generation."""
        try:
            logger.info("Running scheduled daily report...")
            daily_report_service.save_and_send_report()
            logger.info("Daily report completed successfully")
        except Exception as e:
            logger.error(f"Error in scheduled daily report: {e}", exc_info=True)
    
    def _run_follow_up(self):
        """Execute follow-up check."""
        try:
            logger.info("Running scheduled follow-up check...")
            result = follow_up_service.check_and_follow_up()
            logger.info(f"Follow-up check completed: {result['followed_up']} tickets followed up")
        except Exception as e:
            logger.error(f"Error in scheduled follow-up: {e}", exc_info=True)
    
    def _refresh_dashboard(self):
        """Refresh dashboard cache."""
        try:
            logger.info("Refreshing dashboard cache...")
            from .services.dashboard import dashboard_service
            dashboard_service.get_dashboard_data(force_refresh=True)
            logger.info("Dashboard cache refreshed successfully")
        except Exception as e:
            logger.error(f"Error refreshing dashboard: {e}", exc_info=True)
    
    def start(self):
        """Start the scheduler."""
        if not self.enabled:
            logger.info("Scheduler is disabled, not starting")
            return
        
        self.setup_jobs()
        self.scheduler.start()
        logger.info("Scheduler started successfully")
        
        # Log scheduled jobs
        jobs = self.scheduler.get_jobs()
        logger.info(f"Active jobs: {len(jobs)}")
        for job in jobs:
            logger.info(f"  - {job.name} (ID: {job.id}, Next run: {job.next_run_time})")
    
    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")
    
    def get_jobs_status(self) -> list:
        """Get status of all scheduled jobs."""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
            })
        return jobs


# Global scheduler instance
scheduler = SchedulerService()


