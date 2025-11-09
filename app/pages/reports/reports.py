#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
דף דוחות - Reports Page
מציג דוחות על מסמכים, היסטוריה, והדפסות
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional
import io

from shared import get_api_instance, get_logger_instance, check_authentication
from permissions import filter_users_by_departments
from config import config

CONFIG = config.get()

def show():
    """הצגת דף הדוחות"""
    check_authentication()

    # CSS Styling - RTL + כפתורים אדומים
    st.markdown("""
    <style>
        /* RTL Support */
        .stApp {
            direction: rtl;
        }

        /* Action buttons - red gradient like "צור משתמש" */
        .action-button button {
            background: linear-gradient(45deg, #C41E3A, #FF6B6B) !important;
            color: white !important;
            border: none !important;
            box-shadow: 0 4px 15px rgba(196, 30, 58, 0.3) !important;
            border-radius: 25px !important;
            font-weight: 600 !important;
            transition: all 0.3s ease !important;
            width: auto !important;
            max-width: 300px !important;
            padding: 0.5rem 2rem !important;
        }

        .action-button button:hover {
            box-shadow: 0 6px 20px rgba(196, 30, 58, 0.5) !important;
            transform: translateY(-2px) !important;
        }

        /* Fix hover flickering */
        .action-button button * {
            pointer-events: none !important;
        }

        /* Section headers */
        .section-header {
            background: linear-gradient(135deg, rgba(74, 144, 226, 0.1), rgba(196, 30, 58, 0.05));
            padding: 1rem;
            border-radius: 10px;
            margin: 1rem 0;
            border-right: 4px solid #C41E3A;
        }

        /* Info boxes */
        .info-box {
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 1rem;
            margin: 0.5rem 0;
        }

        /* Stats card */
        .stats-card {
            background: linear-gradient(135deg, rgba(74, 144, 226, 0.08), rgba(196, 30, 58, 0.05));
            border-radius: 10px;
            padding: 1.5rem;
            margin: 0.5rem 0;
            border: 1px solid rgba(196, 30, 58, 0.2);
            text-align: center;
        }

        .stats-number {
            font-size: 2rem;
            font-weight: bold;
            color: #C41E3A;
        }

        .stats-label {
            font-size: 0.9rem;
            color: #666;
            margin-top: 0.5rem;
        }

        /* Table styling */
        .dataframe {
            direction: rtl !important;
        }

        /* Export button - different style */
        .export-button button {
            background: linear-gradient(45deg, #28a745, #20c997) !important;
            color: white !important;
            border: none !important;
            box-shadow: 0 4px 15px rgba(40, 167, 69, 0.3) !important;
            border-radius: 20px !important;
            font-weight: 600 !important;
            padding: 0.4rem 1.5rem !important;
        }

        .export-button button:hover {
            box-shadow: 0 6px 20px rgba(40, 167, 69, 0.5) !important;
            transform: translateY(-2px) !important;
        }

        .export-button button * {
            pointer-events: none !important;
        }
    </style>
    """, unsafe_allow_html=True)

    st.title("📊 דוחות ניהול")

    # בדיקת הרשאות
    role = st.session_state.get('role', 'viewer')
    username = st.session_state.get('username', '')

    if role == 'viewer':
        st.warning("⚠️ אין לך הרשאות לצפות בדוחות")
        return

    api = get_api_instance()
    logger = get_logger_instance()

    # יצירת טאבים לסוגי דוחות שונים
    tab1, tab2, tab3 = st.tabs([
        "📜 דוח היסטוריה מפורט",
        "📄 מסמכים לפי משתמש",
        "📊 סטטיסטיקות"
    ])

    # ========== טאב 1: דוח היסטוריה מפורט ==========
    with tab1:
        show_history_report(api, logger, role, username)

    # ========== טאב 2: מסמכים לפי משתמש ==========
    with tab2:
        show_user_documents_report(api, logger, role, username)

    # ========== טאב 3: סטטיסטיקות ==========
    with tab3:
        show_statistics_report(api, logger, role, username)


