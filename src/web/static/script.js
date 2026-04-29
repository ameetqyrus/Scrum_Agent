// Scrum Master Agent - Frontend JavaScript

// Global state
let sessionId = generateSessionId();
let dashboardData = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});

function initializeApp() {
    // Load current user info
    loadCurrentUser();
    
    // Load dashboard data
    loadDashboard();
    
    // Load chat suggestions
    loadSuggestions();
    
    // Set up event listeners
    setupEventListeners();
    
    // Check health status
    checkHealth();
    
    // Auto-refresh dashboard every hour
    setInterval(loadDashboard, 60 * 60 * 1000);
}

function setupEventListeners() {
    // Logout button
    document.getElementById('logoutBtn').addEventListener('click', () => {
        handleLogout();
    });
    
    // Dashboard refresh
    document.getElementById('refreshBtn').addEventListener('click', () => {
        refreshDashboard();
    });
    
    // Generate report
    document.getElementById('generateReportBtn').addEventListener('click', () => {
        generateReport();
    });
    
    // Check follow-ups
    document.getElementById('checkFollowUpBtn').addEventListener('click', () => {
        checkFollowUps();
    });
    
    // Tab switching
    document.querySelectorAll('.tab-button').forEach(button => {
        button.addEventListener('click', (e) => {
            switchTab(e.target.dataset.tab);
        });
    });
    
    // Chat input
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendBtn');
    
    sendBtn.addEventListener('click', () => {
        sendMessage();
    });
    
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
}

// Authentication functions
async function loadCurrentUser() {
    try {
        const response = await fetch('/api/auth/me');
        if (!response.ok) {
            // Not authenticated, redirect to login
            window.location.href = '/login';
            return;
        }
        
        const data = await response.json();
        if (data.success && data.username) {
            document.getElementById('currentUser').textContent = data.username;
        }
    } catch (error) {
        console.error('Error loading user info:', error);
        // On error, redirect to login
        window.location.href = '/login';
    }
}

async function handleLogout() {
    try {
        const response = await fetch('/api/auth/logout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        if (data.success) {
            // Redirect to login page
            window.location.href = '/login';
        }
    } catch (error) {
        console.error('Error during logout:', error);
        // Even on error, redirect to login
        window.location.href = '/login';
    }
}

// Dashboard functions
async function loadDashboard() {
    try {
        showLoading(true);
        hideError();
        
        const response = await fetch('/api/dashboard');
        const data = await response.json();
        
        dashboardData = data;
        renderDashboard(data);
        updateLastUpdated(data.last_updated);
        
    } catch (error) {
        console.error('Error loading dashboard:', error);
        showError('Failed to load dashboard data. Please try again.');
    } finally {
        showLoading(false);
    }
}

async function refreshDashboard() {
    try {
        showLoading(true);
        hideError();
        
        const response = await fetch('/api/dashboard/refresh', {
            method: 'POST'
        });
        const data = await response.json();
        
        dashboardData = data;
        renderDashboard(data);
        updateLastUpdated(data.last_updated);
        
        showNotification('Dashboard refreshed successfully!');
        
    } catch (error) {
        console.error('Error refreshing dashboard:', error);
        showError('Failed to refresh dashboard. Please try again.');
    } finally {
        showLoading(false);
    }
}

function renderDashboard(data) {
    // Render stats cards
    document.getElementById('totalAssigned').textContent = data.stats?.total_assigned || 0;
    document.getElementById('totalMentioned').textContent = data.stats?.total_mentioned || 0;
    document.getElementById('sprintTotal').textContent = data.sprint_stats?.total_issues || 0;
    document.getElementById('sprintCompletion').textContent = 
        (data.sprint_stats?.completion_percentage || 0).toFixed(0) + '%';
    
    document.getElementById('statsCards').style.display = 'grid';
    
    // Render assigned issues
    renderIssues(data.assigned_to_me, 'assignedIssues');
    
    // Render mentioned issues
    renderIssues(data.mentioned_in_comments, 'mentionedIssues');
    
    // Render sprint stats
    renderSprintStats(data.sprint_stats);
    
    // Render recent activity
    renderIssues(data.recent_activity, 'recentActivity');
}

