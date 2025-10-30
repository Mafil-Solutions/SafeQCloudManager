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
