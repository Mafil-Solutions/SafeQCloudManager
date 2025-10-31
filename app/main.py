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
    סטיילינג מודרני עם sidebar בצד ימין, צבעי ברנד עדינים, ורווחים מצומצמים
    """
    direction = ltr
    text_align = ltr

    # צבעי SafeQ (כחול-סגול עדינים)
    primary_color = "#1e3a8a"  # כחול כהה
    secondary_color = "#3b82f6"  # כחול בהיר
    accent_color = "#8b5cf6"  # סגול
    hover_color = "#dbeafe"  # כחול בהיר מאוד
    sidebar_bg = "#f8fafc"  # רקע עדין אפור-לבן

    st.markdown(f"""
    <style>
        /* Global RTL/LTR */
        .stApp {{
            direction: {direction};
            text-align: {text_align};
        }}

        /* Sidebar בצד ימין עבור RTL - עדין ונקי */
        section[data-testid="stSidebar"] {{
            {'right: 0 !important; left: auto !important;' if rtl else ''}
            background-color: {sidebar_bg} !important;
            padding-top: 0.5rem !important;
            border-left: 2px solid {accent_color} !important;
            box-shadow: -2px 0 10px rgba(0, 0, 0, 0.05) !important;
        }}

        section[data-testid="stSidebar"] > div {{
            padding-top: 0.5rem !important;
            background-color: transparent !important;
        }}

        /* אנימציית סגירה מימין לשמאל */
        section[data-testid="stSidebar"][aria-expanded="false"] {{
            {'transform: translateX(100%) !important;' if rtl else 'transform: translateX(-100%) !important;'}
        }}

        section[data-testid="stSidebar"][aria-expanded="true"] {{
            transform: translateX(0) !important;
        }}

        /* תוכן הראשי יתחיל מצד שמאל כשה-sidebar בימין */
        .main {{
            {'margin-right: 21rem !important; margin-left: 0 !important;' if rtl else ''}
        }}

        /* צמצום header */
        header[data-testid="stHeader"] {{
            background-color: transparent;
            height: 2rem !important;
        }}

        /* צמצום padding עליון של התוכן */
        .main .block-container {{
            padding-top: 0.5rem !important;
            padding-bottom: 1rem !important;
            max-width: 100% !important;
        }}

        /* כותרת ראשית קומפקטית */
        .main h1 {{
            font-size: 1.5rem !important;
            margin-top: 0 !important;
            margin-bottom: 0.3rem !important;
            color: {primary_color} !important;
        }}

        .main > div:first-child > div > div > div > div:first-child p {{
            font-size: 0.85rem !important;
            margin: 0 !important;
            color: {secondary_color} !important;
        }}

        /* Sticky navigation */
        [data-testid="stSidebarNav"] {{
            position: sticky !important;
            top: 0 !important;
            z-index: 999 !important;
            background-color: transparent !important;
            padding: 0.5rem !important;
            margin-bottom: 0.5rem !important;
        }}

        /* עיצוב כפתורי ניווט */
        .stPageLink {{
            padding: 0.6rem 1rem !important;
            margin: 0.15rem 0 !important;
            border-radius: 0.5rem !important;
            transition: all 0.3s ease !important;
            color: #334155 !important;
            font-weight: 500 !important;
            background-color: transparent !important;
        }}

        .stPageLink:hover {{
            background-color: {hover_color} !important;
            color: {primary_color} !important;
            transform: translateX({'-3px' if rtl else '3px'}) !important;
            box-shadow: 0 2px 8px rgba(59, 130, 246, 0.2) !important;
        }}

        /* כפתור ניווט פעיל */
        .stPageLink[data-active="true"] {{
            background: linear-gradient(90deg, {secondary_color}, {accent_color}) !important;
            color: white !important;
            font-weight: 600 !important;
        }}

        /* כותרות קטגוריות בניווט */
        [data-testid="stSidebarNav"] ul {{
            padding: 0 !important;
        }}

        /* קטגוריה ראשית (details/summary) - הזחה גדולה */
        [data-testid="stSidebarNav"] > ul > li > details {{
            margin-top: 0.8rem !important;
            margin-bottom: 0.3rem !important;
        }}

        [data-testid="stSidebarNav"] > ul > li > details > summary {{
            padding-right: 2rem !important;
            padding-left: 0.5rem !important;
            font-weight: 700 !important;
            font-size: 1rem !important;
            color: {accent_color} !important;
            list-style: none !important;
            cursor: pointer !important;
            background-color: rgba(139, 92, 246, 0.05) !important;
            border-radius: 0.5rem !important;
            padding-top: 0.5rem !important;
            padding-bottom: 0.5rem !important;
            margin-bottom: 0.3rem !important;
        }}

        /* דפים בודדים ברמה העליונה (כמו "ראשי", "פעילות") */
        [data-testid="stSidebarNav"] > ul > li > div.stPageLink {{
            padding-right: 2rem !important;
        }}

        /* תתי תפריטים - הזחה קטנה יותר */
        [data-testid="stSidebarNav"] details ul li {{
            padding-right: 0rem !important;
        }}

        [data-testid="stSidebarNav"] details ul li .stPageLink {{
            padding-right: 3rem !important;
            font-size: 0.9rem !important;
            font-weight: 400 !important;
        }}

        /* הסתרת marker ברירת המחדל */
        [data-testid="stSidebarNav"] details summary::-webkit-details-marker {{
            display: none !important;
        }}

        /* חץ מותאם אישית - תמיד נראה ומודגש */
        [data-testid="stSidebarNav"] > ul > li > details > summary::before {{
            content: "◀" !important;
            display: inline-block !important;
            position: absolute !important;
            right: 0.5rem !important;
            top: 50% !important;
            transform: translateY(-50%) !important;
            transition: transform 0.3s ease !important;
            color: {accent_color} !important;
            font-size: 1rem !important;
            font-weight: bold !important;
            opacity: 1 !important;
        }}

        [data-testid="stSidebarNav"] details[open] > summary::before {{
            transform: translateY(-50%) rotate(-90deg) !important;
        }}

        /* Hover על קטגוריה ראשית */
        [data-testid="stSidebarNav"] > ul > li > details > summary:hover {{
            background-color: rgba(139, 92, 246, 0.15) !important;
        }}

        /* Sidebar text */
        section[data-testid="stSidebar"] .stMarkdown {{
            color: #334155 !important;
        }}

        /* Buttons */
        .stButton > button {{
            border-radius: 0.5rem;
            font-weight: 500;
            transition: all 0.3s;
            direction: {direction};
            background-color: {secondary_color} !important;
            color: white !important;
            border: none !important;
        }}

        .stButton > button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4) !important;
            background-color: {primary_color} !important;
        }}

        /* Tables */
        .dataframe {{
            direction: {direction};
            text-align: {text_align};
        }}

        /* Expander */
        .streamlit-expanderHeader {{
            background-color: rgba(255, 255, 255, 0.1) !important;
            border-radius: 0.3rem !important;
        }}

        /* Text inputs */
        .stTextInput input, .stSelectbox select, .stNumberInput input {{
            border-radius: 0.5rem !important;
            border: 2px solid {secondary_color} !important;
        }}

        .stTextInput input:focus, .stSelectbox select:focus, .stNumberInput input:focus {{
            border-color: {accent_color} !important;
            box-shadow: 0 0 0 2px rgba(139, 92, 246, 0.2) !important;
        }}
    </style>
    """, unsafe_allow_html=True)


def show_compact_user_info():
    """הצגת מידע משתמש קומפקטי בראש העמוד - שורה אחת"""
    role = st.session_state.get('role', st.session_state.get('access_level', 'viewer'))
    role_icons = {
        'viewer': '👁️',
        'support': '🛠️',
        'admin': '👑',
        'superadmin': '⭐'
    }
    access_icon = role_icons.get(role, '👤')

    role_names = {
        'viewer': 'צופה',
        'support': 'תמיכה',
        'admin': 'מנהל',
        'superadmin': 'מנהל על'
    }
    level_text = role_names.get(role, "משתמש")
    auth_text = "Entra ID" if st.session_state.get('auth_method') == 'entra_id' else "מקומי"

    # שורה אחת - מיושרת ימינה
    col_user, col_auth, col_details, col_logout, col_test = st.columns([3, 2, 2, 1.5, 1.5])

    with col_user:
        st.markdown(f"**{access_icon} {st.session_state.get('username', 'N/A')}** • {level_text}")

    with col_auth:
        st.markdown(f"🔐 {auth_text}")

    with col_details:
        # Expander קטן לקבוצות בלבד
        with st.expander("📁 קבוצות", expanded=False):
            if st.session_state.get('allowed_departments'):
                if st.session_state.allowed_departments == ["ALL"]:
                    st.success("✅ כל המחלקות")
                else:
                    dept_count = len(st.session_state.allowed_departments)
                    st.caption(f"**{dept_count} מחלקות:**")
                    for dept in st.session_state.allowed_departments[:5]:
                        st.write(f"• {dept}")
                    if dept_count > 5:
                        st.caption(f"ועוד {dept_count - 5}...")
            else:
                st.info("אין קבוצות מוגדרות")

    with col_logout:
        if st.button("🚪 יציאה", key="logout_btn", help="התנתק מהמערכת", use_container_width=True):
            # Clear session
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    with col_test:
        api = SafeQAPI()
        if st.button("🔍 בדוק", key="header_test_connection", help="בדיקת חיבור", use_container_width=True):
            logger = AuditLogger()
            with st.spinner("..."):
                if api.test_connection():
                    st.success("✅")
                    logger.log_action(st.session_state.username, "Connection Test", "Success",
                                    st.session_state.get('user_email', ''), "", True,
                                    st.session_state.get('access_level', 'viewer'))
                else:
                    st.error("❌")
                    logger.log_action(st.session_state.username, "Connection Test", "Failed",
                                    st.session_state.get('user_email', ''), "", False,
                                    st.session_state.get('access_level', 'viewer'))


def show_sidebar_info():
    """הצגת מידע מפורט במסגרת צד"""
    with st.sidebar:
        st.markdown("### 🔧 מערכת")
        st.info(f"🌐 {CONFIG['SERVER_URL']}")

        st.markdown("### 👤 משתמש")

        role = st.session_state.get('role', st.session_state.get('access_level', 'viewer'))
        role_icons = {
            'viewer': '👁️',
            'support': '🛠️',
            'admin': '👑',
            'superadmin': '⭐'
        }
        access_icon = role_icons.get(role, '👤')

        st.info(f"{access_icon} {st.session_state.get('username', 'N/A')}")

        # אימייל עם expander
        with st.expander("📧 פרטים נוספים"):
            st.write(f"**אימייל:** {st.session_state.get('user_email', 'N/A')}")

            if st.session_state.get('local_username'):
                st.write(f"**משתמש לוקאלי:** {st.session_state.local_username}")

            auth_text = "Entra ID" if st.session_state.get('auth_method') == 'entra_id' else "מקומי"
            st.write(f"**אימות:** {auth_text}")

        # הרשאות
        if st.session_state.get('allowed_departments'):
            if st.session_state.allowed_departments == ["ALL"]:
                st.success("📁 כל המחלקות")
            else:
                dept_count = len(st.session_state.allowed_departments)
                with st.expander(f"📁 {dept_count} מחלקות"):
                    for dept in st.session_state.allowed_departments:
                        st.write(f"• {dept}")


def main():
    st.set_page_config(
        page_title="SafeQ Cloud Manager",
        page_icon="🔐",
        layout="wide",
        initial_sidebar_state="expanded"  # פתוח אחרי login
    )

    init_session_state()

    # Apply compact styling
    is_logged_in = st.session_state.get('logged_in', False) and is_session_valid()
    apply_modern_styling_compact(rtl=is_logged_in)

    # Hide sidebar before login
    if not is_logged_in:
        st.markdown("""
        <style>
            section[data-testid="stSidebar"] {
                display: none !important;
            }
        </style>
        """, unsafe_allow_html=True)

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
        return  # עוצר כאן - לא מגיע לניווט!

    # ===== רק אחרי login מגיעים לכאן =====

    # Header קומפקטי עם לוגו
    st.markdown("""
    <style>
        .header-logo {
            display: flex;
            align-items: center;
            gap: 1rem;
            margin-bottom: 1rem;
        }
        .logo-icon {
            width: 50px;
            height: 50px;
            background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 50%, #8b5cf6 100%);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
        }
        .logo-text {
            font-size: 1.8rem;
            font-weight: 700;
            background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 50%, #8b5cf6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin: 0;
            padding: 0;
            line-height: 1;
        }
        .logo-subtitle {
            font-size: 0.75rem;
            color: #64748b;
            margin-top: 0.2rem;
            font-weight: 400;
        }
    </style>
    """, unsafe_allow_html=True)

    col_logo, col_user = st.columns([3, 2])
    with col_logo:
        st.markdown("""
        <div class="header-logo">
            <div class="logo-icon">🔐</div>
            <div>
                <div class="logo-text">SafeQ Cloud Manager</div>
                <div class="logo-subtitle">Print Management Platform</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col_user:
        show_compact_user_info()

    st.markdown("---")

    if not check_config():
        st.stop()

    # ייבוא דפים (רק אחרי login!)
    from pages.home import show as home_show
    from pages.my_activity import show as my_activity_show
    from pages.users.overview import show as users_overview_show
    from pages.users.user_list import show as users_list_show
    from pages.users.search_edit import show as users_search_show
    from pages.users.add_user import show as users_add_show
    from pages.users.groups import show as users_groups_show
    from pages.printers import show as printers_show
    from pages.scanning import show as scanning_show
    from pages.reports import show as reports_show

    # הגדרת דפים עם st.Page() - עם URL ייחודי לכל אחד
    home_page = st.Page(home_show, title="בית", icon="🏠", url_path="home", default=True)

    # דפי משתמשים - עם דף סקירה
    users_overview_page = st.Page(users_overview_show, title="סקירה", icon="👥", url_path="users_overview")
    users_list_page = st.Page(users_list_show, title="רשימת משתמשים", icon="📋", url_path="users_list")
    users_search_page = st.Page(users_search_show, title="חיפוש ועריכה", icon="🔍", url_path="users_search")
    users_add_page = st.Page(users_add_show, title="הוספת משתמש", icon="➕", url_path="users_add")
    users_groups_page = st.Page(users_groups_show, title="קבוצות", icon="👨‍👩‍👧‍👦", url_path="users_groups")

    # דפים עתידיים
    printers_page = st.Page(printers_show, title="מדפסות", icon="🖨️", url_path="printers")
    scanning_page = st.Page(scanning_show, title="תהליכי סריקה", icon="📄", url_path="scanning")
    reports_page = st.Page(reports_show, title="דוחות", icon="📊", url_path="reports")

    # דף הפעילות שלי
    my_activity_page = st.Page(my_activity_show, title="הפעילות שלי", icon="📋", url_path="my_activity")

    # יצירת ניווט עם קבוצות היררכיות
    nav = st.navigation({
        "ראשי": [home_page],
        "👥 משתמשים": [users_overview_page, users_list_page, users_search_page, users_add_page, users_groups_page],
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