def show_history_report(api, logger, role, username):
    """דוח היסטוריה מפורט עם סינונים"""

    st.markdown('<div class="section-header"><h3>📜 דוח היסטוריית מסמכים</h3></div>',
                unsafe_allow_html=True)

    st.markdown("""
    <div class="info-box">
    דוח זה מציג היסטוריה מפורטת של כל המסמכים במערכת.<br>
    ניתן לסנן לפי טווח תאריכים (עד שבוע), משתמש, מדפסת, סטטוס וסוג עבודה.
    </div>
    """, unsafe_allow_html=True)

    # טופס סינון
    st.markdown("### 🔍 פרמטרי חיפוש")

    col1, col2, col3 = st.columns(3)

    with col1:
        # טווח תאריכים (עד שבוע)
        st.markdown("**טווח תאריכים:**")
        date_end = st.date_input(
            "תאריך סיום",
            value=datetime.now(),
            key="history_date_end"
        )

        # ברירת מחדל: 24 שעות אחורה
        default_start = datetime.now() - timedelta(days=1)
        date_start = st.date_input(
            "תאריך התחלה",
            value=default_start,
            max_value=date_end,
            key="history_date_start"
        )

        # בדיקה שהטווח לא עולה על שבוע
        date_diff = (date_end - date_start).days
        if date_diff > 7:
            st.warning("⚠️ טווח התאריכים מוגבל לשבוע אחד בלבד")

    with col2:
        # סינון לפי משתמש
        st.markdown("**סינון לפי משתמש:**")
        filter_username = st.text_input(
            "שם משתמש (השאר ריק לכולם)",
            key="history_filter_username"
        )

        # סינון לפי מדפסת
        filter_port = st.text_input(
            "שם מדפסת (השאר ריק לכולם)",
            key="history_filter_port"
        )

    with col3:
        # סינון לפי סוג עבודה
        st.markdown("**סוג עבודה:**")
        job_types_map = {
            "הכל": None,
            "הדפסה": "PRINT",
            "העתקה": "COPY",
            "סריקה": "SCAN",
            "פקס": "FAX"
        }
        job_type_he = st.selectbox(
            "בחר סוג",
            list(job_types_map.keys()),
            key="history_job_type"
        )
        job_type = job_types_map[job_type_he]

        # סינון לפי סטטוס
        st.markdown("**סטטוס:**")
        status_map = {
            "הכל": None,
            "מוכן": [0],
            "הודפס": [1],
            "נמחק": [2],
            "פג תוקף": [3],
            "נכשל": [4],
            "התקבל": [5]
        }
        status_he = st.selectbox(
            "בחר סטטוס",
            list(status_map.keys()),
            key="history_status"
        )
        status_filter = status_map[status_he]

    # מספר תוצאות לדף
    col_records, col_spacer = st.columns([1, 3])
    with col_records:
        max_records = st.number_input(
            "תוצאות לדף",
            min_value=50,
            max_value=2000,
            value=200,
            step=50,
            key="history_max_records"
        )

    # כפתור חיפוש
    st.markdown("---")
    col_search, col_export, col_spacer = st.columns([1, 1, 2])

    with col_search:
        st.markdown('<div class="action-button">', unsafe_allow_html=True)
        search_clicked = st.button("🔍 הצג דוח", key="search_history_btn")
        st.markdown('</div>', unsafe_allow_html=True)

    # ביצוע החיפוש
    if search_clicked or 'history_report_data' in st.session_state:
        if search_clicked:
            with st.spinner("⏳ טוען נתונים..."):
                # המרת תאריכים ל-ISO format
                date_start_iso = datetime.combine(date_start, datetime.min.time()).isoformat() + "Z"
                date_end_iso = datetime.combine(date_end, datetime.max.time()).isoformat() + "Z"

                # קריאה ל-API
                result = api.get_documents_history(
                    datestart=date_start_iso,
                    dateend=date_end_iso,
                    username=filter_username if filter_username else None,
                    portname=filter_port if filter_port else None,
                    jobtype=job_type,
                    status=status_filter,
                    maxrecords=max_records
                )

                if result:
                    st.session_state.history_report_data = result
                    logger.log_action(
                        username=username,
                        action="VIEW_HISTORY_REPORT",
                        details=f"Filters: user={filter_username}, port={filter_port}, jobtype={job_type}"
                    )
                else:
                    st.error("❌ לא הצלחנו לקבל נתונים מהשרת")
                    if 'history_report_data' in st.session_state:
                        del st.session_state.history_report_data

        # הצגת התוצאות
        if 'history_report_data' in st.session_state:
            data = st.session_state.history_report_data
            documents = data.get('documents', [])

            if documents:
                st.markdown("---")
                st.markdown(f"### 📋 נמצאו {len(documents)} תוצאות")

                # הצגת מידע על pagination
                if data.get('nextPageToken'):
                    st.info(f"ℹ️ יש עוד תוצאות זמינות. מוצגים {data.get('recordsOnPage', 0)} רשומות בדף זה.")

                # המרת הנתונים ל-DataFrame
                df = prepare_history_dataframe(documents)

                # הצגת הטבלה
                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True
                )

                # כפתור ייצוא ל-Excel
                with col_export:
                    st.markdown('<div class="export-button">', unsafe_allow_html=True)
                    excel_data = export_to_excel(df, "history_report")
                    st.download_button(
                        label="📥 ייצא ל-Excel",
                        data=excel_data,
                        file_name=f"history_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="export_history_btn"
                    )
                    st.markdown('</div>', unsafe_allow_html=True)

            else:
                st.warning("⚠️ לא נמצאו תוצאות עבור הפרמטרים שנבחרו")


