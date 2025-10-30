#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SafeQ Cloud Manager - Reports Module
מודול דוחות - בפיתוח
"""

import streamlit as st

def show():
    """הצגת דף דוחות (placeholder)"""
    st.header("📊 דוחות וסטטיסטיקות")

    st.info("📌 מודול זה נמצא בפיתוח")

    st.markdown("""
    ### פיצ'רים מתוכננים:
    - 📈 דוחות שימוש
    - 💰 דוחות עלויות
    - 👥 דוחות משתמשים
    - 🖨️ דוחות מדפסות
    - 📅 דוחות לפי תקופה
    - 📥 ייצוא דוחות (PDF, Excel)
    """)

    st.warning("⏳ תכונה זו תהיה זמינה בגרסה הבאה")

if __name__ == "__main__":
    show()
