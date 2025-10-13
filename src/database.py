"""Database models and setup for Scrum Agent."""

from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator

from .config import config

Base = declarative_base()


class JiraIssue(Base):
    """Cache for Jira issues."""
    __tablename__ = 'jira_issues'
    
    id = Column(Integer, primary_key=True)
    issue_key = Column(String(50), unique=True, nullable=False, index=True)
    issue_id = Column(String(50), nullable=False)
    summary = Column(Text)
    description = Column(Text)
    status = Column(String(50))
    assignee = Column(String(100))
    reporter = Column(String(100))
    priority = Column(String(50))
    issue_type = Column(String(50))
    project_key = Column(String(50))
    created_date = Column(DateTime)
    updated_date = Column(DateTime)
    resolved_date = Column(DateTime, nullable=True)
    sprint_id = Column(String(50), nullable=True)
    sprint_name = Column(String(200), nullable=True)
    story_points = Column(Integer, nullable=True)
    labels = Column(JSON)
    components = Column(JSON)
    raw_data = Column(JSON)
    last_synced = Column(DateTime, default=datetime.utcnow)


class IssueComment(Base):
    """Cache for issue comments."""
    __tablename__ = 'issue_comments'
    
    id = Column(Integer, primary_key=True)
    comment_id = Column(String(50), unique=True, nullable=False)
    issue_key = Column(String(50), nullable=False, index=True)
    author = Column(String(100))
    body = Column(Text)
    created_date = Column(DateTime)
    updated_date = Column(DateTime)
    last_synced = Column(DateTime, default=datetime.utcnow)


class DailyReport(Base):
    """Store generated daily reports."""
    __tablename__ = 'daily_reports'
    
    id = Column(Integer, primary_key=True)
    report_date = Column(DateTime, nullable=False, index=True)
    report_html = Column(Text)
    report_text = Column(Text)
    sent_email = Column(Boolean, default=False)
    email_sent_date = Column(DateTime, nullable=True)
    created_date = Column(DateTime, default=datetime.utcnow)


class FollowUp(Base):
    """Track follow-ups sent for issues."""
    __tablename__ = 'follow_ups'
    
    id = Column(Integer, primary_key=True)
    issue_key = Column(String(50), nullable=False, index=True)
    follow_up_date = Column(DateTime, nullable=False)
    reason = Column(Text)
    sent_via = Column(String(50))  # jira_comment, email, slack
    comment_id = Column(String(50), nullable=True)
    created_date = Column(DateTime, default=datetime.utcnow)


class DashboardCache(Base):
    """Cache dashboard data to reduce API calls."""
    __tablename__ = 'dashboard_cache'
    
    id = Column(Integer, primary_key=True)
    cache_key = Column(String(100), unique=True, nullable=False)
    data = Column(JSON)
    last_updated = Column(DateTime, default=datetime.utcnow)


class Database:
    """Database connection and session management."""
    
    def __init__(self):
        self.engine = create_engine(
            f'sqlite:///{config.database_path}',
            echo=False,
            connect_args={"check_same_thread": False}
        )
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.create_tables()
    
    def create_tables(self):
        """Create all tables if they don't exist."""
        Base.metadata.create_all(bind=self.engine)
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Provide a transactional scope for database operations."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


# Global database instance
db = Database()


