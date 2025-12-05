#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SafeQ Cloud Manager - Print Queues Module
מודול ניהול תורי הדפסה
"""

import streamlit as st
import pandas as pd
import sys
import os
import io

# הוספת תיקיית app ל-path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import get_api_instance, check_authentication

def export_to_excel(df: pd.DataFrame, sheet_name: str) -> bytes:
    """ייצוא DataFrame ל-Excel עם עיצוב"""
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False, engine='openpyxl')

        # עיצוב הגליון
        workbook = writer.book
        worksheet = writer.sheets[sheet_name]

        # רוחב עמודות אוטומטי
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter

            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass

            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width

    output.seek(0)
    return output.getvalue()

def filter_input_ports_by_departments(input_ports, allowed_departments):
    """
    סינון תורי הדפסה לפי מחלקות מורשות (דרך containerName)

    Args:
        input_ports: רשימת תורי הדפסה
        allowed_departments: מחלקות מורשות (["ALL"] עבור superadmin)

    Returns:
        list: רשימת תורי הדפסה מסוננות
    """
    if not input_ports:
        return []

    # Superadmin רואה הכל
    if allowed_departments == ["ALL"]:
        return input_ports

    filtered_ports = []

    for port in input_ports:
        container_name = port.get('containerName', '')

        # אם containerName ריק - הצג את התור
        if not container_name:
            filtered_ports.append(port)
            continue

        # containerName זהה לשם קבוצה - נשווה ל-allowed_departments
        if container_name in allowed_departments:
            filtered_ports.append(port)

    return filtered_ports

def show():
    """הצגת דף תורי הדפסה"""
    check_authentication()

    st.title("🗂️ תורי הדפסה (Input Ports)")

    # קבלת API instance
    api = get_api_instance()

    # טעינת תורי הדפסה
    with st.spinner("טוען תורי הדפסה..."):
        try:
            # קריאה ל-API לקבלת InputPorts עם enrichPorts=true כדי לקבל containerName
            import requests
            url = f"{api.server_url}/api/v1/inputports?enrichPorts=true"
            response = requests.get(url, headers=api.headers, verify=False, timeout=30)

            if response.status_code == 200:
                input_ports = response.json()

                # טעינת מדפסות לצורך קבלת מספרים סידוריים
                printers = api.get_output_ports_for_user(username=None, provider_id=None, enrich_ports=True)
                # יצירת מיפוי: שם מדפסת -> מספר סידורי
                printer_serial_map = {p.get('name'): p.get('deviceSerial', '-') for p in printers if p.get('name')}

                # סינון לפי מחלקות מורשות (דרך containerName)
                allowed_departments = st.session_state.get('allowed_departments', [])
                original_count = len(input_ports)
                filtered_input_ports = filter_input_ports_by_departments(input_ports, allowed_departments)

                # הצגת מטריקות
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("כמות תורי הדפסה", len(filtered_input_ports))

                with col2:
                    # ספירת תורים לפי סוג (portType)
                    port_types = {}
                    for port in filtered_input_ports:
                        port_type = port.get('portType', 'Unknown')
                        port_types[port_type] = port_types.get(port_type, 0) + 1
                    st.metric("סוגי תורים", len(port_types))

                # הודעת סינון לפי הרשאות
                if allowed_departments != ["ALL"] and len(filtered_input_ports) < original_count:
                    st.info(f"ℹ️ מציג תורי הדפסה עבור בתי הספר שלך בלבד ({len(filtered_input_ports)} מתוך {original_count})")

                st.markdown("---")

                # בניית טבלה
                if filtered_input_ports:
                    rows = []
                    for port in filtered_input_ports:
                        # תרגום סוג תור
                        port_type = port.get('portType', '-')
                        port_type_map = {
                            0: 'הדפסה עם קוד',
                            1: 'הדפסה ישירה'
                        }
                        port_type_display = port_type_map.get(port_type, str(port_type))

                        # קבלת מספר סידורי של המדפסת המקושרת
                        linked_printer = port.get('outputPort', '-')
                        printer_serial = printer_serial_map.get(linked_printer, '-')

                        row = {
                            'שם התור': port.get('name', '-'),
                            'תור הדפסה': port_type_display,
                            'מדפסת מקושרת': linked_printer,
                            'מספר סידורי': printer_serial,
                            'בית ספר': port.get('containerName', '-'),
                        }
                        rows.append(row)

                    df = pd.DataFrame(rows)

                    # סידור עמודות RTL - מימין לשמאל
                    df = df[['בית ספר', 'מספר סידורי', 'מדפסת מקושרת', 'תור הדפסה', 'שם התור']]

                    # הצגת הטבלה וכפתור ייצוא
                    result_col1, result_col2 = st.columns([3, 1])

                    with result_col1:
                        st.info(f"📊 סה\"כ {len(df)} תורי הדפסה")

                    with result_col2:
                        excel_data = export_to_excel(df, "print_queues")
                        st.download_button(
                            label="📥 ייצא ל-Excel",
                            data=excel_data,
                            file_name=f"print_queues.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key="export_queues_btn",
                            use_container_width=True
                        )

                    st.dataframe(
                        df,
                        use_container_width=True,
                        hide_index=True,
                        height=min(len(df) * 35 + 38, 738)
                    )
                else:
                    st.warning("⚠️ לא נמצאו תורי הדפסה")

            else:
                st.error(f"❌ שגיאה בטעינת תורי הדפסה: HTTP {response.status_code}")
                st.code(response.text)

        except Exception as e:
            st.error(f"❌ שגיאה בטעינת תורי הדפסה: {str(e)}")
