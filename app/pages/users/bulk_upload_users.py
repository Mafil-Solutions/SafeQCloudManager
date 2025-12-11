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


@st.dialog("📊 תוצאות העלאה", width="large")
def show_upload_results_dialog(stats):
    """Modal להצגת תוצאות העלאה"""
    st.subheader("📈 תוצאות העלאה")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("✅ הצלחות", stats['success'], delta=None, delta_color="normal")
    with col2:
        st.metric("❌ כשלונות", stats['failed'], delta=None, delta_color="inverse")

    if stats['success'] > 0:
        st.success(f"🎉 {stats['success']} משתמשים נוצרו בהצלחה!")
        st.balloons()

    if stats['failed'] > 0:
        st.error(f"⚠️ {stats['failed']} משתמשים נכשלו")
        if stats['errors']:
            with st.expander("📋 פרטי שגיאות", expanded=True):
                for error in stats['errors']:
                    st.write(f"• {error}")

    st.markdown("---")

    col_ok = st.columns(1)[0]
    if st.button("✓ סיום - נקה מסך", key="upload_results_ok", type="primary", use_container_width=True):
        # ניקוי מלא של כל ה-session state הקשור להעלאה
        keys_to_delete = [
            'validated_df', 'general_errors', 'confirm_upload',
            'upload_completed', 'upload_stats'
        ]
        for key in keys_to_delete:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()