function renderIssues(issues, containerId) {
    const container = document.getElementById(containerId);
    
    if (!issues || issues.length === 0) {
        container.innerHTML = '<p style="color: var(--ink-3); padding: 20px; text-align: center; font-family: var(--font-mono); font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em;">No issues found</p>';
        return;
    }
    
    container.innerHTML = issues.map(issue => `
        <div class="issue-card">
            <a href="${issue.url}" target="_blank" class="issue-key">${issue.key}</a>
            <div class="issue-summary">${escapeHtml(issue.summary)}</div>
            <div class="issue-meta">
                <span class="badge badge-status">${issue.status}</span>
                <span class="badge badge-priority">${issue.priority}</span>
                <span class="badge badge-type">${issue.type}</span>
                <span>👤 ${escapeHtml(issue.assignee)}</span>
            </div>
        </div>
    `).join('');
}

function renderSprintStats(stats) {
    const container = document.getElementById('sprintStats');
    
    if (!stats || Object.keys(stats).length === 0) {
        container.innerHTML = '<p style="color: var(--ink-3); padding: 20px; text-align: center; font-family: var(--font-mono); font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em;">No active sprint data available</p>';
        return;
    }
    
    let html = '<h3>Active Sprint Overview</h3>';
    
    // Progress bar
    if (stats.completion_percentage !== undefined) {
        html += `
            <div class="progress-bar">
                <div class="progress-fill" style="width: ${stats.completion_percentage}%">
                    ${stats.completion_percentage.toFixed(0)}%
                </div>
            </div>
        `;
    }
    
    // Stats
    html += '<div style="margin-top: 20px;">';
    html += `<div class="stat-row"><span>Total Issues:</span><strong>${stats.total_issues || 0}</strong></div>`;
    
    if (stats.story_points_total) {
        html += `<div class="stat-row">
            <span>Story Points:</span>
            <strong>${stats.story_points_completed || 0} / ${stats.story_points_total}</strong>
        </div>`;
    }
    
    // By status
    if (stats.by_status) {
        html += '<h4 style="margin-top: 20px;">By Status:</h4>';
        Object.entries(stats.by_status).forEach(([status, count]) => {
            html += `<div class="stat-row"><span>${status}:</span><strong>${count}</strong></div>`;
        });
    }
    
    html += '</div>';
    container.innerHTML = html;
}

function switchTab(tabName) {
    // Update buttons
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    
    // Update panes
    document.querySelectorAll('.tab-pane').forEach(pane => {
        pane.classList.remove('active');
    });
    document.getElementById(tabName).classList.add('active');
}

// Chat functions
async function loadSuggestions() {
    try {
        const response = await fetch('/api/chat/suggestions');
        const data = await response.json();
        
        const container = document.getElementById('suggestionButtons');
        container.innerHTML = data.suggestions.map(q => 
            `<button class="suggestion-btn" onclick="askQuestion('${escapeHtml(q)}')">${escapeHtml(q)}</button>`
        ).join('');
        
    } catch (error) {
        console.error('Error loading suggestions:', error);
    }
}

async function sendMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    
    if (!message) return;
    
    // Clear input
    input.value = '';
    
    // Add user message to chat
    addMessage(message, 'user');
    
    try {
        // Send to API
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                session_id: sessionId,
                include_context: true
            })
        });
        
        const data = await response.json();
        
        // Add assistant response
        addMessage(data.response, 'assistant');
        
    } catch (error) {
        console.error('Error sending message:', error);
        addMessage('Sorry, I encountered an error. Please try again.', 'assistant');
    }
}

function askQuestion(question) {
    document.getElementById('chatInput').value = question;
    sendMessage();
}

