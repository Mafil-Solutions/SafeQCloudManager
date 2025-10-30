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
    st.header("🏠 ברוכים הבאים למנהל SafeQ Cloud")

    # מידע על המשתמש
    if 'username' in st.session_state:
        role = st.session_state.get('role', st.session_state.get('access_level', 'user'))
        role_icons = {
            'viewer': '👁️ צופה',
            'support': '🛠️ תמיכה',
            'admin': '👑 מנהל',
            'superadmin': '⭐ מנהל על'
        }
        role_text = role_icons.get(role, '👤 משתמש')

        st.success(f"שלום, {st.session_state.username}! ({role_text})")

        # סטטיסטיקות בסיסיות
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                label="🌐 שרת",
                value="מחובר",
                delta=CONFIG.get('SERVER_URL', 'N/A')
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
                label="📁 מחלקות מורשות",
                value=dept_text
            )

        st.markdown("---")

        # מדריך מהיר
        st.subheader("📚 מדריך מהיר")

        st.markdown("""
        ### 👥 משתמשים
        - **רשימת משתמשים** - צפייה בכל המשתמשים במערכת
        - **חיפוש ועריכה** - חיפוש מתקדם ועריכת פרטי משתמשים
        - **הוספת משתמש** - יצירת משתמש חדש
        - **קבוצות** - ניהול קבוצות משתמשים

        ### 📋 הפעילות שלי
        צפייה בפעולות האחרונות שביצעת במערכת

        ### 🔮 בקרוב
        - 🖨️ **מדפסות** - ניהול מדפסות
        - 📄 **תהליכי סריקה** - ניהול תהליכי סריקה
        - 📊 **דוחות** - דוחות וסטטיסטיקות
        """)
    else:
        st.warning("⚠️ לא מזוהה משתמש במערכת")

if __name__ == "__main__":
    show()
