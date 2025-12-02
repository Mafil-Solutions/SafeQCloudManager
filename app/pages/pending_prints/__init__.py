#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SafeQ Cloud Manager - Pending Prints Module
מודול הדפסות ממתינות
"""

import streamlit as st
import pandas as pd
import sys
import os
import io
from datetime import datetime
import pytz

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
    """הצגת דף הדפסות ממתינות"""
    check_authentication()

    st.title("⏳ הדפסות ממתינות")

    st.info("ℹ️ דף זה מציג את כל ההדפסות שממתינות בתור (סטטוס: מוכן)")

    # קבלת API instance
    api = get_api_instance()

    # טעינת הדפסות ממתינות אוטומטית
    with st.spinner("טוען הדפסות ממתינות..."):
        try:
            # קריאה ל-API עם status=0 (READY)
            result = api.get_documents_history(
                status=None,  # לא מסננים ב-API
                maxrecords=1000
            )

            if result and 'documents' in result:
                documents = result.get('documents', [])

                # סינון לסטטוס 0 בלבד (READY/מוכן)
                pending_docs = [doc for doc in documents if doc.get('status') == 0]

                # סינון לפי הרשאות - school_manager רואה רק את בתי הספר שלו
                allowed_departments = st.session_state.get('allowed_departments', ["ALL"])

                if allowed_departments != ["ALL"]:
                    def doc_has_allowed_department(doc):
                        tags = doc.get('tags', [])
                        for tag in tags:
                            if tag.get('tagType') == 0:  # Department tag
                                dept_name = tag.get('name', '')
                                if dept_name in allowed_departments:
                                    return True
                        return False

                    original_count = len(pending_docs)
                    pending_docs = [doc for doc in pending_docs if doc_has_allowed_department(doc)]

                    if len(pending_docs) < original_count:
                        st.info(f"ℹ️ מציג נתונים עבור בתי הספר שלך בלבד ({len(pending_docs)} מתוך {original_count})")

                # הצגת מטריקות
                if pending_docs:
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric("הדפסות ממתינות", len(pending_docs))

                    with col2:
                        # ספירת משתמשים ייחודיים
                        unique_users = len(set(doc.get('userName', '') for doc in pending_docs if doc.get('userName')))
                        st.metric("משתמשים", unique_users)

                    with col3:
                        # ספירת עמודים כולל
                        total_pages = sum(doc.get('totalPages', 0) for doc in pending_docs)
                        st.metric("סה\"כ עמודים", total_pages)

                    st.markdown("---")

                    # בניית טבלה
                    rows = []
                    for doc in pending_docs:
                        # המרת timestamp ל-datetime בשעון ישראל
                        timestamp = doc.get('dateTime', 0)
                        if timestamp:
                            # המרה מ-UTC לשעון ישראל (מטפל אוטומטית בשעון חורף/קיץ)
                            utc_dt = datetime.fromtimestamp(timestamp / 1000, tz=pytz.UTC)
                            israel_tz = pytz.timezone('Asia/Jerusalem')
                            israel_dt = utc_dt.astimezone(israel_tz)
                            date_str = israel_dt.strftime('%d/%m/%Y %H:%M:%S')
                        else:
                            date_str = ''

                        # הפרדת מחלקות מתגיות
                        tags = doc.get('tags', [])
                        departments = [tag.get('name', '') for tag in tags if tag.get('tagType') == 0]
                        department_str = ', '.join(departments) if departments else ''

                        # זיהוי מקור
                        username = doc.get('userName', '')
                        source = 'Entra' if '@' in username else 'מקומי'

                        # תרגום סוג עבודה
                        job_type_en = doc.get('jobType', '')
                        job_type_map = {
                            'PRINT': 'הדפסה',
                            'COPY': 'העתקה',
                            'SCAN': 'סריקה',
                            'FAX': 'פקס'
                        }
                        job_type_he = job_type_map.get(job_type_en, job_type_en)

                        row = {
                            'תאריך': date_str,
                            'משתמש': username,
                            'מקור': source,
                            'מחלקה': department_str,
                            'שם מסמך': doc.get('documentName', ''),
                            'סוג': job_type_he,
                            'עמודים': doc.get('totalPages', 0),
                            'צבע': doc.get('colorPages', 0),
                            'עותקים': doc.get('copies', 1),
                        }
                        rows.append(row)

                    df = pd.DataFrame(rows)

                    # כפתור ייצוא
                    result_col1, result_col2 = st.columns([3, 1])

                    with result_col1:
                        st.info(f"📊 סה\"כ {len(df)} הדפסות ממתינות")

                    with result_col2:
                        excel_data = export_to_excel(df, "pending_prints")
                        st.download_button(
                            label="📥 ייצא ל-Excel",
                            data=excel_data,
                            file_name=f"pending_prints_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key="export_pending_btn",
                            use_container_width=True
                        )

                    # הצגת הטבלה
                    st.dataframe(
                        df,
                        use_container_width=True,
                        hide_index=True,
                        height=min(len(df) * 35 + 38, 738)
                    )
                else:
                    st.success("✅ אין הדפסות ממתינות כרגע!")

            else:
                st.error("❌ לא הצלחנו לקבל נתונים מהשרת")

        except Exception as e:
            st.error(f"❌ שגיאה בטעינת הדפסות ממתינות: {str(e)}")
            st.exception(e)
