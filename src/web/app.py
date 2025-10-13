"""FastAPI web application."""

import logging
import secrets
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from pathlib import Path
from typing import Optional
from pydantic import BaseModel

from ..config import config
from ..services.dashboard import dashboard_service
from ..services.daily_report import daily_report_service
from ..services.follow_up import follow_up_service
from ..chatbot import chatbot
from ..scheduler import scheduler

logger = logging.getLogger(__name__)

# Simple in-memory session store (in production, use Redis or database)
SESSIONS = {}

# Default credentials (in production, use environment variables and hashed passwords)
DEFAULT_USERS = {
    "admin": "admin123"
}

# Create FastAPI app
app = FastAPI(
    title="Scrum Master Agent",
    description="An intelligent assistant for agile teams",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=secrets.token_hex(32),
    session_cookie="scrum_agent_session",
    max_age=86400  # 24 hours
)

# Serve static files
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Templates directory
templates_dir = Path(__file__).parent / "templates"
templates_dir.mkdir(exist_ok=True)


# Helper functions
def is_authenticated(request: Request) -> bool:
    """Check if user is authenticated."""
    session_id = request.session.get("session_id")
    if not session_id:
        return False
    
    session_data = SESSIONS.get(session_id)
    if not session_data:
        return False
    
    # Check if session is expired
    if session_data.get("expires_at") < datetime.now():
        del SESSIONS[session_id]
        return False
    
    return True


def get_current_user(request: Request) -> Optional[str]:
    """Get current logged-in username."""
    session_id = request.session.get("session_id")
    if not session_id:
        return None
    
    session_data = SESSIONS.get(session_id)
    if not session_data:
        return None
    
    return session_data.get("username")


# Pydantic models for request/response
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    message: str
    username: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    include_context: Optional[bool] = True


class ChatResponse(BaseModel):
    response: str
    session_id: str
    timestamp: str
    success: bool


# Authentication Routes
@app.get("/login", response_class=HTMLResponse)
async def login_page():
    """Serve the login page."""
    login_html = templates_dir / "login.html"
    if login_html.exists():
        return login_html.read_text()
    return HTMLResponse(content="<h1>Login page not found</h1>", status_code=404)


@app.post("/api/auth/login", response_model=LoginResponse)
async def login(login_data: LoginRequest, request: Request):
    """Authenticate user and create session."""
    username = login_data.username
    password = login_data.password
    
    # Check credentials
    if username not in DEFAULT_USERS or DEFAULT_USERS[username] != password:
        return LoginResponse(
            success=False,
            message="Invalid username or password"
        )
    
    # Create session
    session_id = secrets.token_hex(32)
    SESSIONS[session_id] = {
        "username": username,
        "created_at": datetime.now(),
        "expires_at": datetime.now() + timedelta(hours=24)
    }
    
    # Store session ID in cookie
    request.session["session_id"] = session_id
    
    logger.info(f"User '{username}' logged in successfully")
    
    return LoginResponse(
        success=True,
        message="Login successful",
        username=username
    )


@app.get("/api/auth/me")
async def get_current_user_endpoint(request: Request):
    """Get current logged-in user information."""
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    username = get_current_user(request)
    return {
        "success": True,
        "username": username,
        "authenticated": True
    }


@app.post("/api/auth/logout")
async def logout(request: Request):
    """Logout user and destroy session."""
    session_id = request.session.get("session_id")
    if session_id and session_id in SESSIONS:
        username = SESSIONS[session_id].get("username")
        del SESSIONS[session_id]
        logger.info(f"User '{username}' logged out")
    
    request.session.clear()
    return {"success": True, "message": "Logged out successfully"}


# Main Dashboard Routes
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the main dashboard page."""
    # Check authentication
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)
    
    html_file = static_dir / "index.html"
    if html_file.exists():
        with open(html_file, 'r') as f:
            return f.read()
    else:
        return """
        <html>
            <head><title>Scrum Master Agent</title></head>
            <body>
                <h1>Scrum Master Agent</h1>
                <p>Dashboard is loading...</p>
                <p>API is running. Access <a href="/docs">/docs</a> for API documentation.</p>
            </body>
        </html>
        """


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "scheduler_running": scheduler.scheduler.running if scheduler.enabled else False,
        "jobs": scheduler.get_jobs_status() if scheduler.enabled else []
    }


@app.get("/api/dashboard")
async def get_dashboard(request: Request):
    """Get dashboard data."""
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        data = dashboard_service.get_dashboard_data()
        return JSONResponse(content=data)
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dashboard/refresh")
async def refresh_dashboard(request: Request):
    """Force refresh dashboard data."""
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        data = dashboard_service.get_dashboard_data(force_refresh=True)
        return JSONResponse(content=data)
    except Exception as e:
        logger.error(f"Error refreshing dashboard: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
async def chat_endpoint(chat_request: ChatRequest, request: Request):
    """Chat with the scrum bot."""
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        response = chatbot.chat(
            message=chat_request.message,
            session_id=chat_request.session_id,
            include_context=chat_request.include_context
        )
        return JSONResponse(content=response)
    except Exception as e:
        logger.error(f"Error in chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/chat/suggestions")
async def get_suggestions(request: Request):
    """Get suggested questions for the chatbot."""
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        suggestions = chatbot.get_suggested_questions()
        return JSONResponse(content={"suggestions": suggestions})
    except Exception as e:
        logger.error(f"Error getting suggestions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/chat/history/{session_id}")
async def clear_chat_history(session_id: str):
    """Clear chat history for a session."""
    try:
        chatbot.clear_history(session_id)
        return JSONResponse(content={"message": "Chat history cleared"})
    except Exception as e:
        logger.error(f"Error clearing chat history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/report/generate")
async def generate_report():
    """Manually trigger daily report generation."""
    try:
        success = daily_report_service.save_and_send_report()
        return JSONResponse(content={
            "success": success,
            "message": "Report generated and sent" if success else "Report generation failed"
        })
    except Exception as e:
        logger.error(f"Error generating report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/follow-up/check")
async def check_follow_ups():
    """Manually trigger follow-up check."""
    try:
        result = follow_up_service.check_and_follow_up()
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error checking follow-ups: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/follow-up/history")
async def get_follow_up_history(days: int = 7):
    """Get follow-up history."""
    try:
        history = follow_up_service.get_follow_up_history(days=days)
        return JSONResponse(content={"history": history})
    except Exception as e:
        logger.error(f"Error getting follow-up history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Starting Scrum Master Agent web application...")
    
    # Start scheduler if enabled
    if scheduler.enabled:
        scheduler.start()
        logger.info("Scheduler started")
    
    logger.info("Application started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Scrum Master Agent...")
    
    # Stop scheduler
    if scheduler.enabled:
        scheduler.stop()
    
    logger.info("Application shut down successfully")

