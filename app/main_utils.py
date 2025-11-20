#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SafeQ Cloud Manager - Main Application
"""

import streamlit as st
import requests
import pandas as pd
import urllib3
from typing import Dict, List, Optional
import json
import os
import sqlite3
import re
from datetime import datetime, timedelta
import msal
import sys

# ייבוא config
from config import config
# ייבוא permissions (hybrid auth)
from permissions import (
    initialize_user_permissions,
    filter_users_by_departments,
    filter_groups_by_departments,
    get_department_options
)

def resource_path(relative_path: str) -> str:
    """
    מחזיר נתיב תקין לקובץ גם בהרצה רגילה וגם אחרי קומפילציה ל-exe עם PyInstaller
    """
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ============ CONFIGURATION ============
# טעינת הגדרות מ-config.py (שקורא מ-secrets או .env)
CONFIG = config.get()

# בדיקת תקינות הגדרות
is_valid, errors, warnings = config.validate()
if not is_valid:
    st.error("⚠️ שגיאות תצורה:")
    for error in errors:
        st.error(error)
    st.stop()

if warnings:
    for warning in warnings:
        st.warning(warning)

class AuditLogger:
    def __init__(self):
        self.log_to_file = CONFIG.get('LOG_TO_FILE', True)
        self.log_to_db = CONFIG.get('LOG_TO_DATABASE', True)
        self.log_file = CONFIG.get('AUDIT_LOG_PATH', 'safeq_audit.log')
        self.db_path = CONFIG.get('DATABASE_PATH', 'safeq_audit.db')
        
        if self.log_to_db:
            self._init_database()
    
    def _init_database(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    username TEXT NOT NULL,
                    user_email TEXT,
                    user_groups TEXT,
                    action TEXT NOT NULL,
                    details TEXT,
                    session_id TEXT,
                    success BOOLEAN DEFAULT 1,
                    access_level TEXT
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_logs(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_username ON audit_logs(username)')
            conn.commit()
            conn.close()
        except Exception as e:
            st.error(f"כשל באתחול מסד הנתונים: {str(e)}")
    
    def log_action(self, username, action, details="", user_email="", user_groups="", success=True, access_level="user"):
        timestamp = datetime.now().isoformat()
        session_id = st.session_state.get('session_id', '')
        
        # File logging
        if self.log_to_file:
            try:
                log_entry = f"{timestamp} | {username} | {user_email} | {action}"
                if details: log_entry += f" | {details}"
                if user_groups: log_entry += f" | Groups: {user_groups}"
                if not success: log_entry += " | FAILED"
                
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(log_entry + "\n")
            except: pass
        
        # Database logging
        if self.log_to_db:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO audit_logs 
                    (timestamp, username, user_email, user_groups, action, details, session_id, success, access_level)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (timestamp, username, user_email, user_groups, action, details, session_id, success, access_level))
                conn.commit()
                conn.close()
            except: pass
        
        # Session logging
        if 'audit_log' not in st.session_state:
            st.session_state.audit_log = []
        st.session_state.audit_log.append({
            'timestamp': timestamp, 'username': username, 'action': action,
            'details': details, 'success': success
        })
        if len(st.session_state.audit_log) > 50:
            st.session_state.audit_log = st.session_state.audit_log[-50:]

class EntraIDAuth:
    def __init__(self):
        self.client_id = CONFIG['ENTRA_ID']['CLIENT_ID']
        self.tenant_id = CONFIG['ENTRA_ID']['TENANT_ID']
        self.client_secret = CONFIG['ENTRA_ID']['CLIENT_SECRET']
        self.authority = CONFIG['ENTRA_ID']['AUTHORITY']
        self.scope = CONFIG['ENTRA_ID']['SCOPE']
    
    def get_auth_url(self):
        try:
            import uuid
            import base64
            import hashlib
            import secrets
            import urllib.parse
            import os
            
            # Generate PKCE parameters
            code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
            code_challenge = base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode('utf-8')).digest()
            ).decode('utf-8').rstrip('=')
            
            state = str(uuid.uuid4())
            
            # Save both state and code_verifier to file for later retrieval
            try:
                with open(f'auth_data_{state}.json', 'w') as f:
                    import json
                    json.dump({
                        'code_verifier': code_verifier,
                        'code_challenge': code_challenge,
                        'state': state
                    }, f)
            except Exception as e:
                st.error(f"Failed to save auth data: {e}")
                return None
            
            # Build authorization URL manually
            auth_params = {
                'client_id': self.client_id,
                'response_type': 'code',
                'redirect_uri': CONFIG['ENTRA_ID']['REDIRECT_URI'],
                'response_mode': 'query',
                'scope': ' '.join(self.scope),
                'state': state,
                'code_challenge': code_challenge,
                'code_challenge_method': 'S256'
            }
            
            auth_url = f"{self.authority}/oauth2/v2.0/authorize?" + urllib.parse.urlencode(auth_params)
            
            return auth_url
        except Exception as e:
            st.error(f"כשל בקבלת URL לאימות: {str(e)}")
            return None
    
    def get_token_from_code(self, auth_code):
        try:
            # Get state from query params
            query_params = st.query_params.to_dict()
            state = query_params.get('state', '')

            if not state:
                st.error("לא נמצא פרמטר state")
                return None
            
            # Read auth data from file
            auth_data = None
            try:
                import json
                import os
                with open(f'auth_data_{state}.json', 'r') as f:
                    auth_data = json.load(f)
                # Clean up the file
                os.remove(f'auth_data_{state}.json')
                st.info("נתוני אימות נשלפו בהצלחה")
            except Exception as e:
                st.error(f"כשל בשליפת נתוני אימות: {e}")
                return None

            if not auth_data or 'code_verifier' not in auth_data:
                st.error("נתוני אימות לא תקינים")
                return None
            
            # Make token request
            token_url = f"{self.authority}/oauth2/v2.0/token"
            
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'code': auth_code,
                'grant_type': 'authorization_code',
                'redirect_uri': CONFIG['ENTRA_ID']['REDIRECT_URI'],
                'code_verifier': auth_data['code_verifier'],
                'scope': ' '.join(self.scope)
            }
            
            st.info("מבצע בקשת Token...")
            response = requests.post(token_url, data=data)
            
            if response.status_code == 200:
                token_data = response.json()
                if 'access_token' in token_data:
                    st.success("Token התקבל בהצלחה!")
                    return token_data
                else:
                    st.error(f"אין access token בתגובה: {token_data}")
            else:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                st.error(f"בקשת Token נכשלה: {response.status_code}")
                st.error(f"פרטי שגיאה: {error_data}")

            return None

        except Exception as e:
            st.error(f"קבלת Token נכשלה: {str(e)}")
            return None
    
    def get_user_info(self, access_token):
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get('https://graph.microsoft.com/v1.0/me', headers=headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                st.error(f"כשל בקבלת פרטי משתמש: {response.status_code}")
                return None
        except Exception as e:
            st.error(f"שגיאה בקבלת פרטי משתמש: {str(e)}")
            return None
    
    def get_user_groups(self, access_token):
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get(
                'https://graph.microsoft.com/v1.0/me/memberOf?$select=displayName,id',
                headers=headers
            )
            
            if response.status_code == 200:
                groups_data = response.json()
                groups = []
                
                for group in groups_data.get('value', []):
                    if group.get('@odata.type') == '#microsoft.graph.group':
                        groups.append({
                            'displayName': group.get('displayName', ''),
                            'id': group.get('id', '')
                        })
                return groups
            else:
                st.warning(f"לא ניתן לשלוף קבוצות משתמש: {response.status_code}")
                return []
        except Exception as e:
            st.warning(f"כשל בקבלת קבוצות משתמש: {str(e)}")
            return []
    
    def check_group_membership(self, user_groups, required_groups):
        if not CONFIG['ACCESS_CONTROL']['ENABLE_GROUP_RESTRICTION']:
            return True
        if not required_groups:
            return True
        
        user_group_names = [group['displayName'] for group in user_groups]
        user_group_ids = [group['id'] for group in user_groups]
        
        for required_group in required_groups:
            if required_group in user_group_names or required_group in user_group_ids:
                return True
        return False
    
class SafeQAPI:
    def __init__(self):
        self.server_url = CONFIG['SERVER_URL'].rstrip('/')
        self.api_key = CONFIG['API_KEY']
        self.headers = {
            'X-Api-Key': self.api_key,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
    
    def test_connection(self):
        try:
            url = f"{self.server_url}/api/v1/groups"
            response = requests.get(url, headers=self.headers, verify=False, timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def get_users(self, provider_id, max_records=50):
        try:
            url = f"{self.server_url}/api/v1/users/all"
            params = {'providerid': provider_id, 'maxrecords': max_records}
            response = requests.get(url, headers=self.headers, params=params, verify=False, timeout=30)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    # הנתונים מגיעים בפורמט {'items': [...]}
                    if isinstance(data, dict) and 'items' in data:
                        return data['items']  # מחזיר את רשימת המשתמשים
                    elif isinstance(data, list):
                        return data  # אם זה כבר רשימה
                    else:
                        st.error(f"פורמט תגובה לא צפוי: {type(data)}")
                        return []
                        
                except json.JSONDecodeError as e:
                    st.error(f"תגובת JSON לא תקינה: {str(e)}")
                    return []
            else:
                st.error(f"שגיאה: HTTP {response.status_code}")
                return []
        except Exception as e:
            st.error(f"שגיאת חיבור: {str(e)}")
            return []
    
    def search_user(self, username, provider_id=None):
        try:
            url = f"{self.server_url}/api/v1/users"
            params = {'username': username}
            if provider_id:
                params['providerid'] = provider_id

            response = requests.get(url, headers=self.headers, params=params, verify=False, timeout=10)
            if response.status_code == 200:
                data = response.json()

                # אם התגובה היא dictionary עם 'items', קח את הפריט הראשון
                if isinstance(data, dict) and 'items' in data and data['items']:
                    return data['items'][0]
                elif isinstance(data, dict):
                    return data  # אם זה כבר משתמש יחיד
                return None
            return None
        except Exception as e:
            st.error(f"שגיאת חיפוש: {str(e)}")
            return None

    def check_pin_exists(self, pin_code, exclude_username=None):
        """
        בודק אם PIN code כבר קיים במערכת

        Args:
            pin_code: קוד PIN לבדיקה
            exclude_username: שם משתמש להחרגה (לעריכת משתמש קיים)

        Returns:
            tuple: (exists: bool, username: str or None)
        """
        if not pin_code or not pin_code.strip():
            return False, None

        try:
            # חיפוש בכל המשתמשים (Local + Entra)
            for provider_id in [CONFIG['PROVIDERS']['LOCAL'], CONFIG['PROVIDERS']['ENTRA']]:
                users = self.get_users(provider_id, max_records=1000)

                for user in users:
                    user_pin = user.get('shortId', '')
                    user_name = user.get('userName') or user.get('username', '')

                    # אם מצאנו PIN זהה
                    if user_pin == pin_code.strip():
                        # אם זה לא המשתמש שאנחנו עורכים
                        if exclude_username is None or user_name != exclude_username:
                            return True, user_name

            return False, None
        except Exception as e:
            st.warning(f"שגיאה בבדיקת PIN: {str(e)}")
            return False, None

    def check_username_exists(self, username, exclude_username=None):
        """
        בדיקה האם שם משתמש כבר קיים במערכת
        exclude_username: שם משתמש להחרגה (למשל בעריכה)
        מחזיר: (קיים, provider_id) או (False, None)
        """
        if not username or not username.strip():
            return False, None

        try:
            # חיפוש בכל המשתמשים (Local + Entra)
            for provider_id in [CONFIG['PROVIDERS']['LOCAL'], CONFIG['PROVIDERS']['ENTRA']]:
                users = self.get_users(provider_id, max_records=1000)

                for user in users:
                    user_name = user.get('userName') or user.get('username', '')

                    # אם מצאנו username זהה
                    if user_name and user_name.strip().lower() == username.strip().lower():
                        # אם זה לא המשתמש שאנחנו עורכים
                        if exclude_username is None or user_name != exclude_username:
                            provider_name = "מקומי" if provider_id == CONFIG['PROVIDERS']['LOCAL'] else "Entra"
                            return True, provider_name

            return False, None
        except Exception as e:
            st.warning(f"שגיאה בבדיקת שם משתמש: {str(e)}")
            return False, None

    def create_user(self, username, provider_id, details):
        try:
            url = f"{self.server_url}/api/v1/users"
            form_data = [('username', username), ('providerid', str(provider_id))]
            
            detail_types = {'fullname': 0, 'email': 1, 'password': 3, 'cardid': 4, 'shortid': 5, 'department': 11}
            
            for key, value in details.items():
                if key in detail_types and value:
                    form_data.append(('detailtype', str(detail_types[key])))
                    form_data.append(('detaildata', str(value)))
            
            import urllib.parse
            data = urllib.parse.urlencode(form_data)
            response = requests.put(url, headers=self.headers, data=data, verify=False, timeout=10)
            return response.status_code == 200
        except Exception as e:
            st.error(f"שגיאה ביצירת משתמש: {str(e)}")
            return False
            
    def update_user_detail(self, username, detail_type, detail_data, provider_id=None):
        """
        עדכון פרט של משתמש
        detail_type: 0=full name, 1=email, 3=password, 4=cardid, 5=shortid, 6=pin, 11=department
        """
        try:
            url = f"{self.server_url}/api/v1/users/{username}"
            
            data = {
                'detailtype': detail_type,
                'detaildata': detail_data
            }
            
            if provider_id:
                data['providerid'] = provider_id
            
            import urllib.parse
            encoded_data = urllib.parse.urlencode(data)
            
            response = requests.post(url, headers=self.headers, data=encoded_data, verify=False, timeout=10)
            
            if response.status_code == 200:
                return True
            else:
                st.error(f"כשל בעדכון משתמש: HTTP {response.status_code}")
                if response.text:
                    try:
                        error_detail = response.json()
                        st.error(f"פרטי שגיאה: {error_detail}")
                    except:
                        st.error(f"פרטי שגיאה: {response.text}")
                return False
        except Exception as e:
            st.error(f"שגיאה בעדכון משתמש: {str(e)}")
            return False

    def delete_user(self, username, provider_id):
        """
        מחיקת משתמש מהמערכת
        """
        try:
            url = f"{self.server_url}/api/v1/users/{username}"
            params = {'providerid': provider_id}

            response = requests.delete(url, headers=self.headers, params=params, verify=False, timeout=10)

            if response.status_code == 200:
                return True
            else:
                st.error(f"כשל במחיקת משתמש: HTTP {response.status_code}")
                if response.text:
                    try:
                        error_detail = response.json()
                        st.error(f"פרטי שגיאה: {error_detail}")
                    except:
                        st.error(f"פרטי שגיאה: {response.text}")
                return False
        except Exception as e:
            st.error(f"שגיאה במחיקת משתמש: {str(e)}")
            return False

    def get_single_user(self, username, provider_id=None):
        """קבלת נתוני משתמש בודד"""
        try:
            url = f"{self.server_url}/api/v1/users"
            params = {'username': username}
            if provider_id:
                params['providerid'] = provider_id
            
            response = requests.get(url, headers=self.headers, params=params, verify=False, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict) and 'items' in data and data['items']:
                    return data['items'][0]
                elif isinstance(data, dict):
                    return data
            return None
        except Exception as e:
            st.error(f"שגיאה בקבלת משתמש: {str(e)}")
            return None
    
    def get_groups(self):
        try:
            url = f"{self.server_url}/api/v1/groups"
            response = requests.get(url, headers=self.headers, verify=False, timeout=10)
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            st.error(f"שגיאת קבוצות: {str(e)}")
            return []
    
    def get_group_members(self, group_id):
        try:
            url = f"{self.server_url}/api/v1/groups/{group_id}/members"
            response = requests.get(url, headers=self.headers, verify=False, timeout=10)
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            st.error(f"שגיאת חברי קבוצה: {str(e)}")
            return []
            
    def add_user_to_group(self, username, group_id):
        try:
            # על פי התיעוד: PUT /users/USERNAME/groups עם groupid בתור parameter
            url = f"{self.server_url}/api/v1/users/{username}/groups"
            
            # שליחת group_id כ-form data
            data = {'groupid': group_id}
            
            import urllib.parse
            encoded_data = urllib.parse.urlencode(data)
            
            response = requests.put(url, headers=self.headers, data=encoded_data, verify=False, timeout=10)
            
            if response.status_code == 200:
                return True
            else:
                st.error(f"כשל בהוספת משתמש לקבוצה: HTTP {response.status_code}")
                if response.text:
                    try:
                        error_detail = response.json()
                        st.error(f"פרטי שגיאה: {error_detail}")
                    except:
                        st.error(f"פרטי שגיאה: {response.text}")
                return False
        except Exception as e:
            st.error(f"שגיאה בהוספת משתמש לקבוצה: {str(e)}")
            return False

    def remove_user_from_group(self, username, group_id):
        """
        הסרת משתמש מקבוצה
        """
        try:
            # על פי התיעוד: DELETE /users/USERNAME/groups עם groupid בתור parameter
            url = f"{self.server_url}/api/v1/users/{username}/groups"

            # שליחת group_id כ-parameter
            params = {'groupid': group_id}

            response = requests.delete(url, headers=self.headers, params=params, verify=False, timeout=10)

            if response.status_code == 200:
                return True
            else:
                st.error(f"כשל בהסרת משתמש מקבוצה: HTTP {response.status_code}")
                if response.text:
                    try:
                        error_detail = response.json()
                        st.error(f"פרטי שגיאה: {error_detail}")
                    except:
                        st.error(f"פרטי שגיאה: {response.text}")
                return False
        except Exception as e:
            st.error(f"שגיאה בהסרת משתמש מקבוצה: {str(e)}")
            return False

    def get_user_groups(self, username):
            try:
                url = f"{self.server_url}/api/v1/users/{username}/groups"
                response = requests.get(url, headers=self.headers, verify=False, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    # אם התגובה היא dictionary עם 'items', קח את הפריטים
                    if isinstance(data, dict) and 'items' in data:
                        return data['items']
                    elif isinstance(data, list):
                        return data
                    else:
                        return []
                elif response.status_code == 404:
                    return []  # User not found or no groups
                else:
                    st.warning(f"כשל בקבלת קבוצות משתמש: HTTP {response.status_code}")
                    return []
            except Exception as e:
                st.warning(f"שגיאה בקבלת קבוצות משתמש: {str(e)}")
                return []

def init_session_state():
    defaults = {
        'logged_in': False, 'username': None, 'user_email': None, 'user_groups': [],
        'access_level': 'user', 'login_time': None, 'auth_method': None, 'session_id': None,
        # Hybrid auth fields
        'entra_username': None, 'local_username': None, 'role': None,
        'local_groups': [], 'allowed_departments': []
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            if key == 'session_id':
                import uuid
                st.session_state[key] = str(uuid.uuid4())
            else:
                st.session_state[key] = value

def is_session_valid():
    if not st.session_state.logged_in or not st.session_state.login_time:
        return False
    session_duration = datetime.now() - st.session_state.login_time
    return session_duration <= timedelta(minutes=CONFIG['SESSION_TIMEOUT'])

def show_access_denied_page():
    st.title("🚫 הגישה נדחתה")

    # הצגת פרטי המשתמש שניסה להתחבר
    if hasattr(st.session_state, 'denied_user_name') and st.session_state.denied_user_name:
        st.warning(f"👤 משתמש: **{st.session_state.denied_user_name}** ({st.session_state.get('denied_user_email', '')})")

    st.error(CONFIG['ACCESS_CONTROL']['DENY_MESSAGE'])
    st.info("**קבוצות SafeQ נדרשות (אחת לפחות):**")
    for group_name, role in CONFIG['ACCESS_CONTROL']['ROLE_MAPPING'].items():
        st.write(f"• {group_name} ({role})")
    st.markdown("---")
    st.write("אם לדעתך זו טעות, פנה למנהל ה-IT שלך.")
    if st.button("🔄 נסה שוב"):
        # ניקוי פרטי המשתמש הנדחה
        if 'denied_user_name' in st.session_state:
            del st.session_state.denied_user_name
        if 'denied_user_email' in st.session_state:
            del st.session_state.denied_user_email
        st.rerun()

def show_login_page():
    st.markdown("""
