#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SafeQ Cloud Manager - Scanning Module
מודול תהליכי סריקה - בפיתוח
"""

import streamlit as st

def show():
    """הצגת דף תהליכי סריקה (placeholder)"""
    st.header("📄 תהליכי סריקה")

    st.info("📌 מודול זה נמצא בפיתוח")

    st.markdown("""
    ### פיצ'רים מתוכננים:
    - 📋 רשימת תהליכי סריקה
    - ➕ יצירת תהליך סריקה חדש
    - ✏️ עריכת תהליך קיים
    - 📊 סטטיסטיקות סריקה
    - 📁 ניהול יעדי סריקה
    """)

    st.warning("⏳ תכונה זו תהיה זמינה בגרסה הבאה")

if __name__ == "__main__":
    show()
