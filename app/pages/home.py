#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SafeQ Cloud Manager - Home Page
דף הבית של מנהל SafeQ Cloud - מרכז הבקרה
"""

import streamlit as st
from config import config

CONFIG = config.get()

def create_home_page(users_list_page, users_search_page, users_add_page, users_groups_page, my_activity_page):
    """יוצר את דף הבית עם גישה לאובייקטי Page"""

    def show():
        """הצגת דף הבית - מרכז בקרה עם קיצורי דרך"""

        # CSS לכפתורים - page_link מעוצב בדיוק כמו button
        st.markdown("""
        <style>
            /* כפתורי st.button - זהה לעמוד overview */
            .stButton > button {
                background: linear-gradient(45deg, #C41E3A, #FF6B6B) !important;
                color: white !important;
                padding: 0.5rem 1rem !important;
                border-radius: 0.5rem !important;
                font-weight: 600 !important;
                border: none !important;
            }

            .stButton > button:hover {
                opacity: 0.9 !important;
            }

            /* כפתורי st.page_link - מעוצבים בדיוק כמו st.button */
            a[data-testid="stPageLink-NavLink"] {
                background: linear-gradient(45deg, #C41E3A, #FF6B6B) !important;
                color: white !important;
                padding: 0.0rem 0.0rem !important;
                border-radius: 0.9rem !important;
                font-weight: 600 !important;
                border: none !important;
                text-decoration: none !important;
                display: inline-block !important;
                width: 100% !important;
                box-sizing: border-box !important;
                text-align: center !important;
                line-height: 1.5 !important;
            }
            a[data-testid="stPageLink-NavLink"]:hover {
                opacity: 0.9 !important;
                color: white;
            }

           div[data-testid="stPageLink"] {
               padding: 0.0rem 0.0rem !important;
               margin: 0 !important;
               border-radius:0.5rem ;
               transition: 0!important;
               background: none;
            }

            div[data-testid="stPageLink"]:hover {
               padding: 0.0rem 0.0rem !important;
               margin: 0 !important;
               border: none ;
               transition: none !important;
               background-color: none;
               }
             /* הסתרת כל ה-span container שמכיל את האימוג'י - כך המקום ממש משתחרר */
            a[data-testid="stPageLink-NavLink"] > span:first-child {
                display: none !important;
            }

            /* וידוא שהטקסט בתוך page_link לבן */
            a[data-testid="stPageLink-NavLink"] span,
            a[data-testid="stPageLink-NavLink"] p {
                color: white !important;
            }
        </style>
        """, unsafe_allow_html=True)

        st.info("💡 **טיפ:** השתמש בכפתורים למטה או בתפריט הימני (סיידבר) לניווט מהיר")

        # ברוכים הבאים
        if 'username' in st.session_state:
            role = st.session_state.get('role', st.session_state.get('access_level', 'user'))
            role_icons = {
                'viewer': '👁️ צופה',
                'support': '🛠️ תמיכה',
                'admin': '👑 מנהל',
                'superadmin': '⭐ מנהל על'
            }
            role_text = role_icons.get(role, '👤 משתמש')

            st.success(f"👋 שלום, **{st.session_state.username}**! ({role_text})")

            st.markdown("---")

            # גישה מהירה לתפקודים עיקריים - ישר לעניין
            st.subheader("⚡ גישה מהירה למודולים")

            # קטגוריה: ניהול משתמשים
            st.markdown("### 👥 ניהול משתמשים")
            col1, col2 = st.columns(2)

            with col1:
                with st.container():
                    st.markdown("**📋 רשימת משתמשים**")
                    st.caption("צפייה בכל המשתמשים במערכת, סינון לפי מקור (מקומי/Entra), וייצוא לקובץ CSV")
                    st.page_link(users_list_page, label="📋➡️ עבור לרשימת משתמשים", use_container_width=True)
                st.markdown("")

                with st.container():
                    st.markdown("**🔍 חיפוש ועריכה**")
                    st.caption("חיפוש מתקדם ועריכת פרטי משתמשים קיימים")
                    st.page_link(users_search_page, label="🔍➡️ עבור לחיפוש ועריכה", use_container_width=True)

            with col2:
                with st.container():
                    st.markdown("**➕ הוספת משתמש**")
                    st.caption("יצירת משתמש חדש במערכת SafeQ Cloud")
                    st.page_link(users_add_page, label="➕➡️ עבור להוספת משתמש", use_container_width=True)

                st.markdown("")

                with st.container():
                    st.markdown("**👨‍👩‍👧‍👦 קבוצות**")
                    st.caption("ניהול קבוצות משתמשים - יצירה, עריכה, הוספה והסרה")
                    st.page_link(users_groups_page, label=" 👨‍👩‍👧‍👦➡️ עבור לניהול קבוצות", use_container_width=True)

            st.markdown("---")

            # קטגוריות אחרות
            st.markdown("### 📊 מודולים נוספים")
            col_act, col_print, col_scan = st.columns(3)

            with col_act:
                st.markdown("**📋 הפעילות שלי**")
                st.caption("צפייה בפעולות שביצעת במערכת")
                st.page_link(my_activity_page, label="📋➡️ עבור לפעילות", use_container_width=True)

            with col_print:
                st.markdown("**🖨️ מדפסות**")
                st.caption("ניהול מדפסות (בפיתוח)")
                st.info("💡 תכונה זו בפיתוח")

            with col_scan:
                st.markdown("**📄 סריקה**")
                st.caption("תהליכי סריקה (בפיתוח)")
                st.info("💡 תכונה זו בפיתוח")

        else:
            st.warning("⚠️ לא מזוהה משתמש במערכת")

    return st.Page(show, title="בית", icon="🏠", url_path="home", default=True)

if __name__ == "__main__":
    # For standalone testing
    st.info("This page requires Page objects from main.py")
