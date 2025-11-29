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

    def get_user_groups(self, username):
        """קבלת קבוצות של משתמש"""
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
            return []
        except Exception as e:
            st.error(f"שגיאה בקבלת קבוצות משתמש: {str(e)}")
            return []

    def get_group_members(self, group_id):
        """קבלת רשימת חברי קבוצה"""
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
        """הוספת משתמש לקבוצה"""
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
        """הסרת משתמש מקבוצה"""
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

    def get_documents_history(self, datestart=None, dateend=None, username=None,
                             portname=None, status=None, jobtype=None,
                             maxrecords=200, pagetoken=None, domainname=None):
        """
        קבלת היסטוריית מסמכים

        Parameters:
            datestart: ISO-8601 formatted start date (default: last 24h)
            dateend: ISO-8601 formatted end date (default: now)
            username: filter by specific username
            portname: filter by specific port/printer name
            status: list of status codes (0=READY, 1=PRINTED, 2=DELETED, etc.)
            jobtype: PRINT, COPY, SCAN, or FAX
            maxrecords: max records per page (max 2000)
            pagetoken: token for pagination
            domainname: filter by domain

        Returns:
            dict with: documents, recordsOnPage, nextPageToken, etc.
        """
        try:
            url = f"{self.server_url}/api/v1/documents/history"

            params = {}

            if datestart:
                params['datestart'] = datestart
            if dateend:
                params['dateend'] = dateend
            if username:
                params['username'] = username
            if portname:
                params['portname'] = portname
            if jobtype:
                params['jobtype'] = jobtype
            if domainname:
                params['domainname'] = domainname
            if pagetoken:
                params['pagetoken'] = pagetoken
            if maxrecords:
                params['maxrecords'] = maxrecords

            # status הוא list, צריך לשלוח אותו בצורה מיוחדת
            if status and isinstance(status, list):
                params['status'] = ','.join(map(str, status))

            response = requests.get(url, headers=self.headers, params=params,
                                  verify=False, timeout=300)  # 5 min timeout

            if response.status_code == 200:
                return response.json()
            else:
                st.error(f"כשל בקבלת היסטוריית מסמכים: HTTP {response.status_code}")
                if response.text:
                    try:
                        error_detail = response.json()
                        st.error(f"פרטי שגיאה: {error_detail}")
                    except:
                        st.error(f"פרטי שגיאה: {response.text}")
                return None
        except Exception as e:
            st.error(f"שגיאה בקבלת היסטוריית מסמכים: {str(e)}")
            return None

    def get_user_documents(self, status=None, maxrecords=50):
        """
        קבלת רשימת מסמכים למשתמש

        Note: דורש User Token (לא זמין ב-API Key authentication)

        Parameters:
            status: list of status codes (default: [0] for READY)
            maxrecords: max records to retrieve (max 500)

        Returns:
            list of DocumentInfo or None
        """
        try:
            url = f"{self.server_url}/api/v1/documents"

            params = {}

            if maxrecords:
                params['maxRecords'] = maxrecords

            # status הוא list
            if status and isinstance(status, list):
                params['status'] = ','.join(map(str, status))
            elif status is None:
                params['status'] = '0'  # default READY

            response = requests.get(url, headers=self.headers, params=params,
                                  verify=False, timeout=30)

            if response.status_code == 200:
                data = response.json()
                # יכול להיות list או dict עם items
                if isinstance(data, dict) and 'items' in data:
                    return data['items']
                elif isinstance(data, list):
                    return data
                return []
            else:
                st.error(f"כשל בקבלת מסמכים: HTTP {response.status_code}")
                return None
        except Exception as e:
            st.error(f"שגיאה בקבלת מסמכים: {str(e)}")
            return None

    def record_document_job(self, jobtype, username=None, providerid=None,
                          totalpages=None, colorpages=None, papersize=None,
                          duplex=None, title=None, serialnumber=None,
                          address=None, datetime_str=None):
        """
        רישום עבודת הדפסה/העתקה/סריקה חדשה

        Parameters:
            jobtype: PRINT, COPY, SCAN, or FAX (required)
            username: username (required if using device token)
            providerid: provider id (required if using device token)
            totalpages: total pages
            colorpages: color pages
            papersize: paper size
            duplex: boolean (True = LONG, False = SHORT)
            title: document title
            serialnumber: serial number to find output port
            address: address to find output port
            datetime_str: datetime in format YYYY-MM-DDTHH:mm:ss+HH:mm

        Returns:
            bool: True if successful
        """
        try:
            url = f"{self.server_url}/api/v1/documents/history"

            data = {'jobtype': jobtype}

            if username:
                data['username'] = username
            if providerid:
                data['providerid'] = providerid
            if totalpages is not None:
                data['totalpages'] = str(totalpages)
            if colorpages is not None:
                data['colorpages'] = str(colorpages)
            if papersize:
                data['papersize'] = papersize
            if duplex is not None:
                data['duplex'] = 'true' if duplex else 'false'
            if title:
                data['title'] = title
            if serialnumber:
                data['serialnumber'] = serialnumber
            if address:
                data['address'] = address
            if datetime_str:
                data['datetime'] = datetime_str

            import urllib.parse
            encoded_data = urllib.parse.urlencode(data)

            response = requests.post(url, headers=self.headers, data=encoded_data,
                                   verify=False, timeout=10)

            if response.status_code == 200:
                return True
            else:
                st.error(f"כשל ברישום עבודה: HTTP {response.status_code}")
                if response.text:
                    try:
                        error_detail = response.json()
                        st.error(f"פרטי שגיאה: {error_detail}")
                    except:
                        st.error(f"פרטי שגיאה: {response.text}")
                return False
        except Exception as e:
            st.error(f"שגיאה ברישום עבודה: {str(e)}")
            return False

    def get_output_ports_for_user(self, username=None, provider_id=None, enrich_ports=True):
        """
        קבלת רשימת מדפסות (output ports) זמינות עבור משתמש

        Args:
            username: שם המשתמש (אופציונלי - אם לא מסופק, השרת ינסה לנחש)
            provider_id: מזהה ספק (אופציונלי)
            enrich_ports: האם להעשיר את המידע (account, container, location)

        Returns:
            list: רשימת מדפסות עם פרטים (שם, מיקום, IP, מספר סידורי וכו')
        """
        try:
            url = f"{self.server_url}/api/v1/outputports"
            params = {}

            if username:
                params['username'] = username
            if provider_id:
                params['providerid'] = provider_id
            if enrich_ports:
                params['enrichPorts'] = 'true'

            response = requests.get(url, headers=self.headers, params=params, verify=False, timeout=30)

            if response.status_code == 200:
                try:
                    data = response.json()

                    # YSoft API יכול להחזיר dict עם 'items' או list ישירות
                    if isinstance(data, dict) and 'items' in data:
                        return data['items']
                    elif isinstance(data, list):
                        return data
                    else:
                        print(f"[DEBUG] Unexpected response format for output ports: {type(data)}")
                        return []

                except json.JSONDecodeError as e:
                    st.error(f"תגובת JSON לא תקינה: {str(e)}")
                    return []
            else:
                st.error(f"שגיאה בקבלת מדפסות: HTTP {response.status_code}")
                return []
        except Exception as e:
            st.error(f"שגיאה בחיבור לשרת: {str(e)}")
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
