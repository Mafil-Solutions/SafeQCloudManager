#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SafeQ Cloud Manager - Bulk Upload Users from Excel
העלאה המונית של משתמשים מקובץ אקסל
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import sys
import os
import re
from typing import List, Dict, Tuple

# הוספת תיקיית app ל-path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import get_api_instance, get_logger_instance, check_authentication, CONFIG


def validate_excel_data(df: pd.DataFrame, api) -> Tuple[pd.DataFrame, List[str]]:
    """
    בדיקת תקינות הנתונים מהאקסל

    Args:
        df: DataFrame עם הנתונים מהאקסל
        api: SafeQAPI instance

    Returns:
        Tuple של (DataFrame מעודכן עם סטטוס, רשימת שגיאות כלליות)
    """
    errors = []

    # בדיקת עמודות נדרשות
    required_columns = ['username']
    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        errors.append(f"❌ חסרות עמודות חובה: {', '.join(missing_columns)}")
        return df, errors

    # הוספת עמודת סטטוס
    df['status'] = ''
    df['error_message'] = ''

    # בדיקת כל שורה
    for idx, row in df.iterrows():
        username = str(row.get('username', '')).strip()
        email = str(row.get('email', '')).strip() if pd.notna(row.get('email')) else ''
        pin = str(row.get('pin', '')).strip() if pd.notna(row.get('pin')) else ''

        row_errors = []

        # בדיקת username חובה
        if not username:
            row_errors.append("שם משתמש חסר")
        else:
            # בדיקת username קיים
            username_exists, provider_name = api.check_username_exists(username)
            if username_exists:
                row_errors.append(f"שם משתמש קיים במערכת ({provider_name})")

        # בדיקת אימייל
        if email and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            row_errors.append("אימייל לא תקין")

        # בדיקת PIN כפול
        if pin:
            pin_exists, existing_user = api.check_pin_exists(pin)
            if pin_exists:
                row_errors.append(f"PIN כפול (קיים אצל {existing_user})")

        # עדכון סטטוס
        if row_errors:
            df.at[idx, 'status'] = '❌ שגיאה'
            df.at[idx, 'error_message'] = ', '.join(row_errors)
        else:
            df.at[idx, 'status'] = '✅ תקין'
            df.at[idx, 'error_message'] = ''

    return df, errors


def upload_users_from_dataframe(df: pd.DataFrame, api, logger, current_username: str) -> Dict:
    """
    העלאת משתמשים מ-DataFrame

    Args:
        df: DataFrame עם הנתונים
        api: SafeQAPI instance
        logger: Logger instance
        current_username: שם המשתמש המחובר

    Returns:
        Dict עם סטטיסטיקות: {success: int, failed: int, errors: List}
    """
    stats = {
        'success': 0,
        'failed': 0,
        'errors': []
    }

    provider_id = CONFIG['PROVIDERS']['LOCAL']

    # סינון רק שורות תקינות
    valid_rows = df[df['status'] == '✅ תקין']

    for idx, row in valid_rows.iterrows():
        username = str(row.get('username', '')).strip()
        first_name = str(row.get('first_name', '')).strip() if pd.notna(row.get('first_name')) else ''
        last_name = str(row.get('last_name', '')).strip() if pd.notna(row.get('last_name')) else ''
        email = str(row.get('email', '')).strip() if pd.notna(row.get('email')) else ''
        department = str(row.get('department', '')).strip() if pd.notna(row.get('department')) else ''
        password = str(row.get('password', '')).strip() if pd.notna(row.get('password')) else 'Aa123456'
        pin = str(row.get('pin', '')).strip() if pd.notna(row.get('pin')) else ''
        cardid = str(row.get('cardid', '')).strip() if pd.notna(row.get('cardid')) else ''

        # הכנת פרטי משתמש
        details = {
            'fullname': f"{first_name} {last_name}".strip(),
            'email': email,
            'password': password,
            'department': department,
            'shortid': pin,
            'cardid': cardid
        }

        try:
            success = api.create_user(username, provider_id, details)
            if success:
                stats['success'] += 1
                logger.log_action(
                    current_username,
                    "Bulk Upload User Success",
                    f"Username: {username}",
                    st.session_state.get('user_email', ''),
                    '',
                    True,
                    st.session_state.get('access_level', 'admin')
                )
            else:
                stats['failed'] += 1
                stats['errors'].append(f"{username}: יצירה נכשלה")
                logger.log_action(
                    current_username,
                    "Bulk Upload User Failed",
                    f"Username: {username}",
                    st.session_state.get('user_email', ''),
                    '',
                    False,
                    st.session_state.get('access_level', 'admin')
                )
        except Exception as e:
            stats['failed'] += 1
            stats['errors'].append(f"{username}: {str(e)}")

    return stats


