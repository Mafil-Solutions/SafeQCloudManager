#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SafeQ Cloud Manager - Users Overview Page
דף סקירה - ניהול משתמשים
"""

import streamlit as st

def show():
    """הצגת דף סקירה לניהול משתמשים"""

    # CSS לכפתורים מעוצבים
    st.markdown("""
    <style>
        /* כפתורי סקירה מעוצבים */
        div[data-testid="column"] .stButton > button {
            background: linear-gradient(135deg, #C41E3A 0%, #4A90E2 100%) !important;
            color: white !important;
            padding: 0.8rem 1.2rem !important;
            border-radius: 0.7rem !important;
            font-weight: 600 !important;
            text-align: center !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 4px 15px rgba(196, 30, 58, 0.3) !important;
            border: none !important;
            height: auto !important;
            min-height: 2.5rem !important;
        }

        div[data-testid="column"] .stButton > button:hover {
            transform: translateY(-3px) !important;
            box-shadow: 0 6px 25px rgba(196, 30, 58, 0.5) !important;
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
            if st.button("➡️ עבור לרשימת משתמשים", key="goto_users_list", use_container_width=True):
                st.switch_page("pages/users/user_list.py")

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
            if st.button("➡️ עבור להוספת משתמש", key="goto_add_user", use_container_width=True):
                st.switch_page("pages/users/add_user.py")

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
            if st.button("➡️ עבור לחיפוש ועריכה", key="goto_search_edit", use_container_width=True):
                st.switch_page("pages/users/search_edit.py")

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
            if st.button("➡️ עבור לניהול קבוצות", key="goto_groups", use_container_width=True):
                st.switch_page("pages/users/groups.py")

    st.markdown("---")

    # טיפים
    st.info("""
    💡 **טיפ:** לחץ על אחד מהכפתורים למעלה, או השתמש בתפריט הימני (צד ימין) כדי לנווט בין המודולים השונים.
    """)

if __name__ == "__main__":
    show()
