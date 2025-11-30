#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SafeQ Cloud Manager - Printers Module
מודול ניהול מדפסות
"""

import streamlit as st
import pandas as pd
import sys
import os

# הוספת תיקיית app ל-path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import get_api_instance, check_authentication

def filter_printers_by_departments(printers, allowed_departments):
    """
    סינון מדפסות לפי מחלקות מורשות (דרך containerName)

    Args:
        printers: רשימת מדפסות
        allowed_departments: מחלקות מורשות (["ALL"] עבור superadmin)

    Returns:
        list: רשימת מדפסות מסוננות
    """
    if not printers:
        return []

    # Superadmin רואה הכל
    if allowed_departments == ["ALL"]:
        return printers

    filtered_printers = []

    for printer in printers:
        container_name = printer.get('containerName', '')

        # אם containerName ריק (תקלה ב-API) - הצג את המדפסת
        # (ברגע שיתקנו את התקלה, הסינון יעבוד אוטומטית)
        if not container_name:
            filtered_printers.append(printer)
            continue

        # containerName זהה לשם קבוצה - נשווה ל-allowed_departments
        if container_name in allowed_departments:
            filtered_printers.append(printer)

    return filtered_printers

def analyze_printer_structure(printers):
    """
    מנתח את מבנה המדפסות כדי להבין איך הן מאורגנות
    """
    if not printers:
        return None

    # קח דוגמה של מדפסת אחת ונתח אותה
    sample = printers[0] if isinstance(printers, list) and len(printers) > 0 else printers

    return {
        'total_printers': len(printers) if isinstance(printers, list) else 1,
        'sample_keys': list(sample.keys()) if isinstance(sample, dict) else 'Not a dict',
        'sample_data': sample
    }

def show():
    """הצגת דף מדפסות"""
    check_authentication()

    # RTL styling
    st.markdown("""
    <style>
        .stApp {
            direction: rtl !important;
        }

        .block-container {
            text-align: right !important;
            direction: rtl !important;
        }
    </style>
    """, unsafe_allow_html=True)

    st.header("🖨️ ניהול מדפסות")

    # קבלת מידע על המשתמש
    api = get_api_instance()
    username = st.session_state.get('username', '')
    provider_id = st.session_state.get('provider_id', None)
    user_groups = st.session_state.get('user_groups', [])
    allowed_departments = st.session_state.get('allowed_departments', [])
    role = st.session_state.get('role', 'viewer')

    # בדיקת הרשאות
    if role not in ['admin', 'superadmin', 'support', 'viewer']:
        st.warning("👁️ אין לך הרשאה לצפות במדפסות")
        return

    st.markdown("---")

    # כפתורי ניהול
    col1, col2 = st.columns([1, 9])
    with col1:
        if st.button("🔄 רענן", use_container_width=True):
            if 'printers_cache' in st.session_state:
                del st.session_state.printers_cache
            st.rerun()

    # טעינת מדפסות
    with st.spinner("טוען רשימת מדפסות..."):
        # שימוש ב-cache כדי לא לטעון כל פעם מחדש
        if 'printers_cache' not in st.session_state:
            # קורא ללא username וללא enrichPorts (כמו ב-Postman)
            printers = api.get_output_ports_for_user(username=None, provider_id=None, enrich_ports=False)
            st.session_state.printers_cache = printers
        else:
            printers = st.session_state.printers_cache

    if not printers:
        st.info("📭 לא נמצאו מדפסות זמינות")
        st.markdown("""
        ### מדוע אני לא רואה מדפסות?
        - ייתכן שאין מדפסות מוגדרות במערכת
        - ייתכן שאין לך הרשאה לראות מדפסות
        - ה-API endpoint כבר מסנן לפי המשתמש
        """)
        return

    # סינון לפי מחלקות מורשות (דרך containerName)
    # containerName שווה לשם קבוצות - מסננים לפי allowed_departments
    original_count_before_dept = len(printers)
    filtered_printers = filter_printers_by_departments(printers, allowed_departments)

    # הצגת סטטיסטיקה
    col1, col2 = st.columns(2)
    with col1:
        st.metric("כמות מדפסות", len(filtered_printers))
    with col2:
        # ספירת בתי ספר ייחודיים
        unique_schools = set()
        for printer in filtered_printers:
            school = printer.get('containerName', '')
            if school:
                unique_schools.add(school)
        st.metric("בתי ספר", len(unique_schools))

    # הודעת סינון לפי הרשאות
    if allowed_departments != ["ALL"] and len(filtered_printers) < original_count_before_dept:
        st.info(f"ℹ️ מציג מדפסות עבור בתי הספר שלך בלבד ({len(filtered_printers)} מתוך {original_count_before_dept})")

    st.markdown("---")

    # חיפוש ופילטור
    st.markdown("### 🔍 חיפוש")
    search_query = st.text_input("חפש מדפסת", placeholder="שם, כתובת IP, מספר סידורי, יצרן...")

    # סינון לפי חיפוש
    if search_query:
        search_lower = search_query.lower()
        filtered_printers = [
            p for p in filtered_printers
            if search_lower in p.get('name', '').lower() or
               search_lower in p.get('address', '').lower() or
               search_lower in str(p.get('deviceSerial', '')).lower() or
               search_lower in p.get('vendor', '').lower() or
               search_lower in p.get('description', '').lower()
        ]

    # הצגת רשימת מדפסות
    if not filtered_printers:
        st.warning("🔍 לא נמצאו מדפסות התואמות לחיפוש")
        return

    st.subheader(f"📋 רשימת מדפסות ({len(filtered_printers)})")

    # יצירת טבלה עם השדות הנכונים מה-API
    printers_data = []
    for printer in filtered_printers:
        row = {
            'שם': printer.get('name', 'לא ידוע'),
            'מיקום': printer.get('description', '-'),
            'כתובת IP': printer.get('address', '-'),
            'מספר סידורי': printer.get('deviceSerial', '-'),
            'יצרן': printer.get('vendor', '-'),
            'מדפסת צבע?': 'לא' if printer.get('monochrome') else 'כן',
            'בית ספר': printer.get('containerName') or '-',
            'בקר פנימי?': 'כן' if printer.get('embedded') else 'לא',
        }
        printers_data.append(row)

    # הצגת טבלה
    df = pd.DataFrame(printers_data)

    # הצגה עם גלילה
    st.dataframe(
        df,
        use_container_width=True,
        height=400,
        hide_index=True
    )

    # אפשרות להורדת רשימה
    st.markdown("---")
    col1, col2 = st.columns([1, 9])
    with col1:
        # Create Excel file in memory
        from io import BytesIO
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Printers', index=False)
        excel_bytes = output.getvalue()

        st.download_button(
            label="📊 הורד Excel",
            data=excel_bytes,
            file_name=f"printers_list_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

if __name__ == "__main__":
    show()
