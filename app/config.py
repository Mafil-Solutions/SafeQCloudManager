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
            
            # Access Control - Role-based permissions
            'ACCESS_CONTROL': {
                'ENABLE_GROUP_RESTRICTION': self._get_secret('ENABLE_GROUP_RESTRICTION', True),
                'DENY_MESSAGE': 'גישה נדחתה. נדרשת שייכות לקבוצת SafeQ.',
                # Role mapping from Entra ID groups (4 permission levels)
                # Group names are configurable via secrets/environment variables
                'ROLE_MAPPING': {
                    self._get_secret('ROLE_VIEW_GROUP', 'SafeQ-View'): 'viewer',
                    self._get_secret('ROLE_SUPPORT_GROUP', 'SafeQ-Support'): 'support',
                    self._get_secret('ROLE_ADMIN_GROUP', 'SafeQ-Admin'): 'admin',
                    self._get_secret('ROLE_SUPERADMIN_GROUP', 'SafeQ-SuperAdmin'): 'superadmin'
                }
            },

            # Reports - Local Cloud Authentication
            # משתמשים מקומיים שמאומתים מול הענן לצפייה בדוחות
            'REPORTS_VIEW_GROUP': self._get_secret('REPORTS_VIEW_GROUP', 'Reports-View'),
            'LOCAL_ADMIN_USERNAME': self._get_secret('LOCAL_ADMIN_USERNAME', 'Admin'),
            
            # Session
            'SESSION_TIMEOUT': int(self._get_secret('SESSION_TIMEOUT', '120')),
            'USE_ENTRA_ID': self._get_secret('USE_ENTRA_ID', True),
            
            # Logging
            'LOG_TO_FILE': self._get_secret('LOG_TO_FILE', True),
            'LOG_TO_DATABASE': self._get_secret('LOG_TO_DATABASE', True),
            'AUDIT_LOG_PATH': self._get_secret('AUDIT_LOG_PATH', 'safeq_audit.log'),
            'DATABASE_PATH': self._get_secret('DATABASE_PATH', 'safeq_audit.db'),

            # Emergency Local Users (from secrets.toml)
            'LOCAL_USERS': self._parse_emergency_users()
        }
    
    def _parse_list(self, value: str) -> list:
        """ממיר string מופרד בפסיקים לרשימה"""
        if not value:
            return []
        if isinstance(value, list):
            return value
        return [item.strip() for item in value.split(',') if item.strip()]

    def _parse_emergency_users(self) -> dict:
        """
        טוען משתמשי חירום מ-secrets
        פורמט ב-secrets.toml:
        [EMERGENCY_USERS]
        admin = "plain_text_password"
        backup = "plain_text_password"

        הערה: הסיסמאות מאוחסנות בטקסט רגיל ב-secrets (שהוא מוצפן ע"י Streamlit)
        ומומרות ל-hash בזמן ההתחברות
        """
        try:
            # קודם נסה Streamlit secrets
            if hasattr(st, 'secrets') and 'EMERGENCY_USERS' in st.secrets:
                # Streamlit secrets - מחזיר dict עם סיסמאות plain text
                users = dict(st.secrets['EMERGENCY_USERS'])
                print(f"[DEBUG] Loaded {len(users)} emergency users from Streamlit secrets")
                return users

            # נסה environment variables בפורמט: EMERGENCY_USER_admin=password
            emergency_users = {}
            found_vars = []
            skipped_vars = []

            for key, value in os.environ.items():
                if key.startswith('EMERGENCY_USER_'):
                    username = key.replace('EMERGENCY_USER_', '')
                    value_len = len(value) if value else 0
                    print(f"[DEBUG] Checking {key}: value_length={value_len}, value_exists={value is not None}, value_bool={bool(value)}")

                    if value and value.strip():  # וודא שיש ערך
                        emergency_users[username] = value
                        found_vars.append(key)
                        print(f"[DEBUG] ✅ Added emergency user: {username} (password length: {len(value)})")
                    else:
                        skipped_vars.append((key, f"empty or whitespace-only (length={value_len})"))
                        print(f"[DEBUG] ❌ Skipped {key}: value is empty or whitespace-only (length={value_len})")

            if found_vars:
                print(f"[DEBUG] Found emergency user environment variables: {found_vars}")
                print(f"[DEBUG] Loaded {len(emergency_users)} emergency users from environment")
                print(f"[DEBUG] Emergency users dict keys: {list(emergency_users.keys())}")
            else:
                print("[DEBUG] No valid EMERGENCY_USER_* environment variables found")
                if skipped_vars:
                    print(f"[DEBUG] Skipped variables (empty/invalid): {skipped_vars}")
                print(f"[DEBUG] Total environment variables: {len(os.environ)}")
                # הדפס רשימת משתנים שמתחילים ב-EMERGENCY (לדיבוג)
                emergency_vars = [k for k in os.environ.keys() if 'EMERGENCY' in k]
                if emergency_vars:
                    print(f"[DEBUG] Found EMERGENCY-related vars: {emergency_vars}")
                    for ev in emergency_vars:
                        ev_val = os.environ.get(ev, '')
                        print(f"[DEBUG]   - {ev}: length={len(ev_val)}, repr={repr(ev_val[:20]) if ev_val else 'None'}")

            return emergency_users if emergency_users else {}
        except Exception as e:
            print(f"[ERROR] Exception in _parse_emergency_users: {str(e)}")
            import traceback
            traceback.print_exc()
            return {}
    
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

        if not self._config['ACCESS_CONTROL']['ROLE_MAPPING']:
            warnings.append("ℹ️ No ROLE_MAPPING configured - access control may not work properly")

        return len(errors) == 0, errors, warnings

# יצירת instance גלובלי
config = Config()