<div style='text-align: center; margin-bottom: 2rem;'>
    <span style='font-size: 2rem; color: #C41E3A;'>🛡️</span>
    <h1 style='display: inline; color: #2C3E50; margin-left: 10px;'>SafeQ Cloud Manager - Login</h1>
</div>
""", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2, 1])
    
    with col2:
        #st.markdown("### 🔑 Please Login")
        
         # Check if we're on the auth_callback path
        if st.query_params.to_dict().get('path') == '/auth_callback' or '/auth_callback' in str(st.query_params):
            st.info("מעבד אימות...")
            # Force a rerun to process the callback
            st.rerun()
            
        # Handle Entra ID callback
        query_params = st.query_params.to_dict()
        
        # Debug - show what we received
        #if query_params:
        #    st.write("Debug - Query params:", query_params)
        
        if 'code' in query_params and CONFIG['USE_ENTRA_ID']:
            auth_code = query_params['code']
            entra_auth = EntraIDAuth()
            logger = AuditLogger()

            st.success("קוד אימות התקבל! מעבד...")

            with st.spinner("מתחבר ל-Entra ID..."):
                token_result = entra_auth.get_token_from_code(auth_code)

                if token_result and 'access_token' in token_result:
                    user_info = entra_auth.get_user_info(token_result['access_token'])

                    if user_info:
                        # הצגת פרטי המשתמש שהתחבר
                        user_display_name = user_info.get('displayName', 'לא ידוע')
                        user_email = user_info['mail'] or user_info['userPrincipalName']
                        st.info(f"👤 משתמש מחובר: **{user_display_name}** ({user_email})")

                        user_groups = entra_auth.get_user_groups(token_result['access_token'])
                        user_groups_names = [g['displayName'] for g in user_groups]
                        
                        logger.log_action(
                            user_info['displayName'], "Login Attempt",
                            f"Entra ID - Groups: {', '.join(user_groups_names)}",
                            user_email, ', '.join(user_groups_names), True
                        )

                        # בדיקת שייכות לאחת מקבוצות SafeQ (ROLE_MAPPING)
                        required_groups = list(CONFIG['ACCESS_CONTROL']['ROLE_MAPPING'].keys())
                        if entra_auth.check_group_membership(user_groups, required_groups):
                            # Initialize hybrid authentication & permissions
                            with st.spinner("מאמת הרשאות..."):
                                api = SafeQAPI()
                                perm_result = initialize_user_permissions(api, user_info, user_groups, CONFIG)

                            # בדיקה אם אתחול ההרשאות הצליח
                            if not perm_result['success']:
                                st.error(f"❌ אימות הרשאות נכשל עבור **{user_display_name}**")
                                st.error(perm_result['error_message'])

                                logger.log_action(
                                    user_info['displayName'], "Permission Check Failed",
                                    perm_result['error_message'],
                                    user_email, ', '.join(user_groups_names), False
                                )

                                # הצג הוראות למשתמש
                                st.info(f"💡 אנא וודא שקיים משתמש לוקאלי תואם במערכת SafeQ עם שם המשתמש: **{user_display_name}**")

                                # לא ממשיכים - לא מבצעים login
                                st.stop()

                            # הרשאות אושרו - עדכון session_state
                            st.session_state.logged_in = True
                            st.session_state.username = user_info['displayName']
                            st.session_state.user_email = user_email
                            st.session_state.user_groups = user_groups

                            # הוספת שדות הרשאות חדשים
                            st.session_state.entra_username = perm_result['entra_username']
                            st.session_state.local_username = perm_result['local_username']
                            st.session_state.role = perm_result['role']
                            st.session_state.local_groups = perm_result['local_groups']
                            st.session_state.allowed_departments = perm_result['allowed_departments']

                            # Backward compatibility
                            st.session_state.access_level = perm_result['role']

                            st.session_state.login_time = datetime.now()
                            st.session_state.auth_method = 'entra_id'

                            # Clean up auth session data
                            for key in ['auth_flow', 'auth_state', 'code_verifier']:
                                if key in st.session_state:
                                    del st.session_state[key]

                            # הצגת מידע על ההרשאות שהתקבלו
                            role_display = {
                                'viewer': 'צופה',
                                'support': 'תמיכה',
                                'admin': 'מנהל',
                                'superadmin': 'מנהל על'
                            }.get(perm_result['role'], perm_result['role'])

                            dept_display = "כל המחלקות" if perm_result['allowed_departments'] == ["ALL"] else f"{len(perm_result['allowed_departments'])} מחלקות"

                            logger.log_action(
                                st.session_state.username, "Login Success",
                                f"Entra ID - Role: {role_display}, Local User: {perm_result['local_username']}, Departments: {dept_display}",
                                st.session_state.user_email, ', '.join(user_groups_names),
                                True, st.session_state.access_level
                            )

                            # Clear the URL parameters
                            st.query_params.clear()

                            st.success(f"ברוך הבא, {st.session_state.username}!")
                            st.info(f"🔐 רמת הרשאה: {role_display} | 📁 הרשאות: {dept_display}")
                            st.balloons()
                            st.rerun()
                        else:
                            logger.log_action(
                                user_info['displayName'], "Access Denied",
                                f"Not in required groups. User groups: {', '.join(user_groups_names)}",
                                user_email, ', '.join(user_groups_names), False
                            )
                            st.session_state.access_denied = True
                            st.session_state.denied_user_name = user_display_name
                            st.session_state.denied_user_email = user_email
                            st.query_params.clear()
                            st.rerun()
                    else:
                        st.error("כשל בקבלת מידע על המשתמש")
                else:
                    st.error("האימות נכשל - לא התקבל access token")
        
        # Check access denied
        if hasattr(st.session_state, 'access_denied') and st.session_state.access_denied:
            show_access_denied_page()
            return
        
         # Main Entra ID Login
        if CONFIG['USE_ENTRA_ID']:
            st.markdown("#### 🌐 התחברות ארגונית")

            entra_auth = EntraIDAuth()
            auth_url = entra_auth.get_auth_url()

        if auth_url:
            # כפתור התחברות Entra ID - link HTML פשוט
            st.markdown(f"""
                <a href="{auth_url}" target="_top" style="
                    display: inline-block;
                    width: 100%;
                    padding: 0.75rem 1.5rem;
                    background: linear-gradient(135deg, #0078d4 0%, #005a9e 100%);
                    color: white !important;
                    text-align: center;
                    text-decoration: none;
                    border-radius: 0.5rem;
                    font-weight: 600;
                    font-size: 1rem;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                ">
                    🔒 התחבר עם Entra ID
                </a>
                <style>
                a[href]:hover {{
                    background: linear-gradient(135deg, #005a9e 0%, #0078d4 100%) !important;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.2) !important;
                    transform: translateY(-1px) !important;
                    color: white !important;
                }}
                </style>
            """, unsafe_allow_html=True)

        # Emergency Admin Login - מוסתר בתוך expander
        with st.expander("🔑 התחברות מנהל מקומי"):
            #st.markdown("#### 🔑 Local Admin Login")
            with st.form("local_login_form"):
                username = st.text_input("👤 שם משתמש")
                card_id = st.text_input("🔐 סיסמא", type="password", help="הזן את הסיסמא שהוגדרה במערכת")
                login_button = st.form_submit_button("🚀 התחבר", use_container_width=True)

            if login_button:
                if not username or not card_id:
                    st.error("❌ אנא הזן שם משתמש וסיסמא")
                else:
                    logger = AuditLogger()

                    # בדיקה אם יש משתמשי חירום מוגדרים
                    local_users = CONFIG.get('LOCAL_USERS')
                    if not local_users:
                        st.error("❌ אין משתמשי חירום מוגדרים במערכת")

                        # Debug info למשתמש
                        with st.expander("🔍 מידע לדיבוג (לחץ לפרטים)"):
                            st.write("**בדיקת משתני סביבה:**")
                            import os

                            # בדיקה מפורטת של כל משתנה
                            emergency_vars = {}
                            for k in os.environ.keys():
                                if k.startswith('EMERGENCY_USER_'):
                                    value = os.environ.get(k, '')
                                    value_len = len(value)
                                    stripped = value.strip() if value else ''

                                    # בדוק אם יש גרשיים
                                    has_quotes = (stripped.startswith('"') and stripped.endswith('"')) or \
                                                (stripped.startswith("'") and stripped.endswith("'"))

                                    # הסר גרשיים לבדיקה
                                    cleaned = stripped
                                    if has_quotes and len(stripped) >= 2:
                                        cleaned = stripped[1:-1]

                                    is_empty = not cleaned

                                    emergency_vars[k] = {
                                        'length': value_len,
                                        'cleaned_length': len(cleaned),
                                        'is_empty': is_empty,
                                        'has_quotes': has_quotes,
                                        'first_char': value[0] if value else 'N/A',
                                        'has_whitespace': value != value.strip() if value else False
                                    }

                            if emergency_vars:
                                st.success(f"✅ נמצאו {len(emergency_vars)} משתני EMERGENCY_USER_*")

                                for var_name, details in emergency_vars.items():
                                    username = var_name.replace('EMERGENCY_USER_', '')
                                    if details['is_empty']:
                                        st.error(f"❌ **{var_name}** - הערך ריק אחרי ניקוי!")
                                    elif details['length'] == 0:
                                        st.error(f"❌ **{var_name}** - אורך 0")
                                    else:
                                        if details['has_quotes']:
                                            st.warning(f"⚠️ **{var_name}** - אורך: {details['length']} תווים (כולל גרשיים)")
                                            st.info(f"   אחרי הסרת גרשיים: {details['cleaned_length']} תווים")
                                        else:
                                            st.success(f"✅ **{var_name}** - אורך: {details['length']} תווים")

                                        if details['has_whitespace']:
                                            st.warning(f"⚠️ יש רווחים בהתחלה/סוף (יוסרו אוטומטית)")

                                st.write("**מה שהתקבל ב-CONFIG['LOCAL_USERS']:**")
                                st.json(CONFIG.get('LOCAL_USERS') or {})
                            else:
                                st.warning("⚠️ לא נמצאו משתני EMERGENCY_USER_* ב-environment")
                                st.write("משתני סביבה שמכילים 'EMERGENCY':")
                                all_emergency = [k for k in os.environ.keys() if 'EMERGENCY' in k.upper()]
                                if all_emergency:
                                    st.code('\n'.join(all_emergency))
                                else:
                                    st.error("אף משתנה לא מכיל 'EMERGENCY'")

                            st.write("**פורמט נכון ב-Railway:**")
                            st.code("""EMERGENCY_USER_admin=YourPassword123
EMERGENCY_USER_backup=AnotherPassword456""")

                        st.info("💡 הוסף משתני סביבה ב-Railway: Variables → הוסף EMERGENCY_USER_admin ו-EMERGENCY_USER_backup")
                        st.stop()

                    # מקרה 1: משתמש חירום (Emergency User) = SuperAdmin (גישה מלאה)
                    # בודקים אם המשתמש קיים ב-EMERGENCY_USERS (מאומת מול secrets.toml בלבד)
                    if username in local_users:
                        # משתמש חירום - אימות מקומי בלבד (לא מול הענן)
                        if CONFIG['LOCAL_USERS'][username] != card_id:
                            logger.log_action(username, "Login Failed", "Invalid emergency user credentials", "", "", False)
                            st.error("❌ שם משתמש או מזהה כרטיס שגויים")
                            st.stop()

                        # אימות הצליח - משתמש חירום
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.session_state.user_email = f"{username}@local"
                        st.session_state.user_groups = []
                        st.session_state.access_level = 'superadmin'
                        st.session_state.login_time = datetime.now()
                        st.session_state.auth_method = 'local'

                        # שדות hybrid auth - משתמש חירום מקבל גישה לכל
                        st.session_state.role = 'superadmin'
                        st.session_state.allowed_departments = ["ALL"]
                        st.session_state.local_username = username
                        st.session_state.entra_username = None
                        st.session_state.local_groups = []

                        logger.log_action(username, "Login Success", "Emergency user local auth",
                                        st.session_state.user_email, "SuperAdmin", True, 'superadmin')
                        st.success(f"✅ ברוך הבא, {username}!")
                        st.rerun()

                    # מקרה 2: משתמש מקומי אחר - אימות מול הענן
                    else:
                        from permissions import authenticate_local_cloud_user

                        with st.spinner(f"מאמת את המשתמש '{username}' מול הענן..."):
                            api = SafeQAPI()
                            auth_result = authenticate_local_cloud_user(api, username, card_id, CONFIG)

                        if not auth_result['success']:
                            # אימות נכשל
                            logger.log_action(username, "Login Failed", auth_result['error_message'],
                                            "", "", False)
                            st.error(auth_result['error_message'])
                            st.stop()

                        # אימות הצליח - משתמש school_manager
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.session_state.user_email = f"{username}@local"
                        st.session_state.user_groups = auth_result['user_groups']
                        st.session_state.access_level = 'school_manager'
                        st.session_state.login_time = datetime.now()
                        st.session_state.auth_method = 'local_cloud'

                        # שדות hybrid auth - school_manager עם departments מסוננים
                        st.session_state.role = auth_result['role']
                        st.session_state.allowed_departments = auth_result['allowed_departments']
                        st.session_state.local_username = username
                        st.session_state.entra_username = None
                        st.session_state.local_groups = auth_result['user_groups']

                        # הצגת בתי הספר המורשים
                        schools_display = ', '.join(auth_result['allowed_departments'][:3])
                        if len(auth_result['allowed_departments']) > 3:
                            schools_display += f" (+{len(auth_result['allowed_departments']) - 3} נוספים)"

                        logger.log_action(username, "Login Success", f"School manager auth - {schools_display}",
                                        st.session_state.user_email, "School Manager", True, 'school_manager')

                        st.success(f"✅ ברוך הבא, {username}!")
                        st.info(f"🏫 בתי ספר מורשים: {schools_display}")
                        st.rerun()
        
        # Access info
        with st.expander("ℹ️ מידע על הרשאות"):
            if CONFIG['ACCESS_CONTROL']['ENABLE_GROUP_RESTRICTION']:
                st.info("**קבוצות SafeQ נדרשות (אחת לפחות):**")
                for group_name, role in CONFIG['ACCESS_CONTROL']['ROLE_MAPPING'].items():
                    st.write(f"• {group_name} ({role})")
            else:
                st.info("כל משתמשי הארגון יכולים לגשת לאפליקציה זו")

def show_header():
    # Header with logos - מותאם לעברית RTL
    col1, col2, col3, col4 = st.columns([2, 1, 6, 1.6])

    with col1:
        # כפתורים בצד ימין (בגלל RTL)
        # כפתור יציאה
        if st.button("🚪 יציאה", key="logout_btn"):
            logger = AuditLogger()
            logger.log_action(
                st.session_state.username, "Logout",
                f"Session ended ({st.session_state.auth_method})",
                st.session_state.user_email,
                ', '.join([g['displayName'] for g in st.session_state.user_groups]) if st.session_state.user_groups else "",
                True, st.session_state.access_level
            )

            # נקה הכל
            for key in list(st.session_state.keys()):
                del st.session_state[key]

            st.rerun()

        # כפתור ניקוי נתונים
        if st.button("🔄 ניקוי נתונים", key="refresh_page"):
            keys_to_keep = ['logged_in', 'username', 'user_email', 'user_groups', 'access_level',
                            'login_time', 'auth_method', 'session_id',
                            # Hybrid auth fields
                            'entra_username', 'local_username', 'role', 'local_groups', 'allowed_departments']

            for key in list(st.session_state.keys()):
                if key not in keys_to_keep:
                    del st.session_state[key]

            # מונה לאיפוס טפסים
            st.session_state.form_reset_key = datetime.now().timestamp()

            st.success("כל הנתונים נוקו!")
            st.rerun()

    # col2 ריקה

    with col3:
        st.title("מנהל הענן של SafeQ")

    with col4:
        # לוגו של החברה בצד שמאל (בגלל RTL)
        try:
            logo_path = resource_path("assets/MafilIT_Logo.png")
            st.image(logo_path, width=250)
        except Exception as e:
            pass

def show_audit_dashboard():
    st.header("📊 דשבורד ביקורת")
    
    if st.session_state.access_level != 'admin':
        st.warning("👤 באפשרותך לצפות רק בלוגי הפעילות שלך")
    
    logger = AuditLogger()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.session_state.access_level == 'admin':
            filter_username = st.text_input("סינון לפי שם משתמש")
        else:
            filter_username = st.session_state.username
            st.text_input("שם משתמש", value=filter_username, disabled=True)
    
    with col2:
        filter_date_from = st.date_input("מתאריך")
    
    with col3:
        filter_date_to = st.date_input("עד תאריך")
    
    with col4:
        log_limit = st.number_input("רשומות", min_value=10, max_value=1000, value=100)
    
    if st.button("🔍 טען לוגי ביקורת", key="load_audit_logs_btn"):
        try:
            conn = sqlite3.connect(logger.db_path)
            cursor = conn.cursor()
            
            query = "SELECT * FROM audit_logs WHERE 1=1"
            params = []
            
            if st.session_state.access_level != 'admin':
                query += " AND username = ?"
                params.append(st.session_state.username)
            elif filter_username:
                query += " AND username LIKE ?"
                params.append(f"%{filter_username}%")
            
            if filter_date_from:
                query += " AND timestamp >= ?"
                params.append(filter_date_from.isoformat())
            
            if filter_date_to:
                query += " AND timestamp <= ?"
                params.append(filter_date_to.isoformat())
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(log_limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            if rows:
                columns = ['id', 'timestamp', 'username', 'user_email', 'user_groups', 
                          'action', 'details', 'session_id', 'success', 'access_level']
                
                df = pd.DataFrame(rows, columns=columns)
                df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
                
                display_cols = ['timestamp', 'username', 'user_email', 'user_groups', 
                               'action', 'details', 'success', 'access_level']
                
                df_display = df[display_cols].copy()
                df_display.rename(columns={
                    'timestamp': 'חותמת זמן', 'username': 'שם משתמש', 'user_email': 'אימייל',
                    'user_groups': 'קבוצות', 'action': 'פעולה', 'details': 'פרטים',
                    'success': 'הצלחה', 'access_level': 'רמת גישה'
                }, inplace=True)

                st.dataframe(df_display, use_container_width=True)
                
                csv = df.to_csv(index=False)
                st.download_button(
                    "💾 הורד CSV", csv.encode('utf-8-sig'),
                    f"audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", "text/csv"
                )
                st.success(f"✅ נטענו {len(rows)} רשומות")
            else:
                st.warning("לא נמצאו רשומות")
            
            conn.close()
        except Exception as e:
            st.error(f"כשל בטעינת לוגים: {str(e)}")

def check_config():
    if CONFIG['SERVER_URL'] == 'https://your-server.com:7300':
        st.error("⚠️ SERVER_URL לא מוגדר!")
        return False
    if CONFIG['API_KEY'] == 'YOUR_API_KEY_HERE':
        st.error("⚠️ API_KEY לא מוגדר!")
        return False
    if CONFIG['USE_ENTRA_ID'] and CONFIG['ENTRA_ID']['CLIENT_ID'] == 'your-app-client-id':
        st.warning("⚠️ Entra ID לא מוגדר - משתמש באימות מקומי בלבד")
        CONFIG['USE_ENTRA_ID'] = False
    return True

def apply_modern_styling(rtl=False):
    rtl_css = ""
    if rtl:
        rtl_css = """
        .stApp {
            direction: rtl;
        }
        /* יישור כללי לימין */
        .block-container {
            text-align: right;
            margin-left: auto;
            margin-right: 0;
        }
         /* יישור פלטים של טפסים */
        input, textarea, select {
            text-align: right !important;
            direction: rtl;
        }
        /* Make sure text aligns to the right */
        div, p, span, h1, h2, h3, h4, h5, h6, label, .stDataFrame {
            text-align: right !important;
        }
        /* Except for elements that should be centered */
        h1 {
            text-align: center !important;
        }
        /* Align tabs to the right */
        .stTabs [data-baseweb="tab-list"] {
            justify-content: flex-start;
        }
        /* Fix sidebar alignment */
        .css-1d391kg div, .css-1d391kg label {
            text-align: right !important;
        }
        /* Fix dataframe header text alignment */
        .stDataFrame th {
            text-align: right !important;
        }
        /* Fix logout button position which is inside a column */
        [data-testid="stHorizontalBlock"] {
            flex-direction: row-reverse;
        }

        /* תיקון סיידבר - צריך להיות בצד ימין ולהיסגר ימינה */
        [data-testid="stSidebar"] {
            right: 0 !important;
            left: auto !important;
        }

        [data-testid="stSidebar"][aria-expanded="true"] {
            transform: translateX(0) !important;
        }

        [data-testid="stSidebar"][aria-expanded="false"] {
            transform: translateX(100%) !important;
        }

        /* תיקון כפתור הסגירה של הסיידבר */
        [data-testid="collapsedControl"] {
            right: 0 !important;
            left: auto !important;
        }

        /* תיקון הודעות להיות מיושרות לימין */
        .stAlert, .stSuccess, .stError, .stWarning, .stInfo {
            text-align: right !important;
            direction: rtl !important;
        }
        """

    st.markdown(f"""
    <style>
    /* צבעי החברה על בסיס הלוגו */
    :root {{
        --mafil-red: #C41E3A;
        --mafil-blue: #4A90E2;
        --mafil-light-gray: #F5F6FA;
        --mafil-dark-gray: #2C3E50;
    }}
    
    {rtl_css}

    /* רקע כללי */
    .stApp {{
        background: #F5F6FF;
        color: #2C3E50;
    }}
    
    /* כותרת ראשית */
    h1 {{
        background: linear-gradient(800deg, var(--mafil-red));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: bold;
        text-align: center;
        margin-bottom: 2rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }}
    
    /* טאבים */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        background: rgba(255, 255, 255, 0.1);
        padding: 1rem;
        border-radius: 15px;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
    }}
    
    .stTabs [data-baseweb="tab"] {{
        height: 50px;
        padding: 10px 20px;
        background: rgba(255, 255, 255, 0.9);
        border-radius: 25px;
        color: var(--mafil-dark-gray);
        border: 2px solid transparent;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }}
    
    .stTabs [data-baseweb="tab"]:hover {{
        background: var(--mafil-red);
        color: white;
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(196, 30, 58, 0.3);
    }}
    
    .stTabs [aria-selected="true"] {{
        background: var(--mafil-blue);
        color: white !important;
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(196, 30, 58, 0.3);
    }}
    
    /* כפתורים */
    .stButton > button {{
        background: linear-gradient(45deg, var(--mafil-red), #FF6B6B);
        color: white;
        border: none;
        border-radius: 25px;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(196, 30, 58, 0.3);
        position: relative;
        overflow: hidden;
    }}
    
    .stButton > button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(196, 30, 58, 0.4);
    }}
    
    .stButton > button:before {{
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
        transition: left 0.5s;
    }}
    
    .stButton > button:hover:before {{
        left: 100%;
    }}
    
    /* כפתור ראשי */
    .stButton > button[kind="primary"] {{
        background: linear-gradient(45deg, var(--mafil-blue), #4ECDC4);
        box-shadow: 0 1px 15px rgba(74, 144, 226, 0.3);
    }}
    
    /* קלטים */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > div,
    .stNumberInput > div > div > input {{
        border-radius: 15px;
        border: 1px solid rgba(196, 30, 58, 0.2);
        background: rgba(0, 255, 255, 0.9);
        transition: all 0.3s ease;
    }}
    
    .stTextInput > div > div > input:focus,
    .stSelectbox > div > div > div:focus,
    .stNumberInput > div > div > input:focus {{
        border-color: var(--mafil-red);
        box-shadow: 0 0 10px rgba(196, 30, 58, 0.3);
    }}
    
    /* טבלאות */
    .stDataFrame {{
        background: rgba(255, 255, 255, 0.95);
        border-radius: 15px;
        overflow: hidden;
        box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        backdrop-filter: blur(10px);
    }}
    
    /* סייד בר */
    .css-1d391kg {{
        background: linear-gradient(180deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.05) 100%);
        backdrop-filter: blur(10px);
        border-right: 1px solid rgba(255,255,255,0.2);
    }}
    
    /* הודעות הצלחה */
    .stSuccess {{
        background: linear-gradient(45deg, #4ECDC4, #44A08D);
        color: white;
        border-radius: 15px;
        border: none;
        box-shadow: 0 4px 15px rgba(78, 205, 196, 0.3);
    }}
    
    /* הודעות שגיאה */
    .stError {{
        background: linear-gradient(45deg, #FF6B6B, #FF8E53);
        color: white;
        border-radius: 15px;
        border: none;
        box-shadow: 0 4px 15px rgba(255, 107, 107, 0.3);
    }}
    
    /* הודעות מידע */
    .stInfo {{
        background: linear-gradient(45deg, var(--mafil-blue), #667eea);
        color: white;
        border-radius: 15px;
        border: none;
        box-shadow: 0 4px 15px rgba(74, 144, 226, 0.3);
    }}
    
    /* אלמנטים מרחפים */
    .stContainer {{
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 2rem;
        margin: 1rem 0;
        border: 1px solid rgba(255, 255, 255, 0.2);
        box-shadow: 0 8px 25px rgba(0,0,0,0.1);
    }}
    
    /* אנימציות */
    @keyframes fadeInUp {{
        from {{
            opacity: 0;
            transform: translateY(20px);
        }}
        to {{
            opacity: 1;
            transform: translateY(0);
        }}
    }}
    
    .main .block-container {{
        animation: fadeInUp 0.6s ease-out;
    }}
    
    /* מעבר חלק */
    * {{
        transition: all 0.3s ease !important;
    }}
    
    /* גלילה מותאמת אישית */
    ::-webkit-scrollbar {{
        width: 10px;
    }}
    
    ::-webkit-scrollbar-track {{
        background: rgba(255, 255, 255, 0.1);
        border-radius: 10px;
    }}
    
    ::-webkit-scrollbar-thumb {{
        background: linear-gradient(45deg, var(--mafil-red), var(--mafil-blue));
        border-radius: 10px;
    }}
    
    ::-webkit-scrollbar-thumb:hover {{
        background: linear-gradient(45deg, #FF6B6B, #4ECDC4);
    }}
    
    /* לוגו מקום */
    .logo-container {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 2rem;
        padding: 1rem;
        background: rgba(255, 255, 255, 0.1);
        border-radius: 15px;
        backdrop-filter: blur(10px);
    }}
    
    /* responsive */
    @media (max-width: 768px) {{
        .stTabs [data-baseweb="tab"] {{
            padding: 8px 12px;
            font-size: 0.9rem;
        }}

        /* תיקון סיידבר במובייל */
        [data-testid="stSidebar"] {{
            width: 100% !important;
            max-width: 100% !important;
            min-width: 100% !important;
        }}

        [data-testid="stSidebar"] > div {{
            width: 100% !important;
            max-width: 100% !important;
        }}

        /* תיקון כפתורים במובייל */
        .stButton > button {{
            width: 100%;
            padding: 0.75rem 1rem;
            font-size: 0.9rem;
        }}

        /* תיקון טקסט ותיבות במובייל */
        .stTextInput > div > div > input,
        .stSelectbox > div > div > div {{
            font-size: 0.9rem;
        }}

        /* תיקון header במובייל */
        [data-testid="stHorizontalBlock"] {{
            flex-direction: column !important;
        }}

        /* תיקון לוגו במובייל */
        img {{
            max-width: 150px !important;
            height: auto !important;
        }}
    }}

    /* תיקון נוסף לסיידבר */
    [data-testid="stSidebar"] {{
        padding: 1rem;
    }}

    [data-testid="stSidebar"] .element-container {{
        width: 100%;
    }}

    [data-testid="stSidebar"] .stButton > button {{
        width: 100%;
        text-align: center;
    }}
    </style>
    """, unsafe_allow_html=True)

    
def main():
    st.set_page_config(
        page_title="SafeQ Cloud Manager",
        page_icon="🔐",
        layout="wide"
    )
    
    init_session_state()

    # Apply styling: RTL if logged in, LTR for login page
    is_logged_in = st.session_state.get('logged_in', False) and is_session_valid()
    apply_modern_styling(rtl=is_logged_in)

    if not is_logged_in:
        if st.session_state.logged_in and not is_session_valid():
            st.warning("⚠️ פג תוקף ההתחברות. אנא התחבר שוב.")
            logger = AuditLogger()
            logger.log_action(st.session_state.username or "Unknown", "Session Expired", "Timeout")
            
            for key in ['logged_in', 'username', 'user_email', 'user_groups', 
                       'access_level', 'login_time', 'auth_method']:
                if key in st.session_state:
                    del st.session_state[key]
        
        show_login_page()
        return

    show_header()
    st.markdown("---")

    if not check_config():
        st.stop()

    api = SafeQAPI()
    logger = AuditLogger()
    
    # Sidebar
    with st.sidebar:
        st.header("🔧 פרטי מערכת")
        st.info(f"🌐 שרת: {CONFIG['SERVER_URL']}")
        
        st.header("👤 פרטי משתמש")
        # הזזת שם המשתמש מהheader לכאן
        auth_text = "🌐 Entra ID" if st.session_state.auth_method == 'entra_id' else "🔑 מקומי"
        st.info(f"🔐 אימות: {auth_text}")

        # שם המשתמש
        role = st.session_state.get('role', st.session_state.access_level)
        role_icons = {
            'viewer': '👁️',
            'support': '🛠️',
            'admin': '👑',
            'superadmin': '⭐'
        }
        access_icon = role_icons.get(role, '👤')

        st.info(f"{access_icon} {st.session_state.username}")
        st.info(f"📧 אימייל: {st.session_state.user_email}")

        # הצגת Role
        role_names = {
            'viewer': '👁️ צופה',
            'support': '🛠️ תמיכה',
            'admin': '👑 מנהל',
            'superadmin': '⭐ מנהל על'
        }
        level_text = role_names.get(role, "👤 משתמש")
        st.info(f"רמה: {level_text}")

        # הצגת משתמש לוקאלי (אם קיים)
        if st.session_state.get('local_username'):
            st.info(f"🏠 משתמש לוקאלי: {st.session_state.local_username}")

        # הצגת הרשאות מחלקות
        if st.session_state.get('allowed_departments'):
            if st.session_state.allowed_departments == ["ALL"]:
                st.success("📁 הרשאות: כל המחלקות")
            else:
                dept_count = len(st.session_state.allowed_departments)
                st.info(f"📁 מחלקות מורשות: {dept_count}")
                with st.expander("הצג מחלקות"):
                    for dept in st.session_state.allowed_departments:
                        st.write(f"• {dept}")
        
        if st.button("🔍 בדיקת חיבור", key="sidebar_test_connection"):
            with st.spinner("בודק..."):
                if api.test_connection():
                    st.success("✅ החיבור תקין!")
                    logger.log_action(st.session_state.username, "Connection Test", "Success",
                                    st.session_state.user_email, "", True, st.session_state.access_level)
                else:
                    st.error("❌ החיבור נכשל")
                    logger.log_action(st.session_state.username, "Connection Test", "Failed",
                                    st.session_state.user_email, "", False, st.session_state.access_level)
        
        if st.checkbox("📋 פעילות אחרונה"):
            if 'audit_log' in st.session_state and st.session_state.audit_log:
                st.subheader("פעולות אחרונות")
                for log_entry in reversed(st.session_state.audit_log[-5:]):
                    status = "✅" if log_entry['success'] else "❌"
                    st.text(f"{status} {log_entry['action']}")
    
    # Main tabs
    role = st.session_state.get('role', st.session_state.access_level)

    # כולם רואים את אותם tabs, בדיקות הרשאות בתוך כל tab
    if role in ['admin', 'superadmin']:
        tabs = st.tabs(["👥 משתמשים", "✏️ חיפוש ועריכה", "➕ הוספת משתמש", "👨‍👩‍👧‍👦 קבוצות", "📊 ביקורת מלאה"])
    else:
        tabs = st.tabs(["👥 משתמשים", "✏️ חיפוש ועריכה", "➕ הוספת משתמש", "👨‍👩‍👧‍👦 קבוצות", "📊 הפעילות שלי"])

    # Tab 1: Users
    with tabs[0]:
        st.header("רשימת משתמשים")

        # שורה ראשונה: צ'קבוקס מקומיים
        col_check1,  = st.columns([1])
        with col_check1:
            show_local = st.checkbox("משתמשים מקומיים", value=True)

        # רק superadmin יכול לראות משתמשי Entra
        role = st.session_state.get('role', st.session_state.access_level)
        if role == 'superadmin':
            col_check2, = st.columns([1])
            with col_check2:
                show_entra = st.checkbox("משתמשי Entra", value=True)
        else:
            show_entra = False  # אחרים לא רואים Entra בכלל

        # שורה שנייה: משתמשים להצגה וכפתור
        col_num, col_btn = st.columns([2, 2])

        with col_num:
            max_users = st.number_input("משתמשים להצגה", min_value=10, max_value=1000, value=200)

        with col_btn:
            st.write("")  # ריווח לגובה
            load_button = st.button("🔄 טען משתמשים", type="primary", key="load_users_main", use_container_width=True)

        if load_button:
            user_groups_str = ', '.join([g['displayName'] for g in st.session_state.user_groups]) if st.session_state.user_groups else ""
            logger.log_action(
                st.session_state.username, "Load Users",
                f"Local: {show_local}, Entra: {show_entra}, Max: {max_users}",
                st.session_state.user_email, user_groups_str, True, st.session_state.access_level
            )

            all_users = []

            if show_local:
                with st.spinner("טוען משתמשים מקומיים..."):
                    local_users = api.get_users(CONFIG['PROVIDERS']['LOCAL'], max_users)
                    for user in local_users:
                        user['source'] = 'מקומי'
                    all_users.extend(local_users)

            if show_entra:
                with st.spinner("טוען משתמשי Entra..."):
                    entra_users = api.get_users(CONFIG['PROVIDERS']['ENTRA'], max_users)
                    for user in entra_users:
                        user['source'] = 'Entra'
                    all_users.extend(entra_users)

            if all_users:
                # סינון לפי מחלקות מורשות
                allowed_departments = st.session_state.get('allowed_departments', [])
                filtered_users = filter_users_by_departments(all_users, allowed_departments)

                users_before_filter = len(all_users)
                users_after_filter = len(filtered_users)

                if not filtered_users:
                    st.warning(f"לא נמצאו משתמשים במחלקות המורשות (נטענו {users_before_filter} משתמשים, 0 אחרי סינון)")
                    st.info("💡 רק משתמשים מהמחלקות שאליהן אתה שייך יוצגו כאן")
                else:
                    # הצגת מידע על סינון - למעלה מהטבלה
                    if users_after_filter < users_before_filter:
                        st.success(f"✅ מוצגים {users_after_filter} משתמשים מתוך {users_before_filter} (מסוננים לפי מחלקות מורשות)")
                    else:
                        st.success(f"✅ נטענו {users_after_filter} משתמשים")

                    df_data = []
                    for user in filtered_users:
                        if not isinstance(user, dict):
                            st.error(f"פורמט נתוני משתמש לא תקין: {type(user)}")
                            continue

                        department = ""
                        details = user.get('details', [])
                        if isinstance(details, list):
                            for detail in details:
                                if isinstance(detail, dict) and detail.get('detailType') == 11:
                                    department = detail.get('detailData', '')
                                    break

                        pin_code = user.get('shortId', '')

                        df_data.append({
                            'Username': user.get('userName', user.get('username', '')),
                            'Full Name': user.get('fullName', ''),
                            'Email': user.get('email', ''),
                            'PIN Code': pin_code,
                            'Department': user.get('department', department),
                            'Source': user.get('source', ''),
                            'Provider ID': user.get('providerId', '')
                        })

                    df = pd.DataFrame(df_data)
                    df.rename(columns={
                        'Username': 'שם משתמש', 'Full Name': 'שם מלא', 'Email': 'אימייל',
                        'PIN Code': 'קוד PIN', 'Department': 'מחלקה', 'Source': 'מקור',
                        'Provider ID': 'מזהה ספק'
                    }, inplace=True)
                    st.dataframe(df, use_container_width=True)

                    csv = df.to_csv(index=False)
                    st.download_button(
                        "💾 הורד CSV", csv.encode('utf-8-sig'),
                        f"users_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv", "text/csv"
                    )

                    logger.log_action(st.session_state.username, "Users Loaded",
                                    f"Count: {users_before_filter}, Filtered: {users_after_filter}",
                                    st.session_state.user_email, user_groups_str, True, st.session_state.access_level)
            else:
                st.warning("לא נמצאו משתמשים")
    
    # Tab 2: Search & Edit
    with tabs[1]:
        st.header("חיפוש משתמש")

        # שורה ראשונה: מקור (למעלה)
        col_spacer, col_provider = st.columns([4, 2])
        with col_provider:
            # בדיקת הרשאות - רק superadmin יכול לבחור Entra
            role = st.session_state.get('role', st.session_state.access_level)
            if role == 'superadmin':
                provider_options = ["מקומי (12348)", "Entra (12351)"]
                default_index = 0  # ברירת מחדל: מקומי
            else:
                provider_options = ["מקומי (12348)"]
                default_index = 0

            search_provider = st.selectbox("מקור *", provider_options, index=default_index,
                                         help="רק superadmin יכול לבחור Entra" if role != 'superadmin' else None)

        # שורה שנייה: חיפוש לפי ושדות נוספים
        col1, col2 = st.columns([1, 1])
        with col1:
            search_type_map_en_to_he = {
                "Username": "שם משתמש", "Full Name": "שם מלא",
                "Department": "מחלקה", "Email": "אימייל"
            }
        with col2:
            search_type_he_options = list(search_type_map_en_to_he.values())
            search_type_he = st.selectbox("חיפוש לפי", search_type_he_options)

            search_type_map_he_to_en = {v: k for k, v in search_type_map_en_to_he.items()}
            search_type = search_type_map_he_to_en[search_type_he]

            search_term = st.text_input(f"הזן {search_type_he} לחיפוש")
            partial_search = st.checkbox("התאמה חלקית (מכיל)", value=True,
                                       help="מצא את כל המשתמשים המכילים את ערך החיפוש")
        col_spacer, col_provider = st.columns([4, 2])
        with col_provider:
            max_results = st.number_input("תוצאות להצגה", min_value=1, max_value=500, value=200)
        
        if st.button("חפש", key="search_users_btn"):
            if not search_term:
                 st.error("נא להזין ערך לחיפוש")
            elif not search_provider:
                st.error("נא לבחור מקור - שדה זה הינו חובה")
            else:
                provider_id = CONFIG['PROVIDERS']['LOCAL'] if search_provider.startswith("מקומי") else CONFIG['PROVIDERS']['ENTRA']
                
                user_groups_str = ', '.join([g['displayName'] for g in st.session_state.user_groups]) if st.session_state.user_groups else ""
                logger.log_action(st.session_state.username, "Advanced Search", 
                                f"Type: {search_type}, Term: {search_term}, Provider: {search_provider}, Partial: {partial_search}",
                                st.session_state.user_email, user_groups_str, True, st.session_state.access_level)
                
                with st.spinner("מחפש..."):
                    all_users = api.get_users(provider_id, 500)
                    matching_users = []
                    search_lower = search_term.lower()

                    for user in all_users:
                        if not isinstance(user, dict):
                            continue
                            
                        match_found = False
                        user_field = ""
                        
                        if search_type == "Username":
                            user_field = user.get('userName', user.get('username', '')).lower()
                        elif search_type == "Full Name":
                            user_field = user.get('fullName', '').lower()
                        elif search_type == "Department":
                            user_field = user.get('department', '').lower()
                            if not user_field:
                                for detail in user.get('details', []):
                                    if isinstance(detail, dict) and detail.get('detailType') == 11:
                                        user_field = detail.get('detailData', '').lower()
                                        break
                        elif search_type == "Email":
                            user_field = user.get('email', user.get('email', '')).lower()
                            for detail in user.get('details', []):
                                if isinstance(detail, dict) and detail.get('detailType') == 1:
                                    user_field = detail.get('detailData', '').lower()
                                    break
                        
                        if partial_search:
                            match_found = search_lower in user_field if user_field else False
                        else:
                            match_found = search_lower == user_field
                        
                        if match_found:
                            matching_users.append(user)
                            if len(matching_users) >= max_results:
                                break

                    # סינון לפי מחלקות מורשות
                    allowed_departments = st.session_state.get('allowed_departments', [])
                    users_before_filter = len(matching_users)
                    matching_users = filter_users_by_departments(matching_users, allowed_departments)
                    users_after_filter = len(matching_users)

                    if users_after_filter < users_before_filter:
                        st.info(f"🔍 נמצאו {users_before_filter} משתמשים, מוצגים {users_after_filter} (מסוננים לפי מחלקות מורשות)")

                    st.session_state.search_results = matching_users
        
        if 'search_results' in st.session_state:
            matching_users = st.session_state.search_results
            st.success(f"נמצאו {len(matching_users)} משתמשים")
            
            df_data = []
            for user in matching_users:
                username = user.get('userName', user.get('username', ''))
                full_name = user.get('fullName', '')
                email = user.get('email', '')
                
                department = user.get('department', '')
                if not department:
                    for detail in user.get('details', []):
                        if isinstance(detail, dict) and detail.get('detailType') == 11:
                            department = detail.get('detailData', '')
                            break
                
                pin_code = user.get('shortId', '')
                
                df_data.append({
                    'Username': username, 'Full Name': full_name, 'Email': email,
                    'Department': department, 'PIN Code': pin_code, 'Provider ID': user.get('providerId', '')
                })
            
            if df_data:
                df = pd.DataFrame(df_data)
                df.rename(columns={
                    'Username': 'שם משתמש', 'Full Name': 'שם מלא', 'Email': 'אימייל',
                    'Department': 'מחלקה', 'PIN Code': 'קוד PIN', 'Provider ID': 'מזהה ספק'
                }, inplace=True)
                st.dataframe(df, use_container_width=True)
                
                csv = df.to_csv(index=False)
                st.download_button(
                    "הורד CSV", csv.encode('utf-8-sig'),
                    f"search_results_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv", 
                    "text/csv", key="download_search_results"
                )
                
                if st.button("נקה תוצאות", key="clear_search_results"):
                    if 'search_results' in st.session_state:
                        del st.session_state.search_results
                    st.rerun()

                st.markdown("---")
                st.subheader("👤 בחר משתמש לביצוע פעולות")

                # יצירת אפשרויות בחירה עם מידע מלא
                user_options = []
                user_mapping = {}  # מיפוי בין תווית לבין username

                for user_dict in df.to_dict('records'):
                    username = user_dict.get('שם משתמש', '')
                    if not username:
                        continue

                    full_name = user_dict.get('שם מלא', '')
                    department = user_dict.get('מחלקה', '')
                    pin = user_dict.get('קוד PIN', '')

                    # יצירת תווית מפורטת
                    label_parts = [username]
                    if full_name:
                        label_parts.append(f"({full_name})")
                    if department:
                        label_parts.append(f"[{department}]")
                    if pin:
                        label_parts.append(f"PIN: {pin}")

                    label = " • ".join(label_parts)
                    user_options.append(label)
                    user_mapping[label] = username

                if user_options:
                    # אתחול רשימת בחירה ב-session_state
                    if 'selected_users' not in st.session_state:
                        st.session_state.selected_users = []

                    # אתחול counter לרענון widgets
                    if 'user_checkbox_counter' not in st.session_state:
                        st.session_state.user_checkbox_counter = 0

                    # כפתור "בחר הכל" / "נקה בחירה"
                    col_select_all, col_count = st.columns([1, 2])
                    with col_select_all:
                        all_usernames = list(user_mapping.values())
                        if st.session_state.selected_users and len(st.session_state.selected_users) == len(user_options):
                            if st.button("❌ נקה בחירה", key="clear_all_users"):
                                st.session_state.selected_users = []
                                st.session_state.user_checkbox_counter += 1
                                st.rerun()
                        else:
                            if st.button("✅ בחר הכל", key="select_all_users"):
                                st.session_state.selected_users = all_usernames.copy()
                                st.session_state.user_checkbox_counter += 1
                                st.rerun()

                    with col_count:
                        num_selected = len(st.session_state.selected_users)
                        if num_selected > 0:
                            st.info(f"✓ נבחרו {num_selected} משתמשים")

                    # הצגת checkboxes לכל משתמש
                    st.markdown("**בחר משתמשים:**")

                    # תיקון: בנייה מחדש של רשימת בחירה מהצ'קבוקסים
                    temp_selections = []

                    for label in user_options:
                        username = user_mapping[label]
                        is_checked = username in st.session_state.selected_users

                        # תיקון: checkbox עם key דינמי שכולל counter
                        checkbox_result = st.checkbox(label, value=is_checked,
                                                     key=f"user_checkbox_{username}_{st.session_state.user_checkbox_counter}")

                        # אוסף את כל הבחירות
                        if checkbox_result:
                            temp_selections.append(username)

                    # עדכון הסטייט רק אם השתנה משהו
                    if temp_selections != st.session_state.selected_users:
                        st.session_state.selected_users = temp_selections
                        st.rerun()

                    # קביעת משתמש לפעולות בודדות (רק אם נבחר אחד)
                    if len(st.session_state.selected_users) == 1:
                        selected_user_for_actions = st.session_state.selected_users[0]
                        st.success(f"✅ משתמש נבחר: **{selected_user_for_actions}**")
                    elif len(st.session_state.selected_users) > 1:
                        selected_user_for_actions = None  # פעולות bulk
                        st.info(f"🔀 מצב bulk: {len(st.session_state.selected_users)} משתמשים נבחרו")
                    else:
                        selected_user_for_actions = None
                else:
                    selected_user_for_actions = None

                # בדיקה אם נבחרו 2+ משתמשים - מצב bulk
                if len(st.session_state.selected_users) >= 2:
                    st.markdown("---")
                    st.subheader(f"🔀 פעולות קבוצתיות ({len(st.session_state.selected_users)} משתמשים)")

                    role = st.session_state.get('role', st.session_state.access_level)

                    if role == 'viewer':
                        st.info("👁️ צפייה בלבד - אין הרשאת הוספה קבוצתית")
                    else:
                        st.markdown("**➕ הוספה קבוצתית לקבוצה**")

                        # טעינת קבוצות
                        if st.button("📋 טען קבוצות זמינות", key="load_groups_bulk"):
                            with st.spinner("טוען קבוצות..."):
                                available_groups = api.get_groups()
                                if available_groups:
                                    allowed_departments = st.session_state.get('allowed_departments', [])
                                    filtered_groups = filter_groups_by_departments(available_groups, allowed_departments)
                                    group_names = [g.get('groupName') or g.get('name') or str(g) for g in filtered_groups
                                                 if not (g.get('groupName') == "Local Admins" and st.session_state.auth_method != 'local')]
                                    st.session_state.available_groups = group_names
                                    st.success(f"נטענו {len(group_names)} קבוצות מורשות")
                                else:
                                    st.warning("לא נמצאו קבוצות")

                        # בחירת קבוצה
                        if 'available_groups' in st.session_state and st.session_state.available_groups:
                            target_group = st.selectbox("בחר קבוצה להוספה", options=st.session_state.available_groups, key="select_group_bulk")
                        else:
                            target_group = None
                            st.text_input("שם קבוצה", disabled=True, placeholder="לחץ על 'טען קבוצות זמינות' תחילה", key="group_bulk_disabled")

                        # כפתור הוספה bulk
                        if st.button(f"➕ הוסף {len(st.session_state.selected_users)} משתמשים לקבוצה",
                                   key="bulk_add_to_group",
                                   type="primary",
                                   disabled=not target_group):

                            # בדיקה מוקדמת - איזה משתמשים כבר בקבוצה
                            with st.spinner("בודק משתמשים קיימים בקבוצה..."):
                                group_members = api.get_group_members(target_group)
                                existing_usernames = []
                                if group_members:
                                    existing_usernames = [m.get('userName', m.get('username', '')) for m in group_members]

                                # משתמשים שכבר בקבוצה
                                already_in_group = [u for u in st.session_state.selected_users if u in existing_usernames]
                                # משתמשים שצריך להוסיף
                                users_to_add = [u for u in st.session_state.selected_users if u not in existing_usernames]

                            # אתחול משתנים
                            success_count = 0
                            fail_count = 0
                            failed_users = []

                            # הצגת אזהרה אם יש משתמשים שכבר בקבוצה
                            if already_in_group:
                                st.warning(f"⚠️ שים לב: {len(already_in_group)} משתמשים כבר שייכים לקבוצה **{target_group}** ולא יתווספו:")
                                for u in already_in_group:
                                    st.write(f"  • {u}")

                            if not users_to_add:
                                st.info("כל המשתמשים שנבחרו כבר שייכים לקבוצה זו.")
                            else:
                                st.info(f"מוסיף {len(users_to_add)} משתמשים לקבוצה...")

                                progress_bar = st.progress(0)
                                status_text = st.empty()

                                total = len(users_to_add)

                                for idx, username in enumerate(users_to_add):
                                    status_text.text(f"מוסיף {idx + 1}/{total}: {username}...")
                                    progress_bar.progress((idx + 1) / total)

                                    success = api.add_user_to_group(username, target_group)
                                    if success:
                                        success_count += 1
                                    else:
                                        fail_count += 1
                                        failed_users.append(username)

                            # הצגת תוצאות מיד
                            st.markdown("---")
                            st.subheader("📊 סיכום פעולה קבוצתית")

                            col_success, col_fail, col_skip = st.columns(3)
                            with col_success:
                                st.metric("✅ הצלחות", success_count if users_to_add else 0)
                            with col_fail:
                                st.metric("❌ כשלונות", fail_count if users_to_add else 0)
                            with col_skip:
                                st.metric("⏭️ כבר בקבוצה", len(already_in_group))

                            if users_to_add and success_count > 0:
                                st.success(f"✅ {success_count} משתמשים נוספו בהצלחה לקבוצה '{target_group}'")

                            if already_in_group:
                                st.info(f"{len(already_in_group)} משתמשים כבר שייכים לקבוצה ולא התווספו ℹ️")

                            if failed_users:
                                st.error(f"❌ {fail_count} משתמשים נכשלו:")
                                for user in failed_users:
                                    st.write(f"  • {user}")

                            # לוג
                            user_groups_str = ', '.join([g['displayName'] for g in st.session_state.user_groups]) if st.session_state.user_groups else ""
                            logger.log_action(st.session_state.username, "Bulk Add to Group",
                                            f"Added {success_count if users_to_add else 0}/{len(st.session_state.selected_users)} users to {target_group} ({len(already_in_group)} already in group)",
                                            st.session_state.user_email, user_groups_str,
                                            success_count > 0 if users_to_add else False, st.session_state.access_level)

                            # ניקוי בחירה לאחר הצגת התוצאות
                            if st.button("✓ אישור וניקוי בחירה", key="clear_selection_after_bulk", type="primary"):
                                st.session_state.selected_users = []
                                st.rerun()

                # מציאת נתוני משתמש נבחר (לפעולות בודדות)
                elif selected_user_for_actions:

                    selected_user_data = None
                    for user in matching_users:
                        if user.get('userName', user.get('username', '')) == selected_user_for_actions:
                            selected_user_data = user
                            break

                    st.markdown("---")
                    st.subheader("👥 ניהול קבוצות משתמש")

                    # בדיקת הרשאות למשתמש
                    role = st.session_state.get('role', st.session_state.access_level)

                    # Section 1: הצגה והוספה לקבוצות
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown("**➕ הוספה לקבוצה**")
                        # רק support/admin/superadmin יכולים להוסיף לקבוצה
                        if role == 'viewer':
                            st.info("👁️ צפייה בלבד - אין הרשאת הוספה")
                        else:
                            if st.button("📋 טען קבוצות", key="load_groups_for_add_new", help="טען את רשימת הקבוצות הזמינות", disabled=not selected_user_for_actions):
                                with st.spinner("טוען קבוצות..."):
                                    available_groups = api.get_groups()
                                    if available_groups:
                                        # סינון לפי מחלקות מורשות
                                        allowed_departments = st.session_state.get('allowed_departments', [])
                                        filtered_groups = filter_groups_by_departments(available_groups, allowed_departments)

                                        # הסרת "Local Admins" למשתמשים שלא התחברו מקומי
                                        group_names = [g.get('groupName') or g.get('name') or str(g) for g in filtered_groups if not (g.get('groupName') == "Local Admins" and st.session_state.auth_method != 'local')]
                                        st.session_state.available_groups = group_names
                                        st.success(f"נטענו {len(group_names)} קבוצות מורשות")
                                    else:
                                        st.warning("לא נמצאו קבוצות")

                            if 'available_groups' in st.session_state and st.session_state.available_groups:
                                target_group = st.selectbox("בחר קבוצה", options=st.session_state.available_groups, key="select_target_group_new")
                            else:
                                target_group = None
                                st.text_input("שם/מזהה קבוצה", key="target_group_input_new", disabled=True, placeholder="לחץ על 'טען קבוצות' תחילה")

                            if st.button("➕ הוסף לקבוצה", key="add_user_to_group_new", disabled=not selected_user_for_actions or not target_group):
                                # בדיקה אם המשתמש כבר שייך לקבוצה
                                with st.spinner(f"בודק אם {selected_user_for_actions} כבר שייך לקבוצה..."):
                                    user_groups = api.get_user_groups(selected_user_for_actions)
                                    user_group_names = [g.get('groupName') or g.get('name') or str(g) for g in user_groups]

                                    if target_group in user_group_names:
                                        st.warning(f"⚠️ שים לב: המשתמש **{selected_user_for_actions}** כבר שייך לקבוצה **{target_group}**")
                                    else:
                                        with st.spinner(f"מוסיף את {selected_user_for_actions} לקבוצה {target_group}..."):
                                            success = api.add_user_to_group(selected_user_for_actions, target_group)
                                            if success:
                                                st.success(f"✅ המשתמש {selected_user_for_actions} נוסף בהצלחה לקבוצה {target_group}")
                                                # רענון רשימת קבוצות אחרי הוספה
                                                user_groups = api.get_user_groups(selected_user_for_actions)
                                                if user_groups:
                                                    st.session_state.user_groups_display = {
                                                        'username': selected_user_for_actions,
                                                        'groups': user_groups
                                                    }
                                            else:
                                                st.error("❌ ההוספה לקבוצה נכשלה")

                    with col2:
                        st.markdown("**👥 הצגת קבוצות משתמש**")
                        if st.button("🔍 הצג קבוצות", key="get_selected_user_groups_new", disabled=not selected_user_for_actions):
                            with st.spinner(f"טוען קבוצות עבור {selected_user_for_actions}..."):
                                user_groups = api.get_user_groups(selected_user_for_actions)
                                if user_groups:
                                    # שמירה ב-session_state להצגה עם X
                                    st.session_state.user_groups_display = {
                                        'username': selected_user_for_actions,
                                        'groups': user_groups
                                    }
                                    st.rerun()
                                else:
                                    st.warning("לא נמצאו קבוצות עבור משתמש זה")

                        # הצגת קבוצות עם אפשרות הסרה
                        if 'user_groups_display' in st.session_state:
                            display_data = st.session_state.user_groups_display
                            if display_data['username'] == selected_user_for_actions:
                                st.success(f"קבוצות עבור {selected_user_for_actions}:")

                                for group in display_data['groups']:
                                    group_name = group.get('groupName') or group.get('name') or str(group)

                                    # שורה עם X אדום - רק ל-admin ו-superadmin
                                    role = st.session_state.get('role', st.session_state.access_level)
                                    if role in ['admin', 'superadmin']:
                                        col_group, col_remove_btn = st.columns([4, 1])
                                        with col_group:
                                            st.write(f"• {group_name}")
                                        with col_remove_btn:
                                            if st.button("❌", key=f"remove_{selected_user_for_actions}_from_{group_name}",
                                                       help=f"הסר מקבוצה {group_name}"):
                                                # שמירת בקשת הסרה לאימות
                                                st.session_state.remove_from_group_request = {
                                                    'username': selected_user_for_actions,
                                                    'group': group_name
                                                }
                                                st.rerun()
                                    else:
                                        st.write(f"• {group_name}")

                    # אימות הסרה מקבוצה (מחוץ לעמודות, בשורה נפרדת)
                    if 'remove_from_group_request' in st.session_state:
                        request = st.session_state.remove_from_group_request
                        if request['username'] == selected_user_for_actions:
                            st.markdown("---")
                            st.warning(f"⚠️ האם אתה בטוח שברצונך להסיר את **{request['username']}** מהקבוצה **{request['group']}**?")

                            col_spacer1, col_yes, col_no, col_spacer2 = st.columns([1, 2, 2, 1])
                            with col_yes:
                                if st.button("✅ אשר", key="confirm_remove_from_group_yes", type="primary", use_container_width=True):
                                    with st.spinner(f"מסיר את {request['username']} מהקבוצה {request['group']}..."):
                                        success = api.remove_user_from_group(request['username'], request['group'])
                                        if success:
                                            st.success(f"✅ המשתמש הוסר בהצלחה מהקבוצה {request['group']}")

                                            # לוג
                                            user_groups_str = ', '.join([g['displayName'] for g in st.session_state.user_groups]) if st.session_state.user_groups else ""
                                            logger.log_action(st.session_state.username, "Remove User from Group",
                                                            f"Removed {request['username']} from {request['group']}",
                                                            st.session_state.user_email, user_groups_str, True, st.session_state.access_level)

                                            # רענון רשימת קבוצות אחרי הסרה
                                            user_groups = api.get_user_groups(request['username'])
                                            if user_groups:
                                                st.session_state.user_groups_display = {
                                                    'username': request['username'],
                                                    'groups': user_groups
                                                }
                                            else:
                                                if 'user_groups_display' in st.session_state:
                                                    del st.session_state.user_groups_display
                                        else:
                                            st.error("❌ ההסרה מהקבוצה נכשלה")

                                        # ניקוי בקשה
                                        del st.session_state.remove_from_group_request
                                        st.rerun()

                            with col_no:
                                if st.button("❌ ביטול", key="confirm_remove_from_group_no", use_container_width=True):
                                    del st.session_state.remove_from_group_request
                                    st.rerun()

                    # Section 2: עריכה ומחיקה
                    st.markdown("---")
                    st.subheader("🔧 עריכה ומחיקה")

                    col3, col4 = st.columns(2)

                    with col3:
                        st.markdown("**🗑️ מחיקת משתמש**")
                        # רק admin/superadmin יכולים למחוק
                        if role in ['admin', 'superadmin']:
                            if st.button("🗑️ מחק משתמש", key="init_delete_user", type="secondary", disabled=not selected_user_for_actions):
                                st.session_state.delete_user_confirmation = selected_user_for_actions
                                st.rerun()
                        else:
                            st.info("👁️ מוגבל ל-Admin")

                    with col4:
                        st.markdown("**📝 עריכת פרטי משתמש**")
                        # רק support/admin/superadmin יכולים לערוך
                        if role == 'viewer':
                            st.info("👁️ צפייה בלבד - אין הרשאת עריכה")
                        else:
                            if st.button("📝 טען פרטי משתמש", key="load_user_for_edit", disabled=not selected_user_for_actions):
                                if selected_user_data:
                                    st.session_state.user_to_edit = selected_user_data
                                    st.session_state.edit_username = selected_user_for_actions
                                    st.success(f"נטענו הפרטים עבור {selected_user_for_actions}")

                    # אזור אימות מחיקה (מחוץ לעמודות, בשורה נפרדת)
                    if st.session_state.get('delete_user_confirmation') == selected_user_for_actions:
                        st.markdown("---")
                        st.warning(f"⚠️ האם אתה בטוח שברצונך למחוק את המשתמש **{selected_user_for_actions}**?")
                        st.error("⚠️ פעולה זו בלתי הפיכה!")

                        col_spacer1, col_confirm, col_cancel, col_spacer2 = st.columns([1, 2, 2, 1])
                        with col_confirm:
                            if st.button("✅ אשר מחיקה", key="confirm_delete_user", type="primary", use_container_width=True):
                                if selected_user_data:
                                    provider_id = selected_user_data.get('providerId')
                                    with st.spinner(f"מוחק את {selected_user_for_actions}..."):
                                        success = api.delete_user(selected_user_for_actions, provider_id)
                                        if success:
                                            st.success(f"✅ המשתמש {selected_user_for_actions} נמחק בהצלחה")

                                            user_groups_str = ', '.join([g['displayName'] for g in st.session_state.user_groups]) if st.session_state.user_groups else ""
                                            logger.log_action(st.session_state.username, "Delete User",
                                                            f"Deleted: {selected_user_for_actions}, Provider: {provider_id}",
                                                            st.session_state.user_email, user_groups_str, True, st.session_state.access_level)

                                            # ניקוי session state
                                            if 'delete_user_confirmation' in st.session_state:
                                                del st.session_state.delete_user_confirmation
                                            if 'search_results' in st.session_state:
                                                del st.session_state.search_results

                                            # הסרת balloons וזמן המתנה
                                            st.rerun()
                                        else:
                                            st.error("❌ מחיקת המשתמש נכשלה")
                                            logger.log_action(st.session_state.username, "Delete User Failed",
                                                            f"Failed to delete: {selected_user_for_actions}",
                                                            st.session_state.user_email, user_groups_str, False, st.session_state.access_level)

                        with col_cancel:
                            if st.button("❌ ביטול", key="cancel_delete_user", use_container_width=True):
                                if 'delete_user_confirmation' in st.session_state:
                                    del st.session_state.delete_user_confirmation
                                st.rerun()

                if 'user_to_edit' in st.session_state and st.session_state.user_to_edit:
                    st.markdown("---")
                    st.subheader(f"📝 עריכת משתמש: {st.session_state.edit_username}")

                    user_data = st.session_state.user_to_edit
                    current_full_name = user_data.get('fullName', '')
                    current_email = user_data.get('email', '')
                    current_department = user_data.get('department', '')
                    current_pin = user_data.get('shortId', '')
                    current_card_id = next((d.get('detailData', '') for d in user_data.get('details', []) if isinstance(d, dict) and d.get('detailType') == 4), "")

                    # הכנת אפשרויות מחלקה
                    allowed_departments = st.session_state.get('allowed_departments', [])
                    is_superadmin = allowed_departments == ["ALL"]

                    # ניהול מצב הטופס - שמירת ערכים בעת שגיאת ולידציה
                    edit_form_key = f"edit_form_{st.session_state.edit_username}"
                    edit_form_state = st.session_state.get(edit_form_key, {})

                    with st.form(f"edit_user_form_{st.session_state.edit_username}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            new_full_name = st.text_input("שם מלא", value=edit_form_state.get('full_name', current_full_name))
                            new_email = st.text_input("אימייל", value=edit_form_state.get('email', current_email))

                            # שדה Department דינמי - כמו בטאב הוספת משתמש
                            if is_superadmin:
                                new_department = st.text_input("מחלקה", value=edit_form_state.get('department', current_department),
                                                              help="הזן מחלקה בפורמט: עיר - מספר")
                            elif len(allowed_departments) == 1:
                                # מחלקה אחת - disabled
                                new_department = st.text_input("מחלקה", value=allowed_departments[0], disabled=True,
                                                              help="מחלקה קבועה לפי הרשאות")
                            elif len(allowed_departments) > 1:
                                # מספר מחלקות - selectbox
                                # אם המחלקה הנוכחית במורשות, היא תהיה ברירת מחדל
                                default_idx = 0
                                saved_dept = edit_form_state.get('department', current_department)
                                if saved_dept in allowed_departments:
                                    default_idx = allowed_departments.index(saved_dept)
                                elif current_department in allowed_departments:
                                    default_idx = allowed_departments.index(current_department)
                                new_department = st.selectbox("מחלקה", options=allowed_departments,
                                                             index=default_idx,
                                                             help="בחר מחלקה מהרשימה המורשות")
                            else:
                                # אין מחלקות - disabled
                                new_department = st.text_input("מחלקה", value=current_department, disabled=True,
                                                              help="אין הרשאות מחלקה")
                        with col2:
                            new_pin = st.text_input("קוד PIN", value=edit_form_state.get('pin', current_pin))
                            new_card_id = st.text_input("מזהה כרטיס", value=edit_form_state.get('card_id', current_card_id))
                        
                        col_submit, col_cancel = st.columns(2)
                        with col_submit:
                            submit_edit = st.form_submit_button("💾 עדכן משתמש", type="primary")
                        with col_cancel:
                            cancel_edit = st.form_submit_button("❌ ביטול")
                        
                        if cancel_edit:
                            del st.session_state.user_to_edit
                            del st.session_state.edit_username
                            st.rerun()
                        
                        if submit_edit:
                            # שמירת כל הערכים מהטופס ב-session_state
                            st.session_state[edit_form_key] = {
                                'full_name': new_full_name,
                                'email': new_email,
                                'department': new_department,
                                'pin': new_pin,
                                'card_id': new_card_id
                            }

                            # בדיקות validation
                            validation_errors = []

                            # בדיקת אימייל
                            if new_email and new_email != current_email:
                                if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', new_email):
                                    validation_errors.append("❌ כתובת אימייל לא תקינה")

                            # בדיקת PIN כפול
                            if new_pin and new_pin != current_pin:
                                pin_exists, existing_user = api.check_pin_exists(new_pin, exclude_username=st.session_state.edit_username)
                                if pin_exists:
                                    validation_errors.append(f"❌ קוד PIN '{new_pin}' כבר קיים אצל משתמש: {existing_user}")

                            # אם יש שגיאות validation
                            if validation_errors:
                                for error in validation_errors:
                                    st.error(error)
                                st.stop()  # עצור את הביצוע - הערכים כבר נשמרו למעלה
                            else:
                                # אין שגיאות - עדכן משתמש
                                updates_made = 0
                                provider_id = user_data.get('providerId')

                                if new_full_name != current_full_name and api.update_user_detail(st.session_state.edit_username, 0, new_full_name, provider_id): updates_made += 1
                                if new_email != current_email and api.update_user_detail(st.session_state.edit_username, 1, new_email, provider_id): updates_made += 1
                                if new_department != current_department and api.update_user_detail(st.session_state.edit_username, 11, new_department, provider_id): updates_made += 1
                                if new_pin != current_pin and api.update_user_detail(st.session_state.edit_username, 5, new_pin, provider_id): updates_made += 1
                                if new_card_id != current_card_id and api.update_user_detail(st.session_state.edit_username, 4, new_card_id, provider_id): updates_made += 1

                                if updates_made > 0:
                                    st.success(f"עודכנו בהצלחה {updates_made} שדות עבור {st.session_state.edit_username}")
                                    st.balloons()
                                    with st.spinner("העדכון הושלם! רענון בעוד 2 שניות..."):
                                        import time
                                        time.sleep(2)

                                    # ניקוי הטופס והנתונים לאחר הצלחה
                                    if edit_form_key in st.session_state:
                                        del st.session_state[edit_form_key]
                                    del st.session_state.user_to_edit
                                    del st.session_state.edit_username
                                    if 'search_results' in st.session_state:
                                        del st.session_state.search_results
                                    st.rerun()

    # Tab 3: Add User
    with tabs[2]:
        st.header("הוספת משתמש חדש")

        role = st.session_state.get('role', st.session_state.access_level)
        if role not in ['admin', 'superadmin', 'support']:
            st.warning("👁️ רמת ההרשאה שלך (viewer) מאפשרת רק צפייה. יצירת משתמשים חדשים זמינה רק לתמיכה/מנהלים.")
        else:
            # הכנת אפשרויות מחלקה לפני הטופס
            allowed_departments = st.session_state.get('allowed_departments', [])
            local_groups = st.session_state.get('local_groups', [])
            department_options = get_department_options(allowed_departments, local_groups)

            is_superadmin = allowed_departments == ["ALL"]
            has_single_dept = len(department_options) == 1
            has_multiple_depts = len(department_options) > 1

            # ניהול מצב הטופס - שמירת ערכים בעת שגיאת ולידציה
            form_state = st.session_state.get('add_user_form_state', {})

            form_key = st.session_state.get('form_reset_key', 'default')
            with st.form(f"add_user_form_{form_key}", clear_on_submit=False):
                col1, col2 = st.columns(2)

                # עמודה ימנית
                with col2:
                    new_username = st.text_input("שם משתמש *", value=form_state.get('username', ''), help="שם משתמש ייחודי")
                    new_first_name = st.text_input("שם פרטי", value=form_state.get('first_name', ''))
                    new_last_name = st.text_input("שם משפחה", value=form_state.get('last_name', ''))
                    new_email = st.text_input("אימייל", value=form_state.get('email', ''))

                    # שדה Department דינמי
                    if is_superadmin:
                        new_department = st.text_input("מחלקה", value=form_state.get('department', ''), help="הזן מחלקה בפורמט: עיר - מספר (למשל: צפת - 240234)")
                    elif has_single_dept:
                        new_department = st.text_input("מחלקה", value=department_options[0], disabled=True,
                                                      help="מחלקה זו נקבעת אוטומטית לפי ההרשאות שלך")
                    elif has_multiple_depts:
                        default_dept_idx = 0
                        if form_state.get('department') in department_options:
                            default_dept_idx = department_options.index(form_state.get('department'))
                        new_department = st.selectbox("מחלקה *", options=department_options, index=default_dept_idx,
                                                     help="בחר מחלקה מהרשימה המורשות")
                    else:
                        new_department = st.text_input("מחלקה", disabled=True,
                                                      help="לא נמצאו מחלקות זמינות")
                        st.error("⚠️ לא ניתן ליצור משתמש - אין מחלקות מורשות")

                # עמודה שמאלית
                with col1:
                    new_password = st.text_input("סיסמה", type="password", value=form_state.get('password', ''), placeholder="Aa123456",
                                                help="אם לא מוזן - סיסמה ברירת מחדל: Aa123456")
                    new_pin = st.text_input("קוד PIN", value=form_state.get('pin', ''))
                    new_cardid = st.text_input("מזהה כרטיס", value=form_state.get('cardid', ''))

                if st.form_submit_button("➕ צור משתמש", type="primary"):
                    if not new_username:
                        st.error("שם משתמש הוא שדה חובה")
                        st.stop()
                    else:
                        # בדיקות תקינות
                        validation_errors = []

                        # בדיקת username קיים
                        username_exists, provider_name = api.check_username_exists(new_username)
                        if username_exists:
                            validation_errors.append(f"❌ שם המשתמש '{new_username}' כבר קיים במערכת ({provider_name})")

                        # בדיקת אימייל
                        if new_email and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', new_email):
                            validation_errors.append("❌ כתובת אימייל לא תקינה")

                        # בדיקת PIN כפול
                        if new_pin:
                            pin_exists, existing_user = api.check_pin_exists(new_pin)
                            if pin_exists:
                                validation_errors.append(f"❌ קוד PIN '{new_pin}' כבר קיים אצל משתמש: {existing_user}")

                        # אם יש שגיאות validation - שמור ערכים ועצור
                        if validation_errors:
                            # שמירת הערכים רק אחרי שהולידציה נכשלה
                            st.session_state.add_user_form_state = {
                                'username': new_username,
                                'first_name': new_first_name,
                                'last_name': new_last_name,
                                'email': new_email,
                                'department': new_department,
                                'password': new_password,
                                'pin': new_pin,
                                'cardid': new_cardid
                            }
                            for error in validation_errors:
                                st.error(error)
                            st.stop()
                        else:
                            # אין שגיאות - צור משתמש
                            provider_id = CONFIG['PROVIDERS']['LOCAL']
                            details = {
                                'fullname': f"{new_first_name} {new_last_name}".strip(), 'email': new_email,
                                'password': new_password or 'Aa123456', 'department': new_department,
                                'shortid': new_pin, 'cardid': new_cardid
                            }

                            user_groups_str = ', '.join([g['displayName'] for g in st.session_state.user_groups]) if st.session_state.user_groups else ""
                            logger.log_action(st.session_state.username, "Create User Attempt", f"Username: {new_username}, Provider: Local",
                                            st.session_state.user_email, user_groups_str, True, st.session_state.access_level)

                            with st.spinner("יוצר משתמש..."):
                                success = api.create_user(new_username, provider_id, details)
                                if success:
                                    st.success("המשתמש נוצר בהצלחה!")
                                    st.balloons()
                                    # ניקוי הטופס לאחר הצלחה
                                    if 'add_user_form_state' in st.session_state:
                                        del st.session_state.add_user_form_state
                                    # המתנה קצרה כדי לראות את הבלונים והודעת ההצלחה
                                    import time
                                    time.sleep(1.5)
                                    st.rerun()  # רענון הטופס - ינקה את כל השדות
                                else:
                                    st.error("❌ יצירת המשתמש נכשלה")
                                    logger.log_action(st.session_state.username, "User Creation Failed", f"Username: {new_username}",
                                                    st.session_state.user_email, user_groups_str, False, st.session_state.access_level)
    
    # Tab 4: Groups
    with tabs[3]:
        st.header("ניהול קבוצות")

        # שורה עליונה - חיפוש (שמאל) וכפתור (ימין)
        col_search, col_btn = st.columns([2, 1])

        with col_search:
            # חיפוש בקבוצות
            search_term = ""
            if 'available_groups_list' in st.session_state:
                search_term = st.text_input("🔍 חיפוש קבוצות", placeholder="הקלד לחיפוש קבוצות...", key="group_search")
            else:
                # שדה disabled כשאין קבוצות
                st.text_input("🔍 חיפוש קבוצות", placeholder="לחץ על 'טען קבוצות' תחילה", key="group_search_disabled", disabled=True)

        with col_btn:
            st.write("")  # ריווח
            if st.button("🔄 טען קבוצות", key="refresh_groups_btn", use_container_width=True):
                user_groups_str = ', '.join([g['displayName'] for g in st.session_state.user_groups]) if st.session_state.user_groups else ""
                logger.log_action(st.session_state.username, "Load Groups", "",
                                st.session_state.user_email, user_groups_str, True, st.session_state.access_level)
                with st.spinner("טוען קבוצות..."):
                    groups = api.get_groups()
                    if groups:
                        # סינון לפי מחלקות מורשות
                        allowed_departments = st.session_state.get('allowed_departments', [])
                        groups_before_filter = len(groups)
                        filtered_groups = filter_groups_by_departments(groups, allowed_departments)
                        groups_after_filter = len(filtered_groups)

                        st.session_state.available_groups_list = filtered_groups

                        if groups_after_filter < groups_before_filter:
                            st.success(f"נטענו {groups_after_filter} קבוצות מתוך {groups_before_filter} (מסוננות לפי הרשאות)")
                        else:
                            st.success(f"נטענו {groups_after_filter} קבוצות")
                        st.rerun()  # רענון כדי להפעיל את שדה החיפוש
                    else:
                        st.warning("לא נמצאו קבוצות")
        
        # הצגת רשימת קבוצות מסוננת
        if 'available_groups_list' in st.session_state:
            groups_to_show = st.session_state.available_groups_list

            # סינון לפי חיפוש
            if search_term:
                groups_to_show = [
                    group for group in groups_to_show
                    if search_term.lower() in group.get('groupName', group.get('groupId', '')).lower()
                ]

            if groups_to_show:
                # מיון אלפביתי
                groups_to_show = sorted(groups_to_show, key=lambda g: g.get('groupName', '').lower())

                st.subheader(f"📋 בחר קבוצה ({len(groups_to_show)} קבוצות)")

                # תיבה עם רשימה מסודרת
                with st.container():
                    st.markdown("""
                    <style>
                    .stContainer {
                        border: 1px solid #ddd;
                        border-radius: 5px;
                        padding: 10px;
                        max-height: 400px;
                        overflow-y: auto;
                    }
                    </style>
                    """, unsafe_allow_html=True)

                    for group in groups_to_show:
                        group_name = group.get('groupName', group.get('groupId', 'Unknown Group'))

                        # לחיצה על קבוצה טוענת את החברים אוטומטית
                        if st.button(f"👥 {group_name}", key=f"group_btn_{group_name}", use_container_width=True):
                            st.session_state.selected_group_name = group_name

                            # טעינה אוטומטית של חברי הקבוצה
                            with st.spinner(f"טוען חברי '{group_name}'..."):
                                members = api.get_group_members(group_name)
                                if members:
                                    st.session_state.group_members_data = {
                                        'group_name': group_name,
                                        'members': members,
                                        'count': len(members)
                                    }
                                    # איפוס בחירת משתמשים
                                    st.session_state.selected_group_members = []
                                else:
                                    st.session_state.group_members_data = {
                                        'group_name': group_name,
                                        'members': [],
                                        'count': 0
                                    }
                                    st.session_state.selected_group_members = []

                            user_groups_str = ', '.join([g['displayName'] for g in st.session_state.user_groups]) if st.session_state.user_groups else ""
                            logger.log_action(st.session_state.username, "View Group Members", f"Group: {group_name}",
                                            st.session_state.user_email, user_groups_str, True, st.session_state.access_level)
                            st.rerun()

            else:
                st.info("לא נמצאו קבוצות התואמות את קריטריוני החיפוש")
        else:
            st.info("לחץ על 'טען קבוצות' כדי לראות את הקבוצות הזמינות")
        
        # הצגת תוצאות חברי הקבוצה ברוחב מלא
        if 'group_members_data' in st.session_state:
            st.markdown("---")
            group_data = st.session_state.group_members_data
            st.subheader(f"👥 חברי הקבוצה '{group_data['group_name']}' ({group_data['count']} חברים)")

            if group_data['count'] == 0:
                st.info("הקבוצה ריקה")
            else:
                # איתחול רשימת בחירה
                if 'selected_group_members' not in st.session_state:
                    st.session_state.selected_group_members = []

                # אתחול counter לרענון widgets
                if 'group_checkbox_counter' not in st.session_state:
                    st.session_state.group_checkbox_counter = 0

                # כפתור "בחר הכל" / "נקה בחירה"
                role = st.session_state.get('role', st.session_state.access_level)

                # כפתור "בחר הכל" למעלה
                if role not in ['viewer']:  # רק למי שמורשה להסיר
                    all_usernames = [m.get('userName', m.get('username', '')) for m in group_data['members']]

                    if st.session_state.selected_group_members and len(st.session_state.selected_group_members) == len(all_usernames):
                        if st.button("❌ נקה בחירה", key="clear_all_members"):
                            st.session_state.selected_group_members = []
                            st.session_state.group_checkbox_counter += 1
                            st.rerun()
                    else:
                        if st.button("✅ בחר הכל", key="select_all_members"):
                            st.session_state.selected_group_members = all_usernames.copy()
                            st.session_state.group_checkbox_counter += 1
                            st.rerun()

                # טבלה עם checkboxes
                st.markdown("**בחר משתמשים להסרה:**")

                # תיקון: בנייה מחדש של רשימת בחירה מהצ'קבוקסים
                temp_selections = []

                for member in group_data['members']:
                    username = member.get('userName', member.get('username', ''))
                    full_name = member.get('fullName', '')
                    department = member.get('department', '')

                    if not department:
                        for detail in member.get('details', []):
                            if isinstance(detail, dict) and detail.get('detailType') == 11:
                                department = detail.get('detailData', '')
                                break

                    # יצירת תווית
                    label = f"{username}"
                    if full_name:
                        label += f" ({full_name})"
                    if department:
                        label += f" [{department}]"

                    if role not in ['viewer']:  # רק למי שמורשה
                        is_checked = username in st.session_state.selected_group_members

                        # תיקון: checkbox עם key דינמי שכולל counter
                        checkbox_result = st.checkbox(label, value=is_checked,
                                                     key=f"member_checkbox_{username}_{group_data['group_name']}_{st.session_state.group_checkbox_counter}")

                        # אוסף את כל הבחירות
                        if checkbox_result:
                            temp_selections.append(username)
                    else:
                        st.text(f"👁️ {label}")

                # עדכון הסטייט רק אם השתנה משהו
                if role not in ['viewer']:
                    if temp_selections != st.session_state.selected_group_members:
                        st.session_state.selected_group_members = temp_selections
                        st.rerun()

                # מונה וכפתור הסרה למטה
                num_selected = len(st.session_state.selected_group_members)
                if num_selected >= 1:
                    col_count, col_remove = st.columns([1, 1])

                    with col_count:
                        st.info(f"✓ נבחרו {num_selected} משתמשים")

                    with col_remove:
                        if role in ['admin', 'superadmin']:
                            if st.button(f"🗑️ הסר {num_selected} מהקבוצה", key="remove_bulk_from_group", type="secondary"):
                                st.session_state.confirm_bulk_remove = True

                # אימות הסרה - רק אם עדיין לא התחלנו ולא סיימנו
                if st.session_state.get('confirm_bulk_remove', False) and not st.session_state.get('bulk_remove_in_progress', False) and not st.session_state.get('bulk_remove_results'):
                    st.warning(f"⚠️ האם אתה בטוח שברצונך להסיר {num_selected} משתמשים מהקבוצה '{group_data['group_name']}'?")
                    st.error("⚠️ פעולה זו תסיר את המשתמשים מהקבוצה!")

                    # כפתורים מרוכזים יותר
                    col_spacer1, col_yes, col_no, col_spacer2 = st.columns([1, 2, 2, 1])
                    with col_yes:
                        if st.button("✅ אשר הסרה", key="confirm_remove_yes", type="primary", use_container_width=True):
                            st.session_state.bulk_remove_in_progress = True
                            st.session_state.confirm_bulk_remove = False  # ניקוי מיד
                            st.rerun()

                    with col_no:
                        if st.button("❌ ביטול", key="confirm_remove_no", use_container_width=True):
                            st.session_state.confirm_bulk_remove = False
                            st.rerun()

                # ביצוע ההסרה
                if st.session_state.get('bulk_remove_in_progress', False):
                    # יישור לימין עבור עברית
                    col_spacer, col_progress = st.columns([1, 3])
                    with col_progress:
                        progress_bar = st.progress(0)
                        status_text = st.empty()

                    success_count = 0
                    fail_count = 0
                    failed_users = []

                    total = len(st.session_state.selected_group_members)

                    for idx, username in enumerate(st.session_state.selected_group_members):
                        status_text.text(f"מסיר {idx + 1}/{total}: {username}...")
                        progress_bar.progress((idx + 1) / total)

                        success = api.remove_user_from_group(username, group_data['group_name'])
                        if success:
                            success_count += 1
                        else:
                            fail_count += 1
                            failed_users.append(username)

                    # שמירת התוצאות ב-session state
                    st.session_state.bulk_remove_results = {
                        'success_count': success_count,
                        'fail_count': fail_count,
                        'failed_users': failed_users,
                        'total': total,
                        'group_name': group_data['group_name']
                    }

                    # ניקוי הפלאג מיד אחרי הפעולה
                    st.session_state.bulk_remove_in_progress = False

                    # לוג
                    user_groups_str = ', '.join([g['displayName'] for g in st.session_state.user_groups]) if st.session_state.user_groups else ""
                    logger.log_action(st.session_state.username, "Bulk Remove from Group",
                                    f"Removed {success_count}/{total} users from {group_data['group_name']}",
                                    st.session_state.user_email, user_groups_str,
                                    success_count > 0, st.session_state.access_level)

                    st.rerun()

                # הצגת סיכום (אחרי שהפעולה הסתיימה)
                if st.session_state.get('bulk_remove_results'):
                    results = st.session_state.bulk_remove_results

                    st.markdown("---")
                    st.subheader("📊 סיכום הסרה קבוצתית")

                    col_s, col_f = st.columns(2)
                    with col_s:
                        st.metric("✅ הוסרו בהצלחה", results['success_count'])
                    with col_f:
                        st.metric("❌ כשלונות", results['fail_count'])

                    if results['success_count'] > 0:
                        st.success(f"✅ {results['success_count']} משתמשים הוסרו בהצלחה מהקבוצה '{results['group_name']}'")

                    if results['failed_users']:
                        st.error(f"❌ {results['fail_count']} משתמשים נכשלו:")
                        for user in results['failed_users']:
                            st.write(f"  • {user}")

                    # כפתור אישור ורענון
                    if st.button("✓ אישור והמשך", key="confirm_bulk_remove_results", type="primary"):
                        # רענון נתוני הקבוצה תחילה
                        with st.spinner("מרענן את נתוני הקבוצה..."):
                            members = api.get_group_members(results['group_name'])
                            if members is not None:
                                st.session_state.group_members_data = {
                                    'group_name': results['group_name'],
                                    'members': members,
                                    'count': len(members)
                                }

                        # ניקוי מלא של session state
                        st.session_state.selected_group_members = []
                        st.session_state.confirm_bulk_remove = False
                        st.session_state.group_checkbox_counter += 1  # עדכון counter כדי לרענן checkboxes
                        if 'bulk_remove_results' in st.session_state:
                            del st.session_state.bulk_remove_results
                        if 'bulk_remove_in_progress' in st.session_state:
                            del st.session_state.bulk_remove_in_progress

                        st.rerun()

                # כפתור נקה תוצאות
                st.markdown("---")
                if st.button("🗑️ סגור קבוצה", key="clear_group_results"):
                    # ניקוי מלא של כל המצבים הקשורים לקבוצה
                    if 'group_members_data' in st.session_state:
                        del st.session_state.group_members_data
                    if 'selected_group_name' in st.session_state:
                        del st.session_state.selected_group_name
                    if 'selected_group_members' in st.session_state:
                        del st.session_state.selected_group_members
                    if 'confirm_bulk_remove' in st.session_state:
                        del st.session_state.confirm_bulk_remove
                    if 'bulk_remove_in_progress' in st.session_state:
                        del st.session_state.bulk_remove_in_progress
                    if 'bulk_remove_results' in st.session_state:
                        del st.session_state.bulk_remove_results
                    if 'group_checkbox_counter' in st.session_state:
                        del st.session_state.group_checkbox_counter
                    st.rerun()
    
    # Tab 5: Audit
    with tabs[4]:
        show_audit_dashboard()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"שגיאת יישום: {str(e)}")
        st.info("אנא בדוק את ההגדרות ונסה שוב.")
        
        try:
            logger = AuditLogger()
            username = st.session_state.get('username', 'Unknown')
            user_email = st.session_state.get('user_email', '')
            user_groups_str = ', '.join([g['displayName'] for g in st.session_state.get('user_groups', [])])
            access_level = st.session_state.get('access_level', 'unknown')
            
            logger.log_action(username, "Application Error", f"Error: {str(e)}", user_email, user_groups_str, False, access_level)
        except:
            pass
