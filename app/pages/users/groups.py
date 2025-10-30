#!/usr:bin/env python3
# -*- coding: utf-8 -*-
"""
SafeQ Cloud Manager - Groups Management Page
דף ניהול קבוצות
"""

import streamlit as st
import sys
import os

# הוספת תיקיית app ל-path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import get_api_instance, get_logger_instance, check_authentication, CONFIG

def show():
    """הצגת דף ניהול קבוצות"""
    check_authentication()

    api = get_api_instance()
    logger = get_logger_instance()

    st.header("ניהול קבוצות")

    # פלייסהולדר - נעתיק את הלוגיקה המלאה אחר כך
    st.info("📌 דף זה יכיל ניהול קבוצות משתמשים")
    st.warning("🔨 בפיתוח - הלוגיקה המלאה תועבר מהגרסה הישנה")

    # TODO: העתקת לוגיקה מלאה מ-main_utils.py (Tab 4)

if __name__ == "__main__":
    show()
