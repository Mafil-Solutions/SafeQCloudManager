#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SafeQ Cloud Manager - Home Page
דף הבית של מנהל SafeQ Cloud
"""

import streamlit as st
from config import config

CONFIG = config.get()

def show():
    """הצגת דף הבית"""

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
        st.subheader("⚡ גישה מהירה")

        # קטגוריה: ניהול משתמשים
        st.markdown("### 👥 ניהול משתמשים")
        col1, col2 = st.columns(2)

        with col1:
            with st.container():
                st.markdown("**📋 רשימת משתמשים**")
                st.caption("צפייה בכל המשתמשים, סינון וייצוא CSV")
                if st.button("➡️ עבור לרשימת משתמשים", key="home_goto_users_list", use_container_width=True):
                    st.switch_page("pages/users/user_list.py")

            st.markdown("")

            with st.container():
                st.markdown("**➕ הוספת משתמש**")
                st.caption("יצירת משתמש חדש במערכת")
                if st.button("➡️ עבור להוספת משתמש", key="home_goto_add_user", use_container_width=True):
                    st.switch_page("pages/users/add_user.py")

        with col2:
            with st.container():
                st.markdown("**🔍 חיפוש ועריכה**")
                st.caption("חיפוש מתקדם ועריכת משתמשים")
                if st.button("➡️ עבור לחיפוש ועריכה", key="home_goto_search_edit", use_container_width=True):
                    st.switch_page("pages/users/search_edit.py")

            st.markdown("")

            with st.container():
                st.markdown("**👨‍👩‍👧‍👦 קבוצות**")
                st.caption("ניהול קבוצות משתמשים")
                if st.button("➡️ עבור לניהול קבוצות", key="home_goto_groups", use_container_width=True):
                    st.switch_page("pages/users/groups.py")

        st.markdown("---")

        # קטגוריות אחרות
        st.markdown("### 📊 מודולים נוספים")
        col_act, col_print, col_scan = st.columns(3)

        with col_act:
            st.markdown("**📋 הפעילות שלי**")
            st.caption("צפייה בפעולות שביצעת")
            if st.button("➡️ עבור לפעילות", key="home_goto_activity", use_container_width=True):
                st.switch_page("pages/my_activity.py")

        with col_print:
            st.markdown("**🖨️ מדפסות**")
            st.caption("ניהול מדפסות (בקרוב)")
            if st.button("➡️ עבור למדפסות", key="home_goto_printers", use_container_width=True):
                st.switch_page("pages/printers/__init__.py")

        with col_scan:
            st.markdown("**📄 סריקה**")
            st.caption("תהליכי סריקה (בקרוב)")
            if st.button("➡️ עבור לסריקה", key="home_goto_scanning", use_container_width=True):
                st.switch_page("pages/scanning/__init__.py")

        st.markdown("---")

        # טיפ
        st.info("💡 **טיפ:** לחץ על אחד מהכפתורים למעלה לגישה מהירה, או השתמש בתפריט הימני לניווט מלא")

    else:
        st.warning("⚠️ לא מזוהה משתמש במערכת")

if __name__ == "__main__":
    show()