def show_user_documents_report(api, logger, role, username):
    """דוח מסמכים לפי משתמש ספציפי"""

    st.markdown('<div class="section-header"><h3>📄 מסמכים לפי משתמש</h3></div>',
                unsafe_allow_html=True)

    st.markdown("""
    <div class="info-box">
    דוח זה מציג את רשימת המסמכים של משתמש ספציפי.<br>
    שים לב: דוח זה דורש הרשאת ViewJob עבור המשתמש.
    </div>
    """, unsafe_allow_html=True)

    # הערה: ה-endpoint הזה דורש user token, לא API key
    st.warning("⚠️ פונקציה זו דורשת אימות משתמש (User Token) ולא זמינה כרגע באימות API Key")
    st.info("ℹ️ השתמש ב'דוח היסטוריה מפורט' לסינון לפי משתמש ספציפי")


def show_statistics_report(api, logger, role, username):
    """דוח סטטיסטיקות וסיכומים"""

    st.markdown('<div class="section-header"><h3>📊 סטטיסטיקות ניהול</h3></div>',
                unsafe_allow_html=True)

    # בדיקה אם יש נתונים מהדוח הקודם
    if 'history_report_data' not in st.session_state:
        st.info("ℹ️ עבור לטאב 'דוח היסטוריה מפורט' והפעל חיפוש כדי לראות סטטיסטיקות")
        return

    data = st.session_state.history_report_data
    documents = data.get('documents', [])

    if not documents:
        st.warning("⚠️ אין נתונים להצגת סטטיסטיקות")
        return

    st.markdown("### 📈 סיכום כללי")

    # חישוב סטטיסטיקות בסיסיות
    total_docs = len(documents)
    total_pages = sum(doc.get('totalPages', 0) for doc in documents)
    total_color_pages = sum(doc.get('colorPages', 0) for doc in documents)

    # סטטיסטיקות לפי סוג עבודה
    job_types_count = {}
    for doc in documents:
        job_type = doc.get('jobType', 'UNKNOWN')
        job_types_count[job_type] = job_types_count.get(job_type, 0) + 1

    # הצגת כרטיסי סטטיסטיקה
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="stats-card">
            <div class="stats-number">{total_docs:,}</div>
            <div class="stats-label">סה"כ מסמכים</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="stats-card">
            <div class="stats-number">{total_pages:,}</div>
            <div class="stats-label">סה"כ עמודים</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="stats-card">
            <div class="stats-number">{total_color_pages:,}</div>
            <div class="stats-label">עמודי צבע</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        bw_pages = total_pages - total_color_pages
        st.markdown(f"""
        <div class="stats-card">
            <div class="stats-number">{bw_pages:,}</div>
            <div class="stats-label">עמודים ש/ל</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # סטטיסטיקות לפי סוג עבודה
    st.markdown("### 📋 פילוח לפי סוג עבודה")

    job_type_names = {
        'PRINT': '🖨️ הדפסה',
        'COPY': '📄 העתקה',
        'SCAN': '📷 סריקה',
        'FAX': '📠 פקס'
    }

    cols = st.columns(len(job_types_count))
    for idx, (job_type, count) in enumerate(job_types_count.items()):
        with cols[idx]:
            display_name = job_type_names.get(job_type, job_type)
            percentage = (count / total_docs * 100) if total_docs > 0 else 0
            st.markdown(f"""
            <div class="stats-card">
                <div class="stats-label">{display_name}</div>
                <div class="stats-number">{count:,}</div>
                <div class="stats-label">{percentage:.1f}%</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # סטטיסטיקות לפי משתמש (Top 10)
    st.markdown("### 👥 משתמשים מובילים (Top 10)")

    user_stats = {}
    for doc in documents:
        user = doc.get('userName', 'Unknown')
        if user not in user_stats:
            user_stats[user] = {
                'docs': 0,
                'pages': 0,
                'color_pages': 0
            }
        user_stats[user]['docs'] += 1
        user_stats[user]['pages'] += doc.get('totalPages', 0)
        user_stats[user]['color_pages'] += doc.get('colorPages', 0)

    # מיון לפי מספר מסמכים
    top_users = sorted(user_stats.items(), key=lambda x: x[1]['docs'], reverse=True)[:10]

    # יצירת טבלה
    user_df = pd.DataFrame([
        {
            'משתמש': user,
            'מסמכים': stats['docs'],
            'עמודים': stats['pages'],
            'עמודי צבע': stats['color_pages'],
            'ש/ל': stats['pages'] - stats['color_pages']
        }
        for user, stats in top_users
    ])

    st.dataframe(user_df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # סטטיסטיקות לפי מדפסת (Top 10)
    st.markdown("### 🖨️ מדפסות פעילות (Top 10)")

    port_stats = {}
    for doc in documents:
        port = doc.get('outputPortName', 'Unknown')
        if port and port != '':
            port_stats[port] = port_stats.get(port, 0) + 1

    if port_stats:
        top_ports = sorted(port_stats.items(), key=lambda x: x[1], reverse=True)[:10]

        port_df = pd.DataFrame([
            {'מדפסת': port, 'מסמכים': count}
            for port, count in top_ports
        ])

        st.dataframe(port_df, use_container_width=True, hide_index=True)
    else:
        st.info("ℹ️ אין מידע על מדפסות בנתונים")

    st.markdown("---")

    # סטטיסטיקות לפי מחלקה (Department tags)
    st.markdown("### 🏢 פילוח לפי מחלקות")

    dept_stats = {}
    for doc in documents:
        tags = doc.get('tags', [])
        for tag in tags:
            if tag.get('tagType') == 0:  # Department tag
                dept_name = tag.get('name', 'Unknown')
                if dept_name not in dept_stats:
                    dept_stats[dept_name] = {
                        'docs': 0,
                        'pages': 0
                    }
                dept_stats[dept_name]['docs'] += 1
                dept_stats[dept_name]['pages'] += doc.get('totalPages', 0)

    if dept_stats:
        dept_df = pd.DataFrame([
            {
                'מחלקה': dept,
                'מסמכים': stats['docs'],
                'עמודים': stats['pages']
            }
            for dept, stats in sorted(dept_stats.items(), key=lambda x: x[1]['docs'], reverse=True)
        ])

        st.dataframe(dept_df, use_container_width=True, hide_index=True)
    else:
        st.info("ℹ️ אין מידע על מחלקות בנתונים")


def prepare_history_dataframe(documents: List[Dict]) -> pd.DataFrame:
    """המרת נתוני היסטוריה ל-DataFrame"""

    rows = []

    for doc in documents:
        # המרת timestamp ל-datetime
        timestamp = doc.get('dateTime', 0)
        if timestamp:
            dt = datetime.fromtimestamp(timestamp / 1000)  # מילישניות לשניות
            date_str = dt.strftime('%Y-%m-%d %H:%M:%S')
        else:
            date_str = ''

        # המרת סטטוס
        status_map = {
            0: 'מוכן',
            1: 'הודפס',
            2: 'נמחק',
            3: 'פג תוקף',
            4: 'נכשל',
            5: 'התקבל',
            6: 'ממתין להמרה',
            7: 'בהמרה',
            8: 'כשל בהמרה',
            9: 'מאוחסן'
        }
        status = status_map.get(doc.get('status'), 'לא ידוע')

        # איסוף tags
        tags_str = ', '.join([
            f"{tag.get('name', '')} ({'מחלקה' if tag.get('tagType') == 0 else 'קבוצה'})"
            for tag in doc.get('tags', [])
        ])

        row = {
            'תאריך': date_str,
            'משתמש': doc.get('userName', ''),
            'שם מסמך': doc.get('documentName', ''),
            'סוג': doc.get('jobType', ''),
            'סטטוס': status,
            'עמודים': doc.get('totalPages', 0),
            'צבע': doc.get('colorPages', 0),
            'עותקים': doc.get('copies', 1),
            'דופלקס': 'כן' if doc.get('duplex') else 'לא',
            'מדפסת': doc.get('outputPortName', ''),
            'גודל נייר': doc.get('paperSize', ''),
            'תגיות': tags_str
        }

        rows.append(row)

    return pd.DataFrame(rows)


def export_to_excel(df: pd.DataFrame, sheet_name: str) -> bytes:
    """ייצוא DataFrame ל-Excel"""

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
