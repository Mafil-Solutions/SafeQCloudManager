#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SafeQ Cloud Manager - Users Overview Page
דף סקירה - ניהול משתמשים
"""

import streamlit as st

def show():
    """הצגת דף סקירה לניהול משתמשים"""

    st.header("👥 ניהול משתמשים")
    st.caption("בחר פעולה מהאפשרויות למטה")

    st.markdown("---")

    # כרטיסים לניווט
    col1, col2 = st.columns(2)

    with col1:
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
            st.info("📌 השתמש בתפריט הימני: **משתמשים** → **רשימת משתמשים**")

        st.markdown("---")

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
            st.info("📌 השתמש בתפריט הימני: **משתמשים** → **הוספת משתמש**")

    with col2:
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
            st.info("📌 השתמש בתפריט הימני: **משתמשים** → **חיפוש ועריכה**")

        st.markdown("---")

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
            st.info("📌 השתמש בתפריט הימני: **משתמשים** → **קבוצות**")

    st.markdown("---")

    # טיפים
    st.info("""
    💡 **טיפ:** השתמש בתפריט הימני (צד ימין) כדי לנווט במהירות בין המודולים השונים.
    כל הפעולות זמינות ישירות מהתפריט!
    """)

if __name__ == "__main__":
    show()
