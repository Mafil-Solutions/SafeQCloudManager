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

        # הדרכה מהירה
        st.info("💡 **טיפ:** השתמש בתפריט הימני כדי לנווט בין המודולים השונים")

        # קישורים מהירים
        st.subheader("⚡ גישה מהירה")

        col_users, col_activity = st.columns(2)

        with col_users:
            st.markdown("""
            **👥 ניהול משתמשים**
            - רשימת משתמשים
            - חיפוש ועריכה
            - הוספת משתמש חדש
            - ניהול קבוצות
            """)

        with col_activity:
            st.markdown("""
            **📊 מידע ופעילות**
            - הפעילות שלי
            - דוחות (בקרוב)
            - ניהול מדפסות (בקרוב)
            - תהליכי סריקה (בקרוב)
            """)

    else:
        st.warning("⚠️ לא מזוהה משתמש במערכת")

if __name__ == "__main__":
    show()
