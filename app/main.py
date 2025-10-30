#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SafeQ Cloud Manager - Main Application (New Multi-Page Structure)
גרסה חדשה עם ניווט היררכי ודפים נפרדים
"""

import streamlit as st
import sys
import os

# ייבוא config
from config import config

# ייבוא permissions
from permissions import initialize_user_permissions

# ייבוא פונקציות מהקובץ המקורי
from main_utils import (
    init_session_state,
    is_session_valid,
    show_login_page,
    check_config,
    AuditLogger,
    SafeQAPI
)

CONFIG = config.get()

# בדיקת תקינות הגדרות
is_valid, errors, warnings = config.validate()
if not is_valid:
    st.error("⚠️ שגיאות תצורה:")
    for error in errors:
        st.error(error)
    st.stop()

if warnings:
    for warning in warnings:
        st.warning(warning)


def apply_modern_styling_compact(rtl=False):
    """
    סטיילינג מודרני עם header קבוע ורווחים מצומצמים
    """
    direction = "rtl" if rtl else "ltr"
    text_align = "right" if rtl else "left"

    st.markdown(f"""
    <style>
        /* Global RTL/LTR */
        .stApp {{
            direction: {direction};
            text-align: {text_align};
        }}

        /* צמצום רווחים של header */
        header[data-testid="stHeader"] {{
            background-color: transparent;
            height: 2.5rem !important;
        }}

        /* צמצום padding עליון */
        .main .block-container {{
            padding-top: 1rem !important;
            padding-bottom: 2rem !important;
        }}

        /* Sticky navigation - נעול בחלק העליון */
        [data-testid="stSidebarNav"] {{
            position: sticky !important;
            top: 0 !important;
            z-index: 999 !important;
            background-color: var(--background-color) !important;
        }}

        /* עיצוב כפתורי ניווט */
        .stPageLink {{
            padding: 0.5rem 1rem !important;
            margin: 0.2rem 0 !important;
            border-radius: 0.5rem !important;
            transition: all 0.2s !important;
        }}

        .stPageLink:hover {{
            background-color: rgba(151, 166, 195, 0.15) !important;
            transform: translateX(-2px) !important;
        }}

        /* כותרת קטגוריה */
        .stSidebarNav > div > div > div:first-child {{
            font-weight: 600 !important;
            font-size: 0.9rem !important;
            color: var(--text-color) !important;
            margin-top: 1rem !important;
            margin-bottom: 0.5rem !important;
        }}

        /* Buttons */
        .stButton > button {{
            border-radius: 0.5rem;
            font-weight: 500;
            transition: all 0.2s;
            direction: {direction};
        }}

        .stButton > button:hover {{
            transform: translateY(-1px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }}

        /* Sidebar compact */
        section[data-testid="stSidebar"] {{
            padding-top: 1rem !important;
        }}

        section[data-testid="stSidebar"] > div {{
            padding-top: 1rem !important;
        }}

        /* Tables */
        .dataframe {{
            direction: {direction};
            text-align: {text_align};
        }}

        /* Headers */
        h1, h2, h3 {{
            margin-top: 0.5rem !important;
            margin-bottom: 0.5rem !important;
        }}
    </style>
    """, unsafe_allow_html=True)


def show_sidebar_info():
    """הצגת מידע במסגרת צד"""
    with st.sidebar:
        st.markdown("### 🔧 פרטי מערכת")
        st.info(f"🌐 שרת: {CONFIG['SERVER_URL']}")

        st.markdown("### 👤 פרטי משתמש")
        auth_text = "🌐 Entra ID" if st.session_state.get('auth_method') == 'entra_id' else "🔑 מקומי"
        st.info(f"🔐 אימות: {auth_text}")

        role = st.session_state.get('role', st.session_state.get('access_level', 'viewer'))
        role_icons = {
            'viewer': '👁️',
            'support': '🛠️',
            'admin': '👑',
            'superadmin': '⭐'
        }
        access_icon = role_icons.get(role, '👤')

        st.info(f"{access_icon} {st.session_state.get('username', 'N/A')}")
        st.info(f"📧 {st.session_state.get('user_email', 'N/A')}")

        role_names = {
            'viewer': '👁️ צופה',
            'support': '🛠️ תמיכה',
            'admin': '👑 מנהל',
            'superadmin': '⭐ מנהל על'
        }
        level_text = role_names.get(role, "👤 משתמש")
        st.info(f"רמה: {level_text}")

        if st.session_state.get('local_username'):
            st.info(f"🏠 משתמש לוקאלי: {st.session_state.local_username}")

        if st.session_state.get('allowed_departments'):
            if st.session_state.allowed_departments == ["ALL"]:
                st.success("📁 הרשאות: כל המחלקות")
            else:
                dept_count = len(st.session_state.allowed_departments)
                st.info(f"📁 מחלקות מורשות: {dept_count}")
                with st.expander("הצג מחלקות"):
                    for dept in st.session_state.allowed_departments:
                        st.write(f"• {dept}")

        # כפתור בדיקת חיבור
        if st.button("🔍 בדיקת חיבור", key="sidebar_test_connection"):
            api = SafeQAPI()
            logger = AuditLogger()
            with st.spinner("בודק..."):
                if api.test_connection():
                    st.success("✅ החיבור תקין!")
                    logger.log_action(st.session_state.username, "Connection Test", "Success",
                                    st.session_state.get('user_email', ''), "", True,
                                    st.session_state.get('access_level', 'viewer'))
                else:
                    st.error("❌ החיבור נכשל")
                    logger.log_action(st.session_state.username, "Connection Test", "Failed",
                                    st.session_state.get('user_email', ''), "", False,
                                    st.session_state.get('access_level', 'viewer'))


def main():
    st.set_page_config(
        page_title="SafeQ Cloud Manager",
        page_icon="🔐",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    init_session_state()

    # Apply compact styling
    is_logged_in = st.session_state.get('logged_in', False) and is_session_valid()
    apply_modern_styling_compact(rtl=is_logged_in)

    # בדיקת אימות
    if not is_logged_in:
        if st.session_state.get('logged_in') and not is_session_valid():
            st.warning("⚠️ פג תוקף ההתחברות. אנא התחבר שוב.")
            logger = AuditLogger()
            logger.log_action(st.session_state.get('username', 'Unknown'), "Session Expired", "Timeout")

            for key in ['logged_in', 'username', 'user_email', 'user_groups',
                       'access_level', 'login_time', 'auth_method']:
                if key in st.session_state:
                    del st.session_state[key]

        show_login_page()
        return

    # Header
    st.title("🔐 SafeQ Cloud Manager")
    st.caption("ניהול משתמשים ומדפסות SafeQ Cloud")
    st.markdown("---")

    if not check_config():
        st.stop()

    # הצגת sidebar
    show_sidebar_info()

    # ייבוא דפים
    from pages.home import show as home_show
    from pages.my_activity import show as my_activity_show
    from pages.users.user_list import show as users_list_show
    from pages.users.search_edit import show as users_search_show
    from pages.users.add_user import show as users_add_show
    from pages.users.groups import show as users_groups_show
    from pages.printers import show as printers_show
    from pages.scanning import show as scanning_show
    from pages.reports import show as reports_show

    # הגדרת דפים עם st.Page()
    home_page = st.Page(home_show, title="בית", icon="🏠", default=True)

    # דפי משתמשים
    users_list_page = st.Page(users_list_show, title="רשימת משתמשים", icon="📋")
    users_search_page = st.Page(users_search_show, title="חיפוש ועריכה", icon="🔍")
    users_add_page = st.Page(users_add_show, title="הוספת משתמש", icon="➕")
    users_groups_page = st.Page(users_groups_show, title="קבוצות", icon="👨‍👩‍👧‍👦")

    # דפים עתידיים
    printers_page = st.Page(printers_show, title="מדפסות", icon="🖨️")
    scanning_page = st.Page(scanning_show, title="תהליכי סריקה", icon="📄")
    reports_page = st.Page(reports_show, title="דוחות", icon="📊")

    # דף הפעילות שלי
    my_activity_page = st.Page(my_activity_show, title="הפעילות שלי", icon="📋")

    # יצירת ניווט עם קבוצות היררכיות
    nav = st.navigation({
        "ראשי": [home_page],
        "👥 משתמשים": [users_list_page, users_search_page, users_add_page, users_groups_page],
        "🖨️ מדפסות": [printers_page],
        "📄 סריקה": [scanning_page],
        "📊 דוחות": [reports_page],
        "פעילות": [my_activity_page]
    })

    # הרצת הדף הנבחר
    nav.run()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"שגיאה קריטית: {str(e)}")
        st.exception(e)
