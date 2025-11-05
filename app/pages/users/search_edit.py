#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SafeQ Cloud Manager - Search and Edit Users Page
דף חיפוש ועריכת משתמשים - העתקה מלאה מ-MAIN
"""

import streamlit as st
import pandas as pd
import sys
import os
import re

# הוספת תיקיית app ל-path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import get_api_instance, get_logger_instance, check_authentication, CONFIG
from permissions import filter_users_by_departments, filter_groups_by_departments

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

        /* תיקון #5: עיצוב כפתור X למחיקת קבוצה */
        /* * אנחנו משתמשים בסלקטור תכונה (attribute selector)
         * שמחפש כפתור שה-title שלו (שנוצר ע"י help=)
         * מתחיל ב-"הסר מקבוצה"
        */
        .remove-group-button button[data-testid="stBaseButton-secondary"] {
            background-color: 'white' !important;
            color: #ff4444 !important;
            border: 1px solid #ff4444 !important;
            padding: 2px 8px !important;
            font-size: 14px !important;
            font-weight: bold !important;
            min-height: 25px !important;
            height: 25px !important;
        }
        
        /* אפשר להוסיף גם עיצוב ל-hover אם רוצים */
        .remove-group-button button[data-testid="stBaseButton-secondary"] {
            opacity: 0.8 !important;
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

    st.header("🔍 חיפוש ועריכת משתמשים")

    # ============ חיפוש משתמשים ============
    st.subheader("חיפוש")

    # שורה ראשונה: מקור (בצד ימין)
    col_provider, col_spacer = st.columns([3, 4])
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

    with col_spacer:
        pass  # עמודה ריקה משמאל

    # שורה שנייה: חיפוש לפי ושדות (עמודה ימנית מכיל הכל)
    col_right_fields, col_left_spacer = st.columns([3, 4])

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

    with col_left_spacer:
        pass  # עמודה ריקה משמאל

    # שורה שלישית: תוצאות להצגה (בצד ימין) - תיקון #6: הקטנת השדה
    col_max_results, col_spacer2 = st.columns([2, 5])
    with col_max_results:
        max_results = st.number_input("תוצאות להצגה", min_value=1, max_value=500, value=200)
    with col_spacer2:
        pass  # עמודה ריקה משמאל

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
        for idx, user in enumerate(matching_users, start=1):
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

            # סדר העמודות: מס' שורה, שם משתמש, שם מלא, אימייל, PIN, מחלקה, מקור
            # ללא "מזהה ספק"
            df_data.append({
                '#': idx,
                'שם משתמש': username,
                'שם מלא': full_name,
                'אימייל': email,
                'PIN': pin_code,
                'מחלקה': department
            })

        if df_data:
            df = pd.DataFrame(df_data)

            # קביעת סדר עמודות הפוך (RTL) - מימין לשמאל: #, שם משתמש, שם מלא, אימייל, PIN, מחלקה
            df = df[['מחלקה', 'PIN', 'אימייל', 'שם מלא', 'שם משתמש', '#']]

            # הצגת הטבלה - RTL וללא height
            st.dataframe(df, use_container_width=True, hide_index=True)

            # כפתורי פעולה - הורד CSV ונקה, קטנים יותר
            col_csv, col_clear = st.columns(2)
            with col_csv:
                csv = df.to_csv(index=False)
                st.markdown('<div class="small-button">', unsafe_allow_html=True)
                st.download_button(
                    "💾 הורד CSV",
                    csv.encode('utf-8-sig'),
                    f"search_results_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    "text/csv",
                    key="download_search_results",
                    use_container_width=True
                )
                st.markdown('</div>', unsafe_allow_html=True)

            with col_clear:
                st.markdown('<div class="small-button">', unsafe_allow_html=True)
                if st.button("🗑️ נקה", key="clear_search_results", use_container_width=True):
                    if 'search_results' in st.session_state:
                        del st.session_state.search_results
                        if 'selected_users' in st.session_state:
                            del st.session_state.selected_users
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

            st.markdown("---")

            # ============ ביצוע פעולות על משתמשים - CHECKBOXES ============
            st.subheader("👤 בחר משתמשים לביצוע פעולות")

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
                # אתחול רשימת בחירה ב-session_state
                if 'selected_users' not in st.session_state:
                    st.session_state.selected_users = []

                # אתחול counter לרענון widgets
                if 'user_checkbox_counter' not in st.session_state:
                    st.session_state.user_checkbox_counter = 0

                # כפתור "בחר הכל" / "נקה בחירה" - תיקון: key אחיד למניעת flickering
                col_select_all, col_count = st.columns([1, 2])
                with col_select_all:
                    all_usernames = list(user_mapping.values())
                    # בדיקה אם כל המשתמשים נבחרו
                    all_selected = st.session_state.selected_users and len(st.session_state.selected_users) == len(user_options)

                    # כפתור אחד עם key אחיד
                    button_label = "❌ נקה בחירה" if all_selected else "✅ בחר הכל"
                    if st.button(button_label, key="toggle_select_all_users", use_container_width=True):
                        if all_selected:
                            st.session_state.selected_users = []
                        else:
                            st.session_state.selected_users = all_usernames.copy()
                        st.session_state.user_checkbox_counter += 1
                        st.rerun()

                with col_count:
                    num_selected = len(st.session_state.selected_users)
                    if num_selected > 0:
                        st.info(f"✓ נבחרו {num_selected} משתמשים")

                # הצגת checkboxes לכל משתמש
                st.markdown("**בחר משתמשים:**")

                # תיקון: בנייה מחדש של רשימת בחירה מהצ'קבוקסים
                temp_selections = []

                for label in user_options:
                    username = user_mapping[label]
                    is_checked = username in st.session_state.selected_users

                    # תיקון: checkbox עם key דינמי שכולל counter
                    checkbox_result = st.checkbox(label, value=is_checked,
                                                 key=f"user_checkbox_{username}_{st.session_state.user_checkbox_counter}")

                    # אוסף את כל הבחירות
                    if checkbox_result:
                        temp_selections.append(username)

                # עדכון הסטייט רק אם השתנה משהו
                if temp_selections != st.session_state.selected_users:
                    st.session_state.selected_users = temp_selections
                    st.rerun()

                # קביעת משתמש לפעולות בודדות (רק אם נבחר אחד)
                if len(st.session_state.selected_users) == 1:
                    selected_user_for_actions = st.session_state.selected_users[0]
                    st.success(f"✅ משתמש נבחר: **{selected_user_for_actions}**")
                elif len(st.session_state.selected_users) > 1:
                    selected_user_for_actions = None  # פעולות bulk
                    # תיקון #1: סגירת טופס עריכה כשעוברים ל-bulk
                    if 'user_to_edit' in st.session_state:
                        del st.session_state.user_to_edit
                    if 'edit_username' in st.session_state:
                        del st.session_state.edit_username
                    st.info(f"🔀 מצב bulk: {len(st.session_state.selected_users)} משתמשים נבחרו")
                else:
                    selected_user_for_actions = None
            else:
                selected_user_for_actions = None

            # ============ מצב BULK - 2+ משתמשים ============
            if len(st.session_state.selected_users) >= 2:
                st.markdown("---")
                st.subheader(f"🔀 פעולות קבוצתיות ({len(st.session_state.selected_users)} משתמשים)")

                role = st.session_state.get('role', st.session_state.get('access_level', 'viewer'))

                if role == 'viewer':
                    st.info("👁️ צפייה בלבד - אין הרשאת הוספה קבוצתית")
                else:
                    # תיקון #2: בדיקה אם פעולת bulk התחילה
                    bulk_operation_in_progress = st.session_state.get('bulk_operation_in_progress', False)

                    if not bulk_operation_in_progress:
                        st.markdown("**➕ הוספה קבוצתית לקבוצה**")

                        # טעינת קבוצות
                        if st.button("📋 טען קבוצות זמינות", key="load_groups_bulk"):
                            with st.spinner("טוען קבוצות..."):
                                available_groups = api.get_groups(CONFIG['PROVIDERS']['LOCAL'], max_records=500)
                                if available_groups:
                                    allowed_departments = st.session_state.get('allowed_departments', [])
                                    filtered_groups = filter_groups_by_departments(available_groups, allowed_departments)
                                    group_names = [g.get('groupName') or g.get('name') or str(g) for g in filtered_groups
                                                 if not (g.get('groupName') == "Local Admins" and st.session_state.get('auth_method') != 'local')]
                                    st.session_state.available_groups = group_names
                                    st.success(f"נטענו {len(group_names)} קבוצות מורשות")
                                else:
                                    st.warning("לא נמצאו קבוצות")

                        # בחירת קבוצה
                        if 'available_groups' in st.session_state and st.session_state.available_groups:
                            target_group = st.selectbox("בחר קבוצה להוספה", options=st.session_state.available_groups, key="select_group_bulk")
                        else:
                            target_group = None
                            st.text_input("שם קבוצה", disabled=True, placeholder="לחץ על 'טען קבוצות זמינות' תחילה", key="group_bulk_disabled")

                        # כפתור הוספה bulk
                        if st.button(f"➕ הוסף {len(st.session_state.selected_users)} משתמשים לקבוצה",
                                   key="bulk_add_to_group",
                                   type="primary",
                                   disabled=not target_group):
                            # תיקון #2: סימון שהפעולה התחילה + שמירת הקבוצה שנבחרה
                            st.session_state.bulk_operation_in_progress = True
                            st.session_state.bulk_target_group = target_group
                            st.rerun()

                    # תיקון #2: הצגת התוצאות אחרי שהפעולה התחילה
                    if bulk_operation_in_progress:
                        target_group = st.session_state.get('bulk_target_group')

                        # תיקון #2: בדיקה מוקדמת - איזה משתמשים כבר בקבוצה
                        with st.spinner("בודק משתמשים קיימים בקבוצה..."):
                            group_members_response = api.get_group_members(target_group)
                            existing_usernames = []

                            if group_members_response:
                                # טיפול בפורמטים שונים של תגובה
                                if isinstance(group_members_response, dict):
                                    if 'items' in group_members_response:
                                        members_list = group_members_response['items']
                                    else:
                                        # אולי זה משתמש בודד?
                                        members_list = [group_members_response]
                                elif isinstance(group_members_response, list):
                                    members_list = group_members_response
                                else:
                                    members_list = []

                                # חילוץ שמות משתמשים
                                for m in members_list:
                                    if isinstance(m, dict):
                                        username = m.get('userName') or m.get('username') or m.get('name', '')
                                        if username:
                                            existing_usernames.append(username)

                            # משתמשים שכבר בקבוצה
                            already_in_group = [u for u in st.session_state.selected_users if u in existing_usernames]
                            # משתמשים שצריך להוסיף
                            users_to_add = [u for u in st.session_state.selected_users if u not in existing_usernames]

                        # אתחול משתנים
                        success_count = 0
                        fail_count = 0
                        failed_users = []

                        # הצגת אזהרה אם יש משתמשים שכבר בקבוצה
                        if already_in_group:
                            st.warning(f"⚠️ שים לב: {len(already_in_group)} משתמשים כבר שייכים לקבוצה **{target_group}** ולא יתווספו:")
                            for u in already_in_group:
                                st.write(f"  • {u}")

                        if not users_to_add:
                            st.info("כל המשתמשים שנבחרו כבר שייכים לקבוצה זו.")
                        else:
                            st.info(f"מוסיף {len(users_to_add)} משתמשים לקבוצה...")

                            progress_bar = st.progress(0)
                            status_text = st.empty()

                            total = len(users_to_add)

                            for idx, username in enumerate(users_to_add):
                                status_text.text(f"מוסיף {idx + 1}/{total}: {username}...")
                                progress_bar.progress((idx + 1) / total)

                                success = api.add_user_to_group(username, target_group)
                                if success:
                                    success_count += 1
                                else:
                                    fail_count += 1
                                    failed_users.append(username)

                        # הצגת תוצאות מיד
                        st.markdown("---")
                        st.subheader("📊 סיכום פעולה קבוצתית")

                        col_success, col_fail, col_skip = st.columns(3)
                        with col_success:
                            st.metric("✅ הצלחות", success_count if users_to_add else 0)
                        with col_fail:
                            st.metric("❌ כשלונות", fail_count if users_to_add else 0)
                        with col_skip:
                            st.metric("⏭️ כבר בקבוצה", len(already_in_group))

                        if users_to_add and success_count > 0:
                            st.success(f"✅ {success_count} משתמשים נוספו בהצלחה לקבוצה '{target_group}'")

                        if already_in_group:
                            st.info(f"{len(already_in_group)} משתמשים כבר שייכים לקבוצה ולא התווספו ℹ️")

                        if failed_users:
                            st.error(f"❌ {fail_count} משתמשים נכשלו:")
                            for user in failed_users:
                                st.write(f"  • {user}")

                        # לוג
                        user_groups_str = ', '.join([g['displayName'] for g in st.session_state.get('user_groups', [])]) if st.session_state.get('user_groups') else ""
                        logger.log_action(st.session_state.username, "Bulk Add to Group",
                                        f"Added {success_count if users_to_add else 0}/{len(st.session_state.selected_users)} users to {target_group} ({len(already_in_group)} already in group)",
                                        st.session_state.get('user_email', ''), user_groups_str,
                                        success_count > 0 if users_to_add else False, st.session_state.get('access_level', 'viewer'))

                        # ניקוי בחירה לאחר הצגת התוצאות
                        if st.button("✓ אישור וניקוי בחירה", key="clear_selection_after_bulk", type="primary", use_container_width=True):
                            st.session_state.selected_users = []
                            # תיקון #2: ניקוי flags של bulk operation
                            if 'bulk_operation_in_progress' in st.session_state:
                                del st.session_state.bulk_operation_in_progress
                            if 'bulk_target_group' in st.session_state:
                                del st.session_state.bulk_target_group
                            # תיקון #1: ניקוי טופס עריכה
                            if 'user_to_edit' in st.session_state:
                                del st.session_state.user_to_edit
                            if 'edit_username' in st.session_state:
                                del st.session_state.edit_username
                            st.rerun()

            # ============ מצב SINGLE USER - משתמש אחד בלבד ============
            elif selected_user_for_actions:

                selected_user_data = None
                for user in matching_users:
                    if user.get('userName', user.get('username', '')) == selected_user_for_actions:
                        selected_user_data = user
                        break

                st.markdown("---")
                st.subheader("👥 ניהול קבוצות משתמש")

                # בדיקת הרשאות למשתמש
                role = st.session_state.get('role', st.session_state.get('access_level', 'viewer'))

                # Section 1: הצגה והוספה לקבוצות
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("**👥 הצגת קבוצות משתמש**")
                    if st.button("🔍 הצג קבוצות", key="get_selected_user_groups_new", disabled=not selected_user_for_actions):
                        with st.spinner(f"טוען קבוצות עבור {selected_user_for_actions}..."):
                            user_groups = api.get_user_groups(selected_user_for_actions)
                            if user_groups:
                                # שמירה ב-session_state להצגה עם X
                                st.session_state.user_groups_display = {
                                    'username': selected_user_for_actions,
                                    'groups': user_groups
                                }
                                st.rerun()
                            else:
                                st.warning("לא נמצאו קבוצות עבור משתמש זה")

                    # הצגת קבוצות עם אפשרות הסרה
                    if 'user_groups_display' in st.session_state:
                        display_data = st.session_state.user_groups_display
                        if display_data['username'] == selected_user_for_actions:
                            st.success(f"קבוצות עבור {selected_user_for_actions}:")

                            for group in display_data['groups']:
                                group_name = group.get('groupName') or group.get('name') or str(group)

                                # שורה עם X אדום - רק ל-admin ו-superadmin - תיקון: קירוב X לשם הקבוצה
                                role = st.session_state.get('role', st.session_state.get('access_level', 'viewer'))
                                if role in ['admin', 'superadmin']:
                                    col_group, col_remove_btn = st.columns([1, 4], gap="small")
                                    with col_group:
                                        st.write(f"• {group_name}")
                                    with col_remove_btn:
                                        st.markdown('<div class="remove-group-button">', unsafe_allow_html=True)
                                        if st.button("❌", key=f"remove_{selected_user_for_actions}_from_{group_name}",
                                                   help=f"הסר מקבוצה {group_name}"):
                                            # שמירת בקשת הסרה לאימות
                                            st.session_state.remove_from_group_request = {
                                                'username': selected_user_for_actions,
                                                'group': group_name
                                            }
                                            st.rerun()
                                     
                                else:
                                    st.write(f"• {group_name}")

                with col2:
                    st.markdown("**➕ הוספה לקבוצה**")
                    # רק support/admin/superadmin יכולים להוסיף לקבוצה
                    if role == 'viewer':
                        st.info("👁️ צפייה בלבד - אין הרשאת הוספה")
                    else:
                        if st.button("📋 טען קבוצות", key="load_groups_for_add_new", help="טען את רשימת הקבוצות הזמינות", disabled=not selected_user_for_actions):
                            with st.spinner("טוען קבוצות..."):
                                available_groups = api.get_groups(CONFIG['PROVIDERS']['LOCAL'], max_records=500)
                                if available_groups:
                                    # סינון לפי מחלקות מורשות
                                    allowed_departments = st.session_state.get('allowed_departments', [])
                                    filtered_groups = filter_groups_by_departments(available_groups, allowed_departments)

                                    # הסרת "Local Admins" למשתמשים שלא התחברו מקומי
                                    group_names = [g.get('groupName') or g.get('name') or str(g) for g in filtered_groups if not (g.get('groupName') == "Local Admins" and st.session_state.get('auth_method') != 'local')]
                                    st.session_state.available_groups = group_names
                                    st.success(f"נטענו {len(group_names)} קבוצות מורשות")
                                else:
                                    st.warning("לא נמצאו קבוצות")

                        if 'available_groups' in st.session_state and st.session_state.available_groups:
                            target_group = st.selectbox("בחר קבוצה", options=st.session_state.available_groups, key="select_target_group_new")
                        else:
                            target_group = None
                            st.text_input("שם/מזהה קבוצה", key="target_group_input_new", disabled=True, placeholder="לחץ על 'טען קבוצות' תחילה")

                        if st.button("➕ הוסף לקבוצה", key="add_user_to_group_new", disabled=not selected_user_for_actions or not target_group):
                            # בדיקה אם המשתמש כבר שייך לקבוצה
                            with st.spinner(f"בודק אם {selected_user_for_actions} כבר שייך לקבוצה..."):
                                user_groups = api.get_user_groups(selected_user_for_actions)
                                user_group_names = [g.get('groupName') or g.get('name') or str(g) for g in user_groups]

                                if target_group in user_group_names:
                                    st.warning(f"⚠️ שים לב: המשתמש **{selected_user_for_actions}** כבר שייך לקבוצה **{target_group}**")
                                else:
                                    with st.spinner(f"מוסיף את {selected_user_for_actions} לקבוצה {target_group}..."):
                                        success = api.add_user_to_group(selected_user_for_actions, target_group)
                                        if success:
                                            st.success(f"✅ המשתמש {selected_user_for_actions} נוסף בהצלחה לקבוצה {target_group}")
                                            # רענון רשימת קבוצות אחרי הוספה
                                            user_groups = api.get_user_groups(selected_user_for_actions)
                                            if user_groups:
                                                st.session_state.user_groups_display = {
                                                    'username': selected_user_for_actions,
                                                    'groups': user_groups
                                                }
                                        else:
                                            st.error("❌ ההוספה לקבוצה נכשלה")

                # אימות הסרה מקבוצה (מחוץ לעמודות, בשורה נפרדת)
                if 'remove_from_group_request' in st.session_state:
                    request = st.session_state.remove_from_group_request
                    if request['username'] == selected_user_for_actions:
                        st.markdown("---")
                        st.warning(f"⚠️ האם אתה בטוח שברצונך להסיר את **{request['username']}** מהקבוצה **{request['group']}**?")

                        col_spacer1, col_yes, col_no, col_spacer2 = st.columns([1, 2, 2, 1])
                        with col_yes:
                            if st.button("✅ אשר", key="confirm_remove_from_group_yes", type="primary", use_container_width=True):
                                with st.spinner(f"מסיר את {request['username']} מהקבוצה {request['group']}..."):
                                    success = api.remove_user_from_group(request['username'], request['group'])
                                    if success:
                                        st.success(f"✅ המשתמש הוסר בהצלחה מהקבוצה {request['group']}")

                                        # לוג
                                        user_groups_str = ', '.join([g['displayName'] for g in st.session_state.get('user_groups', [])]) if st.session_state.get('user_groups') else ""
                                        logger.log_action(st.session_state.username, "Remove from Group",
                                                        f"Removed {request['username']} from {request['group']}",
                                                        st.session_state.get('user_email', ''), user_groups_str, True,
                                                        st.session_state.get('access_level', 'viewer'))

                                        # רענון
                                        del st.session_state.remove_from_group_request
                                        user_groups = api.get_user_groups(selected_user_for_actions)
                                        if user_groups:
                                            st.session_state.user_groups_display = {
                                                'username': selected_user_for_actions,
                                                'groups': user_groups
                                            }
                                        st.rerun()
                                    else:
                                        st.error("❌ ההסרה מהקבוצה נכשלה")

                        with col_no:
                            if st.button("❌ ביטול", key="confirm_remove_from_group_no", use_container_width=True):
                                del st.session_state.remove_from_group_request
                                st.rerun()

                # תיקון #1: Section 2 - עריכה ומחיקה
                st.markdown("---")
                st.subheader("🔧 עריכה ומחיקה")

                col3, col4 = st.columns(2)

                with col3:
                    st.markdown("**📝 עריכת פרטי משתמש**")
                    # רק support/admin/superadmin יכולים לערוך
                    if role == 'viewer':
                        st.info("👁️ צפייה בלבד - אין הרשאת עריכה")
                    else:
                        if st.button("📝 טען פרטי משתמש", key="load_user_for_edit", disabled=not selected_user_for_actions):
                            if selected_user_data:
                                st.session_state.user_to_edit = selected_user_data
                                st.session_state.edit_username = selected_user_for_actions
                                st.success(f"נטענו הפרטים עבור {selected_user_for_actions}")

                with col4:
                    st.markdown("**🗑️ מחיקת משתמש**")
                    # רק admin/superadmin יכולים למחוק
                    if role in ['admin', 'superadmin']:
                        if st.button("🗑️ מחק משתמש", key="init_delete_user", type="secondary", disabled=not selected_user_for_actions):
                            st.session_state.delete_user_confirmation = selected_user_for_actions
                            st.rerun()
                    else:
                        st.info("👁️ מוגבל ל-Admin")

                # אזור אימות מחיקה (מחוץ לעמודות, בשורה נפרדת)
                if st.session_state.get('delete_user_confirmation') == selected_user_for_actions:
                    st.markdown("---")
                    st.warning(f"⚠️ האם אתה בטוח שברצונך למחוק את המשתמש **{selected_user_for_actions}**?")
                    st.error("⚠️ פעולה זו בלתי הפיכה!")

                    col_spacer1, col_confirm, col_cancel, col_spacer2 = st.columns([1, 2, 2, 1])
                    with col_confirm:
                        if st.button("✅ אשר מחיקה", key="confirm_delete_user", type="primary", use_container_width=True):
                            if selected_user_data:
                                provider_id = selected_user_data.get('providerId')
                                with st.spinner(f"מוחק את {selected_user_for_actions}..."):
                                    success = api.delete_user(selected_user_for_actions, provider_id)
                                    if success:
                                        st.success(f"✅ המשתמש {selected_user_for_actions} נמחק בהצלחה")

                                        user_groups_str = ', '.join([g['displayName'] for g in st.session_state.get('user_groups', [])]) if st.session_state.get('user_groups') else ""
                                        logger.log_action(st.session_state.username, "Delete User",
                                                        f"Deleted: {selected_user_for_actions}, Provider: {provider_id}",
                                                        st.session_state.get('user_email', ''), user_groups_str, True, st.session_state.get('access_level', 'viewer'))

                                        # ניקוי session state
                                        if 'delete_user_confirmation' in st.session_state:
                                            del st.session_state.delete_user_confirmation
                                        if 'search_results' in st.session_state:
                                            del st.session_state.search_results

                                        st.rerun()
                                    else:
                                        st.error("❌ מחיקת המשתמש נכשלה")

                    with col_cancel:
                        if st.button("❌ ביטול", key="cancel_delete_user", use_container_width=True):
                            if 'delete_user_confirmation' in st.session_state:
                                del st.session_state.delete_user_confirmation
                            st.rerun()

            # טופס עריכה (מחוץ ל-elif כי צריך להיות נגיש גם אחרי לחיצה)
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
                        # בדיקות validation
                        validation_errors = []

                        # בדיקת אימייל
                        if new_email and new_email != current_email:
                            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', new_email):
                                validation_errors.append("❌ כתובת אימייל לא תקינה")

                        # בדיקת PIN כפול
                        if new_pin and new_pin != current_pin:
                            pin_exists, existing_user = api.check_pin_exists(new_pin, exclude_username=st.session_state.edit_username)
                            if pin_exists:
                                validation_errors.append(f"❌ קוד PIN '{new_pin}' כבר קיים אצל משתמש: {existing_user}")

                        # אם יש שגיאות validation
                        if validation_errors:
                            for error in validation_errors:
                                st.error(error)
                            st.stop()
                        else:
                            # אין שגיאות - עדכן משתמש
                            updates_made = 0
                            provider_id = user_data.get('providerId')

                            if new_full_name != current_full_name and api.update_user_detail(st.session_state.edit_username, 0, new_full_name, provider_id): updates_made += 1
                            if new_email != current_email and api.update_user_detail(st.session_state.edit_username, 1, new_email, provider_id): updates_made += 1
                            if new_department != current_department and api.update_user_detail(st.session_state.edit_username, 11, new_department, provider_id): updates_made += 1
                            if new_pin != current_pin and api.update_user_detail(st.session_state.edit_username, 5, new_pin, provider_id): updates_made += 1
                            if new_card_id != current_card_id and api.update_user_detail(st.session_state.edit_username, 4, new_card_id, provider_id): updates_made += 1

                            if updates_made > 0:
                                st.success(f"עודכנו בהצלחה {updates_made} שדות עבור {st.session_state.edit_username}")

                                # ניקוי הטופס והנתונים לאחר הצלחה
                                del st.session_state.user_to_edit
                                del st.session_state.edit_username
                                if 'search_results' in st.session_state:
                                    del st.session_state.search_results
                                st.rerun()

if __name__ == "__main__":
    show()