function addMessage(text, sender) {
    const container = document.getElementById('chatMessages');
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    
    // Format the message text
    bubble.innerHTML = formatMessage(text);
    
    messageDiv.appendChild(bubble);
    container.appendChild(messageDiv);
    
    // Scroll to bottom
    container.scrollTop = container.scrollHeight;
}

function formatMessage(text) {
    if (!text) return '';
    
    // Escape HTML to prevent XSS
    let formatted = escapeHtml(text);
    
    // Convert newlines to <br>
    formatted = formatted.replace(/\n/g, '<br>');
    
    // Format bullet lists (lines starting with -)
    formatted = formatted.replace(/^- (.+)$/gm, '<li>$1</li>');
    formatted = formatted.replace(/(<li>.*<\/li>)/s, '<ul style="margin: 10px 0; padding-left: 20px;">$1</ul>');
    
    // Format numbered lists  
    formatted = formatted.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');
    
    // Bold text (**text** or __text__)
    formatted = formatted.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    formatted = formatted.replace(/__(.+?)__/g, '<strong>$1</strong>');
    
    // Code blocks (`code`)
    formatted = formatted.replace(/`([^`]+)`/g, '<code style="background: rgba(0,0,0,0.1); padding: 2px 6px; border-radius: 3px; font-family: monospace;">$1</code>');
    
    // JQL queries (special formatting)
    formatted = formatted.replace(/(JQL:.*?)(<br>|$)/g, '<div style="background: rgba(102, 126, 234, 0.1); padding: 8px; border-radius: 4px; margin: 5px 0; font-family: monospace; font-size: 0.9em;">$1</div>$2');
    
    return formatted;
}

// Report and follow-up functions
async function generateReport() {
    try {
        const btn = document.getElementById('generateReportBtn');
        btn.disabled = true;
        btn.textContent = '⏳ Generating...';
        
        const response = await fetch('/api/report/generate', {
            method: 'POST'
        });
        const data = await response.json();
        
        if (data.success) {
            showNotification('Report generated and sent successfully!');
        } else {
            showNotification('Report generation failed. Check logs.', 'error');
        }
        
    } catch (error) {
        console.error('Error generating report:', error);
        showNotification('Failed to generate report. Please try again.', 'error');
    } finally {
        const btn = document.getElementById('generateReportBtn');
        btn.disabled = false;
        btn.textContent = '📊 Generate Report';
    }
}

async function checkFollowUps() {
    try {
        const btn = document.getElementById('checkFollowUpBtn');
        btn.disabled = true;
        btn.textContent = '⏳ Checking...';
        
        const response = await fetch('/api/follow-up/check', {
            method: 'POST'
        });
        const data = await response.json();
        
        const count = data.followed_up?.length || 0;
        showNotification(`Follow-up check complete. Sent ${count} follow-up(s).`);
        
    } catch (error) {
        console.error('Error checking follow-ups:', error);
        showNotification('Failed to check follow-ups. Please try again.', 'error');
    } finally {
        const btn = document.getElementById('checkFollowUpBtn');
        btn.disabled = false;
        btn.textContent = '⏰ Check Follow-ups';
    }
}

// Health check
async function checkHealth() {
    try {
        const response = await fetch('/api/health');
        const data = await response.json();
        
        const indicator = document.getElementById('status');
        indicator.style.color = data.status === 'healthy'
            ? 'var(--green)'
            : 'var(--red)';

    } catch (error) {
        console.error('Error checking health:', error);
        document.getElementById('status').style.color = 'var(--red)';
    }
}

// Utility functions
function showLoading(show) {
    document.getElementById('loading').style.display = show ? 'block' : 'none';
}

function showError(message) {
    const errorDiv = document.getElementById('error');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
}

function hideError() {
    document.getElementById('error').style.display = 'none';
}

function showNotification(message, type = 'success') {
    // Simple notification (could be enhanced with a toast library)
    alert(message);
}

function updateLastUpdated(timestamp) {
    if (!timestamp) return;
    
    const date = new Date(timestamp);
    document.getElementById('lastUpdated').textContent = date.toLocaleString();
}

function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

