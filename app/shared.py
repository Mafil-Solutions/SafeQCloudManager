#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shared utilities and classes for SafeQ Cloud Manager
משאבים משותפים לכל הדפים
"""

import streamlit as st
import requests
import pandas as pd
import urllib3
import json
from typing import Dict, List, Optional
import sqlite3
from datetime import datetime
from config import config

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CONFIG = config.get()

class AuditLogger:
    """מחלקה לרישום פעולות ביקורת"""
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

class SafeQAPI:
    """מחלקה לתקשורת עם SafeQ Cloud API"""
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
        """קבלת רשימת משתמשים"""
        try:
            url = f"{self.server_url}/api/v1/users/all"
            params = {'providerid': provider_id, 'maxrecords': max_records}
            response = requests.get(url, headers=self.headers, params=params, verify=False, timeout=30)

            if response.status_code == 200:
                try:
                    data = response.json()

                    if isinstance(data, dict) and 'items' in data:
                        return data['items']
                    elif isinstance(data, list):
                        return data
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
        """חיפוש משתמש"""
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
            return None
        except Exception as e:
            st.error(f"שגיאת חיפוש: {str(e)}")
            return None

    def get_groups(self, provider_id, max_records=500):
        """קבלת רשימת קבוצות"""
        try:
            url = f"{self.server_url}/api/v1/groups"
            params = {'providerId': provider_id, 'maxRecords': max_records}
            response = requests.get(url, headers=self.headers, params=params, verify=False, timeout=30)

            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, dict) and 'items' in data:
                        return data['items']
                    elif isinstance(data, list):
                        return data
                    else:
                        return []
                except json.JSONDecodeError:
                    return []
            return []
        except Exception as e:
            st.error(f"שגיאת קבלת קבוצות: {str(e)}")
            return []

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
        """מחיקת משתמש מהמערכת"""
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

    def create_user(self, username, provider_id, details):
        """יצירת משתמש חדש"""
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

def get_api_instance():
    """קבלת instance של SafeQAPI"""
    if 'api' not in st.session_state:
        st.session_state.api = SafeQAPI()
    return st.session_state.api

def get_logger_instance():
    """קבלת instance של AuditLogger"""
    if 'logger' not in st.session_state:
        st.session_state.logger = AuditLogger()
    return st.session_state.logger

def check_authentication():
    """בדיקת אימות משתמש"""
    if 'logged_in' not in st.session_state or not st.session_state.logged_in:
        st.error("❌ נדרש אימות")
        st.stop()
    return True
