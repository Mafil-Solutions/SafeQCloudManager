#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SafeQ Cloud Manager - My Activity Page
דף הפעילות שלי
"""

import streamlit as st
import sys
import os

# הוספת תיקיית app ל-path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared import get_api_instance, get_logger_instance, check_authentication

def show():
    """הצגת דף הפעילות שלי"""
    check_authentication()

    logger = get_logger_instance()

    st.header("📋 הפעילות שלי")

    # הצגת לוג פעולות מה-session state
    if 'audit_log' in st.session_state and st.session_state.audit_log:
        st.subheader("פעולות אחרונות")

        for log_entry in reversed(st.session_state.audit_log):
            status_icon = "✅" if log_entry.get('success', True) else "❌"
            timestamp = log_entry.get('timestamp', 'N/A')
            action = log_entry.get('action', 'N/A')
            details = log_entry.get('details', '')

            with st.expander(f"{status_icon} {action} - {timestamp}"):
                st.write(f"**פעולה:** {action}")
                st.write(f"**זמן:** {timestamp}")
                if details:
                    st.write(f"**פרטים:** {details}")
                st.write(f"**סטטוס:** {'הצלחה' if log_entry.get('success', True) else 'כישלון'}")
    else:
        st.info("אין פעולות אחרונות להצגה")

    # TODO: הוסף אפשרות לצפות בלוג המלא מה-DB

if __name__ == "__main__":
    show()
