#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SafeQ Cloud Manager - Home Page
דף הבית של מנהל SafeQ Cloud - מרכז הבקרה
"""

import streamlit as st
from config import config

CONFIG = config.get()

def show():
    """הצגת דף הבית - מרכז בקרה עם קיצורי דרך"""

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

        # כרטיסי מידע
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                label="🌐 סטטוס שרת",
                value="מחובר ✅"
            )

        with col2:
            auth_method = st.session_state.get('auth_method', 'unknown')
            auth_text = "Entra ID" if auth_method == 'entra_id' else "מקומי"
            st.metric(
                label="🔐 אימות",
                value=auth_text
            )

        with col3:
            dept_count = len(st.session_state.get('allowed_departments', []))
            if st.session_state.get('allowed_departments') == ["ALL"]:
                dept_text = "הכל"
            else:
                dept_text = str(dept_count)
            st.metric(
                label="📁 מחלקות",
                value=dept_text
            )

        st.markdown("---")

        # גישה מהירה לתפקודים עיקריים
        st.subheader("⚡ גישה מהירה למודולים")

        # קטגוריה: ניהול משתמשים
        st.markdown("### 👥 ניהול משתמשים")
        col1, col2 = st.columns(2)

        with col1:
            with st.container():
                st.markdown("**📋 רשימת משתמשים**")
                st.caption("צפייה בכל המשתמשים במערכת, סינון לפי מקור (מקומי/Entra), וייצוא לקובץ CSV")
                st.page_link("pages/users/user_list.py", label="➡️ עבור לרשימת משתמשים", icon="📋", use_container_width=True)

            st.markdown("")

            with st.container():
                st.markdown("**🔍 חיפוש ועריכה**")
                st.caption("חיפוש מתקדם ועריכת פרטי משתמשים קיימים")
                st.page_link("pages/users/search_edit.py", label="➡️ עבור לחיפוש ועריכה", icon="🔍", use_container_width=True)

        with col2:
            with st.container():
                st.markdown("**➕ הוספת משתמש**")
                st.caption("יצירת משתמש חדש במערכת SafeQ Cloud")
                st.page_link("pages/users/add_user.py", label="➡️ עבור להוספת משתמש", icon="➕", use_container_width=True)

            st.markdown("")

            with st.container():
                st.markdown("**👨‍👩‍👧‍👦 קבוצות**")
                st.caption("ניהול קבוצות משתמשים - יצירה, עריכה, הוספה והסרה")
                st.page_link("pages/users/groups.py", label="➡️ עבור לניהול קבוצות", icon="👨‍👩‍👧‍👦", use_container_width=True)

        st.markdown("---")

        # קטגוריות אחרות
        st.markdown("### 📊 מודולים נוספים")
        col_act, col_print, col_scan = st.columns(3)

        with col_act:
            st.markdown("**📋 הפעילות שלי**")
            st.caption("צפייה בפעולות שביצעת במערכת")
            st.page_link("pages/my_activity.py", label="➡️ עבור לפעילות", icon="📋", use_container_width=True)

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

if __name__ == "__main__":
    show()
