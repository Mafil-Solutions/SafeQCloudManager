#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SafeQ Cloud Manager - Add User Page
דף הוספת משתמש
"""

import streamlit as st
import sys
import os

# הוספת תיקיית app ל-path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import get_api_instance, get_logger_instance, check_authentication, CONFIG

def show():
    """הצגת דף הוספת משתמש"""
    check_authentication()

    api = get_api_instance()
    logger = get_logger_instance()

    st.header("הוספת משתמש חדש")

    # פלייסהולדר - נעתיק את הלוגיקה המלאה אחר כך
    st.info("📌 דף זה יכיל טופס להוספת משתמש חדש")
    st.warning("🔨 בפיתוח - הלוגיקה המלאה תועבר מהגרסה הישנה")

    # TODO: העתקת לוגיקה מלאה מ-main_utils.py (Tab 3)

if __name__ == "__main__":
    show()
