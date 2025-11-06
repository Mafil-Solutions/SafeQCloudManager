#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SafeQ Cloud Manager - Groups Management Page
דף ניהול קבוצות
"""

import streamlit as st
import sys
import os

# הוספת תיקיית app ל-path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import get_api_instance, get_logger_instance, check_authentication, CONFIG
from permissions import filter_groups_by_departments

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
        .action-button button {
            background: linear-gradient(45deg, #C41E3A, #FF6B6B) !important;
            color: white !important;
            border: none !important;
            box-shadow: 0 4px 15px rgba(196, 30, 58, 0.3);
            border-radius: 25px;
            font-weight: 600 !important;
            transition: all 0.3s ease !important;
        }

        .action-button button:hover {
            background: linear-gradient(45deg, #FF6B6B, #C41E3A) !important;
            box-shadow: 0 6px 20px rgba(196, 30, 58, 0.5) !important;
            transform: translateY(-2px);
        }

        /* כפתורי קבוצות - עיצוב עדין ונעים לעין */
        .group-button button {
            background: linear-gradient(135deg, rgba(74, 144, 226, 0.08), rgba(196, 30, 58, 0.05)) !important;
            color: #2C3E50 !important;
            border: 1px solid rgba(74, 144, 226, 0.2) !important;
            border-radius: 12px !important;
            padding: 12px 20px !important;
            font-weight: 500 !important;
            transition: all 0.25s ease !important;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05) !important;
        }

        .group-button button:hover {
            background: linear-gradient(135deg, rgba(74, 144, 226, 0.15), rgba(196, 30, 58, 0.1)) !important;
            border-color: rgba(196, 30, 58, 0.4) !important;
            box-shadow: 0 4px 10px rgba(196, 30, 58, 0.15) !important;
            transform: translateY(-1px);
        }

        /* Checkbox styling */
        .stCheckbox {
            direction: rtl !important;
            text-align: right !important;
        }

        /* Container for groups list */
        .groups-container {
            border: 1px solid #e0e0e0;
            border-radius: 10px;
            padding: 15px;
            max-height: 500px;
            overflow-y: auto;
            background-color: #fafafa;
        }
    </style>
    """, unsafe_allow_html=True)

    api = get_api_instance()
    logger = get_logger_instance()

    st.header("👥 ניהול קבוצות")

    # שורה עליונה - חיפוש (שמאל) וכפתור (ימין)
    col_search, col_btn = st.columns([2, 1])

    with col_search:
        # חיפוש בקבוצות
        search_term = ""
        if 'available_groups_list' in st.session_state:
            search_term = st.text_input("🔍 חיפוש קבוצות", placeholder="הקלד לחיפוש קבוצות...", key="group_search")
        else:
            # שדה disabled כשאין קבוצות
            st.text_input("🔍 חיפוש קבוצות", placeholder="לחץ על 'טען קבוצות' תחילה", key="group_search_disabled", disabled=True)

    with col_btn:
        st.write("")  # ריווח
        st.markdown('<div class="action-button">', unsafe_allow_html=True)
        if st.button("🔄 טען קבוצות", key="refresh_groups_btn", use_container_width=True):
            user_groups_str = ', '.join([g['displayName'] for g in st.session_state.get('user_groups', [])]) if st.session_state.get('user_groups') else ""
            logger.log_action(st.session_state.username, "Load Groups", "",
                            st.session_state.get('user_email', ''), user_groups_str, True, st.session_state.get('access_level', 'viewer'))
            with st.spinner("טוען קבוצות..."):
                groups = api.get_groups(CONFIG['PROVIDERS']['LOCAL'], max_records=500)
                if groups:
                    # סינון לפי מחלקות מורשות
                    allowed_departments = st.session_state.get('allowed_departments', [])
                    groups_before_filter = len(groups)
                    filtered_groups = filter_groups_by_departments(groups, allowed_departments)
                    groups_after_filter = len(filtered_groups)

                    st.session_state.available_groups_list = filtered_groups

                    if groups_after_filter < groups_before_filter:
                        st.success(f"נטענו {groups_after_filter} קבוצות מתוך {groups_before_filter} (מסוננות לפי הרשאות)")
                    else:
                        st.success(f"נטענו {groups_after_filter} קבוצות")
                    st.rerun()  # רענון כדי להפעיל את שדה החיפוש
                else:
                    st.warning("לא נמצאו קבוצות")
        st.markdown('</div>', unsafe_allow_html=True)

    # הצגת רשימת קבוצות מסוננת
    if 'available_groups_list' in st.session_state:
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

            st.subheader(f"📋 בחר קבוצה ({len(groups_to_show)} קבוצות)")

            # תיבה עם רשימה מסודרת
            st.markdown('<div class="groups-container">', unsafe_allow_html=True)

            for group in groups_to_show:
                group_name = group.get('groupName', group.get('groupId', 'Unknown Group'))

                # לחיצה על קבוצה טוענת את החברים אוטומטית
                st.markdown('<div class="group-button">', unsafe_allow_html=True)
                if st.button(f"👥 {group_name}", key=f"group_btn_{group_name}", use_container_width=True):
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
                            # איפוס בחירת משתמשים
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
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)

        else:
            st.info("לא נמצאו קבוצות התואמות את קריטריוני החיפוש")
    else:
        st.info("לחץ על 'טען קבוצות' כדי לראות את הקבוצות הזמינות")

    # הצגת תוצאות חברי הקבוצה ברוחב מלא
    if 'group_members_data' in st.session_state:
        st.markdown("---")
        group_data = st.session_state.group_members_data
        st.subheader(f"👥 חברי הקבוצה '{group_data['group_name']}' ({group_data['count']} חברים)")

        if group_data['count'] == 0:
            st.info("הקבוצה ריקה")
        else:
            # איתחול רשימת בחירה
            if 'selected_group_members' not in st.session_state:
                st.session_state.selected_group_members = []

            # אתחול counter לרענון widgets
            if 'group_checkbox_counter' not in st.session_state:
                st.session_state.group_checkbox_counter = 0

            # כפתור "בחר הכל" / "נקה בחירה"
            role = st.session_state.get('role', st.session_state.get('access_level', 'viewer'))

            # כפתור "בחר הכל" למעלה
            if role not in ['viewer']:  # רק למי שמורשה להסיר
                all_usernames = [m.get('userName', m.get('username', '')) for m in group_data['members']]

                st.markdown('<div class="action-button">', unsafe_allow_html=True)
                if st.session_state.selected_group_members and len(st.session_state.selected_group_members) == len(all_usernames):
                    if st.button("❌ נקה בחירה", key="clear_all_members", use_container_width=True):
                        st.session_state.selected_group_members = []
                        st.session_state.group_checkbox_counter += 1
                        st.rerun()
                else:
                    if st.button("✅ בחר הכל", key="select_all_members", use_container_width=True):
                        st.session_state.selected_group_members = all_usernames.copy()
                        st.session_state.group_checkbox_counter += 1
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

            # טבלה עם checkboxes
            st.markdown("**בחר משתמשים להסרה:**")

            # תיקון: בנייה מחדש של רשימת בחירה מהצ'קבוקסים
            temp_selections = []

            for member in group_data['members']:
                username = member.get('userName', member.get('username', ''))
                full_name = member.get('fullName', '')
                department = member.get('department', '')

                if not department:
                    for detail in member.get('details', []):
                        if isinstance(detail, dict) and detail.get('detailType') == 11:
                            department = detail.get('detailData', '')
                            break

                # יצירת תווית
                label = f"{username}"
                if full_name:
                    label += f" ({full_name})"
                if department:
                    label += f" [{department}]"

                if role not in ['viewer']:  # רק למי שמורשה
                    is_checked = username in st.session_state.selected_group_members

                    # תיקון: checkbox עם key דינמי שכולל counter
                    checkbox_result = st.checkbox(label, value=is_checked,
                                                 key=f"member_checkbox_{username}_{group_data['group_name']}_{st.session_state.group_checkbox_counter}")

                    # אוסף את כל הבחירות
                    if checkbox_result:
                        temp_selections.append(username)
                else:
                    st.text(f"👁️ {label}")

            # עדכון הסטייט רק אם השתנה משהו
            if role not in ['viewer']:
                if temp_selections != st.session_state.selected_group_members:
                    st.session_state.selected_group_members = temp_selections
                    st.rerun()

            # מונה וכפתור הסרה למטה - רק אם לא בתהליך הסרה ולא בתצוגת תוצאות
            num_selected = len(st.session_state.selected_group_members)
            if num_selected >= 1 and not st.session_state.get('bulk_remove_results'):
                col_count, col_remove = st.columns([1, 1])

                with col_count:
                    st.info(f"✓ נבחרו {num_selected} משתמשים")

                with col_remove:
                    if role in ['admin', 'superadmin']:
                        st.markdown('<div class="action-button">', unsafe_allow_html=True)
                        if st.button(f"🗑️ הסר {num_selected} מהקבוצה", key="remove_bulk_from_group", use_container_width=True):
                            st.session_state.confirm_bulk_remove = True
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)

            # אימות הסרה - רק אם עדיין לא התחלנו ולא סיימנו
            if st.session_state.get('confirm_bulk_remove', False) and not st.session_state.get('bulk_remove_in_progress', False) and not st.session_state.get('bulk_remove_results'):
                st.warning(f"⚠️ האם אתה בטוח שברצונך להסיר {num_selected} משתמשים מהקבוצה '{group_data['group_name']}'?")
                st.error("⚠️ פעולה זו תסיר את המשתמשים מהקבוצה!")

                # כפתורים מרוכזים יותר
                col_spacer1, col_yes, col_no, col_spacer2 = st.columns([1, 2, 2, 1])
                with col_yes:
                    st.markdown('<div class="action-button">', unsafe_allow_html=True)
                    if st.button("✅ אשר הסרה", key="confirm_remove_yes", use_container_width=True):
                        st.session_state.bulk_remove_in_progress = True
                        st.session_state.confirm_bulk_remove = False  # ניקוי מיד
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

                with col_no:
                    st.markdown('<div class="action-button">', unsafe_allow_html=True)
                    if st.button("❌ ביטול", key="confirm_remove_no", use_container_width=True):
                        st.session_state.confirm_bulk_remove = False
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

            # ביצוע ההסרה
            if st.session_state.get('bulk_remove_in_progress', False):
                # יישור לימין עבור עברית
                col_spacer, col_progress = st.columns([1, 3])
                with col_progress:
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                success_count = 0
                fail_count = 0
                failed_users = []

                total = len(st.session_state.selected_group_members)

                for idx, username in enumerate(st.session_state.selected_group_members):
                    status_text.text(f"מסיר {idx + 1}/{total}: {username}...")
                    progress_bar.progress((idx + 1) / total)

                    success = api.remove_user_from_group(username, group_data['group_name'])
                    if success:
                        success_count += 1
                    else:
                        fail_count += 1
                        failed_users.append(username)

                # שמירת התוצאות ב-session state
                st.session_state.bulk_remove_results = {
                    'success_count': success_count,
                    'fail_count': fail_count,
                    'failed_users': failed_users,
                    'total': total,
                    'group_name': group_data['group_name']
                }

                # ניקוי הפלאג מיד אחרי הפעולה
                st.session_state.bulk_remove_in_progress = False

                # לוג
                user_groups_str = ', '.join([g['displayName'] for g in st.session_state.get('user_groups', [])]) if st.session_state.get('user_groups') else ""
                logger.log_action(st.session_state.username, "Bulk Remove from Group",
                                f"Removed {success_count}/{total} users from {group_data['group_name']}",
                                st.session_state.get('user_email', ''), user_groups_str,
                                success_count > 0, st.session_state.get('access_level', 'viewer'))

                st.rerun()

            # הצגת סיכום (אחרי שהפעולה הסתיימה)
            if st.session_state.get('bulk_remove_results'):
                results = st.session_state.bulk_remove_results

                st.markdown("---")
                st.subheader("📊 סיכום הסרה קבוצתית")

                col_s, col_f = st.columns(2)
                with col_s:
                    st.metric("✅ הוסרו בהצלחה", results['success_count'])
                with col_f:
                    st.metric("❌ כשלונות", results['fail_count'])

                if results['success_count'] > 0:
                    st.success(f"✅ {results['success_count']} משתמשים הוסרו בהצלחה מהקבוצה '{results['group_name']}'")

                if results['failed_users']:
                    st.error(f"❌ {results['fail_count']} משתמשים נכשלו:")
                    for user in results['failed_users']:
                        st.write(f"  • {user}")

                # כפתור אישור ורענון
                st.markdown('<div class="action-button">', unsafe_allow_html=True)
                if st.button("✓ אישור והמשך", key="confirm_bulk_remove_results", use_container_width=True):
                    # רענון נתוני הקבוצה תחילה
                    with st.spinner("מרענן את נתוני הקבוצה..."):
                        members = api.get_group_members(results['group_name'])
                        if members is not None:
                            st.session_state.group_members_data = {
                                'group_name': results['group_name'],
                                'members': members,
                                'count': len(members)
                            }

                    # ניקוי מלא של session state
                    st.session_state.selected_group_members = []
                    st.session_state.confirm_bulk_remove = False
                    st.session_state.group_checkbox_counter += 1  # עדכון counter כדי לרענן checkboxes
                    if 'bulk_remove_results' in st.session_state:
                        del st.session_state.bulk_remove_results
                    if 'bulk_remove_in_progress' in st.session_state:
                        del st.session_state.bulk_remove_in_progress

                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        # הוספת חברים בבאלקים - אקורדיון יפה
        if role not in ['viewer']:
            st.markdown("---")
            with st.expander("➕ הוסף חברים לקבוצה (באלקים)", expanded=False):
                st.markdown("### 📥 הוספת מספר משתמשים בו-זמנית")
                st.info("💡 טעון משתמשים מהמערכת, בחר את המשתמשים הרצויים והוסף אותם לקבוצה בבת אחת")

                # כפתור טעינת משתמשים
                st.markdown('<div class="action-button">', unsafe_allow_html=True)
                if st.button("👥 טען משתמשים זמינים", key="load_available_users", use_container_width=True):
                    with st.spinner("טוען משתמשים..."):
                        all_users = api.get_users(CONFIG['PROVIDERS']['LOCAL'], max_records=500)
                        if all_users:
                            # סינון משתמשים שכבר בקבוצה
                            current_member_usernames = [m.get('userName', m.get('username', '')) for m in group_data['members']]
                            available_users = [u for u in all_users if u.get('userName', u.get('username', '')) not in current_member_usernames]

                            st.session_state.available_users_for_bulk = available_users
                            st.session_state.selected_users_to_add = []
                            st.session_state.user_add_checkbox_counter = 0
                            st.success(f"✅ נמצאו {len(available_users)} משתמשים זמינים להוספה")
                            st.rerun()
                        else:
                            st.warning("לא נמצאו משתמשים")
                st.markdown('</div>', unsafe_allow_html=True)

                # הצגת רשימת משתמשים
                if 'available_users_for_bulk' in st.session_state:
                    users = st.session_state.available_users_for_bulk

                    if 'selected_users_to_add' not in st.session_state:
                        st.session_state.selected_users_to_add = []

                    if 'user_add_checkbox_counter' not in st.session_state:
                        st.session_state.user_add_checkbox_counter = 0

                    # חיפוש משתמשים
                    user_search = st.text_input("🔍 חיפוש משתמשים", placeholder="הקלד שם משתמש או שם מלא...", key="user_add_search")

                    # סינון לפי חיפוש
                    filtered_users = users
                    if user_search:
                        filtered_users = [
                            u for u in users
                            if user_search.lower() in u.get('userName', u.get('username', '')).lower() or
                               user_search.lower() in u.get('fullName', '').lower()
                        ]

                    if filtered_users:
                        st.write(f"**{len(filtered_users)} משתמשים זמינים**")

                        # כפתור בחר הכל / נקה
                        all_user_usernames = [u.get('userName', u.get('username', '')) for u in filtered_users]

                        st.markdown('<div class="action-button">', unsafe_allow_html=True)
                        if st.session_state.selected_users_to_add and len(st.session_state.selected_users_to_add) == len(all_user_usernames):
                            if st.button("❌ נקה בחירה", key="clear_all_users_to_add", use_container_width=True):
                                st.session_state.selected_users_to_add = []
                                st.session_state.user_add_checkbox_counter += 1
                                st.rerun()
                        else:
                            if st.button("✅ בחר הכל", key="select_all_users_to_add", use_container_width=True):
                                st.session_state.selected_users_to_add = all_user_usernames.copy()
                                st.session_state.user_add_checkbox_counter += 1
                                st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)

                        # רשימת משתמשים עם checkboxes
                        temp_add_selections = []
                        for user in filtered_users:
                            username = user.get('userName', user.get('username', ''))
                            full_name = user.get('fullName', '')
                            department = user.get('department', '')

                            label = f"{username}"
                            if full_name:
                                label += f" ({full_name})"
                            if department:
                                label += f" [{department}]"

                            is_checked = username in st.session_state.selected_users_to_add
                            checkbox_result = st.checkbox(label, value=is_checked,
                                                         key=f"add_user_checkbox_{username}_{st.session_state.user_add_checkbox_counter}")

                            if checkbox_result:
                                temp_add_selections.append(username)

                        # עדכון הסטייט
                        if temp_add_selections != st.session_state.selected_users_to_add:
                            st.session_state.selected_users_to_add = temp_add_selections
                            st.rerun()

                        # כפתור הוספה
                        num_to_add = len(st.session_state.selected_users_to_add)
                        if num_to_add >= 1:
                            st.info(f"✓ נבחרו {num_to_add} משתמשים להוספה")

                            st.markdown('<div class="action-button">', unsafe_allow_html=True)
                            if st.button(f"➕ הוסף {num_to_add} משתמשים לקבוצה", key="bulk_add_to_group", use_container_width=True):
                                st.session_state.confirm_bulk_add = True
                                st.rerun()
                            st.markdown('</div>', unsafe_allow_html=True)

                            # אימות הוספה
                            if st.session_state.get('confirm_bulk_add', False):
                                st.warning(f"⚠️ האם אתה בטוח שברצונך להוסיף {num_to_add} משתמשים לקבוצה '{group_data['group_name']}'?")

                                col_y, col_n = st.columns(2)
                                with col_y:
                                    st.markdown('<div class="action-button">', unsafe_allow_html=True)
                                    if st.button("✅ אשר הוספה", key="confirm_add_yes", use_container_width=True):
                                        # ביצוע ההוספה
                                        with st.spinner("מוסיף משתמשים..."):
                                            progress_bar = st.progress(0)
                                            status_text = st.empty()

                                            success_add_count = 0
                                            fail_add_count = 0
                                            failed_add_users = []

                                            total_add = len(st.session_state.selected_users_to_add)

                                            for idx, username in enumerate(st.session_state.selected_users_to_add):
                                                status_text.text(f"מוסיף {idx + 1}/{total_add}: {username}...")
                                                progress_bar.progress((idx + 1) / total_add)

                                                success = api.add_user_to_group(username, group_data['group_name'])
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

                                            # רענון הקבוצה
                                            members = api.get_group_members(group_data['group_name'])
                                            if members is not None:
                                                st.session_state.group_members_data = {
                                                    'group_name': group_data['group_name'],
                                                    'members': members,
                                                    'count': len(members)
                                                }

                                            # ניקוי
                                            st.session_state.confirm_bulk_add = False
                                            if 'available_users_for_bulk' in st.session_state:
                                                del st.session_state.available_users_for_bulk
                                            if 'selected_users_to_add' in st.session_state:
                                                del st.session_state.selected_users_to_add

                                            st.rerun()
                                    st.markdown('</div>', unsafe_allow_html=True)

                                with col_n:
                                    st.markdown('<div class="action-button">', unsafe_allow_html=True)
                                    if st.button("❌ ביטול", key="confirm_add_no", use_container_width=True):
                                        st.session_state.confirm_bulk_add = False
                                        st.rerun()
                                    st.markdown('</div>', unsafe_allow_html=True)
                    else:
                        st.info("לא נמצאו משתמשים התואמים את החיפוש")

        # כפתור נקה תוצאות
        st.markdown("---")
        st.markdown('<div class="action-button">', unsafe_allow_html=True)
        if st.button("🗑️ סגור קבוצה", key="clear_group_results", use_container_width=True):
            # ניקוי מלא של כל המצבים הקשורים לקבוצה
            if 'group_members_data' in st.session_state:
                del st.session_state.group_members_data
            if 'selected_group_name' in st.session_state:
                del st.session_state.selected_group_name
            if 'selected_group_members' in st.session_state:
                del st.session_state.selected_group_members
            if 'confirm_bulk_remove' in st.session_state:
                del st.session_state.confirm_bulk_remove
            if 'bulk_remove_in_progress' in st.session_state:
                del st.session_state.bulk_remove_in_progress
            if 'bulk_remove_results' in st.session_state:
                del st.session_state.bulk_remove_results
            if 'group_checkbox_counter' in st.session_state:
                del st.session_state.group_checkbox_counter
            if 'available_users_for_bulk' in st.session_state:
                del st.session_state.available_users_for_bulk
            if 'selected_users_to_add' in st.session_state:
                del st.session_state.selected_users_to_add
            if 'confirm_bulk_add' in st.session_state:
                del st.session_state.confirm_bulk_add
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    show()