def validate_excel_data(df: pd.DataFrame, api) -> Tuple[pd.DataFrame, List[str]]:
    """
    בדיקת תקינות הנתונים מה-CSV
    פורמט: username, full_name, email, password, shortid, department

    Args:
        df: DataFrame עם הנתונים מה-CSV
        api: SafeQAPI instance

    Returns:
        Tuple של (DataFrame מעודכן עם סטטוס, רשימת שגיאות כלליות)
    """
    errors = []

    # בדיקת עמודות נדרשות - בסדר מדויק
    required_columns = ['username', 'full_name']
    expected_columns = ['username', 'full_name', 'email', 'password', 'shortid', 'department']

    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        errors.append(f"❌ חסרות עמודות חובה: {', '.join(missing_columns)}")
        return df, errors

    # אזהרה אם העמודות לא בסדר הנכון
    if list(df.columns[:6]) != expected_columns[:len(df.columns[:6])]:
        errors.append(f"⚠️ העמודות לא בסדר הנכון. הסדר הנכון: {', '.join(expected_columns)}")

    # בדיקת כפילויות בתוך הקובץ עצמו
    duplicates_in_file = {}

    # בדיקת usernames כפולים בקובץ
    usernames_in_file = df['username'].str.strip()
    duplicate_usernames = usernames_in_file[usernames_in_file.duplicated()].unique()
    if len(duplicate_usernames) > 0:
        duplicates_in_file['usernames'] = list(duplicate_usernames)
        errors.append(f"⚠️ שמות משתמש כפולים בקובץ: {', '.join(duplicate_usernames)}")

    # בדיקת PINים כפולים בקובץ (רק אלה שלא ריקים)
    pins_in_file = df['shortid'].str.strip()
    non_empty_pins = pins_in_file[pins_in_file != '']
    duplicate_pins = non_empty_pins[non_empty_pins.duplicated()].unique()
    if len(duplicate_pins) > 0:
        duplicates_in_file['pins'] = list(duplicate_pins)
        errors.append(f"⚠️ PINים כפולים בקובץ: {', '.join(duplicate_pins)}")

    # בדיקת אימיילים כפולים בקובץ (רק אלה שלא ריקים)
    emails_in_file = df['email'].str.strip()
    non_empty_emails = emails_in_file[emails_in_file != '']
    duplicate_emails = non_empty_emails[non_empty_emails.duplicated()].unique()
    if len(duplicate_emails) > 0:
        duplicates_in_file['emails'] = list(duplicate_emails)
        errors.append(f"⚠️ אימיילים כפולים בקובץ: {', '.join(duplicate_emails)}")

    # הוספת עמודת סטטוס
    df['status'] = ''
    df['error_message'] = ''

    # בדיקת כל שורה
    for idx, row in df.iterrows():
        # הנתונים כבר string בגלל dtype=str, פשוט strip
        username = str(row.get('username', '')).strip()
        full_name = str(row.get('full_name', '')).strip()
        email = str(row.get('email', '')).strip()
        shortid = str(row.get('shortid', '')).strip()

        row_errors = []

        # בדיקת username חובה
        if not username:
            row_errors.append("שם משתמש חסר")
        else:
            # בדיקת username כפול בקובץ
            if 'usernames' in duplicates_in_file and username in duplicates_in_file['usernames']:
                row_errors.append("שם משתמש כפול בקובץ")
            else:
                # רק אם לא כפול בקובץ, בדוק במערכת
                username_exists, provider_name = api.check_username_exists(username)
                if username_exists:
                    row_errors.append(f"שם משתמש קיים במערכת ({provider_name})")

        # בדיקת שם מלא חובה
        if not full_name:
            row_errors.append("שם מלא חסר")

        # בדיקת אימייל
        if email:
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                row_errors.append("אימייל לא תקין")
            elif 'emails' in duplicates_in_file and email in duplicates_in_file['emails']:
                row_errors.append("אימייל כפול בקובץ")

        # בדיקת PIN כפול
        if shortid:
            # בדיקת PIN כפול בקובץ
            if 'pins' in duplicates_in_file and shortid in duplicates_in_file['pins']:
                row_errors.append("PIN כפול בקובץ")
            else:
                # רק אם לא כפול בקובץ, בדוק במערכת
                pin_exists, existing_user = api.check_pin_exists(shortid)
                if pin_exists:
                    row_errors.append(f"PIN כפול במערכת (קיים אצל {existing_user})")

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

    # בדיקת הרשאות - רק למנהלים מקומיים
    role = st.session_state.get('role', st.session_state.get('access_level', 'viewer'))
    local_username = st.session_state.get('local_username', None)

    if not (local_username and role in ['admin', 'superadmin']):
        st.error("❌ תכונה זו זמינה רק למנהלים מקומיים (Admin/SuperAdmin)")
        st.info("💡 יש להתחבר כמשתמש מקומי עם הרשאות ניהול (לא משתמש Entra)")
        return

    api = get_api_instance()
    logger = get_logger_instance()

    # הנחיות שימוש
    with st.expander("📋 הנחיות שימוש", expanded=False):
        st.markdown("""
        ### פורמט קובץ ה-CSV (בדיוק כמו הסקריפט המקורי):

        **⚠️ חשוב: הקובץ חייב להיות ללא שורת כותרות!**

        הקובץ חייב להכיל את העמודות הבאות **בסדר המדויק**:

        | מס' | עמודה | תיאור | חובה | הערות |
        |-----|--------|--------|------|-------|
        | 1 | שם משתמש | username | ✅ | שם ייחודי באנגלית |
        | 2 | שם מלא | full name | ✅ | שם פרטי ומשפחה בעברית |
        | 3 | אימייל | email | ❌ | פורמט תקין (או ריק) |
        | 4 | סיסמה | password | ❌ | ברירת מחדל: Aa123456 (או ריק) |
        | 5 | PIN | shortid | ❌ | קוד ייחודי 4-6 ספרות (או ריק) |
        | 6 | מחלקה | department | ❌ | שם המחלקה (או ריק) |

        ### דוגמה לקובץ CSV (ללא כותרות!):
        ```
        moshe.cohen,משה כהן,moshe@example.com,Aa123456,1234,מחלקת IT
        sarah.levi,שרה לוי,sarah@example.com,Aa123456,5678,מחלקת כספים
        david.israel,דוד ישראל,david@example.com,,2345,הנהלה
        yael.mizrahi,יעל מזרחי,,,3456,
        ```

        ### שימו לב:
        - **חשוב ביותר**: ללא שורת כותרות! השורה הראשונה היא כבר משתמש!
        - **חובה**: הקובץ חייב להיות בפורמט CSV (ייצא מ-Excel כ-CSV)
        - **חובה**: העמודות חייבות להיות בסדר המדויק (6 עמודות)
        - שם משתמש ושם מלא הם שדות חובה - השאר אופציונליים
        - אם לא מציינים סיסמה - תיווצר סיסמת ברירת מחדל: Aa123456
        - עמודות ריקות: השאר ריק בין הפסיקים (כמו בדוגמה)
        - המערכת תבדוק אם שמות משתמשים ו-PINים כבר קיימים
        """)

    st.markdown("---")

    # העלאת קובץ
    st.subheader("📁 העלאת קובץ")
    uploaded_file = st.file_uploader(
        "בחר קובץ CSV",
        type=['csv'],
        help="העלה קובץ CSV עם רשימת המשתמשים להעלאה (בפורמט: username, full_name, email, password, shortid, department)"
    )

    # ניקוי session state כאשר מסירים את הקובץ (לוחצים X)
    if uploaded_file is None:
        # אם היה קובץ לפני והעלאה בתהליך - נקה הכל
        keys_to_delete = [
            'validated_df', 'general_errors', 'confirm_upload',
            'upload_completed', 'upload_stats'
        ]
        for key in keys_to_delete:
            if key in st.session_state:
                del st.session_state[key]

    if uploaded_file is not None:
        try:
            # קריאת הקובץ CSV ללא כותרות (כמו בסקריפט המקורי)
            # העמודות בסדר: username, full_name, email, password, shortid, department
            # חשוב: קריאת כל העמודות כטקסט כדי לשמור 0 מובילים (ת.ז, PIN וכו')
            df = pd.read_csv(
                uploaded_file,
                encoding='utf-8',
                header=None,  # אין כותרות בקובץ
                names=['username', 'full_name', 'email', 'password', 'shortid', 'department'],
                dtype=str,  # קרא הכל כטקסט - חשוב לשמירת 0 מובילים!
                keep_default_na=False  # אל תמיר ערכים ריקים ל-NaN
            )

            st.success(f"✅ הקובץ נטען בהצלחה! ({len(df)} שורות נתונים)")
            st.info(f"📊 הקובץ מכיל {len(df)} משתמשים (ללא שורת כותרות)")

            # תצוגת נתונים גולמיים
            with st.expander("👁️ הצגת נתונים גולמיים", expanded=False):
                st.write("**שימו לב:** הכותרות באפור (username, full_name וכו') הן לתצוגה בלבד. הנתונים מתחילים מאינדקס 0.")
                st.write(f"**מספר שורות בקובץ:** {len(df)}")
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
                    validated_df[['username', 'full_name', 'email', 'shortid', 'department', 'status', 'error_message']],
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
                # בדיקת תקינות - לוודא ש-validated_df קיים
                if 'validated_df' not in st.session_state:
                    st.error("❌ שגיאה: נתוני הקובץ אינם זמינים. אנא העלה את הקובץ מחדש.")
                    if 'confirm_upload' in st.session_state:
                        del st.session_state.confirm_upload
                    return

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
                    # הנתונים כבר string בגלל dtype=str, פשוט strip
                    username = str(row.get('username', '')).strip()
                    full_name = str(row.get('full_name', '')).strip()
                    email = str(row.get('email', '')).strip()
                    password = str(row.get('password', '')).strip()
                    shortid = str(row.get('shortid', '')).strip()
                    department = str(row.get('department', '')).strip()

                    # ברירת מחדל לסיסמה אם ריקה
                    if not password:
                        password = 'Aa123456'

                    details = {
                        'fullname': full_name,
                        'email': email,
                        'password': password,
                        'shortid': shortid,
                        'department': department
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

                # שמירת התוצאות ב-session state והצגת Dialog
                st.session_state.upload_stats = stats
                st.session_state.upload_completed = True
                # חשוב! נקה את confirm_upload לפני rerun כדי למנוע לופ אינסופי
                if 'confirm_upload' in st.session_state:
                    del st.session_state.confirm_upload
                st.rerun()

        except Exception as e:
            st.error(f"❌ שגיאה בקריאת הקובץ: {str(e)}")
            st.info("💡 ודא שהקובץ בפורמט תקין (CSV)")

    # הצגת Dialog עם תוצאות (אחרי rerun)
    if st.session_state.get('upload_completed', False):
        show_upload_results_dialog(st.session_state.upload_stats)


if __name__ == "__main__":
    show()
