#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SafeQ Cloud Manager - Add User Page
דף הוספת משתמש חדש
"""

import streamlit as st
import sys
import os
import re

# הוספת תיקיית app ל-path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import get_api_instance, get_logger_instance, check_authentication, CONFIG
from permissions import filter_groups_by_departments

def get_department_options(allowed_departments, local_groups):
    """מחזיר רשימת אפשרויות מחלקות לפי הרשאות"""
    # Debug: בדיקת מצב ההתחלה
    print(f"[DEBUG] get_department_options called:")
    print(f"  - allowed_departments: {allowed_departments}")
    print(f"  - local_groups count: {len(local_groups)}")
    if local_groups:
        print(f"  - First group example: {local_groups[0]}")

    # חילוץ כל המחלקות מקבוצות מקומיות
    departments = set()
    all_groups = set()  # כל הקבוצות (לגיבוי)

    for group in local_groups:
        group_name = group.get('groupName', '')
        all_groups.add(group_name)
        # נניח שקבוצות מחלקה מכילות " - " (למשל: "צפת - 240234")
        if ' - ' in group_name:
            departments.add(group_name)

    print(f"  - Groups with ' - ': {len(departments)}")
    print(f"  - All groups: {len(all_groups)}")

    # Superadmin רואה את כל המחלקות
    if allowed_departments == ["ALL"]:
        # אם אין מחלקות עם " - ", נחזיר את כל הקבוצות
        if not departments and all_groups:
            print(f"  - Warning: No groups with ' - ', returning all groups for superadmin")
            return sorted(all_groups)
        return sorted(departments)

    # סינון רק מחלקות מורשות (עבור support/admin)
    if allowed_departments:
        filtered_departments = [dept for dept in departments if dept in allowed_departments]
        return sorted(filtered_departments)

    return sorted(departments)

def show():
    """הצגת דף הוספת משתמש"""
    check_authentication()

    # RTL styling + רקע עדין לשדות טקסט
    st.markdown("""
    <style>
        /* כל האפליקציה RTL */
        .stApp {
            direction: rtl !important;
        }

        .block-container {
            text-align: right !important;
            direction: rtl !important;
        }

        /* עמודות */
        div[data-testid="column"] {
            direction: rtl !important;
            text-align: right !important;
        }

        /* אלמנטי טופס */
        .stTextInput, .stSelectbox, .stNumberInput {
            direction: rtl !important;
            text-align: right !important;
        }

        .stTextInput input, .stSelectbox select {
            direction: rtl !important;
            text-align: right !important;
        }

        .stTextInput label, .stSelectbox label {
            direction: rtl !important;
            text-align: right !important;
        }

        /* רקע לבן לשדות טקסט */
        .stTextInput > div > div > input,
        .stSelectbox > div > div > select,
        .stNumberInput > div > div > input {
            background-color: white !important;  
        }

        /* כפתור צור משתמש - צבע כמו כפתור "חפש" */
            div[data-testid="stFormSubmitButton"] > button[kind="primaryFormSubmit"] {
            background: linear-gradient(45deg, #D71F27, #FF6B6B) !important;
            color: white !important;
            border: none !important;
            box-shadow: 0 4px 15px rgba(74, 144, 226, 0.3);
            border-radius: 25px;
            width: 100%;
        }

       div[data-testid="stFormSubmitButton"] > button[kind="primaryFormSubmit"]:hover {
            background: linear-gradient(45deg, #FF6B6B, #D71F27) !important;
            color: white !important;
            box-shadow: 0 6px 20px rgba(74, 144, 226, 0.5) !important;
        }
    </style>
    """, unsafe_allow_html=True)

    api = get_api_instance()
    logger = get_logger_instance()

    st.header("➕ הוספת משתמש חדש")

    # בדיקת הרשאות
    role = st.session_state.get('role', st.session_state.get('access_level', 'viewer'))
    if role not in ['admin', 'superadmin', 'support']:
        st.warning("👁️ רמת ההרשאה שלך (viewer) מאפשרת רק צפייה. יצירת משתמשים חדשים זמינה רק לתמיכה/מנהלים.")
        return

    # הכנת אפשרויות מחלקה
    allowed_departments = st.session_state.get('allowed_departments', [])
    local_groups = st.session_state.get('local_groups', [])

    # Debug: הצגת מצב התחלתי
    print(f"[DEBUG] Add User - Initial state:")
    print(f"  - allowed_departments: {allowed_departments}")
    print(f"  - local_groups in session: {len(local_groups)}")

    # Superadmin תמיד טוען את כל הקבוצות מה-API (לא תלוי במה שב-session)
    # כי משתמשים דרך Entra עשויים להיות שייכים רק לחלק מהקבוצות
    if allowed_departments == ["ALL"]:
        with st.spinner("טוען רשימת מחלקות..."):
            provider_id = CONFIG['PROVIDERS']['LOCAL']
            print(f"[DEBUG] Superadmin: Loading ALL groups from API (provider_id: {provider_id})...")
            local_groups = api.get_groups(provider_id) or []
            print(f"[DEBUG] Loaded {len(local_groups)} groups from API")
            st.session_state.local_groups = local_groups

    department_options = get_department_options(allowed_departments, local_groups)
    print(f"[DEBUG] Final department_options: {len(department_options)} options")
    if department_options:
        print(f"  - First 3 options: {department_options[:3]}")

    is_superadmin = allowed_departments == ["ALL"]
    has_single_dept = len(department_options) == 1
    has_multiple_depts = len(department_options) > 1

    # ניהול מצב הטופס
    form_state = st.session_state.get('add_user_form_state', {})

    form_key = st.session_state.get('form_reset_key', 'default')
    with st.form(f"add_user_form_{form_key}", clear_on_submit=False):
        # עמודות מימין לשמאל - כמו בטופס עריכה
        col1, col2 = st.columns(2)

        # עמודה ימנית (col1 מופיע ראשון ב-RTL)
        with col1:
            new_username = st.text_input("שם משתמש *", value=form_state.get('username', ''),
                                        help="שם משתמש ייחודי")
            new_first_name = st.text_input("שם פרטי", value=form_state.get('first_name', ''))
            new_last_name = st.text_input("שם משפחה", value=form_state.get('last_name', ''))
            new_email = st.text_input("אימייל", value=form_state.get('email', ''))

            # שדה Department דינמי
            # Superadmin תמיד מקבל dropdown (גם אם יש רק מחלקה אחת)
            # משתמשים אחרים: dropdown רק אם יש יותר ממחלקה אחת
            if is_superadmin and department_options:
                # Superadmin - תמיד dropdown
                default_dept_idx = 0
                if form_state.get('department') in department_options:
                    default_dept_idx = department_options.index(form_state.get('department'))
                new_department = st.selectbox("מחלקה *", options=department_options, index=default_dept_idx,
                                             help="בחר מחלקה מהרשימה")
            elif has_single_dept:
                # משתמש רגיל עם מחלקה אחת - שדה חסום
                new_department = st.text_input("מחלקה", value=department_options[0], disabled=True,
                                              help="מחלקה זו נקבעת אוטומטית לפי ההרשאות שלך")
            elif has_multiple_depts:
                # משתמש רגיל עם מספר מחלקות - dropdown
                default_dept_idx = 0
                if form_state.get('department') in department_options:
                    default_dept_idx = department_options.index(form_state.get('department'))
                new_department = st.selectbox("מחלקה *", options=department_options, index=default_dept_idx,
                                             help="בחר מחלקה מהרשימה המורשות")
            else:
                # אין מחלקות זמינות
                new_department = st.text_input("מחלקה", disabled=True,
                                              help="לא נמצאו מחלקות זמינות")
                st.error("⚠️ לא ניתן ליצור משתמש - אין מחלקות מורשות")

        # עמודה שמאלית (col2 מופיע שני ב-RTL)
        with col2:
            new_password = st.text_input("סיסמה", type="password", value=form_state.get('password', ''),
                                        placeholder="Aa123456",
                                        help="אם לא מוזן - סיסמה ברירת מחדל: Aa123456")
            new_pin = st.text_input("קוד PIN", value=form_state.get('pin', ''),
                                   help="קוד PIN ייחודי למשתמש")
            new_cardid = st.text_input("מזהה כרטיס", value=form_state.get('cardid', ''),
                                      help="מזהה כרטיס ייחודי")

        # כפתורים
        col_submit, col_cancel = st.columns(2)
        with col_submit:
            submit = st.form_submit_button("➕ צור משתמש", type="primary", use_container_width=True)
        with col_cancel:
            cancel = st.form_submit_button("❌ נקה טופס",type="secondary", use_container_width=True)

        if cancel:
            # ניקוי הטופס - גם state וגם reset key
            if 'add_user_form_state' in st.session_state:
                del st.session_state.add_user_form_state
            # עדכון form_reset_key כדי לאפס את הטופס
            import time
            st.session_state.form_reset_key = f"form_{int(time.time())}"
            st.rerun()

        if submit:
            # בדיקת שדה חובה
            if not new_username:
                st.error("❌ שם משתמש הוא שדה חובה")
                st.stop()

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

            # בדיקת מזהה כרטיס כפול (אם קיימת פונקציה)
            if new_cardid and hasattr(api, 'check_cardid_exists'):
                cardid_exists, existing_user = api.check_cardid_exists(new_cardid)
                if cardid_exists:
                    validation_errors.append(f"❌ מזהה כרטיס '{new_cardid}' כבר קיים אצל משתמש: {existing_user}")

            # אם יש שגיאות validation
            if validation_errors:
                # שמירת הערכים
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

            # אין שגיאות - צור משתמש
            provider_id = CONFIG['PROVIDERS']['LOCAL']
            details = {
                'fullname': f"{new_first_name} {new_last_name}".strip(),
                'email': new_email,
                'password': new_password or 'Aa123456',
                'department': new_department,
                'shortid': new_pin,
                'cardid': new_cardid
            }

            user_groups_str = ', '.join([g['displayName'] for g in st.session_state.get('user_groups', [])]) if st.session_state.get('user_groups') else ""
            logger.log_action(st.session_state.username, "Create User Attempt", f"Username: {new_username}, Provider: Local",
                            st.session_state.get('user_email', ''), user_groups_str, True, st.session_state.get('access_level', 'viewer'))

            with st.spinner("יוצר משתמש..."):
                success = api.create_user(new_username, provider_id, details)
                if success:
                    st.success("✅ המשתמש נוצר בהצלחה!")
                    st.balloons()
                    # ניקוי הטופס - גם state וגם reset key
                    if 'add_user_form_state' in st.session_state:
                        del st.session_state.add_user_form_state
                    # עדכון form_reset_key כדי לאפס את הטופס
                    import time
                    st.session_state.form_reset_key = f"form_{int(time.time())}"
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.error("❌ יצירת המשתמש נכשלה")
                    logger.log_action(st.session_state.username, "User Creation Failed", f"Username: {new_username}",
                                    st.session_state.get('user_email', ''), user_groups_str, False, st.session_state.get('access_level', 'viewer'))

if __name__ == "__main__":
    show()
