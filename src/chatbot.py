"""Chatbot service using Azure OpenAI."""

import logging
from typing import List, Dict, Any
from datetime import datetime
from openai import AzureOpenAI

from .config import config
from .jira_client import jira_client
from .services.dashboard import dashboard_service

logger = logging.getLogger(__name__)


class ScrumChatbot:
    """Azure OpenAI-powered chatbot for scrum assistance."""
    
    def __init__(self):
        self.client = AzureOpenAI(
            api_key=config.azure_openai_api_key,
            api_version=config.azure_openai_api_version,
            azure_endpoint=config.azure_openai_endpoint
        )
        
        self.deployment = config.azure_openai_deployment
        self.chatbot_config = config.get('chatbot', {})
        self.system_prompt = self.chatbot_config.get('system_prompt', '')
        # GPT-5 uses reasoning tokens internally, need higher limit for reasoning + output
        self.max_tokens = self.chatbot_config.get('max_tokens', 4000)
        self.temperature = self.chatbot_config.get('temperature', 0.7)
        
        # Conversation history (in-memory, could be moved to DB for persistence)
        self.conversations = {}
    
    def get_context(self) -> str:
        """Get current context from Jira for the chatbot."""
        try:
            # Get dashboard data for context
            dashboard_data = dashboard_service.get_dashboard_data()
            
            context = "Current Jira Context:\n"
            context += f"- You have {dashboard_data['stats'].get('total_assigned', 0)} tickets assigned to you\n"
            context += f"- You are mentioned in {dashboard_data['stats'].get('total_mentioned', 0)} ticket comments\n"
            
            # Add assigned tickets
            if dashboard_data.get('assigned_to_me'):
                context += "\nYour Assigned Tickets:\n"
                for issue in dashboard_data['assigned_to_me'][:5]:  # Limit to 5
                    context += f"  - {issue['key']}: {issue['summary'][:50]} (Status: {issue['status']})\n"
            
            # Add mentioned tickets
            if dashboard_data.get('mentioned_in_comments'):
                context += "\nTickets Where You're Mentioned in Comments:\n"
                for issue in dashboard_data['mentioned_in_comments'][:5]:  # Limit to 5
                    context += f"  - {issue['key']}: {issue['summary'][:50]} (Status: {issue['status']})\n"
            
            if dashboard_data['stats'].get('by_status'):
                context += "\n- Status breakdown:\n"
                for status, count in dashboard_data['stats']['by_status'].items():
                    context += f"  - {status}: {count}\n"
            
            if dashboard_data.get('sprint_stats'):
                sprint = dashboard_data['sprint_stats']
                context += f"\nActive Sprint:\n"
                context += f"- Total issues: {sprint.get('total_issues', 0)}\n"
                if sprint.get('story_points_total', 0) > 0:
                    context += f"- Story points: {sprint.get('story_points_completed', 0)}/{sprint.get('story_points_total', 0)} "
                    context += f"({sprint.get('completion_percentage', 0):.1f}% complete)\n"
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting context: {e}")
            return "Unable to fetch current Jira context."
    
    def chat(
        self,
        message: str,
        session_id: str = "default",
        include_context: bool = True
    ) -> Dict[str, Any]:
        """Send a message to the chatbot and get a response."""
        try:
            # Get or create conversation history
            if session_id not in self.conversations:
                self.conversations[session_id] = []
            
            conversation = self.conversations[session_id]
            
            # Build messages
            messages = [
                {"role": "system", "content": self.system_prompt}
            ]
            
            # Add context if requested
            if include_context:
                context = self.get_context()
                messages.append({
                    "role": "system",
                    "content": f"Here's the current state of the user's work:\n{context}"
                })
            
            # Add conversation history (limited to last 10 messages)
            messages.extend(conversation[-10:])
            
            # Add current message
            messages.append({"role": "user", "content": message})
            
            # Get response from Azure OpenAI
            logger.info(f"Sending message to Azure OpenAI: {message[:50]}...")
            
            # GPT-5 only supports default temperature (1), so we omit it
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=messages,
                max_completion_tokens=self.max_tokens
            )
            
            assistant_message = response.choices[0].message.content
            
            # Update conversation history
            conversation.append({"role": "user", "content": message})
            conversation.append({"role": "assistant", "content": assistant_message})
            
            # Keep only last 20 messages to prevent memory issues
            if len(conversation) > 20:
                self.conversations[session_id] = conversation[-20:]
            
            return {
                "response": assistant_message,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error in chatbot: {e}", exc_info=True)
            return {
                "response": "I'm sorry, I encountered an error processing your request. Please try again.",
                "error": str(e),
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "success": False
            }
    
    def clear_history(self, session_id: str = "default"):
        """Clear conversation history for a session."""
        if session_id in self.conversations:
            del self.conversations[session_id]
    
    def get_suggested_questions(self) -> List[str]:
        """Get suggested questions users can ask."""
        return [
            "What's my sprint progress?",
            "Show me my assigned tickets",
            "What are the blockers?",
            "How much time was logged today?",
            "What's our team velocity?",
            "Which tickets need attention?",
            "Explain the daily standup best practices",
            "How should we run a retrospective?",
        ]


# Global chatbot instance
chatbot = ScrumChatbot()

