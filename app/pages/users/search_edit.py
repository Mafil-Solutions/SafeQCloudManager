#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SafeQ Cloud Manager - Search and Edit Users Page
דף חיפוש ועריכת משתמשים
"""

import streamlit as st
import pandas as pd
import sys
import os

# הוספת תיקיית app ל-path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import get_api_instance, get_logger_instance, check_authentication, CONFIG
from permissions import filter_users_by_departments

def show():
    """הצגת דף חיפוש ועריכת משתמשים"""
    check_authentication()

    api = get_api_instance()
    logger = get_logger_instance()

    st.header("חיפוש ועריכת משתמשים")

    # פלייסהולדר - נעתיק את הלוגיקה המלאה אחר כך
    st.info("📌 דף זה יכיל חיפוש מתקדם ועריכת משתמשים")
    st.warning("🔨 בפיתוח - הלוגיקה המלאה תועבר מהגרסה הישנה")

    # TODO: העתקת לוגיקה מלאה מ-main_utils.py (Tab 2)

if __name__ == "__main__":
    show()
