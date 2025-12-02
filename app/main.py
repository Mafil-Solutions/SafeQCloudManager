#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SafeQ Cloud Manager - Main Application (New Multi-Page Structure)
גרסה חדשה עם ניווט היררכי ודפים נפרדים
Version: 2.0.1 - UI Overhaul Complete
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
    primary_color = "#D71F27"  # אדום Mafil
    secondary_color = "#009BDB"  # כחול Mafil
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

         div[data-testid="stMainBlockContainer"] {{
            padding: 3rem 1rem 10rem !important;
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
            transform: translateX(100%) !important;' if rtl else 'transform: translateX(-100%) !important;
            width: 0 !important;
            width: 0 !important;
            min-width: 0 !important;
            max-width: 0 !important;
            opacity: 0 !important;
            pointer-events: none !important; /* לא מאפשר אינטראקציה */
            overflow: hidden !important;
            border: none !important;
            box-shadow: none !important;
            transition: all 0.35s ease-in-out !important;
        }}

        section[data-testid="stSidebar"][aria-expanded="true"] {{
            transform: translateX(0) !important;
        }}
        
        /* הפוך את כל החיצים בסיידבר לגלויים תמיד */
        [data-testid="stSidebar"] [data-testid="stIconMaterial"] {{
            visibility: visible !important;
            opacity: 1 !important;
            transition: none !important;
            color: #343436;
            transform: rotate(180deg) !important;  /* שמאלה */
        }}

        [data-testid="stSidebar"] details[open] > [data-testid="stIconMaterial"] {{
            transform: rotate(270deg) !important; /* למעלה */
            color: #333 !important;  /* כהה יותר כשהוא פתוח */
        }}
        [data-testid="stSidebar"] details[open] summary span[data-testid="stIconMaterial"],
        [data-testid="stSidebar"] details[open] summary div span[data-testid="stIconMaterial"] {{
            color: #333 !important;
        }}

        /* אם Streamlit מכניס display:none בשלב כלשהו */
        [data-testid="stSidebar"] [data-testid="stIconMaterial"] {{
            display: inline-block !important;
        }}

        /* תוכן הראשי יתחיל מצד שמאל כשה-sidebar בימין */
        .main {{
            {'margin-right: 21rem !important; margin-left: 0 !important;' if rtl else ''}
        }}
        /* סוגר כל קטגוריה פתוחה (מסתיר תוכן) */
        [data-testid="stSidebarNav"] details[open] > ul {{
            display: none !important;
        }}
        
        /* משנה את כיוון החץ כך שייראה סגור */
        [data-testid="stSidebarNav"] details[open] summary svg {{
            transform: rotate(-90deg) !important;
            transition: none !important;
        }}

        /* צמצום header */
        header[data-testid="stHeader"] {{
            background-color: inherit;
            height: 1rem !important;
        }}
        /* מסובב את החיצים בהדר העליון של Streamlit */
        header [data-testid="stIconMaterial"] {{
            transform: rotate(180deg) !important;
            display: inline-block !important;
            color: black;
        }}
        /*מסתיר את השלוש נקודות מההדר העליו ב Streamlit */
        span[data-testid="stMainMenu"] {{
            visibility: hidden !important;
            pointer-events: none !important;
            }}
        
        /*מסתיר את המילה - Fork Streamlit */
        span[data-testid="stToolbarActionButtonLabel"] {{
            visibility: hidden !important;
            pointer-events: none !important;
        }}
        
        /*מסתיר את לוגו של ה- Fork Streamlit */
        div[data-testid="stToolbarActionButtonIcon"] {{
            visibility: hidden !important;
            pointer-events: none !important;
        }}

        /* הסתרת פוטר Streamlit */
        footer {{
            visibility: hidden !important;
            height: 0 !important;
            pointer-events: none !important;
        }}

        footer::before {{
            display: none !important;
        }}

        footer::after {{
            display: none !important;
        }}

        div[data-testid="stStatusWidget"] {{
            visibility: hidden !important;
            height: 0 !important;
            pointer-events: none !important;
        }}

        /* הסתרת "Made with Streamlit" */
        #MainMenu {{
            visibility: hidden !important;
        }}

        /* הסתרת App Creator Avatar ואלמנטים תחתונים */
        [data-testid="appCreatorAvatar"] {{
            display: none !important;
            visibility: hidden !important;
        }}

        div[class*="_profileContainer"] {{
            display: none !important;
            visibility: hidden !important;
        }}

        div[class*="_profilePreview"] {{
            display: none !important;
            visibility: hidden !important;
        }}

        /* הסתרת כל האלמנטים התחתונים ב-Streamlit Cloud */
        [class*="viewerBadge"] {{
            display: none !important;
        }}

        /* צמצום padding עליון של התוכן */
        .main .block-container {{
            padding-top: 1rem !important;
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

        /* Sidebar navigation - NOT sticky */
        [data-testid="stSidebarNavLink"] {{
            position: relative !important;
            /* background-color: transparent !important;*/
            padding-right: 2rem !important;
            margin-bottom: 0.1rem !important;
        }}

        /* עיצוב כפתורי ניווט */
        .stPageLink {{
            padding: 0.6rem 1rem !important;
            margin: 0.15rem 0 !important;
            border-radius: 0.5rem !important;
            transition: all 0.3s ease !important;
            color: #ffff !important;
            font-weight: 600 !important;
            background: linear-gradient(45deg, {primary_color}, #FF6B6B) !important;
        }}

        .stPageLink:hover {{
            background: linear-gradient(45deg, #FF6B6B, {primary_color}) !important;
            transform: translateY(-1px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2) !important;
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

        /* כותרות קטגוריות ראשיות - עם חץ גלוי והזחה ימינה */
        [data-testid="stSidebarNav"] > ul > li > details {{
            margin: 0.8rem 0 0.3rem 0 !important;
            position: relative !important;
            padding-right: 1rem !important;
        }}

        [data-testid="stSidebarNav"] > ul > li > details > summary {{
            padding: 0.6rem 1rem 0.6rem 2.5rem !important;
            font-weight: 700 !important;
            font-size: 1rem !important;
            color: {accent_color} !important;
            list-style: none !important;
            cursor: pointer !important;
            background: linear-gradient(45deg, rgba(196, 30, 58, 0.08), rgba(74, 144, 226, 0.05)) !important;
            border-radius: 0.5rem !important;
            margin-bottom: 0.3rem !important;
            position: relative !important;
            border: 1px solid rgba(196, 30, 58, 0.15) !important;
        }}

        /* דפים בודדים ברמה העליונה */
        [data-testid="stSidebarNav"] > ul > li > div:not([data-baseweb]) {{
            margin-bottom: 0.5rem !important;
            padding-right: 1rem !important;
        }}

        /* תתי תפריטים - הזחה מימין (RTL) */
        [data-testid="stSidebarNav"] details > ul {{
            background-color: rgba(255, 255, 255, 0.6) !important;
            border-radius: 0.4rem !important;
            padding: 0.5rem 0.5rem 0.5rem 3rem !important;
            margin-top: 0.3rem !important;
            margin-bottom: 0.5rem !important;
            margin-right: 0 !important;
            margin-left: 0 !important;
            border-right: 4px solid {accent_color} !important;
            box-shadow: inset 2px 0 5px rgba(0,0,0,0.05) !important;
        }}

        [data-testid="stSidebarNav"] details > ul > li {{
            margin: 0.15rem 0 !important;
        }}

        [data-testid="stSidebarNav"] details > ul > li > div {{
            padding: 0.4rem 0.8rem !important;
            font-size: 0.9rem !important;
            font-weight: 400 !important;
            border-radius: 0.3rem !important;
        }}

        /* החצים נשלטים על ידי Streamlit - אין שליטה מלאה דרך CSS */

        /* Hover על קטגוריה */
        [data-testid="stSidebarNavLink"] > ul > li > details[open] > summary:hover {{
            background-color: linear-gradient(45deg, rgba(196, 30, 58, 0.15), rgba(74, 144, 226, 0.1)) !important;
            border-color: rgba(196, 30, 58, 0.3) !important;
            transform: translateX(-2px) !important;
        }}

        /* דף פעיל - הדגשה חזקה */
        [data-testid="stSidebarNav"] .stPageLink[data-active="true"] {{
            background: linear-gradient(135deg, {primary_color} 0%, {secondary_color} 100%) !important;
            color: white !important;
            font-weight: 700 !important;
            box-shadow: 0 4px 15px rgba(196, 30, 58, 0.5) !important;
            border-right: 5px solid {primary_color} !important;
            transform: translateX(-5px) !important;
        }}

        /* קטגוריה פעילה */
        [data-testid="stSidebarNav"] > ul > li > details[open] > summary {{
            background: linear-gradient(45deg, rgba(196, 30, 58, 0.2), rgba(74, 144, 226, 0.15)) !important;
            border-color: {primary_color} !important;
            font-weight: 800 !important;
            box-shadow: 0 2px 10px rgba(196, 30, 58, 0.2) !important;
        }}

        /* Sidebar text */
        section[data-testid="stSidebar"] .stMarkdown {{
            color: #334155 !important;
        }}

        /* Buttons */
        .stButton > button {{
            background: linear-gradient(45deg,{primary_color}, #FF6B6B) !important;
            color: white;
            border: none;
            border-radius: 25px;
            padding: 0.5rem 1.5rem;
            font-weight: 600;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(196, 30, 58, 0.3);
            position: relative;
            overflow: hidden;

        }}

        .stButton > button:hover {{
            background: linear-gradient(45deg, #FF6B6B, {primary_color}) !important;
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(196, 30, 58, 0.5) !important;
        }}

        /* Primary button */
        .stButton > button[kind="primary"] {{
            background: linear-gradient(45deg,{primary_color}, #FF6B6B) !important;
            box-shadow: 0 4px 15px rgba(74, 144, 226, 0.3);
        }}

        .stButton > button[kind="primary"]:hover {{
            background: linear-gradient(45deg, #FF6B6B, {primary_color}) !important;
            box-shadow: 0 6px 20px rgba(74, 144, 226, 0.5) !important;
        }}
        
         /* Secondary Buttons */
        button[data-testid="stBaseButton-secondary"] {{
        background-color: inherit !important;
        transition:border-radius 200ms cubic-bezier(0.23, 1, 0.32, 1) 300ms, background-color 150ms;
        }}

        button[data-testid="stBaseButton-secondary"]:hover {{
        background-color: rgba(151, 166, 195, 0.15) !important;
        }}

        /* Tables */
        .dataframe {{
            direction: {direction};
            text-align: {text_align};
        }}

        /* Expander */
        .streamlit-expanderHeader {{
            display:none;
            background-color: rgba(0, 0, 0, 0.1) !important;
            border-radius: 0.3rem !important;
        }}

        /* Text inputs - רקע עדין בהיר */
        .stTextInput input, .stSelectbox select, .stNumberInput input {{
            border-radius: 0.5rem !important;
            border: 1px solid {secondary_color} !important;
            background-color: white !important;
        }}

        .stTextInput input:focus, .stSelectbox select:focus, .stNumberInput input:focus {{
            border-color: {accent_color} !important;
           /* box-shadow: 0 0 0 2px rgba(139, 92, 246, 0.2) !important;*/
        }}

        .stTextInput > div > div, .stSelectbox > div > div, .stNumberInput > div > div {{
         background-color: white !important;
         }}

         .stTextInput > div > div > input,
         .stSelectbox > div > div > select,
         .stNumberInput > div > div > input {{
         background-color: white !important;
         }}

        /* Navigation buttons with gradient */
        .nav-button {{
            background: linear-gradient(135deg, {primary_color} 0%, {secondary_color} 100%) !important;
            color: white !important;
            padding: 1rem 2rem;
            border-radius: 15px;
            text-align: center;
            font-weight: 700;
            font-size: 1.2rem;
            box-shadow: 0 6px 20px rgba(196, 30, 58, 0.4);
            border: none;
            width: 100%;
            margin: 0.5rem 0;
        }}

        .nav-button:hover {{
            background: linear-gradient(135deg, {secondary_color} 0%, {primary_color} 100%) !important;
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(74, 144, 226, 0.5);
        }}

        a[href^="https://streamlit.io/cloud"] {{
            display: none !important;
        }}

        /* Logo size - make it bigger */
        [data-testid="stLogo"] {{
            width: 200px !important;
            max-width: 200px !important;
        }}

        [data-testid="stLogo"] img {{
            width: 200px !important;
            max-width: 200px !important;
            max-height: 10rem !important;
        }}

        /* Logo size - make it bigger */
        [data-testid="stSidebarLogo"] {{
            width: 200px !important;
            max-width: 200px !important;
            max-height: 10rem !important;
            height: auto !important;
        }}

        [data-testid="stHeaderLogo"] {{
            width: 200px !important;
            max-width: 200px !important;
            height: auto !important;
            max-height: 10rem !important;
        }}
    </style>
    """, unsafe_allow_html=True)




def show_compact_user_info():
    """הצגת מידע משתמש קומפקטי בראש העמוד - משתמש בתוך expander"""
    role = st.session_state.get('role', st.session_state.get('access_level', 'viewer'))

    role_names = {
        'viewer': 'צופה',
        'support': 'תמיכה',
        'admin': 'מנהל',
        'superadmin': 'מנהל על'
    }
    level_text = role_names.get(role, "משתמש")

    # CSS לכפתורים וexpander זעירים
    st.markdown("""
    <style>
        /* כפתורים זעירים בהדר - עם רקע */
        div[data-testid="column"] .stButton > button {
            padding: 0.2rem 0.5rem !important;
            font-size: 0.8rem !important;
            height: 1.5rem !important;
            min-height: 1.5rem !important;
            background: #f8f9fa !important;
            color: #666 !important;
            border: 1px solid #ddd !important;
            border-radius: 0.3rem !important;
        }

        div[data-testid="column"] .stButton > button:hover {
            background: #e9ecef !important;
            color: #C41E3A !important;
        }

        /* Expander זעיר עם רקע */
        div[data-testid="column"] .streamlit-expanderHeader {
            font-size: 0.8rem !important;
            padding: 0.15rem 0.6rem !important;
            min-height: 1.5rem !important;
            background: #f8f9fa !important;
            border: 1px solid #ddd !important;
            border-radius: 0.3rem !important;
        }

        div[data-testid="column"] .streamlit-expanderHeader:hover {
            background: #e9ecef !important;
        }

        /* טקסט זעיר */
        div[data-testid="column"] p, div[data-testid="column"] small {
            font-size: 0.75rem !important;
            margin: 0 !important;
            line-height: 1.3rem !important;
        }

        /* הפרדה */
        .header-divider {
            border-left: 3px solid #ddd;
            height: 2.5rem;
            margin: 0 0.2rem;
        }
    </style>
    """, unsafe_allow_html=True)

    # שורה עם expander משתמש ליד כפתורי פעולה
    col_user_exp, col_divider1, col_refresh, col_divider2, col_logout = st.columns([1.5, 0.1, 1, 0.1, 1])

    with col_user_exp:
        # משתמש + הרשאה בתוך expander עם בתי ספר - עם חץ בטקסט
        username = st.session_state.get('username', 'N/A')
        with st.expander(f"👤 {username}-{level_text}", expanded=False):
            st.markdown("**🏫 בתי ספר זמינים:**")
            if st.session_state.get('allowed_departments'):
                if st.session_state.allowed_departments == ["ALL"]:
                    st.caption("✅ כל בתי הספר")
                else:
                    dept_count = len(st.session_state.allowed_departments)
                    st.caption(f"**{dept_count} בתי ספר זמינים**")
                    for dept in st.session_state.allowed_departments[:10]:
                        st.caption(f"• {dept}")
                    if dept_count > 10:
                        st.caption(f"+{dept_count - 10} נוספים")
            else:
                st.caption("אין בתי ספר")

    with col_divider1:
        st.markdown("<div class='header-divider'></div>", unsafe_allow_html=True)

    with col_refresh:
        if st.button("🔄 ניקוי", key="refresh_page", help="ניקוי נתונים זמניים", use_container_width=True):
            keys_to_keep = ['logged_in', 'username', 'user_email', 'user_groups', 'access_level',
                            'login_time', 'auth_method', 'session_id',
                            'entra_username', 'local_username', 'role', 'local_groups', 'allowed_departments']
            for key in list(st.session_state.keys()):
                if key not in keys_to_keep:
                    del st.session_state[key]
            st.rerun()

    with col_divider2:
        st.markdown("<div class='header-divider'></div>", unsafe_allow_html=True)

    with col_logout:
        # אייקון יציאה - דלת
        if st.button("🚪 יציאה", key="logout_btn", help="יציאה מהמערכת", use_container_width=True):
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
            'superadmin': '⭐',
            'school_manager': '🏫'
        }
        role_names = {
            'viewer': 'צופה',
            'support': 'תמיכה',
            'admin': 'מנהל',
            'superadmin': 'מנהל על',
            'school_manager': 'מנהל בית ספר'
        }
        access_icon = role_icons.get(role, '👤')
        role_name = role_names.get(role, role)

        st.info(f"{access_icon} {st.session_state.get('username', 'N/A')} ({role_name})")

        # אימייל עם expander
        with st.expander("📧 פרטים נוספים"):
            st.write(f"**אימייל:** {st.session_state.get('user_email', 'N/A')}")

            if st.session_state.get('local_username'):
                st.write(f"**משתמש לוקאלי:** {st.session_state.local_username}")

            auth_text = {
                'entra_id': 'Entra ID',
                'local': 'מקומי (Admin)',
                'local_cloud': 'מקומי (מאומת בענן)'
            }.get(st.session_state.get('auth_method'), 'לא ידוע')
            st.write(f"**אימות:** {auth_text}")

        # הרשאות - הצגה מורחבת למשתמשי school_manager
        if st.session_state.get('allowed_departments'):
            if st.session_state.allowed_departments == ["ALL"]:
                st.success("📁 גישה לכל המחלקות")
            else:
                dept_count = len(st.session_state.allowed_departments)
                # עבור school_manager - הצג בולט יותר
                if role == 'school_manager':
                    st.markdown("### 🏫 בתי הספר שלך")
                    st.info(f"גישה ל-{dept_count} בתי ספר")
                    for dept in st.session_state.allowed_departments:
                        st.write(f"✅ {dept}")
                else:
                    with st.expander(f"📁 {dept_count} מחלקות"):
                        for dept in st.session_state.allowed_departments:
                            st.write(f"• {dept}")


def main():
    st.set_page_config(
        page_title="Mafil Cloud Manager",
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

    # Header קומפקטי - עיצוב כותרת בלבד
    st.markdown("""
    <style>
        .title-text {
            font-size: 2.2rem;
            font-weight: 700;
            margin: 0;
            padding: 0;
            line-height: 2.2rem;
        }

        .title-mafil {
            color: #D71F27;
        }

        .title-services {
            color: #009BDB;
        }
    </style>
    """, unsafe_allow_html=True)

    col_user, col_title = st.columns([2, 1])

    with col_user:
        show_compact_user_info()
        
    st.markdown('<hr style="margin: 0; border: 0.5px solid #e5e7eb;">', unsafe_allow_html=True)
    
    if not check_config():
        st.stop()  
        
    with col_title:
        st.markdown('<div class="title-text"><span class="title-mafil">Mafil</span> <span class="title-services">Cloud Manager</span></div>', unsafe_allow_html=True)

    # ייבוא דפים (רק אחרי login!)
    from pages.my_activity import show as my_activity_show
    from pages.users.user_list import show as users_list_show
    from pages.users.search_edit import show as users_search_show
    from pages.users.add_user import show as users_add_show
    from pages.groups.groups import show as users_groups_show
    from pages.printers import show as printers_show
    from pages.print_queues import show as print_queues_show
    from pages.pending_prints import show as pending_prints_show
    from pages.scanning import show as scanning_show
    from pages.reports import show as reports_show

    # הגדרת דפים עם st.Page() - עם URL ייחודי לכל אחד
    # דפי משתמשים
    users_list_page = st.Page(users_list_show, title="רשימת משתמשים", icon="📋", url_path="users_list")
    users_search_page = st.Page(users_search_show, title="חיפוש ועריכה", icon="🔍", url_path="users_search")
    users_add_page = st.Page(users_add_show, title="הוספת משתמש", icon="➕", url_path="users_add")
    users_groups_page = st.Page(users_groups_show, title="קבוצות", icon="👨‍👩‍👧‍👦", url_path="users_groups")

    # דף סקירה - עם גישה לדפים אחרים
    from pages.users.overview import create_overview_page
    users_overview_page = create_overview_page(users_list_page, users_search_page, users_add_page, users_groups_page)

    # דפי מדפסות ותורי הדפסה
    printers_page = st.Page(printers_show, title="מדפסות", icon="📋", url_path="printers")
    print_queues_page = st.Page(print_queues_show, title="תורי הדפסה", icon="🗂️", url_path="print_queues")
    pending_prints_page = st.Page(pending_prints_show, title="הדפסות ממתינות", icon="⏳", url_path="pending_prints")

    # דפים עתידיים
    scanning_page = st.Page(scanning_show, title="תהליכי סריקה", icon="📄", url_path="scanning")
    reports_page = st.Page(reports_show, title="דוחות", icon="📊", url_path="reports")

    # דף הפעילות שלי
    my_activity_page = st.Page(my_activity_show, title="הפעילות שלי", icon="📋", url_path="my_activity")

    # דף הבית - עם גישה לאובייקטי Page
    from pages.home import create_home_page
    home_page = create_home_page(users_list_page, users_search_page, users_add_page, users_groups_page, my_activity_page, reports_page, printers_page)

    # לוגו בראש הסיידבר - מעל הניווט
    try:
        import sys
        import os

        def resource_path(relative_path: str) -> str:
            """מחזיר נתיב תקין לקובץ"""
            if hasattr(sys, "_MEIPASS"):
                return os.path.join(sys._MEIPASS, relative_path)
            return os.path.join(os.path.abspath("."), relative_path)

        logo_path = resource_path("assets/MafilIT_Logo.png")
        st.logo(logo_path)
    except Exception as e:
        # אם יש שגיאה בטעינת הלוגו, פשוט נמשיך בלי לוגו
        pass

    # יצירת ניווט עם קבוצות היררכיות - מותאם לפי סוג משתמש
    role = st.session_state.get('role', st.session_state.get('access_level', 'viewer'))
    local_username = st.session_state.get('local_username', None)

    # בדיקת הרשאה לגישה לרשימת משתמשים
    # רק superadmin או admin מקומי (משתמש חירום) רואים את רשימת המשתמשים
    can_view_user_list = (role == 'superadmin') or (role == 'admin' and local_username)

    if role == 'school_manager':
        # משתמשי school_manager רואים רק דוחות
        nav = st.navigation({
            "📊 דוחות היסטוריים": [reports_page]
        })
    else:
        # כל השאר רואים את התפריט (עם או בלי רשימת משתמשים)
        # בניית רשימת דפי משתמשים לפי הרשאות
        user_pages = [users_overview_page, users_search_page, users_add_page, users_groups_page]
        if can_view_user_list:
            # הוספת רשימת משתמשים למיקום השני (אחרי סקירה)
            user_pages.insert(1, users_list_page)

        nav = st.navigation({
            "ראשי": [home_page],
            "👥 משתמשים": user_pages,
            "🖨️ מדפסות ותורי הדפסה": [printers_page, print_queues_page, pending_prints_page],
            # "📄 סריקה": [scanning_page],  # מוסתר זמנית - לשימוש עתידי
            "📊 דוחות היסטוריים": [reports_page],
            "📋פעילות": [my_activity_page]
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
