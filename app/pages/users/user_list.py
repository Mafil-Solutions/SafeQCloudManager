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

# הוספת תיקיית app ל-path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import get_api_instance, get_logger_instance, check_authentication, CONFIG
from permissions import filter_users_by_departments

def show():
    """הצגת דף רשימת משתמשים"""
    check_authentication()

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

    # שורה שנייה: משתמשים להצגה וכפתור
    col_num, col_btn = st.columns([2, 2])

    with col_num:
        max_users = st.number_input("משתמשים להצגה", min_value=10, max_value=1000, value=200)

    with col_btn:
        st.write("")  # ריווח לגובה
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
                                st.session_state.get('user_email', ''), user_groups_str, True, st.session_state.get('access_level', 'viewer'))
        else:
            st.warning("לא נמצאו משתמשים")

if __name__ == "__main__":
    show()
