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

def show():
    """הצגת דף תורי הדפסה"""
    check_authentication()

    st.title("🗂️ תורי הדפסה (Input Ports)")

    # קבלת API instance
    api = get_api_instance()

    # טעינת תורי הדפסה
    with st.spinner("טוען תורי הדפסה..."):
        try:
            # קריאה ל-API לקבלת InputPorts
            import requests
            url = f"{api.server_url}/api/v1/inputports"
            response = requests.get(url, headers=api.headers, verify=False, timeout=30)

            if response.status_code == 200:
                input_ports = response.json()

                # DEBUG MODE - הצגת המבנה של תור הדפסה אחד
                if input_ports and len(input_ports) > 0:
                    st.warning("🔍 DEBUG MODE - מבנה של תור הדפסה אחד:")
                    debug_fields = []
                    sample_port = input_ports[0]
                    for key, value in sample_port.items():
                        debug_fields.append(f"- **{key}**: {value}")
                    st.markdown("\n".join(debug_fields))
                    st.markdown("---")

                # הצגת מטריקות
                total_queues = len(input_ports)

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("כמות תורי הדפסה", total_queues)

                with col2:
                    # ספירת תורים לפי סוג (portType)
                    port_types = {}
                    for port in input_ports:
                        port_type = port.get('portType', 'Unknown')
                        port_types[port_type] = port_types.get(port_type, 0) + 1
                    st.metric("סוגי תורים", len(port_types))

                st.markdown("---")

                # בניית טבלה
                if input_ports:
                    rows = []
                    for port in input_ports:
                        row = {
                            'מזהה': port.get('id', '-'),
                            'שם התור': port.get('name', '-'),
                            'סוג': port.get('portType', '-'),
                            'מדפסת מקושרת': port.get('outputPort', '-'),
                            'מיקום': port.get('locationId', '-'),
                            'בית ספר': port.get('containerName', '-'),
                        }
                        rows.append(row)

                    df = pd.DataFrame(rows)

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
