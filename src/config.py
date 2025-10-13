"""Configuration management for Scrum Agent."""

import os
import yaml
from pathlib import Path
from typing import Any, Dict
from configparser import ConfigParser


class Config:
    """Centralized configuration management."""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.config_dir = self.base_dir / "config"
        
        # Load YAML config
        self.yaml_config = self._load_yaml_config()
        
        # Load credentials
        self.credentials = self._load_credentials()
    
    def _load_yaml_config(self) -> Dict[str, Any]:
        """Load the main YAML configuration file."""
        config_path = self.config_dir / "config.yaml"
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _load_credentials(self) -> ConfigParser:
        """Load credentials from properties file."""
        cred_path = self.config_dir / "credentials.properties"
        if not cred_path.exists():
            raise FileNotFoundError(
                f"Credentials file not found: {cred_path}\n"
                f"Please copy credentials.properties.example to credentials.properties "
                f"and fill in your credentials."
            )
        
        config = ConfigParser()
        config.read(cred_path)
        return config
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value using dot notation."""
        keys = key.split('.')
        value = self.yaml_config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            
            if value is None:
                return default
        
        return value
    
    def get_credential(self, section: str, key: str) -> str:
        """Get a credential value."""
        try:
            return self.credentials.get(section, key)
        except Exception:
            return None
    
    @property
    def jira_url(self) -> str:
        return self.get_credential('jira', 'url')
    
    @property
    def jira_email(self) -> str:
        return self.get_credential('jira', 'email')
    
    @property
    def jira_api_token(self) -> str:
        return self.get_credential('jira', 'api_token')
    
    @property
    def user_email(self) -> str:
        return self.get_credential('user', 'email')
    
    @property
    def user_jira_account_id(self) -> str:
        return self.get_credential('user', 'jira_account_id')
    
    @property
    def azure_openai_endpoint(self) -> str:
        return self.get_credential('azure', 'openai.endpoint')
    
    @property
    def azure_openai_api_key(self) -> str:
        return self.get_credential('azure', 'openai.api_key')
    
    @property
    def azure_openai_deployment(self) -> str:
        return self.get_credential('azure', 'openai.deployment_name')
    
    @property
    def azure_openai_api_version(self) -> str:
        return self.get_credential('azure', 'openai.api_version')
    
    @property
    def email_smtp_host(self) -> str:
        return self.get_credential('email', 'smtp_host')
    
    @property
    def email_smtp_port(self) -> int:
        return int(self.get_credential('email', 'smtp_port') or 587)
    
    @property
    def email_from_address(self) -> str:
        return self.get_credential('email', 'from_address')
    
    @property
    def email_password(self) -> str:
        return self.get_credential('email', 'password')
    
    @property
    def database_path(self) -> Path:
        """Get the database file path."""
        db_path = self.get('database.path', 'scrum_agent.db')
        return self.base_dir / db_path


# Global config instance
config = Config()


