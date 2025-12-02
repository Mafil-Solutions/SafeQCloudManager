#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SafeQ Cloud Manager - User List Page
דף רשימת משתמשים
"""

import streamlit as st
import pandas as pd
import sys
import os
import io

# הוספת תיקיית app ל-path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import get_api_instance, get_logger_instance, check_authentication, CONFIG
from permissions import filter_users_by_departments

def export_to_excel(df: pd.DataFrame, sheet_name: str) -> bytes:
    """ייצוא DataFrame ל-Excel עם עיצוב"""
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False, engine='openpyxl')

        # עיצוב הגליון
        workbook = writer.book
        worksheet = writer.sheets[sheet_name]

        # רוחב עמודות אוטומטי
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter

            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass

            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width

    output.seek(0)
    return output.getvalue()

def show():
    """הצגת דף רשימת משתמשים"""
    check_authentication()

    # הוספת CSS ל-RTL וכפתורים
    st.markdown("""
    <style>
        /* DataFrame RTL */
        .stDataFrame {
            direction: rtl !important;
        }

        /* הפוך את כל האפליקציה ל־RTL */
        .stApp {
            direction: rtl !important;
        }

        /* מיקום בלוק התוכן הראשי לימין */
        .block-container {
            text-align: right !important;
            direction: rtl !important;
        }

        /* עמודות - RTL עם יישור ימינה */
        div[data-testid="column"] {
            direction: rtl !important;
            text-align: right !important;
            display: flex !important;
            justify-content: flex-end !important;
        }

        /* כל אלמנטי הטופס - RTL חזק */
        .stTextInput, .stSelectbox, .stNumberInput {
            direction: rtl !important;
            text-align: right !important;
            width: 100% !important;
        }

        /* עיצוב כפתורים קטנים יותר */
        .small-button button {
            font-size: 14px !important;
            padding: 8px 16px !important;
            min-height: 38px !important;
            height: 38px !important;
        }
    </style>
    """, unsafe_allow_html=True)

    api = get_api_instance()
    logger = get_logger_instance()

    st.header("רשימת משתמשים")

    # שורה ראשונה: צ'קבוקס מקומיים
    col_check1,  = st.columns([1])
    with col_check1:
        show_local = st.checkbox("משתמשים מקומיים", value=True)

    # רק superadmin יכול לראות משתמשי Entra
    role = st.session_state.get('role', st.session_state.get('access_level', 'viewer'))
    if role == 'superadmin':
        col_check2, = st.columns([1])
        with col_check2:
            show_entra = st.checkbox("משתמשי Entra", value=True)
    else:
        show_entra = False  # אחרים לא רואים Entra בכלל

    # שורה שנייה: משתמשים להצגה
    col_spacer2, col_max_users = st.columns([1, 4])
    with col_max_users:
        pass  # עמודה ריקה משמאל
    with col_spacer2:
        max_users = st.number_input("משתמשים להצגה", min_value=10, max_value=1000, value=200)

    # שורה שלישית: כפתור טעינה
    load_button = st.button("🔄 טען משתמשים", type="primary", key="load_users_main", use_container_width=True)

    if load_button:
        user_groups_str = ', '.join([g['displayName'] for g in st.session_state.get('user_groups', [])]) if st.session_state.get('user_groups') else ""
        logger.log_action(
            st.session_state.username, "Load Users",
            f"Local: {show_local}, Entra: {show_entra}, Max: {max_users}",
            st.session_state.get('user_email', ''), user_groups_str, True, st.session_state.get('access_level', 'viewer')
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

                # שמירה ב-session_state
                st.session_state.user_list_data = filtered_users

    # הצגת טבלה אם יש נתונים
    if 'user_list_data' in st.session_state and st.session_state.user_list_data:
        filtered_users = st.session_state.user_list_data

        df_data = []
        for idx, user in enumerate(filtered_users, start=1):
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

            # סדר העמודות: מס' שורה, שם משתמש, שם מלא, אימייל, PIN, מחלקה, מקור
            # ללא "מזהה ספק"
            df_data.append({
                '#': idx,
                'שם משתמש': user.get('userName', user.get('username', '')),
                'שם מלא': user.get('fullName', ''),
                'אימייל': user.get('email', ''),
                'PIN': pin_code,
                'מחלקה': user.get('department', department),
                'סוג משתמש': user.get('source', '')
            })

        df = pd.DataFrame(df_data)

        # קביעת סדר עמודות הפוך (RTL) - מימין לשמאל: #, שם משתמש, שם מלא, אימייל, PIN, מחלקה, מקור
        df = df[['סוג משתמש', 'מחלקה', 'PIN', 'אימייל', 'שם מלא', 'שם משתמש', '#']]

        # הצגת הטבלה - RTL וללא height
        st.dataframe(df, use_container_width=True, hide_index=True)

        # כפתורים - הורד Excel ונקה בשורה אחת
        col_excel, col_clear = st.columns(2)
        with col_excel:
            excel_data = export_to_excel(df, "users")
            st.markdown('<div class="small-button">', unsafe_allow_html=True)
            st.download_button(
                "📥 ייצא ל-Excel",
                excel_data,
                f"users_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_user_list",
                use_container_width=True
            )
            st.markdown('</div>', unsafe_allow_html=True)

        with col_clear:
            st.markdown('<div class="small-button">', unsafe_allow_html=True)
            if st.button("🗑️ נקה", key="clear_user_list", use_container_width=True):
                if 'user_list_data' in st.session_state:
                    del st.session_state.user_list_data
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        user_groups_str = ', '.join([g['displayName'] for g in st.session_state.get('user_groups', [])]) if st.session_state.get('user_groups') else ""
        logger.log_action(st.session_state.username, "Users Loaded",
                        f"Count: {len(filtered_users)}",
                        st.session_state.get('user_email', ''), user_groups_str, True, st.session_state.get('access_level', 'viewer'))

if __name__ == "__main__":
    show()
