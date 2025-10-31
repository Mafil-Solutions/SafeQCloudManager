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
                # Use navigation instead of switch_page - it's more reliable
                st.info("💡 השתמש בתפריט הימני: **משתמשים** → **רשימת משתמשים**")

            st.markdown("")

            with st.container():
                st.markdown("**➕ הוספת משתמש**")
                st.caption("יצירת משתמש חדש במערכת")
                st.info("💡 השתמש בתפריט הימני: **משתמשים** → **הוספת משתמש**")

        with col2:
            with st.container():
                st.markdown("**🔍 חיפוש ועריכה**")
                st.caption("חיפוש מתקדם ועריכת משתמשים")
                st.info("💡 השתמש בתפריט הימני: **משתמשים** → **חיפוש ועריכה**")

            st.markdown("")

            with st.container():
                st.markdown("**👨‍👩‍👧‍👦 קבוצות**")
                st.caption("ניהול קבוצות משתמשים")
                st.info("💡 השתמש בתפריט הימני: **משתמשים** → **קבוצות**")

        st.markdown("---")

        # קטגוריות אחרות
        st.markdown("### 📊 מודולים נוספים")
        col_act, col_print, col_scan = st.columns(3)

        with col_act:
            st.markdown("**📋 הפעילות שלי**")
            st.caption("צפייה בפעולות שביצעת")
            st.info("💡 השתמש בתפריט הימני: **פעילות** → **הפעילות שלי**")

        with col_print:
            st.markdown("**🖨️ מדפסות**")
            st.caption("ניהול מדפסות (בקרוב)")
            st.info("💡 תכונה זו בפיתוח")

        with col_scan:
            st.markdown("**📄 סריקה**")
            st.caption("תהליכי סריקה (בקרוב)")
            st.info("💡 תכונה זו בפיתוח")

        st.markdown("---")

        # טיפ
        st.info("💡 **טיפ:** השתמש בתפריט הימני לניווט מהיר בין המודולים השונים")

    else:
        st.warning("⚠️ לא מזוהה משתמש במערכת")

if __name__ == "__main__":
    show()
