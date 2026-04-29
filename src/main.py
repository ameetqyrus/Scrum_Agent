"""Main entry point for Scrum Master Agent."""

import logging
import sys
import argparse
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('scrum_agent.log')
    ]
)

logger = logging.getLogger(__name__)


def run_web_server(host: str, port: int, reload: bool = False):
    """Run the web server."""
    import uvicorn
    from .web.app import app
    
    logger.info(f"Starting web server on {host}:{port}")
    
    uvicorn.run(
        "src.web.app:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )


def run_daily_report():
    """Run daily report generation once."""
    logger.info("Running daily report generation...")
    from .services.daily_report import daily_report_service
    
    success = daily_report_service.save_and_send_report()
    
    if success:
        logger.info("Daily report generated successfully")
    else:
        logger.error("Daily report generation failed")
        sys.exit(1)


def run_follow_up():
    """Run follow-up check once."""
    logger.info("Running follow-up check...")
    from .services.follow_up import follow_up_service
    
    result = follow_up_service.check_and_follow_up()
    
    logger.info(f"Follow-up check complete: {result}")


def test_jira_connection():
    """Test Jira connection and credentials."""
    logger.info("Testing Jira connection...")
    
    try:
        from .jira_client import jira_client
        
        user_info = jira_client.get_user_info()
        logger.info(f"✅ Successfully connected to Jira")
        logger.info(f"   User: {user_info['display_name']}")
        logger.info(f"   Email: {user_info['email']}")
        logger.info(f"   Account ID: {user_info['account_id']}")
        
        # Test fetching issues
        logger.info("Testing issue retrieval...")
        issues = jira_client.get_my_issues()
        logger.info(f"✅ Found {len(issues)} issues assigned to or mentioning you")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to connect to Jira: {e}")
        logger.error("Please check your credentials in config/credentials.properties")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Scrum Master Agent')
    
    parser.add_argument(
        'command',
        choices=['web', 'report', 'follow-up', 'test'],
        help='Command to run'
    )
    
    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='Host for web server (default: 0.0.0.0)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=8000,
        help='Port for web server (default: 8000)'
    )
    
    parser.add_argument(
        '--reload',
        action='store_true',
        help='Enable auto-reload for development'
    )
    
    args = parser.parse_args()
    
    try:
        if args.command == 'web':
            run_web_server(args.host, args.port, args.reload)
        
        elif args.command == 'report':
            run_daily_report()
        
        elif args.command == 'follow-up':
            run_follow_up()
        
        elif args.command == 'test':
            success = test_jira_connection()
            sys.exit(0 if success else 1)
    
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        sys.exit(0)
    
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()



