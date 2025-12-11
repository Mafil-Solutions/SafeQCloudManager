#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SafeQ Cloud Manager - Groups Management Page
דף ניהול קבוצות
"""

import streamlit as st
import streamlit.components.v1 as components
import sys
import os

# הוספת תיקיית app ל-path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import get_api_instance, get_logger_instance, check_authentication, CONFIG
from permissions import filter_groups_by_departments, filter_users_by_departments

@st.dialog("אישור הסרת משתמשים", width="small")
def confirm_bulk_remove_dialog(num_selected, group_name, selected_users, api, logger):
    """Modal לאישור הסרת משתמשים מקבוצה"""
    st.warning(f"⚠️ האם אתה בטוח שברצונך להסיר {num_selected} משתמשים מהקבוצה **{group_name}**?")
    st.error("⚠️ פעולה זו תסיר את המשתמשים מהקבוצה!")

    col_yes, col_no = st.columns(2)
    with col_yes:
        if st.button("✅ אשר הסרה", key="modal_confirm_bulk_remove_yes", type="primary", use_container_width=True):
            with st.spinner("מסיר משתמשים..."):
                progress_bar = st.progress(0)
                status_text = st.empty()

                success_count = 0
                fail_count = 0
                failed_users = []

                total = len(selected_users)

                for idx, username in enumerate(selected_users):
                    status_text.text(f"מסיר {idx + 1}/{total}: {username}...")
                    progress_bar.progress((idx + 1) / total)

                    success = api.remove_user_from_group(username, group_name)
                    if success:
                        success_count += 1
                    else:
                        fail_count += 1
                        failed_users.append(username)

                # תוצאות
                if success_count > 0:
                    st.success(f"✅ {success_count} משתמשים הוסרו בהצלחה!")
                if failed_users:
                    st.error(f"❌ {fail_count} משתמשים נכשלו:")
                    for u in failed_users:
                        st.write(f"  • {u}")

                # לוג
                user_groups_str = ', '.join([g['displayName'] for g in st.session_state.get('user_groups', [])]) if st.session_state.get('user_groups') else ""
                logger.log_action(st.session_state.username, "Bulk Remove from Group",
                                f"Removed {success_count}/{total} users from {group_name}",
                                st.session_state.get('user_email', ''), user_groups_str, success_count > 0,
                                st.session_state.get('access_level', 'viewer'))

                # רענון הקבוצה
                members = api.get_group_members(group_name)
                if members is not None:
                    st.session_state.group_members_data = {
                        'group_name': group_name,
                        'members': members,
                        'count': len(members)
                    }

                # ניקוי
                if 'confirm_bulk_remove' in st.session_state:
                    del st.session_state.confirm_bulk_remove
                st.session_state.selected_group_members = []
                st.rerun()

    with col_no:
        if st.button("❌ ביטול", key="modal_confirm_bulk_remove_no", use_container_width=True):
            if 'confirm_bulk_remove' in st.session_state:
                del st.session_state.confirm_bulk_remove
            st.rerun()

@st.dialog("אישור הוספת משתמשים", width="small")
def confirm_bulk_add_dialog(num_selected, group_name, selected_users, api, logger):
    """Modal לאישור הוספת משתמשים לקבוצה"""
    st.warning(f"⚠️ האם אתה בטוח שברצונך להוסיף {num_selected} משתמשים לקבוצה **{group_name}**?")

    col_yes, col_no = st.columns(2)
    with col_yes:
        if st.button("✅ אשר", key="modal_confirm_bulk_add_yes", type="primary", use_container_width=True):
            with st.spinner("מוסיף משתמשים..."):
                progress_bar = st.progress(0)
                status_text = st.empty()

                success_add_count = 0
                fail_add_count = 0
                failed_add_users = []

                total_add = len(selected_users)

                for idx, username in enumerate(selected_users):
                    status_text.text(f"מוסיף {idx + 1}/{total_add}: {username}...")
                    progress_bar.progress((idx + 1) / total_add)

                    success = api.add_user_to_group(username, group_name)
                    if success:
                        success_add_count += 1
                    else:
                        fail_add_count += 1
                        failed_add_users.append(username)

                # תוצאות
                if success_add_count > 0:
                    st.success(f"✅ {success_add_count} משתמשים נוספו בהצלחה!")
                if failed_add_users:
                    st.error(f"❌ {fail_add_count} משתמשים נכשלו:")
                    for u in failed_add_users:
                        st.write(f"  • {u}")

                # לוג
                user_groups_str = ', '.join([g['displayName'] for g in st.session_state.get('user_groups', [])]) if st.session_state.get('user_groups') else ""
                logger.log_action(st.session_state.username, "Bulk Add to Group",
                                f"Added {success_add_count}/{total_add} users to {group_name}",
                                st.session_state.get('user_email', ''), user_groups_str, success_add_count > 0,
                                st.session_state.get('access_level', 'viewer'))

                # רענון הקבוצה
                members = api.get_group_members(group_name)
                if members is not None:
                    st.session_state.group_members_data = {
                        'group_name': group_name,
                        'members': members,
                        'count': len(members)
                    }

                # ניקוי
                if 'confirm_bulk_add' in st.session_state:
                    del st.session_state.confirm_bulk_add
                st.session_state.users_to_add_selected = []
                if 'search_results_add' in st.session_state:
                    del st.session_state.search_results_add

                st.rerun()

    with col_no:
        if st.button("❌ ביטול", key="modal_confirm_bulk_add_no", use_container_width=True):
            if 'confirm_bulk_add' in st.session_state:
                del st.session_state.confirm_bulk_add
            st.rerun()

def show():
    """הצגת דף ניהול קבוצות"""
    check_authentication()

    # RTL styling + CSS מעוצב
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

        /* רקע לבן לשדות טקסט */
        .stTextInput > div > div > input,
        .stSelectbox > div > div > select,
        .stNumberInput > div > div > input {
            background-color: white !important;
        }

        /* כפתורי פעולות - עיצוב בולט כמו "צור משתמש" */
        .action-button button,
        .action-button button:hover,
        .action-button button:active,
        .action-button button:focus,
        .action-button button:visited {
            background: linear-gradient(45deg, #C41E3A, #FF6B6B) !important;
            color: white !important;
            border: none !important;
            box-shadow: 0 4px 15px rgba(196, 30, 58, 0.3) !important;
            border-radius: 25px !important;
            font-weight: 600 !important;
            width: auto !important;
            max-width: 300px !important;
            padding: 0.5rem 1.5rem !important;
            cursor: pointer !important;
            user-select: none !important;

            /* ביטול כל אנימציות ואפקטים */
            transition: none !important;
            transform: none !important;
            animation: none !important;
            outline: none !important;
            opacity: 1 !important;
            filter: none !important;
            will-change: auto !important;

            /* נעילת מיקום - אפס תזוזה */
            position: relative !important;
            top: 0 !important;
            left: 0 !important;
            right: 0 !important;
            bottom: 0 !important;
            margin: 0 !important;
            vertical-align: baseline !important;
        }

        /* ביטול pointer-events tricks שגורמים לריצוד */
        .action-button button *,
        .action-button button::before,
        .action-button button::after {
            pointer-events: none !important;
        }

        .action-button {
            display: inline-block !important;
            line-height: 1 !important;
        }

        /* כפתורי קבוצות בלבד - לא משפיע על action buttons */
        /* נכנס רק לכפתורים בתוך אזור רשימת הקבוצות */
        [data-testid="stVerticalBlock"]:has(.groups-table-header) button[kind="secondary"] {
            background: white !important;
            color: #333 !important;
            border: none !important;
            border-bottom: 1px solid #e9ecef !important;
            border-radius: 0 !important;
            padding: 0.75rem 1rem !important;
            font-weight: 400 !important;
            font-size: 0.95rem !important;
            text-align: right !important;
            transition: all 0.15s ease !important;
            width: 100% !important;
            box-shadow: none !important;
        }

        [data-testid="stVerticalBlock"]:has(.groups-table-header) button[kind="secondary"]:hover {
            background-color: #f8f9fa !important;
            color: #C41E3A !important;
        }

        [data-testid="stVerticalBlock"]:has(.groups-table-header) button[kind="secondary"]:focus,
        [data-testid="stVerticalBlock"]:has(.groups-table-header) button[kind="secondary"]:active {
            box-shadow: none !important;
            outline: none !important;
            background-color: white !important;
        }

        /* כפתורי action - להישאר אדומים */
        .action-button button {
            background: linear-gradient(45deg, #C41E3A, #FF6B6B) !important;
            color: white !important;
        }

        /* Checkbox styling - פשוט וללא מסגרות מסביב */
        .stCheckbox {
            direction: rtl !important;
            text-align: right !important;
        }

        .stCheckbox label {
            cursor: pointer !important;
        }

        .stCheckbox label:hover {
            background-color: rgba(196, 30, 58, 0.05) !important;
        }

        /* רקע לבן לקונטיינרים הנגללים */
        div[data-testid="stLayoutWrapper"] > div[data-testid="stVerticalBlock"] {
            background-color: white !important;
        }
    </style>
    """, unsafe_allow_html=True)

    api = get_api_instance()
    logger = get_logger_instance()

    # טעינה אוטומטית של קבוצות בכניסה לדף
    if 'available_groups_list' not in st.session_state:
        with st.spinner("טוען קבוצות..."):
            groups = api.get_groups(CONFIG['PROVIDERS']['LOCAL'], max_records=500)
            if groups:
                allowed_departments = st.session_state.get('allowed_departments', [])
                filtered_groups = filter_groups_by_departments(groups, allowed_departments)

                # סינון קבוצות מערכת
                system_groups = ['Local Users', 'Local admins']
                filtered_groups = [g for g in filtered_groups if g.get('groupName', '') not in system_groups]

                # טעינת מספר משתמשים לכל קבוצה
                st.session_state.group_member_counts = {}
                progress_text = st.empty()
                progress_bar = st.progress(0)

                total = len(filtered_groups)
                for idx, group in enumerate(filtered_groups):
                    group_name = group.get('groupName', group.get('groupId', ''))
                    progress_text.text(f"טוען משתמשים... ({idx + 1}/{total})")
                    progress_bar.progress((idx + 1) / total)

                    try:
                        members = api.get_group_members(group_name)
                        if members:
                            st.session_state.group_member_counts[group_name] = len(members)
                        else:
                            st.session_state.group_member_counts[group_name] = 0
                    except:
                        st.session_state.group_member_counts[group_name] = 0

                progress_text.empty()
                progress_bar.empty()
                st.session_state.available_groups_list = filtered_groups

    # Breadcrumb navigation
    if 'group_members_data' in st.session_state:
        group_name = st.session_state.group_members_data.get('group_name', '')

        # שורת ניווט
        st.markdown(f"""
        <div style="margin-bottom: 1rem; padding: 0.5rem; background-color: #f8f9fa; border-radius: 5px; direction: rtl;">
            <span style="color: #666; font-size: 0.9rem;">
                <a href="#" style="color: #C41E3A; text-decoration: none; font-weight: 600;"
                   onclick="return false;">קבוצות</a>
                <span style="margin: 0 0.5rem; color: #999;">/</span>
                <span style="color: #333; font-weight: 600;">{group_name}</span>
            </span>
        </div>
        """, unsafe_allow_html=True)

        # כפתור חזרה
        col_back, col_spacer = st.columns([1, 3])
        with col_back:
            st.markdown('<div class="action-button">', unsafe_allow_html=True)
            if st.button("⬅️ חזור לקבוצות", key="back_to_groups"):
                # ניקוי מלא
                keys_to_delete = [
                    'group_members_data', 'selected_group_name', 'selected_group_members',
                    'confirm_bulk_remove', 'bulk_remove_in_progress', 'bulk_remove_results',
                    'group_checkbox_counter', 'show_remove_section', 'show_add_section',
                    'users_cart', 'search_results_add', 'confirm_bulk_add'
                ]
                for key in keys_to_delete:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.header("👥 ניהול קבוצות")

        # כפתור רענן קבוצות - רק בדף הראשי (לא בתצוגת קבוצה ספציפית)
        col_spacer, col_refresh = st.columns([3, 1])
        with col_refresh:
            st.markdown('<div class="action-button">', unsafe_allow_html=True)
            if st.button("🔄 רענן קבוצות", key="refresh_groups_btn"):
                user_groups_str = ', '.join([g['displayName'] for g in st.session_state.get('user_groups', [])]) if st.session_state.get('user_groups') else ""
                logger.log_action(st.session_state.username, "Refresh Groups", "",
                                st.session_state.get('user_email', ''), user_groups_str, True, st.session_state.get('access_level', 'viewer'))
                with st.spinner("מרענן קבוצות..."):
                    groups = api.get_groups(CONFIG['PROVIDERS']['LOCAL'], max_records=500)
                    if groups:
                        allowed_departments = st.session_state.get('allowed_departments', [])
                        groups_before_filter = len(groups)
                        filtered_groups = filter_groups_by_departments(groups, allowed_departments)
                        groups_after_filter = len(filtered_groups)

                        # סינון קבוצות מערכת
                        system_groups = ['Local Users', 'Local admins']
                        filtered_groups = [g for g in filtered_groups if g.get('groupName', '') not in system_groups]

                        # טעינת מספר משתמשים לכל קבוצה
                        st.session_state.group_member_counts = {}
                        progress_text = st.empty()
                        progress_bar = st.progress(0)

                        total = len(filtered_groups)
                        for idx, group in enumerate(filtered_groups):
                            group_name = group.get('groupName', group.get('groupId', ''))
                            progress_text.text(f"טוען משתמשים... ({idx + 1}/{total})")
                            progress_bar.progress((idx + 1) / total)

                            try:
                                members = api.get_group_members(group_name)
                                if members:
                                    st.session_state.group_member_counts[group_name] = len(members)
                                else:
                                    st.session_state.group_member_counts[group_name] = 0
                            except:
                                st.session_state.group_member_counts[group_name] = 0

                        progress_text.empty()
                        progress_bar.empty()
                        st.session_state.available_groups_list = filtered_groups

                        if groups_after_filter < groups_before_filter:
                            st.success(f"נטענו {groups_after_filter} קבוצות מתוך {groups_before_filter} (מסוננות לפי הרשאות)")
                        else:
                            st.success(f"נטענו {groups_after_filter} קבוצות")
                        st.rerun()
                    else:
                        st.warning("לא נמצאו קבוצות")
            st.markdown('</div>', unsafe_allow_html=True)

    # הצגת חיפוש ורשימת קבוצות - רק אחרי טעינה וכשלא בתצוגת קבוצה ספציפית
    if 'available_groups_list' in st.session_state and 'group_members_data' not in st.session_state:
        st.markdown("---")

        # חיפוש קבוצות (מיידי עם on_change)
        def on_search_change():
            # פונקציה זו מאלצת rerun בכל שינוי
            pass

        search_term = st.text_input(
            "🔍 חיפוש קבוצות",
            placeholder="הקלד לחיפוש - תוצאות מיידיות",
            key="group_search",
            on_change=on_search_change,
            label_visibility="visible"
        )

        groups_to_show = st.session_state.available_groups_list

        # סינון לפי חיפוש
        if search_term:
            groups_to_show = [
                group for group in groups_to_show
                if search_term.lower() in group.get('groupName', group.get('groupId', '')).lower()
            ]

        if groups_to_show:
            # מיון אלפביתי
            groups_to_show = sorted(groups_to_show, key=lambda g: g.get('groupName', '').lower())

            st.subheader(f"📋 קבוצות זמינות ({len(groups_to_show)})")

            # עיצוב טבלה נקייה
            st.markdown("""
            <style>
                /* כותרות טבלה */
                .groups-table-header {
                    display: flex;
                    padding: 0.75rem 1rem;
                    background-color: #f8f9fa;
                    border-bottom: 2px solid #dee2e6;
                    font-weight: 600;
                    color: #495057;
                    direction: rtl;
                }

                .header-group-name {
                    flex: 2;
                    text-align: right;
                }

                .header-user-count {
                    flex: 1;
                    text-align: center;
                    padding-right: 1rem;
                }
            </style>
            """, unsafe_allow_html=True)

            # כותרות טבלה
            st.markdown("""
            <div class="groups-table-header">
                <div class="header-group-name">👥 שם הקבוצה</div>
                <div class="header-user-count">👤 משתמשים בקבוצה</div>
            </div>
            """, unsafe_allow_html=True)

            # שורות הטבלה
            for idx, group in enumerate(groups_to_show):
                group_name = group.get('groupName', group.get('groupId', 'Unknown Group'))

                # קבלת מספר משתמשים מהמטמון
                user_count = st.session_state.group_member_counts.get(group_name, 0)

                # כל שורה עם 2 עמודות
                col_name, col_count = st.columns([2, 1])

                with col_name:
                    if st.button(f"{group_name}", key=f"group_btn_{group_name}", use_container_width=True):
                        st.session_state.selected_group_name = group_name

                        # טעינה אוטומטית של חברי הקבוצה
                        with st.spinner(f"טוען חברי '{group_name}'..."):
                            members = api.get_group_members(group_name)
                            if members:
                                st.session_state.group_members_data = {
                                    'group_name': group_name,
                                    'members': members,
                                    'count': len(members)
                                }
                                st.session_state.selected_group_members = []
                            else:
                                st.session_state.group_members_data = {
                                    'group_name': group_name,
                                    'members': [],
                                    'count': 0
                                }
                                st.session_state.selected_group_members = []

                        user_groups_str = ', '.join([g['displayName'] for g in st.session_state.get('user_groups', [])]) if st.session_state.get('user_groups') else ""
                        logger.log_action(st.session_state.username, "View Group Members", f"Group: {group_name}",
                                        st.session_state.get('user_email', ''), user_groups_str, True, st.session_state.get('access_level', 'viewer'))

                        # איפוס מצב הכפתורים
                        if 'show_remove_section' in st.session_state:
                            del st.session_state.show_remove_section
                        if 'show_add_section' in st.session_state:
                            del st.session_state.show_add_section

                        st.rerun()

                with col_count:
                    # הצגת מספר משתמשים במרכז
                    st.markdown(f"<div style='padding: 0.75rem; color: #666; font-size: 0.95rem; text-align: center;'>{user_count}</div>", unsafe_allow_html=True)

        else:
            st.info("לא נמצאו קבוצות התואמות את קריטריוני החיפוש")

    # הצגת פרטי קבוצה נבחרת
    if 'group_members_data' in st.session_state:
        st.markdown("---")
        group_data = st.session_state.group_members_data
        st.subheader(f"👥 קבוצה: '{group_data['group_name']}' ({group_data['count']} חברים)")

        role = st.session_state.get('role', st.session_state.get('access_level', 'viewer'))

        # כפתורים: הסרה (רק אם יש משתמשים) והוספה (תמיד)
        if role not in ['viewer']:
            # אם יש משתמשים - 2 כפתורים, אם אין - רק כפתור הוספה
            if group_data['count'] > 0:
                col_btn1, col_btn2, col_spacer = st.columns([1, 1, 2])

                with col_btn1:
                    st.markdown('<div class="action-button">', unsafe_allow_html=True)
                    if st.button("🗑️ הסרת משתמשים", key="show_remove_btn"):
                        st.session_state.show_remove_section = True
                        if 'show_add_section' in st.session_state:
                            del st.session_state.show_add_section
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

                with col_btn2:
                    st.markdown('<div class="action-button">', unsafe_allow_html=True)
                    if st.button("➕ הוספת משתמשים", key="show_add_btn"):
                        st.session_state.show_add_section = True
                        if 'show_remove_section' in st.session_state:
                            del st.session_state.show_remove_section
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
            else:
                # קבוצה ריקה - רק כפתור הוספה
                col_btn, col_spacer = st.columns([1, 3])
                with col_btn:
                    st.markdown('<div class="action-button">', unsafe_allow_html=True)
                    if st.button("➕ הוספת משתמשים", key="show_add_btn"):
                        st.session_state.show_add_section = True
                        if 'show_remove_section' in st.session_state:
                            del st.session_state.show_remove_section
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

        # === טופס הסרה ===
        if st.session_state.get('show_remove_section', False):
            st.markdown("---")
            st.markdown("### 🗑️ הסרת משתמשים מהקבוצה")

            # גלילה אוטומטית למטה
            components.html("""
            <script>
                // מנסה מספר דרכים לגלילה
                setTimeout(function() {
                    // דרך 1: גלילה ל-main section
                    try {
                        var mainSection = window.parent.document.querySelector('section.main');
                        if (mainSection) {
                            mainSection.scrollTop = mainSection.scrollHeight;
                        }
                    } catch(e) {}

                    // דרך 2: גלילה לחלון כולו
                    try {
                        window.parent.window.scrollTo(0, document.body.scrollHeight);
                    } catch(e) {}

                    // דרך 3: גלילה לאלמנט האחרון
                    try {
                        var elements = window.parent.document.querySelectorAll('[data-testid="stVerticalBlock"]');
                        if (elements.length > 0) {
                            elements[elements.length - 1].scrollIntoView({ behavior: 'smooth', block: 'end' });
                        }
                    } catch(e) {}
                }, 300);
            </script>
            """, height=0)

            # איתחול
            if 'selected_group_members' not in st.session_state:
                st.session_state.selected_group_members = []
            if 'group_checkbox_counter' not in st.session_state:
                st.session_state.group_checkbox_counter = 0

            all_usernames = [m.get('userName', m.get('username', '')) for m in group_data['members']]

            # כפתור בחר הכל / נקה
            col_select, col_spacer = st.columns([1, 3])
            with col_select:
                st.markdown('<div class="action-button">', unsafe_allow_html=True)
                if st.session_state.selected_group_members and len(st.session_state.selected_group_members) == len(all_usernames):
                    if st.button("❌ נקה בחירה", key="clear_all_members"):
                        st.session_state.selected_group_members = []
                        st.session_state.group_checkbox_counter += 1
                        st.rerun()
                else:
                    if st.button("✅ בחר הכל", key="select_all_members"):
                        st.session_state.selected_group_members = all_usernames.copy()
                        st.session_state.group_checkbox_counter += 1
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

            # רשימת משתמשים
            st.markdown("**בחר משתמשים:**")

            temp_selections = []

            # שימוש ב-container עם גובה קבוע ליצירת סקרול אוטומטי
            with st.container(height=400, border=True):
                for member in group_data['members']:
                    username = member.get('userName', member.get('username', ''))
                    full_name = member.get('fullName', '')
                    department = member.get('department', '')

                    if not department:
                        for detail in member.get('details', []):
                            if isinstance(detail, dict) and detail.get('detailType') == 11:
                                department = detail.get('detailData', '')
                                break

                    label = f"{username}"
                    if full_name:
                        label += f" ({full_name})"
                    if department:
                        label += f" [{department}]"

                    is_checked = username in st.session_state.selected_group_members
                    checkbox_result = st.checkbox(label, value=is_checked,
                                                 key=f"member_checkbox_{username}_{group_data['group_name']}_{st.session_state.group_checkbox_counter}")

                    if checkbox_result:
                        temp_selections.append(username)

            # עדכון הסטייט - רק אם באמת השתנה
            if set(temp_selections) != set(st.session_state.selected_group_members):
                st.session_state.selected_group_members = temp_selections
                st.rerun()

            # כפתור הסרה
            num_selected = len(st.session_state.selected_group_members)
            if num_selected >= 1 and not st.session_state.get('bulk_remove_results'):
                st.info(f"✓ נבחרו {num_selected} משתמשים")

                col_remove, col_spacer = st.columns([1, 3])
                with col_remove:
                    if role in ['admin', 'superadmin']:
                        st.markdown('<div class="action-button">', unsafe_allow_html=True)
                        if st.button(f"🗑️ הסר {num_selected} מהקבוצה", key="remove_bulk_from_group"):
                            st.session_state.confirm_bulk_remove = True
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)

            # אימות הסרה - עם Modal Dialog
            if st.session_state.get('confirm_bulk_remove', False):
                confirm_bulk_remove_dialog(num_selected, group_data['group_name'],
                                          st.session_state.selected_group_members, api, logger)

        # === טופס הוספה ===
        if st.session_state.get('show_add_section', False):
            st.markdown("---")
            st.markdown("### ➕ הוספת משתמשים לקבוצה")

            # גלילה אוטומטית למטה
            components.html("""
            <script>
                // מנסה מספר דרכים לגלילה
                setTimeout(function() {
                    // דרך 1: גלילה ל-main section
                    try {
                        var mainSection = window.parent.document.querySelector('section.main');
                        if (mainSection) {
                            mainSection.scrollTop = mainSection.scrollHeight;
                        }
                    } catch(e) {}

                    // דרך 2: גלילה לחלון כולו
                    try {
                        window.parent.window.scrollTo(0, document.body.scrollHeight);
                    } catch(e) {}

                    // דרך 3: גלילה לאלמנט האחרון
                    try {
                        var elements = window.parent.document.querySelectorAll('[data-testid="stVerticalBlock"]');
                        if (elements.length > 0) {
                            elements[elements.length - 1].scrollIntoView({ behavior: 'smooth', block: 'end' });
                        }
                    } catch(e) {}
                }, 300);
            </script>
            """, height=0)

            # איתחול מחסנית משתמשים
            if 'users_cart' not in st.session_state:
                st.session_state.users_cart = []

            # טופס חיפוש משתמש - שדות קטנים יותר
            st.markdown("**חפש משתמש להוספה:**")

            col1, col2, col3, col_spacer = st.columns([1.5, 1.5, 1.2, 1.8])

            with col1:
                search_type_map = {
                    "שם משתמש": "Username",
                    "שם מלא": "Full Name",
                    "מחלקה": "Department",
                    "אימייל": "Email"
                }
                search_type_he = st.selectbox("חיפוש לפי", list(search_type_map.keys()), key="add_user_search_type")
                search_type = search_type_map[search_type_he]

            with col2:
                search_term = st.text_input(f"ערך לחיפוש", key="add_user_search_term")

            with col3:
                # רווח אנכי כדי ליישר את הכפתור עם השדות
                st.markdown("<div style='margin-top: 32px;'></div>", unsafe_allow_html=True)
                st.markdown('<div class="action-button">', unsafe_allow_html=True)
                if st.button("🔍 חפש", key="search_users_to_add", use_container_width=True):
                    if search_term:
                        with st.spinner("מחפש משתמשים..."):
                            try:
                                # נסה תחילה עם 1000, אם נכשל נרד ל-500
                                all_users = api.get_users(CONFIG['PROVIDERS']['LOCAL'], max_records=1000)

                                if not all_users:
                                    st.warning("לא נמצאו משתמשים במערכת")
                                    st.session_state.search_results_add = []
                                    st.rerun()
                                    st.stop()

                                # סינון לפי סוג חיפוש
                                matching_users = []
                                search_lower = search_term.lower()

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
                                    elif search_type == "Email":
                                        user_field = user.get('email', '').lower()

                                    if search_lower in user_field:
                                        match_found = True

                                    if match_found:
                                        matching_users.append(user)

                                # סינון משתמשים שכבר בקבוצה
                                current_member_usernames = [m.get('userName', m.get('username', '')) for m in group_data['members']]
                                matching_users = [u for u in matching_users if u.get('userName', u.get('username', '')) not in current_member_usernames]

                                # סינון לפי מחלקות מורשות
                                allowed_departments = st.session_state.get('allowed_departments', [])
                                matching_users = filter_users_by_departments(matching_users, allowed_departments)

                                st.session_state.search_results_add = matching_users

                                # הצגת הודעה אם לא נמצאו תוצאות
                                if not matching_users:
                                    st.warning(f"🔍 לא נמצאו משתמשים עבור החיפוש: **{search_term}** ב-**{search_type_he}**")
                                    st.info("💡 נסה:\n- לשנות את סוג החיפוש\n- לבדוק שהמשתמש לא כבר בקבוצה\n- לוודא שהמשתמש שייך למחלקות המורשות שלך")

                                st.rerun()

                            except Exception as e:
                                st.error(f"❌ שגיאה בחיפוש משתמשים: {str(e)}")
                                st.info("💡 ניסיון חיפוש עם כמות מוגבלת יותר...")

                                try:
                                    # נסיון שני עם 500 רשומות
                                    all_users = api.get_users(CONFIG['PROVIDERS']['LOCAL'], max_records=500)

                                    if not all_users:
                                        st.warning("לא נמצאו משתמשים במערכת")
                                        st.session_state.search_results_add = []
                                    else:
                                        # אותו סינון כמו למעלה
                                        matching_users = []
                                        search_lower = search_term.lower()

                                        for user in all_users:
                                            if not isinstance(user, dict):
                                                continue

                                            user_field = ""
                                            if search_type == "Username":
                                                user_field = user.get('userName', user.get('username', '')).lower()
                                            elif search_type == "Full Name":
                                                user_field = user.get('fullName', '').lower()
                                            elif search_type == "Department":
                                                user_field = user.get('department', '').lower()
                                            elif search_type == "Email":
                                                user_field = user.get('email', '').lower()

                                            if search_lower in user_field:
                                                matching_users.append(user)

                                        current_member_usernames = [m.get('userName', m.get('username', '')) for m in group_data['members']]
                                        matching_users = [u for u in matching_users if u.get('userName', u.get('username', '')) not in current_member_usernames]

                                        allowed_departments = st.session_state.get('allowed_departments', [])
                                        matching_users = filter_users_by_departments(matching_users, allowed_departments)

                                        st.session_state.search_results_add = matching_users

                                        # הצגת הודעה אם לא נמצאו תוצאות
                                        if matching_users:
                                            st.success(f"✓ החיפוש הושלם בהצלחה (מוגבל ל-500 משתמשים)")
                                        else:
                                            st.warning(f"🔍 לא נמצאו משתמשים עבור החיפוש: **{search_term}** ב-**{search_type_he}**")
                                            st.info("💡 נסה:\n- לשנות את סוג החיפוש\n- לבדוק שהמשתמש לא כבר בקבוצה\n- לוודא שהמשתמש שייך למחלקות המורשות שלך")

                                    st.rerun()

                                except Exception as e2:
                                    st.error(f"❌ החיפוש נכשל: {str(e2)}")
                                    st.session_state.search_results_add = []
                    else:
                        st.error("נא להזין ערך לחיפוש")
                st.markdown('</div>', unsafe_allow_html=True)

            # הצגת תוצאות חיפוש עם צ'קבוקסים
            if 'search_results_add' in st.session_state and st.session_state.search_results_add:
                st.markdown(f"**תוצאות חיפוש ({len(st.session_state.search_results_add)} נמצאו):**")

                # איתחול counter אם לא קיים
                if 'user_search_checkbox_counter' not in st.session_state:
                    st.session_state.user_search_checkbox_counter = 0

                # כפתור בחר הכל / נקה בחירה
                all_search_usernames = [u.get('userName', u.get('username', '')) for u in st.session_state.search_results_add]

                col_select_search, col_spacer_search = st.columns([1, 3])
                with col_select_search:
                    st.markdown('<div class="action-button">', unsafe_allow_html=True)
                    if st.session_state.users_cart and len(st.session_state.users_cart) == len(all_search_usernames):
                        if st.button("❌ נקה בחירה", key="clear_all_search_users"):
                            st.session_state.users_cart = []
                            st.session_state.user_search_checkbox_counter += 1
                            st.rerun()
                    else:
                        if st.button("✅ בחר הכל", key="select_all_search_users"):
                            st.session_state.users_cart = all_search_usernames.copy()
                            st.session_state.user_search_checkbox_counter += 1
                            st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

                # שימוש ב-container עם גובה קבוע ליצירת סקרול אוטומטי
                temp_cart_selections = []

                with st.container(height=400, border=True):
                    for user in st.session_state.search_results_add[:500]:  # הגבלה ל-500 תוצאות
                        username = user.get('userName', user.get('username', ''))
                        full_name = user.get('fullName', '')
                        department = user.get('department', '')

                        label = f"{username}"
                        if full_name:
                            label += f" - {full_name}"
                        if department:
                            label += f" [{department}]"

                        # צ'קבוקס מצד ימין
                        is_checked = username in st.session_state.users_cart
                        checkbox_result = st.checkbox(label, value=is_checked,
                                                     key=f"search_user_checkbox_{username}_{st.session_state.user_search_checkbox_counter}")

                        if checkbox_result:
                            temp_cart_selections.append(username)

                # עדכון הבחירה רק אם השתנה משהו
                if set(temp_cart_selections) != set(st.session_state.users_cart):
                    st.session_state.users_cart = temp_cart_selections
                    st.rerun()

            # הצגת הודעת info עם מספר המשתמשים הנבחרים וכפתור הוספה
            if st.session_state.users_cart:
                num_to_add = len(st.session_state.users_cart)
                st.info(f"✓ נבחרו {num_to_add} משתמשים להוספה")

                col_add, col_spacer = st.columns([1, 3])
                with col_add:
                    st.markdown('<div class="action-button">', unsafe_allow_html=True)
                    if st.button(f"➕ הוסף {num_to_add} משתמשים", key="add_users_from_selection"):
                        st.session_state.confirm_bulk_add = True
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

                # אימות הוספה - עם Modal Dialog
                if st.session_state.get('confirm_bulk_add', False):
                    confirm_bulk_add_dialog(num_to_add, group_data['group_name'],
                                          st.session_state.users_cart, api, logger)

        # כפתור סגור קבוצה
        if role not in ['viewer']:
            st.markdown("---")
            col_close, col_spacer = st.columns([1, 3])
            with col_close:
                st.markdown('<div class="action-button">', unsafe_allow_html=True)
                if st.button("🗑️ סגור קבוצה", key="clear_group_results"):
                    # ניקוי מלא
                    keys_to_delete = [
                        'group_members_data', 'selected_group_name', 'selected_group_members',
                        'confirm_bulk_remove', 'bulk_remove_in_progress', 'bulk_remove_results',
                        'group_checkbox_counter', 'show_remove_section', 'show_add_section',
                        'users_cart', 'search_results_add', 'confirm_bulk_add'
                    ]
                    for key in keys_to_delete:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    show()
