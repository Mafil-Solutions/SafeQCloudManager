#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SafeQ Cloud Manager - Users Overview Page
דף סקירה - ניהול משתמשים
"""

import streamlit as st

def create_overview_page(users_list_page, users_search_page, users_add_page, users_groups_page):
    """יוצר את דף הסקירה עם גישה לאובייקטי Page"""

    def show():
        """הצגת דף סקירה לניהול משתמשים"""

        # CSS לכפתורים - page_link מעוצב כמו button
        st.markdown("""
        <style>
            /* כפתורי סקירה */
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
                padding: 0.5rem 1rem !important;
                border-radius: 0.5rem !important;
                font-weight: 600 !important;
                border: none !important;
                text-decoration: none !important;
                display: inline-block !important;
                width: 100% !important;
                box-sizing: border-box !important;
                text-align: center !important;
                line-height: 1.6 !important;
            }

            a[data-testid="stPageLink-NavLink"]:hover {
                opacity: 0.9 !important;
            }

            /* הסתרת האייקון של page_link */
            a[data-testid="stPageLink-NavLink"] svg {
                display: none !important;
            }

            /* וידוא שהטקסט בתוך page_link לבן */
            a[data-testid="stPageLink-NavLink"] span,
            a[data-testid="stPageLink-NavLink"] p {
                color: white !important;
            }
        </style>
        """, unsafe_allow_html=True)

        st.header("👥 ניהול משתמשים")
        st.caption("בחר פעולה מהאפשרויות למטה")

        st.markdown("---")

        # כרטיסים לניווט
        col1, col2 = st.columns(2)

        with col1:
            # כרטיס 1: רשימת משתמשים
            with st.container():
                st.subheader("📋 רשימת משתמשים")
                st.markdown("""
                צפייה בכל המשתמשים במערכת, סינון לפי מקור (מקומי/Entra),
                וייצוא לקובץ CSV.

                **תכונות:**
                - צפייה במשתמשים מקומיים
                - צפייה במשתמשי Entra (superadmin)
                - סינון לפי מחלקות
                - ייצוא CSV
                """)
                st.page_link(users_list_page, label="➡️ עבור לרשימת משתמשים", use_container_width=True)

            st.markdown("---")

            # כרטיס 2: הוספת משתמש
            with st.container():
                st.subheader("➕ הוספת משתמש")
                st.markdown("""
                יצירת משתמש חדש במערכת SafeQ Cloud.

                **תכונות:**
                - טופס יצירת משתמש
                - הגדרת פרטים אישיים
                - קוד PIN
                - הרשאות ומחלקות
                """)
                st.page_link(users_add_page, label="➡️ עבור להוספת משתמש", use_container_width=True)

        with col2:
            # כרטיס 3: חיפוש ועריכה
            with st.container():
                st.subheader("🔍 חיפוש ועריכה")
                st.markdown("""
                חיפוש מתקדם ועריכת פרטי משתמשים קיימים.

                **תכונות:**
                - חיפוש לפי שם, אימייל, מחלקה
                - התאמה חלקית או מדויקת
                - עריכת פרטי משתמש
                - מחיקת משתמש (admin)
                """)
                st.page_link(users_search_page, label="➡️ עבור לחיפוש ועריכה", use_container_width=True)

            st.markdown("---")

            # כרטיס 4: קבוצות
            with st.container():
                st.subheader("👨‍👩‍👧‍👦 קבוצות")
                st.markdown("""
                ניהול קבוצות משתמשים במערכת.

                **תכונות:**
                - רשימת קבוצות
                - יצירת קבוצה חדשה
                - הוספת/הסרת משתמשים
                - הגדרות הרשאות
                """)
                st.page_link(users_groups_page, label="➡️ עבור לניהול קבוצות", use_container_width=True)

        st.markdown("---")

        # טיפים
        st.info("""
        💡 **טיפ:** לחץ על אחד מהכפתורים למעלה, או השתמש בתפריט הימני (צד ימין) כדי לנווט בין המודולים השונים.
        """)

    return st.Page(show, title="סקירה", icon="👥", url_path="users_overview")

if __name__ == "__main__":
    show()
