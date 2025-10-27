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
from datetime import datetime, timedelta
import msal
import sys

# ייבוא config
from config import config

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
    
    def get_user_access_level(self, user_groups):
        admin_groups = CONFIG['ACCESS_CONTROL']['ADMIN_GROUPS']
        if self.check_group_membership(user_groups, admin_groups):
            return 'admin'
        return 'user'

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
        'access_level': 'user', 'login_time': None, 'auth_method': None, 'session_id': None
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
    st.error(CONFIG['ACCESS_CONTROL']['DENY_MESSAGE'])
    st.info("**קבוצות נדרשות:**")
    for group in CONFIG['ACCESS_CONTROL']['AUTHORIZED_GROUPS']:
        st.write(f"• {group}")
    st.markdown("---")
    st.write("אם לדעתך זו טעות, פנה למנהל ה-IT שלך.")
    if st.button("🔄 נסה שוב"):
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
                        user_email = user_info['mail'] or user_info['userPrincipalName']
                        user_groups = entra_auth.get_user_groups(token_result['access_token'])
                        user_groups_names = [g['displayName'] for g in user_groups]
                        
                        logger.log_action(
                            user_info['displayName'], "Login Attempt",
                            f"Entra ID - Groups: {', '.join(user_groups_names)}",
                            user_email, ', '.join(user_groups_names), True
                        )
                        
                        if entra_auth.check_group_membership(user_groups, CONFIG['ACCESS_CONTROL']['AUTHORIZED_GROUPS']):
                            st.session_state.logged_in = True
                            st.session_state.username = user_info['displayName']
                            st.session_state.user_email = user_email
                            st.session_state.user_groups = user_groups
                            st.session_state.access_level = entra_auth.get_user_access_level(user_groups)
                            st.session_state.login_time = datetime.now()
                            st.session_state.auth_method = 'entra_id'
                            # Clean up auth session data
                            for key in ['auth_flow', 'auth_state', 'code_verifier']:
                                if key in st.session_state:
                                    del st.session_state[key]
                            
                            logger.log_action(
                                st.session_state.username, "Login Success",
                                f"Entra ID - Access level: {st.session_state.access_level}",
                                st.session_state.user_email, ', '.join(user_groups_names),
                                True, st.session_state.access_level
                            )
                            
                            # Clear the URL parameters
                            st.query_params.clear()
                            
                            st.success(f"ברוך הבא, {st.session_state.username}!")
                            st.balloons()
                            st.rerun()
                        else:
                            logger.log_action(
                                user_info['displayName'], "Access Denied",
                                f"Not in required groups. User groups: {', '.join(user_groups_names)}",
                                user_email, ', '.join(user_groups_names), False
                            )
                            st.session_state.access_denied = True
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
            st.link_button("🔒 התחבר עם Entra ID", auth_url, type="primary", use_container_width=True)

        # Emergency Admin Login - מוסתר בתוך expander
        with st.expander("🔑 התחברות מנהל מקומי"):
            #st.markdown("#### 🔑 Local Admin Login")
            with st.form("local_login_form"):
                username = st.text_input("👤 שם משתמש")
                password = st.text_input("🔒 סיסמה", type="password")
                login_button = st.form_submit_button("🚀 התחבר", use_container_width=True)
            
            if login_button:
                if not username or not password:
                    st.error("❌ אנא הזן שם משתמש וסיסמה")
                else:
                    import hashlib
                    password_hash = hashlib.sha256(password.encode()).hexdigest()
                    logger = AuditLogger()
                    
                    if username in CONFIG['LOCAL_USERS'] and CONFIG['LOCAL_USERS'][username] == password_hash:
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.session_state.user_email = f"{username}@local"
                        st.session_state.user_groups = []
                        st.session_state.access_level = 'admin'
                        st.session_state.login_time = datetime.now()
                        st.session_state.auth_method = 'local'
                        
                        logger.log_action(username, "Login Success", "Local emergency auth",
                                        st.session_state.user_email, "Emergency Admin", True, 'admin')
                        st.success(f"✅ ברוך הבא, {username}!")
                        st.rerun()
                    else:
                        logger.log_action(username, "Login Failed", "Invalid local credentials", "", "", False)
                        st.error("❌ שם משתמש או סיסמה שגויים")
        
        # Access info
        with st.expander("ℹ️ מידע על הרשאות"):
            if CONFIG['ACCESS_CONTROL']['ENABLE_GROUP_RESTRICTION']:
                st.info("**קבוצות נדרשות:**")
                for group in CONFIG['ACCESS_CONTROL']['AUTHORIZED_GROUPS']:
                    st.write(f"• {group}")
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
                            'login_time', 'auth_method', 'session_id']

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
        background: rgba(255, 255, 255, 0.9);
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
        access_icon = "👑" if st.session_state.access_level == 'admin' else "👤"
        st.info(f"{access_icon} {st.session_state.username}")
        st.info(f"📧 אימייל: {st.session_state.user_email}")
        
        level_text = "👑 מנהל" if st.session_state.access_level == 'admin' else "👤 משתמש"
        st.info(f"רמה: {level_text}")
        
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
    if st.session_state.access_level == 'admin':
        tabs = st.tabs(["👥 משתמשים", "✏️ חיפוש ועריכה", "➕ הוספת משתמש", "👨‍👩‍👧‍👦 קבוצות", "📊 ביקורת מלאה"])
    else:
        tabs = st.tabs(["👥 משתמשים", "✏️ חיפוש ועריכה", "➕ הוספת משתמש", "👨‍👩‍👧‍👦 קבוצות", "📊 הפעילות שלי"])
    
    # Tab 1: Users
    with tabs[0]:
        st.header("רשימת משתמשים")

        # שורה ראשונה: צ'קבוקסים
        col_check1, col_check2 = st.columns([1, 1])

        with col_check1:
            show_local = st.checkbox("משתמשים מקומיים", value=True)

        with col_check2:
            show_entra = st.checkbox("משתמשי Entra", value=True)

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
                df_data = []
                for user in all_users:
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
                
                st.success(f"✅ נטענו {len(all_users)} משתמשים")
                logger.log_action(st.session_state.username, "Users Loaded", f"Count: {len(all_users)}",
                                st.session_state.user_email, user_groups_str, True, st.session_state.access_level)
            else:
                st.warning("לא נמצאו משתמשים")
    
    # Tab 2: Search & Edit
    with tabs[1]:
        st.header("חיפוש משתמש")

        # שורה ראשונה: מקור (למעלה)
        col_spacer, col_provider = st.columns([4, 2])
        with col_provider:
            search_provider = st.selectbox("מקור *", ["", "מקומי (12348)", "Entra (12351)"])

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
            max_results = st.number_input("תוצאות להצגה", min_value=1, max_value=500, value=20)
        
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

                selected_user_for_actions = st.selectbox(
                    "בחר משתמש מתוצאות החיפוש:", 
                    options=[user['שם משתמש'] for user in df.to_dict('records') if user['שם משתמש']],
                    key="selected_user_main",
                    help="המשתמש שייבחר ישמש לכל הפעולות מטה"
                )

                if selected_user_for_actions:
                    st.info(f"משתמש נבחר: **{selected_user_for_actions}**")
                    
                    selected_user_data = None
                    for user in matching_users:
                        if user.get('userName', user.get('username', '')) == selected_user_for_actions:
                            selected_user_data = user
                            break

                    st.markdown("---")
                    st.subheader("🔧 פעולות על משתמש")

                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.markdown("**📝 עריכת פרטי משתמש**")
                        if st.button("📝 טען פרטי משתמש", key="load_user_for_edit", disabled=not selected_user_for_actions):
                            if selected_user_data:
                                st.session_state.user_to_edit = selected_user_data
                                st.session_state.edit_username = selected_user_for_actions
                                st.success(f"נטענו הפרטים עבור {selected_user_for_actions}")

                    with col2:
                        st.markdown("**👥 הצגת קבוצות משתמש**")
                        if st.button("🔍 הצג קבוצות", key="get_selected_user_groups_new", disabled=not selected_user_for_actions):
                            with st.spinner(f"טוען קבוצות עבור {selected_user_for_actions}..."):
                                user_groups = api.get_user_groups(selected_user_for_actions)
                                if user_groups:
                                    st.success(f"קבוצות עבור {selected_user_for_actions}:")
                                    for group in user_groups:
                                        group_name = group.get('groupName') or group.get('name') or str(group)
                                        st.write(f"• {group_name}")
                                else:
                                    st.warning("לא נמצאו קבוצות עבור משתמש זה")

                    with col3:
                        st.markdown("**➕ הוספה לקבוצה**")
                        if st.button("📋 טען קבוצות", key="load_groups_for_add_new", help="טען את רשימת הקבוצות הזמינות", disabled=not selected_user_for_actions):
                            with st.spinner("טוען קבוצות..."):
                                available_groups = api.get_groups()
                                if available_groups:
                                    group_names = [g.get('groupName') or g.get('name') or str(g) for g in available_groups if not (g.get('groupName') == "Local Admins" and st.session_state.auth_method != 'local')]
                                    st.session_state.available_groups = group_names
                                    st.success(f"נטענו {len(group_names)} קבוצות")
                                else:
                                    st.warning("לא נמצאו קבוצות")

                        if 'available_groups' in st.session_state and st.session_state.available_groups:
                            target_group = st.selectbox("בחר קבוצה", options=st.session_state.available_groups, key="select_target_group_new")
                        else:
                            target_group = None
                            st.text_input("שם/מזהה קבוצה", key="target_group_input_new", disabled=True, placeholder="לחץ על 'טען קבוצות' תחילה")
                        
                        if st.button("➕ הוסף לקבוצה", key="add_user_to_group_new", disabled=not selected_user_for_actions or not target_group):
                            with st.spinner(f"מוסיף את {selected_user_for_actions} לקבוצה {target_group}..."):
                                success = api.add_user_to_group(selected_user_for_actions, target_group)
                                if success:
                                    st.success(f"המשתמש {selected_user_for_actions} נוסף בהצלחה לקבוצה {target_group}")
                                else:
                                    st.error("ההוספה לקבוצה נכשלה")

                if 'user_to_edit' in st.session_state and st.session_state.user_to_edit:
                    st.markdown("---")
                    st.subheader(f"📝 עריכת משתמש: {st.session_state.edit_username}")
                    
                    user_data = st.session_state.user_to_edit
                    current_full_name = user_data.get('fullName', '')
                    current_email = user_data.get('email', '')
                    current_department = user_data.get('department', '')
                    current_pin = user_data.get('shortId', '')
                    current_card_id = next((d.get('detailData', '') for d in user_data.get('details', []) if isinstance(d, dict) and d.get('detailType') == 4), "")
                    
                    with st.form(f"edit_user_form_{st.session_state.edit_username}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            new_full_name = st.text_input("שם מלא", value=current_full_name)
                            new_email = st.text_input("אימייל", value=current_email)
                            new_department = st.text_input("מחלקה", value=current_department)
                        with col2:
                            new_pin = st.text_input("קוד PIN", value=current_pin)
                            new_card_id = st.text_input("מזהה כרטיס", value=current_card_id)
                        
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
                                
                                del st.session_state.user_to_edit
                                del st.session_state.edit_username
                                if 'search_results' in st.session_state:
                                    del st.session_state.search_results
                                st.rerun()

    # Tab 3: Add User
    with tabs[2]:
        st.header("הוספת משתמש חדש")

        if st.session_state.access_level != 'admin':
            st.info("👤 לתשומת לבך: כמשתמש, באפשרותך ליצור משתמשים חדשים אך ייתכנו הגבלות מסוימות.")

        form_key = st.session_state.get('form_reset_key', 'default')
        with st.form(f"add_user_form_{form_key}", clear_on_submit=True):
            col1, col2 = st.columns(2)

            # עמודה ימנית
            with col2:
                new_username = st.text_input("שם משתמש *", help="שם משתמש ייחודי")
                new_first_name = st.text_input("שם פרטי")
                new_last_name = st.text_input("שם משפחה")
                new_email = st.text_input("אימייל")
                new_department = st.text_input("מחלקה")

            # עמודה שמאלית
            with col1:
                new_password = st.text_input("סיסמה", type="password")
                new_pin = st.text_input("קוד PIN")
                new_cardid = st.text_input("מזהה כרטיס")
            
            if st.form_submit_button("➕ צור משתמש", type="primary"):
                if not new_username:
                    st.error("שם משתמש הוא שדה חובה")
                else:
                    provider_id = CONFIG['PROVIDERS']['LOCAL']
                    details = {
                        'fullname': f"{new_first_name} {new_last_name}".strip(), 'email': new_email,
                        'password': new_password, 'department': new_department,
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
                        st.session_state.available_groups_list = groups
                        st.success(f"נטענו {len(groups)} קבוצות")
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
                st.subheader(f"📋 קבוצות (נמצאו {len(groups_to_show)})")
                
                # הצגה בעמודות מרובות לחסכון במקום
                num_columns = min(3, len(groups_to_show))
                columns = st.columns(num_columns)
                
                for i, group in enumerate(groups_to_show):
                    group_name = group.get('groupName', group.get('groupId', 'Unknown Group'))
                    col_index = i % num_columns
                    
                    with columns[col_index]:
                        if st.button(f"📁 {group_name}", key=f"select_group_{i}",
                                    help="לחץ לבחירת קבוצה זו", use_container_width=True):
                            st.session_state.selected_group_name = group_name
                            st.success(f"נבחרה: {group_name}")
                            st.rerun()
                
                # כפתור Show Members מרכזי
                st.markdown("---")
                
                # בדיקה אם יש קבוצה נבחרת
                selected_group = st.session_state.get('selected_group_name', '')
                button_disabled = not selected_group

                if selected_group:
                    st.info(f"קבוצה נבחרת: **{selected_group}**")
                else:
                    st.warning("אנא בחר קבוצה למעלה")
                
                col_center = st.columns([1, 2, 1])[1]
                with col_center:
                    if st.button("👥 הצג חברים", key="show_members_btn",
                               disabled=button_disabled, use_container_width=True):
                        target_group = st.session_state.selected_group_name

                        user_groups_str = ', '.join([g['displayName'] for g in st.session_state.user_groups]) if st.session_state.user_groups else ""
                        logger.log_action(st.session_state.username, "View Group Members", f"Group: {target_group}",
                                        st.session_state.user_email, user_groups_str, True, st.session_state.access_level)

                        with st.spinner("טוען חברי קבוצה..."):
                            members = api.get_group_members(target_group)
                            if members:
                                st.session_state.group_members_data = {
                                    'group_name': target_group,
                                    'members': members,
                                    'count': len(members)
                                }
                                st.success(f"נמצאו {len(members)} חברים בקבוצה '{target_group}'")
                                # השבת הכפתור (grayed out) אחרי לחיצה
                                st.session_state.members_loaded = True
                            else:
                                st.warning("הקבוצה ריקה או לא נמצאה")
                                if 'group_members_data' in st.session_state:
                                    del st.session_state.group_members_data
            else:
                st.info("לא נמצאו קבוצות התואמות את קריטריוני החיפוש")
        else:
            st.info("לחץ על 'טען קבוצות' כדי לראות את הקבוצות הזמינות")
        
        # הצגת תוצאות חברי הקבוצה ברוחב מלא
        if 'group_members_data' in st.session_state:
            st.markdown("---")
            group_data = st.session_state.group_members_data
            st.subheader(f"👥 חברי הקבוצה '{group_data['group_name']}' ({group_data['count']} חברים)")
            
            df_data = []
            for member in group_data['members']:
                username = member.get('userName', member.get('username', ''))
                full_name = member.get('fullName', '')
                email = member.get('email', '')
                
                department = member.get('department', '')
                if not department:
                    for detail in member.get('details', []):
                        if isinstance(detail, dict) and detail.get('detailType') == 11:
                            department = detail.get('detailData', '')
                            break
                
                df_data.append({
                    'Username': username,
                    'Full Name': full_name,
                    'Email': email,
                    'Department': department
                })
            
            if df_data:
                df = pd.DataFrame(df_data)
                st.dataframe(df, use_container_width=True)
                
                col_download, col_clear = st.columns([1, 1])
                
                with col_download:
                    csv = df.to_csv(index=False)
                    st.download_button(
                        "💾 הורד CSV", csv.encode('utf-8-sig'),
                        f"group_{group_data['group_name']}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        "text/csv", key="download_group_members",
                        use_container_width=True
                    )

                with col_clear:
                    if st.button("🗑️ נקה תוצאות", key="clear_group_results", use_container_width=True):
                        if 'group_members_data' in st.session_state:
                            del st.session_state.group_members_data
                        if 'selected_group_name' in st.session_state:
                            del st.session_state.selected_group_name
                        if 'members_loaded' in st.session_state:
                            del st.session_state.members_loaded
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
