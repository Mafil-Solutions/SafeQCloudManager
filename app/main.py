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
    סטיילינג מודרני עם sidebar בצד ימין, צבעי Mafil, ורווחים מצומצמים
    """
    direction = "rtl" if rtl else "ltr"
    text_align = "right" if rtl else "left"

    # צבעי Mafil (אדום-כחול)
    primary_color = "#C41E3A"  # אדום Mafil
    secondary_color = "#4A90E2"  # כחול Mafil
    accent_color = "#C41E3A"  # אדום לנקודות הדגשה
    hover_color = "#ffe4e9"  # אדום בהיר מאוד
    sidebar_bg = "#f8fafc"  # רקע עדין אפור-לבן

    st.markdown(f"""
    <style>
        /* Global RTL/LTR */
        .stApp {{
            direction: {direction};
            text-align: {text_align};
            background: #F5F6FF !important;
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
            text-align: right;
            margin-left: auto;
            margin-right: 0;
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

        /* כותרות קטגוריות ראשיות - ללא הזחה */
        [data-testid="stSidebarNav"] > ul > li > details {{
            margin-top: 0.8rem !important;
            margin-bottom: 0.3rem !important;
            position: relative !important;
        }}

        [data-testid="stSidebarNav"] > ul > li > details > summary {{
            padding: 0.6rem 2.5rem 0.6rem 1rem !important;
            font-weight: 700 !important;
            font-size: 1rem !important;
            color: {accent_color} !important;
            list-style: none !important;
            cursor: pointer !important;
            background-color: rgba(196, 30, 58, 0.08) !important;
            border-radius: 0.5rem !important;
            margin-bottom: 0.3rem !important;
            position: relative !important;
            border: 1px solid rgba(196, 30, 58, 0.1) !important;
        }}

        /* דפים בודדים ברמה העליונה - ללא הזחה */
        [data-testid="stSidebarNav"] > ul > li > div {{
            margin-bottom: 0.5rem !important;
        }}

        /* תתי תפריטים - הזחה ברורה */
        [data-testid="stSidebarNav"] details > ul {{
            background-color: rgba(255, 255, 255, 0.5) !important;
            border-radius: 0.3rem !important;
            padding: 0.5rem 0.5rem 0.5rem 0 !important;
            margin: 0.3rem 0 0.5rem 2rem !important;
            border-right: 3px solid {accent_color} !important;
        }}

        [data-testid="stSidebarNav"] details > ul > li {{
            margin: 0.2rem 0 !important;
        }}

        [data-testid="stSidebarNav"] details > ul > li > div {{
            padding: 0.4rem 1rem 0.4rem 0.5rem !important;
            font-size: 0.9rem !important;
            font-weight: 400 !important;
            margin-right: 0.5rem !important;
        }}

        /* הסתרת marker ברירת המחדל */
        [data-testid="stSidebarNav"] details summary::-webkit-details-marker,
        [data-testid="stSidebarNav"] summary::-moz-list-bullet {{
            display: none !important;
        }}

        /* חץ מותאם אישית - תמיד גלוי וברור */
        [data-testid="stSidebarNav"] > ul > li > details > summary::after {{
            content: "◀" !important;
            position: absolute !important;
            right: 0.7rem !important;
            top: 50% !important;
            transform: translateY(-50%) !important;
            transition: transform 0.25s ease !important;
            color: {accent_color} !important;
            font-size: 1.2rem !important;
            font-weight: 900 !important;
            opacity: 1 !important;
            z-index: 10 !important;
        }}

        [data-testid="stSidebarNav"] details[open] > summary::after {{
            transform: translateY(-50%) rotate(-90deg) !important;
        }}

        /* Hover על קטגוריה ראשית */
        [data-testid="stSidebarNav"] > ul > li > details > summary:hover {{
            background-color: rgba(196, 30, 58, 0.15) !important;
            border-color: rgba(196, 30, 58, 0.3) !important;
        }}

        /* Sidebar text */
        section[data-testid="stSidebar"] .stMarkdown {{
            color: #334155 !important;
        }}

        /* Buttons */
        .stButton > button {{
            border-radius: 25px;
            font-weight: 600;
            transition: all 0.3s;
            direction: {direction};
            background: linear-gradient(45deg, {primary_color}, #FF6B6B) !important;
            color: white !important;
            border: none !important;
            padding: 0.5rem 1.5rem;
            box-shadow: 0 4px 15px rgba(196, 30, 58, 0.3);
        }}

        .stButton > button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(196, 30, 58, 0.4) !important;
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
    """הצגת מידע משתמש קומפקטי בראש העמוד - שורה אחת זעירה"""
    role = st.session_state.get('role', st.session_state.get('access_level', 'viewer'))

    role_names = {
        'viewer': 'צופה',
        'support': 'תמיכה',
        'admin': 'מנהל',
        'superadmin': 'מנהל על'
    }
    level_text = role_names.get(role, "משתמש")

    # CSS לכפתורים קטנים מאוד
    st.markdown("""
    <style>
        /* כפתורים זעירים בהדר */
        div[data-testid="column"] .stButton > button {
            padding: 0.15rem 0.5rem !important;
            font-size: 0.8rem !important;
            height: 1.6rem !important;
            min-height: 1.6rem !important;
            background: white !important;
            color: #666 !important;
            border: 1px solid #ddd !important;
        }

        div[data-testid="column"] .stButton > button:hover {
            background: #f5f5f5 !important;
            border-color: #C41E3A !important;
        }

        /* Expander זעיר */
        div[data-testid="column"] .streamlit-expanderHeader {
            font-size: 0.75rem !important;
            padding: 0.15rem 0.4rem !important;
            min-height: 1.6rem !important;
        }

        /* טקסט זעיר */
        div[data-testid="column"] p {
            font-size: 0.8rem !important;
            margin: 0.1rem 0 !important;
            line-height: 1.2 !important;
        }
    </style>
    """, unsafe_allow_html=True)

    # שורה קומפקטית מאוד
    col_user, col_info, col_refresh, col_logout = st.columns([3, 1, 0.8, 0.9])

    with col_user:
        # אייקון משתמש + שם + רמה
        st.markdown(f"<small style='font-size:0.85rem'>👤 **{st.session_state.get('username', 'N/A')}** · {level_text}</small>", unsafe_allow_html=True)

    with col_info:
        # אייקון מידע עם קבוצות
        with st.expander("ℹ️", expanded=False):
            if st.session_state.get('allowed_departments'):
                if st.session_state.allowed_departments == ["ALL"]:
                    st.caption("✅ הכל")
                else:
                    dept_count = len(st.session_state.allowed_departments)
                    st.caption(f"**{dept_count} מחלקות**")
                    for dept in st.session_state.allowed_departments[:3]:
                        st.caption(f"• {dept}")
                    if dept_count > 3:
                        st.caption(f"+{dept_count - 3}")
            else:
                st.caption("אין קבוצות")

    with col_refresh:
        if st.button("🔄", key="refresh_page", help="ניקוי נתונים", use_container_width=True):
            keys_to_keep = ['logged_in', 'username', 'user_email', 'user_groups', 'access_level',
                            'login_time', 'auth_method', 'session_id',
                            'entra_username', 'local_username', 'role', 'local_groups', 'allowed_departments']
            for key in list(st.session_state.keys()):
                if key not in keys_to_keep:
                    del st.session_state[key]
            st.rerun()

    with col_logout:
        if st.button("🚪➡️", key="logout_btn", help="יציאה מהמערכת", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()


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

    # Header קומפקטי מאוד עם לוגו
    st.markdown("""
    <style>
        .header-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 0.3rem;
            padding: 0.25rem 0;
        }
        .title-text {
            font-size: 1.1rem;
            font-weight: 700;
            color: #C41E3A;
            margin: 0;
            padding: 0;
            line-height: 1;
        }
        .logo-small {
            height: 40px;
        }
    </style>
    """, unsafe_allow_html=True)

    col_logo, col_title, col_user = st.columns([1.2, 2, 6.8])

    with col_logo:
        # לוגו של החברה - קטן יותר
        try:
            import sys
            import os

            def resource_path(relative_path: str) -> str:
                """מחזיר נתיב תקין לקובץ"""
                if hasattr(sys, "_MEIPASS"):
                    return os.path.join(sys._MEIPASS, relative_path)
                return os.path.join(os.path.abspath("."), relative_path)

            logo_path = resource_path("assets/MafilIT_Logo.png")
            st.image(logo_path, width=140)
        except Exception as e:
            # אם הלוגו לא נמצא, הצג טקסט
            st.markdown("**MafilIT**")

    with col_title:
        st.markdown('<div class="title-text">Mafil Cloud Services</div>', unsafe_allow_html=True)

    with col_user:
        show_compact_user_info()

    st.markdown('<hr style="margin: 0.3rem 0; border: 1px solid #e5e7eb;">', unsafe_allow_html=True)

    if not check_config():
        st.stop()

    # ייבוא דפים (רק אחרי login!)
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

    # דף הבית - עם גישה לאובייקטי Page
    from pages.home import create_home_page
    home_page = create_home_page(users_list_page, users_search_page, users_add_page, users_groups_page, my_activity_page)

    # יצירת ניווט עם קבוצות היררכיות
    nav = st.navigation({
        "ראשי": [home_page],
        "👥 משתמשים": [users_overview_page, users_list_page, users_search_page, users_add_page, users_groups_page],
        "🖨️ מדפסות": [printers_page],
        "📄 סריקה": [scanning_page],
        "📊 דוחות": [reports_page],
        "פעילות": [my_activity_page]
    })

    # בדיקת חיבור בסיידבר
    with st.sidebar:
        st.markdown("---")
        st.markdown("##### 🔌 בדיקת חיבור")
        if st.button("בדוק חיבור לשרת", key="sidebar_test_connection", use_container_width=True):
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

    # הרצת הדף הנבחר
    nav.run()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"שגיאה קריטית: {str(e)}")
        st.exception(e)
