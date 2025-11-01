#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SafeQ Cloud Manager - Search and Edit Users Page
דף חיפוש ועריכת משתמשים - עם לוגיקה מלאה
"""

import streamlit as st
import pandas as pd
import sys
import os
import re

# הוספת תיקיית app ל-path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import get_api_instance, get_logger_instance, check_authentication, CONFIG
from permissions import filter_users_by_departments

def show():
    """הצגת דף חיפוש ועריכת משתמשים"""
    check_authentication()

    # RTL styling - חזק מאוד + יישור ימינה
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

        .stTextInput > div, .stSelectbox > div, .stNumberInput > div {
            direction: rtl !important;
            text-align: right !important;
        }

        .stTextInput > div > div, .stSelectbox > div > div, .stNumberInput > div > div {
            direction: rtl !important;
            text-align: right !important;
        }

        .stTextInput input, .stSelectbox select, .stNumberInput input {
            direction: rtl !important;
            text-align: right !important;
        }

        .stTextInput label, .stSelectbox label, .stNumberInput label {
            direction: rtl !important;
            text-align: right !important;
            display: block !important;
        }

        /* Checkbox RTL */
        .stCheckbox {
            direction: rtl !important;
            text-align: right !important;
        }

        /* Button RTL */
        .stButton {
            direction: rtl !important;
            text-align: right !important;
        }

        /* כל הדיווים */
        div[data-baseweb] {
            direction: rtl !important;
        }
    </style>
    """, unsafe_allow_html=True)

    api = get_api_instance()
    logger = get_logger_instance()

    st.header("🔍 חיפוש ועריכת משתמשים")

    # ============ חיפוש משתמשים ============
    st.subheader("חיפוש")

    # שורה ראשונה: מקור (בצד ימין)
    col_spacer, col_provider = st.columns([1, 1])
    with col_spacer:
        pass  # עמודה ריקה משמאל
    with col_provider:
        # בדיקת הרשאות - רק superadmin יכול לבחור Entra
        role = st.session_state.get('role', st.session_state.get('access_level', 'viewer'))
        if role == 'superadmin':
            provider_options = ["מקומי (12348)", "Entra (12351)"]
            default_index = 0  # ברירת מחדל: מקומי
        else:
            provider_options = ["מקומי (12348)"]
            default_index = 0

        search_provider = st.selectbox("מקור *", provider_options, index=default_index,
                                     help="רק superadmin יכול לבחור Entra" if role != 'superadmin' else None)

    # שורה שנייה: חיפוש לפי ושדות (עמודה ימנית מכיל הכל)
    col_left_spacer, col_right_fields = st.columns([1, 5])

    with col_left_spacer:
        pass  # עמודה ריקה משמאל

    with col_right_fields:
        search_type_map_en_to_he = {
            "Username": "שם משתמש", "Full Name": "שם מלא",
            "Department": "מחלקה", "Email": "אימייל"
        }
        search_type_he_options = list(search_type_map_en_to_he.values())
        search_type_he = st.selectbox("חיפוש לפי", search_type_he_options)

        search_type_map_he_to_en = {v: k for k, v in search_type_map_en_to_he.items()}
        search_type = search_type_map_he_to_en[search_type_he]

        search_term = st.text_input(f"הזן {search_type_he} לחיפוש",
                                   help="השתמש ב-* כתו כלשהו (wildcard). לדוגמה: *admin*, test*")
        partial_search = st.checkbox("התאמה חלקית (מכיל)", value=True,
                                   help="מצא את כל המשתמשים המכילים את ערך החיפוש")

    # שורה שלישית: תוצאות להצגה (בצד ימין)
    col_spacer2, col_max_results = st.columns([1, 5])
    with col_spacer2:
        pass  # עמודה ריקה משמאל
    with col_max_results:
        max_results = st.number_input("תוצאות להצגה", min_value=1, max_value=500, value=200)

    if st.button("🔍 חפש", key="search_users_btn", type="primary", use_container_width=True):
        if not search_term:
             st.error("נא להזין ערך לחיפוש")
        elif not search_provider:
            st.error("נא לבחור מקור - שדה זה הינו חובה")
        else:
            provider_id = CONFIG['PROVIDERS']['LOCAL'] if search_provider.startswith("מקומי") else CONFIG['PROVIDERS']['ENTRA']

            user_groups_str = ', '.join([g['displayName'] for g in st.session_state.get('user_groups', [])]) if st.session_state.get('user_groups') else ""
            logger.log_action(st.session_state.username, "Advanced Search",
                            f"Type: {search_type}, Term: {search_term}, Provider: {search_provider}, Partial: {partial_search}",
                            st.session_state.get('user_email', ''), user_groups_str, True, st.session_state.get('access_level', 'viewer'))

            with st.spinner("מחפש..."):
                all_users = api.get_users(provider_id, 500)
                matching_users = []
                search_lower = search_term.lower()

                # Check if wildcard is used
                use_wildcard = '*' in search_term
                if use_wildcard:
                    # Convert wildcard pattern to regex
                    # Escape special regex chars except *
                    regex_pattern = re.escape(search_lower).replace(r'\*', '.*')
                    # Add anchors for non-partial search
                    if not partial_search:
                        regex_pattern = '^' + regex_pattern + '$'
                    try:
                        search_regex = re.compile(regex_pattern)
                    except re.error:
                        st.error("תבנית חיפוש לא תקינה")
                        search_regex = None
                else:
                    search_regex = None

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

                    # Perform matching based on search mode
                    if use_wildcard and search_regex:
                        # Wildcard search using regex
                        match_found = bool(search_regex.search(user_field)) if user_field else False
                    elif partial_search:
                        # Partial match (contains)
                        match_found = search_lower in user_field if user_field else False
                    else:
                        # Exact match
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

    # ============ תוצאות חיפוש ============
    if 'search_results' in st.session_state and st.session_state.search_results:
        matching_users = st.session_state.search_results
        st.success(f"✅ נמצאו {len(matching_users)} משתמשים")

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
            st.dataframe(df, use_container_width=True, height=400)

            # כפתורי פעולה
            col_spacer3, col_csv, col_clear = st.columns([1, 3, 1])
            with col_spacer3:
                pass  # עמודה ריקה משמאל
            with col_csv:
                csv = df.to_csv(index=False)
                st.download_button(
                    "💾 הורד CSV", csv.encode('utf-8-sig'),
                    f"search_results_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    "text/csv", key="download_search_results",
                    use_container_width=True
                )
            with col_clear:
                if st.button("🗑️ נקה", key="clear_search_results", use_container_width=True):
                    if 'search_results' in st.session_state:
                        del st.session_state.search_results
                    st.rerun()

            st.markdown("---")

            # ============ עריכת משתמש ============
            st.subheader("✏️ ביצוע פעולות על משתמשים")

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
                # בחירת משתמש
                selected_label = st.selectbox(
                    "בחר משתמש מהתוצאות",
                    user_options,
                    key="edit_user_select"
                )

                if selected_label and selected_label in user_mapping:
                    selected_username = user_mapping[selected_label]

                    # כפתורים לפעולות שונות
                    st.markdown("**פעולות זמינות:**")

                    col_edit, col_delete, col_info = st.columns(3)

                    with col_edit:
                        if st.button("✏️ ערוך פרטים", key="edit_user_btn", use_container_width=True):
                            st.info(f"📝 עריכת פרטי משתמש: {selected_username}")
                            st.warning("🔨 תכונת עריכה בפיתוח")

                    with col_delete:
                        # בדיקת הרשאות למחיקה
                        can_delete = role in ['admin', 'superadmin']
                        if st.button("🗑️ מחק משתמש", key="delete_user_btn", disabled=not can_delete, use_container_width=True):
                            st.error(f"⚠️ מחיקת משתמש: {selected_username}")
                            st.warning("🔨 תכונת מחיקה בפיתוח")

                    with col_info:
                        if st.button("ℹ️ פרטים מלאים", key="view_user_info_btn", use_container_width=True):
                            st.info(f"📋 צפייה במידע מלא על: {selected_username}")
                            st.warning("🔨 תכונת הצגת פרטים מלאים בפיתוח")

if __name__ == "__main__":
    show()