def show():
    """הצגת דף העלאה המונית"""
    check_authentication()

    # RTL styling
    st.markdown("""
    <style>
        .stApp {
            direction: rtl !important;
        }
        .block-container {
            text-align: right !important;
            direction: rtl !important;
        }

        /* כפתורים אדומים */
        .stButton > button[kind="primary"] {
            background: linear-gradient(45deg, #C41E3A, #FF6B6B) !important;
            color: white !important;
            border: none !important;
            box-shadow: 0 4px 15px rgba(196, 30, 58, 0.3) !important;
        }

        .stButton > button[kind="primary"]:hover {
            background: linear-gradient(45deg, #a01829, #e05555) !important;
            box-shadow: 0 6px 20px rgba(196, 30, 58, 0.4) !important;
        }

        /* טבלאות */
        .dataframe {
            direction: rtl !important;
            text-align: right !important;
        }
    </style>
    """, unsafe_allow_html=True)

    st.title("📤 העלאה המונית של משתמשים")

    # בדיקת הרשאות - רק Admin מקומי
    role = st.session_state.get('role', st.session_state.get('access_level', 'viewer'))
    local_username = st.session_state.get('local_username', None)

    if not (role == 'admin' and local_username):
        st.error("❌ תכונה זו זמינה רק למשתמש Admin מקומי")
        st.info("💡 יש להתחבר כמשתמש Admin מקומי (לא משתמש Entra)")
        return

    api = get_api_instance()
    logger = get_logger_instance()

    # הנחיות שימוש
    with st.expander("📋 הנחיות שימוש", expanded=False):
        st.markdown("""
        ### פורמט קובץ האקסל:

        הקובץ חייב להכיל את העמודות הבאות (בשורה הראשונה):

        | עמודה | שם באנגלית | חובה | הערות |
        |--------|------------|------|-------|
        | שם משתמש | username | ✅ | שם ייחודי |
        | שם פרטי | first_name | ❌ | |
        | שם משפחה | last_name | ❌ | |
        | אימייל | email | ❌ | פורמט תקין |
        | מחלקה | department | ❌ | |
        | סיסמה | password | ❌ | ברירת מחדל: Aa123456 |
        | PIN | pin | ❌ | ייחודי |
        | מזהה כרטיס | cardid | ❌ | |

        ### דוגמה:
        ```
        username,first_name,last_name,email,department,password,pin,cardid
        user1,משה,כהן,moshe@example.com,מחלקת IT,Aa123456,1234,
        user2,שרה,לוי,sarah@example.com,מחלקת כספים,,5678,
        ```

        ### שימו לב:
        - הקובץ חייב להיות בפורמט Excel (.xlsx) או CSV
        - שם המשתמש הוא שדה חובה
        - המערכת תבדוק אם שמות המשתמשים והPINים כבר קיימים
        - משתמשים עם שגיאות לא יועלו
        """)

    st.markdown("---")

    # העלאת קובץ
    st.subheader("📁 העלאת קובץ")
    uploaded_file = st.file_uploader(
        "בחר קובץ Excel או CSV",
        type=['xlsx', 'xls', 'csv'],
        help="העלה קובץ עם רשימת המשתמשים להעלאה"
    )

    if uploaded_file is not None:
        try:
            # קריאת הקובץ
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)

            st.success(f"✅ הקובץ נטען בהצלחה! ({len(df)} שורות)")

            # תצוגת נתונים גולמיים
            with st.expander("👁️ הצגת נתונים גולמיים", expanded=False):
                st.dataframe(df, use_container_width=True)

            st.markdown("---")

            # כפתור בדיקת תקינות
            if st.button("🔍 בדוק תקינות נתונים", type="primary", use_container_width=True):
                with st.spinner("בודק תקינות..."):
                    validated_df, general_errors = validate_excel_data(df.copy(), api)
                    st.session_state.validated_df = validated_df
                    st.session_state.general_errors = general_errors
                st.rerun()

            # הצגת תוצאות בדיקה
            if 'validated_df' in st.session_state:
                st.markdown("---")
                st.subheader("📊 תוצאות בדיקת תקינות")

                validated_df = st.session_state.validated_df
                general_errors = st.session_state.general_errors

                # שגיאות כלליות
                if general_errors:
                    for error in general_errors:
                        st.error(error)
                    return

                # סטטיסטיקות
                total_rows = len(validated_df)
                valid_rows = len(validated_df[validated_df['status'] == '✅ תקין'])
                error_rows = len(validated_df[validated_df['status'] == '❌ שגיאה'])

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("סה\"כ משתמשים", total_rows)
                with col2:
                    st.metric("תקינים", valid_rows, delta=None, delta_color="normal")
                with col3:
                    st.metric("שגיאות", error_rows, delta=None, delta_color="inverse")

                # טבלה מפורטת
                st.dataframe(
                    validated_df[['username', 'first_name', 'last_name', 'email', 'status', 'error_message']],
                    use_container_width=True,
                    height=400
                )

                # כפתור העלאה
                if valid_rows > 0:
                    st.markdown("---")
                    st.warning(f"⚠️ עומדים להיווצר {valid_rows} משתמשים חדשים במערכת")

                    col_confirm, col_cancel = st.columns([1, 1])

                    with col_confirm:
                        if st.button("✅ אשר והעלה למערכת", type="primary", use_container_width=True):
                            st.session_state.confirm_upload = True
                            st.rerun()

                    with col_cancel:
                        if st.button("❌ ביטול", use_container_width=True):
                            # ניקוי
                            if 'validated_df' in st.session_state:
                                del st.session_state.validated_df
                            if 'general_errors' in st.session_state:
                                del st.session_state.general_errors
                            st.rerun()
                else:
                    st.error("❌ אין משתמשים תקינים להעלאה. תקן את השגיאות ונסה שוב.")

            # ביצוע העלאה
            if st.session_state.get('confirm_upload', False):
                st.markdown("---")
                st.subheader("⏳ מעלה משתמשים...")

                validated_df = st.session_state.validated_df
                valid_rows = len(validated_df[validated_df['status'] == '✅ תקין'])

                progress_bar = st.progress(0)
                progress_text = st.empty()

                # העלאה עם progress
                current_username = st.session_state.get('username', '')

                # ספירה ידנית
                uploaded_count = 0
                total_to_upload = valid_rows
                stats = {'success': 0, 'failed': 0, 'errors': []}

                provider_id = CONFIG['PROVIDERS']['LOCAL']
                valid_df = validated_df[validated_df['status'] == '✅ תקין']

                for idx, row in valid_df.iterrows():
                    username = str(row.get('username', '')).strip()
                    first_name = str(row.get('first_name', '')).strip() if pd.notna(row.get('first_name')) else ''
                    last_name = str(row.get('last_name', '')).strip() if pd.notna(row.get('last_name')) else ''
                    email = str(row.get('email', '')).strip() if pd.notna(row.get('email')) else ''
                    department = str(row.get('department', '')).strip() if pd.notna(row.get('department')) else ''
                    password = str(row.get('password', '')).strip() if pd.notna(row.get('password')) else 'Aa123456'
                    pin = str(row.get('pin', '')).strip() if pd.notna(row.get('pin')) else ''
                    cardid = str(row.get('cardid', '')).strip() if pd.notna(row.get('cardid')) else ''

                    details = {
                        'fullname': f"{first_name} {last_name}".strip(),
                        'email': email,
                        'password': password,
                        'department': department,
                        'shortid': pin,
                        'cardid': cardid
                    }

                    try:
                        success = api.create_user(username, provider_id, details)
                        if success:
                            stats['success'] += 1
                        else:
                            stats['failed'] += 1
                            stats['errors'].append(f"{username}: יצירה נכשלה")
                    except Exception as e:
                        stats['failed'] += 1
                        stats['errors'].append(f"{username}: {str(e)}")

                    uploaded_count += 1
                    progress = uploaded_count / total_to_upload
                    progress_bar.progress(progress)
                    progress_text.text(f"מעלה משתמש {uploaded_count} מתוך {total_to_upload}...")

                progress_bar.empty()
                progress_text.empty()

                # תוצאות
                st.markdown("---")
                st.subheader("📈 תוצאות העלאה")

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("הצלחות", stats['success'], delta=None, delta_color="normal")
                with col2:
                    st.metric("כשלונות", stats['failed'], delta=None, delta_color="inverse")

                if stats['success'] > 0:
                    st.success(f"✅ {stats['success']} משתמשים נוצרו בהצלחה!")
                    st.balloons()

                if stats['failed'] > 0:
                    st.error(f"❌ {stats['failed']} משתמשים נכשלו")
                    if stats['errors']:
                        with st.expander("פרטי שגיאות"):
                            for error in stats['errors']:
                                st.write(f"• {error}")

                # לוג
                logger.log_action(
                    current_username,
                    "Bulk Upload Completed",
                    f"Success: {stats['success']}, Failed: {stats['failed']}",
                    st.session_state.get('user_email', ''),
                    '',
                    stats['success'] > 0,
                    st.session_state.get('access_level', 'admin')
                )

                # כפתור לאיפוס
                if st.button("🔄 העלאה נוספת", use_container_width=True):
                    # ניקוי
                    if 'validated_df' in st.session_state:
                        del st.session_state.validated_df
                    if 'general_errors' in st.session_state:
                        del st.session_state.general_errors
                    if 'confirm_upload' in st.session_state:
                        del st.session_state.confirm_upload
                    st.rerun()

        except Exception as e:
            st.error(f"❌ שגיאה בקריאת הקובץ: {str(e)}")
            st.info("💡 ודא שהקובץ בפורמט תקין (Excel או CSV)")


if __name__ == "__main__":
    show()
