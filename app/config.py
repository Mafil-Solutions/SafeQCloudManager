"""
SafeQ Manager - Configuration Management
טעינת הגדרות מ-Streamlit secrets או מ-environment variables
"""

import os
import streamlit as st
from typing import Dict, Any, Optional

class Config:
    """מחלקה לניהול הגדרות האפליקציה"""
    
    def __init__(self):
        self._config = None
        self._load_config()
    
    def _get_secret(self, key: str, default: Any = None) -> Any:
        """
        מחזיר ערך מ-Streamlit secrets או מ-environment variables
        סדר עדיפות: Streamlit secrets → Environment → Default
        """
        # נסה Streamlit secrets (Cloud)
        try:
            if hasattr(st, 'secrets') and key in st.secrets:
                value = st.secrets[key]
                # המר string boolean ל-boolean אמיתי
                if isinstance(value, str):
                    if value.lower() in ['true', 'false']:
                        return value.lower() == 'true'
                return value
        except:
            pass
        
        # נסה environment variables (Local)
        env_value = os.getenv(key)
        if env_value is not None:
            # המר string boolean ל-boolean אמיתי
            if env_value.lower() in ['true', 'false']:
                return env_value.lower() == 'true'
            return env_value
        
        return default
    
    def _load_config(self):
        """טעינת כל ההגדרות"""
        
        tenant_id = self._get_secret('TENANT_ID', '')
        
        self._config = {
            # Server Settings
            'SERVER_URL': self._get_secret('SERVER_URL', 'https://localhost:7300'),
            'API_KEY': self._get_secret('API_KEY', ''),
            
            # Providers
            'PROVIDERS': {
                'LOCAL': int(self._get_secret('PROVIDER_LOCAL', '12348')),
                'ENTRA': int(self._get_secret('PROVIDER_ENTRA', '12351'))
            },
            
            # Entra ID
            'ENTRA_ID': {
                'CLIENT_ID': self._get_secret('CLIENT_ID', ''),
                'TENANT_ID': tenant_id,
                'CLIENT_SECRET': self._get_secret('CLIENT_SECRET', ''),
                'AUTHORITY': self._get_secret('AUTHORITY', f'https://login.microsoftonline.com/{tenant_id}'),
                'SCOPE': [
                    'https://graph.microsoft.com/User.Read',
                    'https://graph.microsoft.com/GroupMember.Read.All',
                    'https://graph.microsoft.com/Directory.Read.All'
                ],
                'REDIRECT_URI': self._get_secret('REDIRECT_URI', 'http://localhost:8501'),
            },
            
            # Access Control
            'ACCESS_CONTROL': {
                'ENABLE_GROUP_RESTRICTION': self._get_secret('ENABLE_GROUP_RESTRICTION', True),
                'AUTHORIZED_GROUPS': self._parse_list(self._get_secret('AUTHORIZED_GROUPS', '')),
                'ADMIN_GROUPS': self._parse_list(self._get_secret('ADMIN_GROUPS', '')),
                'SUPERADMIN_GROUP': self._get_secret('SUPERADMIN_GROUP', 'SafeQ-SuperAdmin'),
                'DENY_MESSAGE': 'Access denied. You must be a member of SafeQ authorized groups.',
            },
            
            # Session
            'SESSION_TIMEOUT': int(self._get_secret('SESSION_TIMEOUT', '120')),
            'USE_ENTRA_ID': self._get_secret('USE_ENTRA_ID', True),
            
            # Logging
            'LOG_TO_FILE': self._get_secret('LOG_TO_FILE', True),
            'LOG_TO_DATABASE': self._get_secret('LOG_TO_DATABASE', True),
            'AUDIT_LOG_PATH': self._get_secret('AUDIT_LOG_PATH', 'safeq_audit.log'),
            'DATABASE_PATH': self._get_secret('DATABASE_PATH', 'safeq_audit.db')
        }
    
    def _parse_list(self, value: str) -> list:
        """ממיר string מופרד בפסיקים לרשימה"""
        if not value:
            return []
        if isinstance(value, list):
            return value
        return [item.strip() for item in value.split(',') if item.strip()]
    
    def get(self, key: str = None) -> Any:
        """מחזיר הגדרה או את כל ההגדרות"""
        if key is None:
            return self._config
        return self._config.get(key)
    
    def validate(self) -> tuple[bool, list]:
        """בדיקת תקינות הגדרות"""
        errors = []
        warnings = []
        
        # בדיקות קריטיות
        if not self._config['API_KEY']:
            errors.append("⚠️ API_KEY not configured")
        
        if self._config['USE_ENTRA_ID']:
            if not self._config['ENTRA_ID']['CLIENT_ID']:
                errors.append("⚠️ Entra ID CLIENT_ID not configured")
            if not self._config['ENTRA_ID']['CLIENT_SECRET']:
                errors.append("⚠️ Entra ID CLIENT_SECRET not configured")
            if not self._config['ENTRA_ID']['TENANT_ID']:
                errors.append("⚠️ Entra ID TENANT_ID not configured")
        
        # בדיקות אזהרה
        if 'localhost' in self._config['SERVER_URL']:
            warnings.append("ℹ️ SERVER_URL points to localhost")
        
        if not self._config['ACCESS_CONTROL']['AUTHORIZED_GROUPS']:
            warnings.append("ℹ️ No AUTHORIZED_GROUPS configured - all users will have access")
        
        return len(errors) == 0, errors, warnings

# יצירת instance גלובלי
config = Config()