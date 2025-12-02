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
from typing import Dict, List, Optional, Tuple
import io
import time
import pytz

from shared import get_api_instance, get_logger_instance, check_authentication
from permissions import filter_users_by_departments
from config import config

CONFIG = config.get()


def apply_data_filters(df: pd.DataFrame) -> Tuple[pd.DataFrame, dict]:
    """
    הצגת סינונים משותפים לדשבורד ולדוח המפורט

    Args:
        df: DataFrame המקורי

    Returns:
        tuple: (DataFrame מסונן, dict של הבחירות)
    """
    # מונה לאיפוס סינונים - כל פעם שעולה, הקומפוננטים מתאפסים
    if 'filter_reset_counter' not in st.session_state:
        st.session_state.filter_reset_counter = 0

    counter = st.session_state.filter_reset_counter

    st.markdown("---")

    with st.expander("🔍 **סינון נתונים** (לחץ להצגה/הסתרה)", expanded=True):
        st.markdown("##### סנן את הנתונים המוצגים בדשבורד ובדוח המפורט")

        filter_row1_col1, filter_row1_col2, filter_row1_col3 = st.columns(3)

        with filter_row1_col1:
            search_text = st.text_input(
                "חיפוש חופשי",
                placeholder="שם, מסמך, מדפסת...",
                key=f"shared_search_{counter}",
                help="חפש בכל השדות"
            )

        with filter_row1_col2:
            source_options = ['הכל'] + sorted(df['סוג משתמש'].unique().tolist())
            selected_source = st.selectbox(
                "סוג משתמש",
                source_options,
                key=f"shared_filter_source_{counter}"
            )

        with filter_row1_col3:
            jobtype_options = ['הכל'] + sorted(df['סוג'].unique().tolist())
            selected_jobtype = st.selectbox(
                "סוג עבודה",
                jobtype_options,
                key=f"shared_filter_jobtype_{counter}"
            )

        filter_row2_col1, filter_row2_col2, filter_row2_col3 = st.columns(3)

        with filter_row2_col1:
            status_options = ['הכל'] + sorted(df['סטטוס'].unique().tolist())
            selected_status = st.selectbox(
                "סטטוס",
                status_options,
                key=f"shared_filter_status_{counter}"
            )

        with filter_row2_col2:
            dept_options = ['הכל'] + sorted([d for d in df['מחלקה'].unique() if d], key=str)
            selected_dept = st.selectbox(
                "מחלקה",
                dept_options,
                key=f"shared_filter_dept_{counter}"
            )

        with filter_row2_col3:
            # איפוס סינונים - העלאת המונה גורמת לכל הקומפוננטים להתאפס
            if st.button("🔄 איפוס סינונים", use_container_width=True, key=f"reset_filters_btn_{counter}"):
                st.session_state.filter_reset_counter += 1
                st.rerun()

    # החלת סינונים
    filtered_df = df.copy()
    filters_applied = {
        'search': search_text,
        'source': selected_source,
        'jobtype': selected_jobtype,
        'status': selected_status,
        'dept': selected_dept
    }

    if search_text:
        mask = filtered_df.astype(str).apply(
            lambda x: x.str.contains(search_text, case=False, na=False)
        ).any(axis=1)
        filtered_df = filtered_df[mask]

    if selected_source != 'הכל':
        filtered_df = filtered_df[filtered_df['סוג משתמש'] == selected_source]

    if selected_jobtype != 'הכל':
        filtered_df = filtered_df[filtered_df['סוג'] == selected_jobtype]

    if selected_status != 'הכל':
        filtered_df = filtered_df[filtered_df['סטטוס'] == selected_status]

    if selected_dept != 'הכל':
        filtered_df = filtered_df[filtered_df['מחלקה'] == selected_dept]

    # הצגת מידע על הסינון
    if len(filtered_df) < len(df):
        st.info(f"🔍 מציג {len(filtered_df):,} מתוך {len(df):,} רשומות (סוננו {len(df) - len(filtered_df):,} רשומות)")

    return filtered_df, filters_applied


def show_report_settings(api):
    """
    הגדרות דוח משותפות לכל הטאבים

    Returns:
        tuple: (date_start, date_end, filter_username, filter_port, job_type, status_filter_list, max_records, search_clicked)
    """
    # CSS להבלטת expander
    st.markdown("""
    <style>
        .streamlit-expanderHeader {
           /* background-color: rgba(74, 144, 226, 0.1) !important;*/
            border: 2px solid rgba(196, 30, 58, 0.3) !important;
            border-radius: 8px !important;
            font-size: 1.1em !important;
            font-weight: 600 !important;
            padding: 0.8rem !important;
        }
        .streamlit-expanderHeader:hover {
            /*background-color: rgba(74, 144, 226, 0.15) !important;*/
            border-color: rgba(196, 30, 58, 0.5) !important;
        }

                /* עטיפת הטאבים */
        .stTabs [data-baseweb="tab-list"] {
            display: flex;
            justify-content: space-between;
            width: 100%;
        }
        
        /* כל טאב בנפרד */
        .stTabs [data-baseweb="tab"] {
            flex: 1 1 50%;         /* כל טאב תופס 50% */
            max-width: 50%;
            text-align: center;     /* טקסט במרכז */
            font-size: 20px;        /* גודל טקסט גדול יותר */
            padding: 16px 0;        /* גובה גדול */
        }
        
        /* כותרת טאב נבחר */
        .stTabs [aria-selected="true"] {
            background-color: #dce6f7;   /* צבע רקע לטאב נבחר */
            border-bottom: 3px solid #1f66d1;
            font-weight: bold;
            color: black;
        }
        
        /* כותרת טאב לא נבחר
         .stTabs [aria-selected="false"] {
             background-color: #f5f5f5; */
        }
    </style>
    """, unsafe_allow_html=True)

    with st.expander("⚙️ הגדרות דוח (לחץ להסתרה/הרחבה)", expanded=True):

        # שורה 0: פילטר מהיר + איפוס
        col_quick, col_reset = st.columns([3, 1])

        with col_quick:
            quick_filters_options = [
                "📅 7 ימים אחרונים",
                "📅 30 ימים אחרונים",
                "📅 חודש נוכחי",
                "🎯 טווח מותאם אישית"
            ]

            # ברירת מחדל
            if 'quick_filter_selection' not in st.session_state:
                st.session_state.quick_filter_selection = "📅 7 ימים אחרונים"

            quick_filter = st.selectbox(
                "פילטר מהיר",
                quick_filters_options,
                index=quick_filters_options.index(st.session_state.quick_filter_selection) if st.session_state.quick_filter_selection in quick_filters_options else 0,
                key="quick_filter_select"
            )

            st.session_state.quick_filter_selection = quick_filter

        with col_reset:
            st.write("")  # spacing
            st.write("")  # spacing
            if st.button("🔄 איפוס", use_container_width=True):
                # איפוס מלא
                st.session_state.quick_filter_selection = "📅 7 ימים אחרונים"
                st.session_state.report_date_start = (datetime.now() - timedelta(days=6)).date()
                st.session_state.report_date_end = datetime.now().date()
                st.session_state.history_filter_username = ""
                st.session_state.history_filter_port = ""
                if 'history_report_data' in st.session_state:
                    del st.session_state.history_report_data
                if 'user_lookup_cache' in st.session_state:
                    del st.session_state.user_lookup_cache
                st.rerun()

        # חישוב תאריכים לפי פילטר מהיר
        if quick_filter == "📅 7 ימים אחרונים":
            date_start = (datetime.now() - timedelta(days=6)).date()
            date_end = datetime.now().date()
            st.session_state.report_date_start = date_start
            st.session_state.report_date_end = date_end
            show_dates = False
        elif quick_filter == "📅 30 ימים אחרונים":
            date_start = (datetime.now() - timedelta(days=29)).date()
            date_end = datetime.now().date()
            st.session_state.report_date_start = date_start
            st.session_state.report_date_end = date_end
            show_dates = False
        elif quick_filter == "📅 חודש נוכחי":
            today = datetime.now().date()
            date_start = today.replace(day=1)
            date_end = today
            st.session_state.report_date_start = date_start
            st.session_state.report_date_end = date_end
            show_dates = False
        else:  # טווח מותאם אישית
            show_dates = True
            # ברירות מחדל אם לא קיימות
            if 'report_date_start' not in st.session_state:
                st.session_state.report_date_start = (datetime.now() - timedelta(days=6)).date()
            if 'report_date_end' not in st.session_state:
                st.session_state.report_date_end = datetime.now().date()

            date_start = st.session_state.report_date_start
            date_end = st.session_state.report_date_end

        # הצגת תאריכים רק אם בחרנו "טווח מותאם אישית"
        if show_dates:
            st.markdown("##### 📅 בחירת טווח תאריכים")
            col_date1, col_date2 = st.columns(2)

            with col_date1:
                date_start = st.date_input(
                    "תאריך התחלה",
                    value=st.session_state.report_date_start,
                    key="date_start_input",
                    format="DD/MM/YYYY"
                )
                st.session_state.report_date_start = date_start

            with col_date2:
                date_end = st.date_input(
                    "תאריך סיום",
                    value=st.session_state.report_date_end,
                    key="date_end_input",
                    format="DD/MM/YYYY"
                )
                st.session_state.report_date_end = date_end
        else:
            # הצגת טווח התאריכים שנבחר
            st.info(f"📆 טווח נבחר: {date_start.strftime('%d/%m/%Y')} - {date_end.strftime('%d/%m/%Y')}")

        # בדיקת תקינות תאריכים
        if date_start > date_end:
            st.error("⚠️ תאריך ההתחלה חייב להיות לפני תאריך הסיום")
            return None, None, None, None, False

        # שורה 2: סטטוס ותוצאות לדף
        col_status, col_records = st.columns(2)

        with col_status:
            status_map = {
                "עבודות שבוצעו בפועל": [1, 5],  # הודפס, התקבל
                "עבודות שלא בוצעו": [2, 3, 4],  # נמחק, פג תוקף, נכשל
            }
            status_he = st.selectbox(
                "⚡ סטטוס",
                list(status_map.keys()),
                key="history_status"
            )
            status_filter_list = status_map[status_he]

        with col_records:
            max_records = st.number_input(
                "תוצאות לדף",
                min_value=50,
                max_value=2000,
                value=1000,
                step=50,
                key="history_max_records"
            )

        # שורה 3: כפתור חיפוש
        col_search, col_spacer = st.columns([1, 3])

        with col_search:
            st.write("")  # spacing
            st.write("")  # spacing
            search_clicked = st.button("🔍 הצג דוח", use_container_width=True, type="primary")

    return date_start, date_end, status_filter_list, max_records, search_clicked


def fetch_report_data(api, logger, username, date_start, date_end, status_filter_list, max_records):
    """
    קריאת נתונים מה-API ושמירה ב-session_state
    """
    date_diff = (date_end - date_start).days

    if date_diff < 7:  # טווח קטן - קריאה בודדת
        with st.spinner("⏳ טוען נתונים..."):
            date_start_iso = datetime.combine(date_start, datetime.min.time()).isoformat() + "Z"

            if date_end >= datetime.now().date():
                date_end_iso = datetime.now().isoformat() + "Z"
            else:
                date_end_iso = datetime.combine(date_end, datetime.max.time()).isoformat() + "Z"

            result = api.get_documents_history(
                datestart=date_start_iso,
                dateend=date_end_iso,
                status=None,  # לא שולחים status ל-API
                maxrecords=max_records
            )

            if result:
                st.session_state.history_report_data = result
                logger.log_action(
                    username=username,
                    action="VIEW_REPORT",
                    details=f"Date range: {date_start} to {date_end}"
                )
            else:
                st.error("❌ לא הצלחנו לקבל נתונים מהשרת")
                if 'history_report_data' in st.session_state:
                    del st.session_state.history_report_data
    else:
        # טווח גדול - קריאות מרובות
        all_documents = []
        week_ranges = split_date_range_to_weeks(date_start, date_end)
        total_weeks = len(week_ranges)

        progress_bar = st.progress(0)
        status_text = st.empty()

        success_count = 0
        for idx, (week_start, week_end) in enumerate(week_ranges):
            status_text.text(f"⏳ טוען שבוע {idx + 1} מתוך {total_weeks}...")

            week_start_iso = datetime.combine(week_start, datetime.min.time()).isoformat() + "Z"

            if week_end >= datetime.now().date():
                week_end_iso = datetime.now().isoformat() + "Z"
            else:
                week_end_iso = datetime.combine(week_end, datetime.max.time()).isoformat() + "Z"

            result = api.get_documents_history(
                datestart=week_start_iso,
                dateend=week_end_iso,
                status=None,  # לא שולחים status ל-API
                maxrecords=max_records
            )

            if result and 'documents' in result:
                all_documents.extend(result['documents'])
                success_count += 1

            progress_bar.progress((idx + 1) / total_weeks)

        # הצגת 100%
        status_text.text(f"✅ הסתיים! נטענו {success_count} שבועות")
        progress_bar.progress(1.0)
        time.sleep(0.5)

        progress_bar.empty()
        status_text.empty()

        if all_documents:
            if date_end >= datetime.now().date():
                final_end_iso = datetime.now().isoformat() + "Z"
            else:
                final_end_iso = datetime.combine(date_end, datetime.max.time()).isoformat() + "Z"

            st.session_state.history_report_data = {
                'documents': all_documents,
                'recordsOnPage': len(all_documents),
                'dateStart': datetime.combine(date_start, datetime.min.time()).isoformat() + "Z",
                'dateEnd': final_end_iso
            }

            st.success(f"✅ נטענו {len(all_documents)} מסמכים מ-{success_count} שבועות")

            logger.log_action(
                username=username,
                action="VIEW_REPORT",
                details=f"Multi-week report: {total_weeks} weeks, {len(all_documents)} documents"
            )
        else:
            st.error(f"❌ לא נמצאו נתונים עבור הטווח שנבחר ({success_count}/{total_weeks} שבועות הצליחו)")
            if 'history_report_data' in st.session_state:
                del st.session_state.history_report_data


def show_dashboard_tab(api, status_filter_list):
    """
    דשבורד מבט על - סטטיסטיקות
    משתמש בנתונים המסוננים מהsession_state
    """
    if 'filtered_df' not in st.session_state:
        st.info("ℹ️ לחץ על 'הצג דוח' כדי לטעון נתונים")
        return

    df = st.session_state.filtered_df

    if len(df) == 0:
        st.warning("⚠️ אין נתונים להצגה לאחר הסינון")
        st.info("💡 טיפ: נסה לשנות את הגדרות הסינון")
        return

    st.markdown("## 📈 סיכום כל העבודות")

    # חישוב סטטיסטיקות ישירות מהDataFrame המסונן
    # כולל כל סוגי העבודות: הדפסה, העתקה, סריקה, פקס
    total_docs = len(df)
    total_pages = int(df['עמודים'].sum())
    total_color_pages = int(df['צבע'].sum())

    # כרטיסי סטטיסטיקה
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="stats-card">
            <div class="stats-number">{total_docs:,}</div>
            <div class="stats-label">סה"כ עבודות</div>
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

    # פילוח לפי סוג עבודה
    st.markdown("### 📋 פילוח לפי סוג עבודה")

    # חישוב סטטיסטיקות לפי סוג עבודה מהDataFrame
    job_types_stats = {}
    for job_type in df['סוג'].unique():
        job_type_df = df[df['סוג'] == job_type]
        job_types_stats[job_type] = {
            'count': len(job_type_df),
            'pages': int(job_type_df['עמודים'].sum())
        }

    job_type_names = {
        'הדפסה': '🖨️ הדפסה',
        'העתקה': '📄 העתקה',
        'סריקה': '📷 סריקה',
        'פקס': '📠 פקס'
    }

    if job_types_stats:
        cols = st.columns(len(job_types_stats))
        for idx, (job_type, stats) in enumerate(job_types_stats.items()):
            with cols[idx]:
                display_name = job_type_names.get(job_type, job_type)
                count = stats['count']
                pages = stats['pages']
                # חישוב אחוזים לפי עמודים (ולא לפי מספר עבודות)
                percentage = (pages / total_pages * 100) if total_pages > 0 else 0
                st.markdown(f"""
                <div class="stats-card">
                    <div class="stats-label">{display_name}</div>
                    <div><span class="stats-number">{count:,}</span> <span class="stats-label">עבודות</span></div>
                    <div><span class="stats-number">{pages:,}</span> <span class="stats-label">עמודים</span></div>
                    <div class="stats-label">{percentage:.1f}%</div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("---")

    # TOP 10 משתמשים
    st.markdown("### 👥 משתמשים מובילים (Top 10)")

    # חישוב סטטיסטיקות משתמשים מהDataFrame
    user_stats = df.groupby('משתמש').agg({
        'עמודים': 'sum',
        'צבע': 'sum',
        'שם מלא': 'first'  # לוקח את השם המלא הראשון
    }).reset_index()

    user_stats['מסמכים'] = df.groupby('משתמש').size().values
    user_stats['ש/ל'] = user_stats['עמודים'] - user_stats['צבע']

    # מיון לפי עמודים והצגת Top 10
    top_users_df = user_stats.nlargest(10, 'עמודים')[['שם מלא', 'משתמש', 'מסמכים', 'עמודים', 'צבע', 'ש/ל']]
    top_users_df.columns = ['שם מלא', 'משתמש', 'מסמכים', 'עמודים', 'עמודי צבע', 'ש/ל']

    st.dataframe(top_users_df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # TOP 10 מדפסות
    st.markdown("### 🖨️ מדפסות פעילות (Top 10)")

    # חישוב סטטיסטיקות מדפסות מהDataFrame
    port_stats = df[df['מדפסת'] != ''].groupby('מדפסת').agg({
        'עמודים': 'sum'
    }).reset_index()
    port_stats['מסמכים'] = df[df['מדפסת'] != ''].groupby('מדפסת').size().values

    # מיון לפי עמודים והצגת Top 10
    if len(port_stats) > 0:
        top_ports_df = port_stats.nlargest(10, 'עמודים')[['מדפסת', 'מסמכים', 'עמודים']]
        st.dataframe(top_ports_df, use_container_width=True, hide_index=True)
    else:
        st.info("ℹ️ אין מידע על מדפסות בנתונים")

    st.markdown("---")

    # פילוח לפי מחלקות
    st.markdown("### 🏢 פילוח לפי מחלקות")

    # חישוב סטטיסטיקות מחלקות מהDataFrame
    dept_stats = df[df['מחלקה'] != ''].groupby('מחלקה').agg({
        'עמודים': 'sum'
    }).reset_index()

    if len(dept_stats) > 0:
        dept_stats['מסמכים'] = df[df['מחלקה'] != ''].groupby('מחלקה').size().values

        # מיון לפי עמודים
        dept_df = dept_stats.sort_values('עמודים', ascending=False)[['מחלקה', 'מסמכים', 'עמודים']]
        st.dataframe(dept_df, use_container_width=True, hide_index=True)
    else:
        st.info("ℹ️ אין מידע על מחלקות בנתונים")


def show_detailed_report_tab(api, status_filter_list):
    """
    דוח היסטוריה מפורט
    """
    if 'history_report_data' not in st.session_state:
        st.info("ℹ️ לחץ על 'הצג דוח' כדי לטעון נתונים")
        return

    data = st.session_state.history_report_data
    documents = data.get('documents', [])

    if not documents:
        st.warning("⚠️ אין נתונים להצגה")
        return

    # סינון לפי הרשאות - school_manager רואה רק את בתי הספר שלו
    allowed_departments = st.session_state.get('allowed_departments', ["ALL"])

    if allowed_departments != ["ALL"]:
        original_count_before_dept = len(documents)

        # פונקציה עזר לבדיקה אם דוקומנט שייך למחלקה מורשית
        def doc_has_allowed_department(doc):
            tags = doc.get('tags', [])
            for tag in tags:
                if tag.get('tagType') == 0:  # Department tag
                    dept_name = tag.get('name', '')
                    if dept_name in allowed_departments:
                        return True
            return False

        # סינון דוקומנטים לפי מחלקות מורשות
        documents = [doc for doc in documents if doc_has_allowed_department(doc)]

        if len(documents) < original_count_before_dept:
            st.info(f"ℹ️ מציג נתונים עבור בתי הספר שלך בלבד ({len(documents)} מתוך {original_count_before_dept})")

    # בניית cache של שמות משתמשים
    if 'user_lookup_cache' not in st.session_state:
        with st.spinner("טוען מידע משתמשים..."):
            usernames = [doc.get('userName', '') for doc in documents if doc.get('userName')]
            st.session_state.user_lookup_cache = build_user_lookup_cache(api, usernames)

    user_cache = st.session_state.user_lookup_cache

    # סינון לפי סטטוס
    filtered_documents = [doc for doc in documents if doc.get('status') in status_filter_list]

    # המרת הנתונים ל-DataFrame
    df = prepare_history_dataframe(filtered_documents, user_cache)

    # הצגת מספר תוצאות
    st.markdown(f"## 📋 נמצאו {len(df)} תוצאות")

    if len(filtered_documents) < len(documents):
        st.info(f"ℹ️ סוננו {len(documents) - len(filtered_documents)} רשומות לפי סטטוס")

    if len(df) == 0:
        st.warning("⚠️ אין תוצאות להצגה")
        return

    # שימוש בנתונים המסוננים מה-session_state (סינון משותף עם הדשבורד)
    filtered_df = st.session_state.get('filtered_df', df)
    original_df = st.session_state.get('original_df', df)

    # הצגת מונה וכפתור ייצוא
    result_col1, result_col2 = st.columns([3, 1])

    with result_col1:
        if len(filtered_df) < len(original_df):
            st.info(f"📊 מוצגים {len(filtered_df)} מתוך {len(original_df)} רשומות")
        else:
            st.info(f"📊 סה\"כ {len(filtered_df)} רשומות")

    with result_col2:
        excel_data = export_to_excel(filtered_df, "history_report")
        st.download_button(
            label="📥 ייצא ל-Excel",
            data=excel_data,
            file_name=f"history_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="export_detail_btn",
            use_container_width=True
        )

    # הצגת הטבלה
    st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True,
        height=min(len(filtered_df) * 35 + 38, 738)
    )


def build_user_lookup_cache(api, usernames: List[str]) -> Dict[str, str]:
    """
    בונה cache של username -> fullName

    Args:
        api: instance של SafeQAPI
        usernames: רשימת usernames לחיפוש

    Returns:
        dict: {username: fullName}
    """
    user_cache = {}

    if not usernames:
        return user_cache

    # הסרת כפילויות
    unique_usernames = list(set(usernames))

    try:
        # נסה לטעון משתמשים מקומיים ו-Entra (בשקט, בלי הודעות)
        all_users = []

        # Local users
        try:
            local_users = api.get_users(CONFIG['PROVIDERS']['LOCAL'], max_records=500)
            if local_users:
                all_users.extend(local_users)
        except Exception:
            pass

        # Entra users
        try:
            entra_users = api.get_users(CONFIG['PROVIDERS']['ENTRA'], max_records=500)
            if entra_users:
                all_users.extend(entra_users)
        except Exception:
            pass

        # בניית cache
        for user in all_users:
            username = user.get('userName', '') or user.get('username', '')
            full_name = user.get('fullName', '') or user.get('displayName', '') or user.get('name', '')

            if username and full_name:
                user_cache[username] = full_name

    except Exception as e:
        # שגיאה כללית - לא מציג למשתמש
        pass

    return user_cache


def split_date_range_to_weeks(start_date, end_date):
    """
    מפצל טווח תאריכים לשבועות (7 ימים לכל שבוע)

    Args:
        start_date: תאריך התחלה (date object)
        end_date: תאריך סיום (date object)

    Returns:
        list of tuples: [(week1_start, week1_end), (week2_start, week2_end), ...]
    """
    weeks = []
    current_start = start_date

    while current_start <= end_date:
        # חישוב סוף השבוע - 7 ימים או עד תאריך הסיום (הנמוך מבניהם)
        current_end = min(current_start + timedelta(days=6), end_date)

        weeks.append((current_start, current_end))

        # המשך לשבוע הבא
        current_start = current_end + timedelta(days=1)

    return weeks


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

    st.title("📊 דוחות שימוש")

    # בדיקת הרשאות
    role = st.session_state.get('role', 'viewer')
    username = st.session_state.get('username', '')

    if role == 'viewer':
        st.warning("⚠️ אין לך הרשאות לצפות בדוחות")
        return

    api = get_api_instance()
    logger = get_logger_instance()

    # הגדרות דוח משותפות
    settings_result = show_report_settings(api)

    if settings_result[0] is None:  # אם יש שגיאה בתאריכים
        return

    date_start, date_end, status_filter_list, max_records, search_clicked = settings_result

    # ביצוע החיפוש
    if search_clicked or 'history_report_data' in st.session_state:
        if search_clicked:
            # קריאת נתונים מ-API
            fetch_report_data(api, logger, username, date_start, date_end, status_filter_list, max_records)

        # טעינת הנתונים והכנת DataFrame מסונן משותף
        if 'history_report_data' in st.session_state:
            data = st.session_state.history_report_data
            documents = data.get('documents', [])

            if documents:
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

                    documents = [doc for doc in documents if doc_has_allowed_department(doc)]

                # סינון לפי סטטוס
                filtered_documents = [doc for doc in documents if doc.get('status') in status_filter_list]

                # בניית cache של שמות משתמשים
                if 'user_lookup_cache' not in st.session_state:
                    with st.spinner("טוען מידע משתמשים..."):
                        usernames = [doc.get('userName', '') for doc in filtered_documents if doc.get('userName')]
                        st.session_state.user_lookup_cache = build_user_lookup_cache(api, usernames)

                user_cache = st.session_state.user_lookup_cache

                # המרת הנתונים ל-DataFrame
                df = prepare_history_dataframe(filtered_documents, user_cache)

                # הצגת סינון משותף (בexpander)
                filtered_df, filters_applied = apply_data_filters(df)

                # שמירת הנתונים המסוננים ב-session_state כדי שהטאבים יוכלו להשתמש בהם
                st.session_state.filtered_df = filtered_df
                st.session_state.original_df = df
                st.session_state.filters_applied = filters_applied
            else:
                st.warning("⚠️ אין נתונים להצגה")
                return

    # יצירת טאבים - רק 2 טאבים
    tab1, tab2 = st.tabs([
        "🏠 דשבורד מבט על",
        "📜 דוח היסטוריה מפורט"
    ])

    # ========== טאב 1: דשבורד מבט על ==========
    with tab1:
        show_dashboard_tab(api, status_filter_list)

    # ========== טאב 2: דוח היסטוריה מפורט ==========
    with tab2:
        show_detailed_report_tab(api, status_filter_list)


def show_history_report(api, logger, role, username):
    """דוח היסטוריה מפורט עם סינונים"""

    st.markdown('<div class="section-header"><h3>📜 דוח היסטוריית מסמכים</h3></div>',
                unsafe_allow_html=True)

    st.markdown("""
    <div class="info-box">
    דוח זה מציג היסטוריה מפורטת של כל המסמכים במערכת.<br>
    ניתן לסנן לפי טווח תאריכים (ללא הגבלה), משתמש, מדפסת, סטטוס וסוג עבודה.
    </div>
    """, unsafe_allow_html=True)

    # ====== טופס חיפוש מחודש ======
    st.markdown("### ⚙️ הגדרות דוח")

    # שורה 1: תאריכים
    col_date1, col_date2 = st.columns(2)

    with col_date1:
        # ברירות מחדל מ-session state או ערכים חדשים
        if 'report_date_start' not in st.session_state:
            st.session_state.report_date_start = (datetime.now() - timedelta(days=1)).date()

        date_start = st.date_input(
            "📅 תאריך התחלה",
            value=st.session_state.report_date_start,
            key="history_date_start",
            format="DD/MM/YYYY"
        )
        st.session_state.report_date_start = date_start

    with col_date2:
        if 'report_date_end' not in st.session_state:
            st.session_state.report_date_end = datetime.now().date()

        date_end = st.date_input(
            "📅 תאריך סיום",
            value=st.session_state.report_date_end,
            key="history_date_end",
            format="DD/MM/YYYY"
        )
        st.session_state.report_date_end = date_end

    # בדיקת תקינות תאריכים
    if date_start > date_end:
        st.error("⚠️ תאריך ההתחלה חייב להיות לפני תאריך הסיום")
        return

    # הצגת מידע על הטווח שנבחר
    date_diff = (date_end - date_start).days
    if date_diff >= 7:  # 7 ימים ביניהם = 8 ימים כולל, צריך פיצול
        num_weeks = (date_diff // 7) + 1
        st.info(f"ℹ️ הדוח יבוצע ב-{num_weeks} קריאות API (שבוע לכל קריאה)")

    # שורה 2: סינון לפי משתמש/מדפסת
    col_user, col_printer = st.columns(2)

    with col_user:
        filter_username = st.text_input(
            "👤 סינון לפי משתמש (אופציונלי)",
            placeholder="השאר ריק לכולם",
            key="history_filter_username"
        )

    with col_printer:
        filter_port = st.text_input(
            "🖨️ סינון לפי מדפסת (אופציונלי)",
            placeholder="השאר ריק לכולם",
            key="history_filter_port"
        )

    # שורה 3: סוג עבודה/סטטוס
    col_jobtype, col_status = st.columns(2)

    with col_jobtype:
        job_types_map = {
            "הכל": None,
            "הדפסה": "PRINT",
            "העתקה": "COPY",
            "סריקה": "SCAN",
            "פקס": "FAX"
        }
        job_type_he = st.selectbox(
            "📋 סוג עבודה",
            list(job_types_map.keys()),
            key="history_job_type"
        )
        job_type = job_types_map[job_type_he]

    with col_status:
        status_map = {
            "עבודות שבוצעו בפועל": [1, 5],  # הודפס, התקבל
            "עבודות שלא בוצעו": [2, 3, 4],  # נמחק, פג תוקף, נכשל
        }
        status_he = st.selectbox(
            "⚡ סטטוס",
            list(status_map.keys()),
            key="history_status"
        )
        status_filter_list = status_map[status_he]  # שומרים לסינון בצד לקוח
        status_filter = None  # לא שולחים ל-API - נסנן בצד לקוח

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
            # בדיקה אם צריך לפצל לשבועות
            # date_diff מחשב ימים ביניהם, אז date_diff=6 זה 7 ימים (כולל התחלה)
            date_diff = (date_end - date_start).days

            if date_diff < 7:  # פחות מ-7 ימים ביניהם = מקסימום 7 ימים כולל
                # טווח קטן/שווה לשבוע - קריאה בודדת
                with st.spinner("⏳ טוען נתונים..."):
                    date_start_iso = datetime.combine(date_start, datetime.min.time()).isoformat() + "Z"

                    # אם תאריך הסיום הוא היום, השתמש בזמן הנוכחי במקום סוף היום
                    if date_end >= datetime.now().date():
                        date_end_iso = datetime.now().isoformat() + "Z"
                    else:
                        date_end_iso = datetime.combine(date_end, datetime.max.time()).isoformat() + "Z"

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
                            details=f"Filters: user={filter_username}, port={filter_port}, jobtype={job_type}, days={date_diff}"
                        )
                    else:
                        st.error("❌ לא הצלחנו לקבל נתונים מהשרת")
                        if 'history_report_data' in st.session_state:
                            del st.session_state.history_report_data
            else:
                # טווח גדול - קריאות מרובות
                all_documents = []

                # פיצול לשבועות
                week_ranges = split_date_range_to_weeks(date_start, date_end)
                total_weeks = len(week_ranges)

                st.info(f"📊 מבצע {total_weeks} קריאות API לטווח של {date_diff} ימים...")

                # Progress bar
                progress_bar = st.progress(0)
                status_text = st.empty()

                success_count = 0
                for idx, (week_start, week_end) in enumerate(week_ranges):
                    status_text.text(f"⏳ טוען שבוע {idx + 1} מתוך {total_weeks}...")

                    week_start_iso = datetime.combine(week_start, datetime.min.time()).isoformat() + "Z"

                    # אם תאריך הסיום הוא היום או בעתיד, השתמש בזמן הנוכחי
                    if week_end >= datetime.now().date():
                        week_end_iso = datetime.now().isoformat() + "Z"
                    else:
                        week_end_iso = datetime.combine(week_end, datetime.max.time()).isoformat() + "Z"

                    result = api.get_documents_history(
                        datestart=week_start_iso,
                        dateend=week_end_iso,
                        username=filter_username if filter_username else None,
                        portname=filter_port if filter_port else None,
                        jobtype=job_type,
                        status=status_filter,
                        maxrecords=max_records
                    )

                    if result and 'documents' in result:
                        all_documents.extend(result['documents'])
                        success_count += 1

                    # עדכון progress bar
                    progress_bar.progress((idx + 1) / total_weeks)

                # הצגת 100% לפני ניקוי
                status_text.text(f"✅ הסתיים! נטענו {success_count} שבועות")
                progress_bar.progress(1.0)

                # המתנה קצרה לפני ניקוי
                time.sleep(0.5)

                # ניקוי progress bar
                progress_bar.empty()
                status_text.empty()

                if all_documents:
                    # יצירת אובייקט result מאוחד
                    # תאריך סיום - אם זה היום או בעתיד, השתמש בזמן הנוכחי
                    if date_end >= datetime.now().date():
                        final_end_iso = datetime.now().isoformat() + "Z"
                    else:
                        final_end_iso = datetime.combine(date_end, datetime.max.time()).isoformat() + "Z"

                    st.session_state.history_report_data = {
                        'documents': all_documents,
                        'recordsOnPage': len(all_documents),
                        'dateStart': datetime.combine(date_start, datetime.min.time()).isoformat() + "Z",
                        'dateEnd': final_end_iso
                    }

                    st.success(f"✅ נטענו {len(all_documents)} מסמכים מ-{success_count} שבועות")

                    logger.log_action(
                        username=username,
                        action="VIEW_HISTORY_REPORT",
                        details=f"Multi-week report: {total_weeks} weeks, {len(all_documents)} documents"
                    )
                else:
                    st.error(f"❌ לא נמצאו נתונים עבור הטווח שנבחר ({success_count}/{total_weeks} שבועות הצליחו)")
                    if 'history_report_data' in st.session_state:
                        del st.session_state.history_report_data

        # הצגת התוצאות
        if 'history_report_data' in st.session_state:
            data = st.session_state.history_report_data
            documents = data.get('documents', [])

            if documents:
                st.markdown("---")

                # בניית cache של שמות משתמשים (רק פעם אחת)
                if 'user_lookup_cache' not in st.session_state:
                    with st.spinner("טוען מידע משתמשים..."):
                        usernames = [doc.get('userName', '') for doc in documents if doc.get('userName')]
                        st.session_state.user_lookup_cache = build_user_lookup_cache(api, usernames)

                user_cache = st.session_state.user_lookup_cache

                # סינון לפי סטטוס (בצד לקוח)
                filtered_documents = [doc for doc in documents if doc.get('status') in status_filter_list]

                # המרת הנתונים ל-DataFrame
                df = prepare_history_dataframe(filtered_documents, user_cache)

                # הצגת מספר תוצאות אחרי סינון
                st.markdown(f"### 📋 נמצאו {len(df)} תוצאות")

                # הסבר על סינון אם יש הפרש
                if len(filtered_documents) < len(documents):
                    st.info(f"ℹ️ סוננו {len(documents) - len(filtered_documents)} רשומות לפי סטטוס")

                # הצגת מידע על pagination
                if data.get('nextPageToken'):
                    st.info(f"ℹ️ יש עוד תוצאות זמינות מהשרת")

                # סינון וחיפוש
                st.markdown("---")
                st.markdown("#### 🔍 סינון נתונים")

                # שורה 1: חיפוש חופשי + מקור
                filter_row1_col1, filter_row1_col2, filter_row1_col3 = st.columns(3)

                with filter_row1_col1:
                    search_text = st.text_input("חיפוש חופשי", placeholder="שם, מסמך, מדפסת...", key="history_search")

                with filter_row1_col2:
                    source_options = ['הכל'] + sorted(df['סוג משתמש'].unique().tolist())
                    selected_source = st.selectbox("סוג משתמש", source_options, key="filter_source")

                with filter_row1_col3:
                    jobtype_options = ['הכל'] + sorted(df['סוג'].unique().tolist())
                    selected_jobtype = st.selectbox("סוג עבודה", jobtype_options, key="filter_jobtype")

                # שורה 2: סטטוס + מחלקה
                filter_row2_col1, filter_row2_col2, filter_row2_col3 = st.columns(3)

                with filter_row2_col1:
                    status_options = ['הכל'] + sorted(df['סטטוס'].unique().tolist())
                    selected_status = st.selectbox("סטטוס", status_options, key="filter_status")

                with filter_row2_col2:
                    dept_options = ['הכל'] + sorted([d for d in df['מחלקה'].unique() if d], key=str)
                    selected_dept = st.selectbox("מחלקה", dept_options, key="filter_dept")

                # החלת סינונים
                filtered_df = df.copy()

                if search_text:
                    mask = filtered_df.astype(str).apply(lambda x: x.str.contains(search_text, case=False, na=False)).any(axis=1)
                    filtered_df = filtered_df[mask]

                if selected_source != 'הכל':
                    filtered_df = filtered_df[filtered_df['סוג משתמש'] == selected_source]

                if selected_jobtype != 'הכל':
                    filtered_df = filtered_df[filtered_df['סוג'] == selected_jobtype]

                if selected_status != 'הכל':
                    filtered_df = filtered_df[filtered_df['סטטוס'] == selected_status]

                if selected_dept != 'הכל':
                    filtered_df = filtered_df[filtered_df['מחלקה'] == selected_dept]

                # הצגת מונה תוצאות וכפתור ייצוא
                st.markdown("---")
                result_col1, result_col2 = st.columns([3, 1])

                with result_col1:
                    if len(filtered_df) < len(df):
                        st.info(f"📊 מוצגים {len(filtered_df)} מתוך {len(df)} רשומות")
                    else:
                        st.info(f"📊 סה\"כ {len(df)} רשומות")

                with result_col2:
                    excel_data = export_to_excel(filtered_df, "history_report")
                    st.download_button(
                        label="📥 ייצא ל-Excel",
                        data=excel_data,
                        file_name=f"history_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="export_history_btn",
                        use_container_width=True
                    )

                # הצגת הטבלה (עד 20 שורות)
                st.dataframe(
                    filtered_df,
                    use_container_width=True,
                    hide_index=True,
                    height=min(len(filtered_df) * 35 + 38, 738)  # 20 שורות מקסימום (20*35 + 38 header)
                )

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

    # סינון: רק עבודות שבוצעו בפועל (הודפס, התקבל)
    original_count = len(documents)
    filtered_documents = []
    for doc in documents:
        if doc.get('status') in [1, 5]:  # רק הודפס/התקבל
            filtered_documents.append(doc)

    documents = filtered_documents

    st.markdown("### 📈 סיכום הדפסות/צילומים")

    # בדיקה אם יש נתונים לאחר סינון
    if not documents:
        st.warning("⚠️ אין עבודות שבוצעו בפועל בתוצאות שנבחרו")
        st.info("💡 טיפ: הסטטיסטיקות מציגות רק עבודות עם סטטוס 'הודפס' או 'התקבל'. בחר 'עבודות שבוצעו בפועל' בסינון הדוח כדי לראות סטטיסטיקות.")
        return

    # הסבר על סינון
    if len(documents) < original_count:
        st.info(f"ℹ️ הסטטיסטיקות מציגות רק עבודות שבוצעו בפועל ({len(documents)} מתוך {original_count} תוצאות)")

    # חישוב סטטיסטיקות - רק הדפסה וצילום (לא סריקה!)
    print_copy_docs = [doc for doc in documents if doc.get('jobType') in ['PRINT', 'COPY']]

    total_docs = len(print_copy_docs)
    total_pages = sum(doc.get('totalPages', 0) for doc in print_copy_docs)
    total_color_pages = sum(doc.get('colorPages', 0) for doc in print_copy_docs)

    # תרגום סוגי עבודה לעברית
    job_type_translation = {
        'PRINT': 'הדפסה',
        'COPY': 'העתקה',
        'SCAN': 'סריקה',
        'FAX': 'פקס'
    }

    # סטטיסטיקות לפי סוג עבודה
    job_types_stats = {}
    for doc in documents:
        job_type = doc.get('jobType', 'UNKNOWN')
        job_type_he = job_type_translation.get(job_type, job_type)
        if job_type_he not in job_types_stats:
            job_types_stats[job_type_he] = {'count': 0, 'pages': 0}
        job_types_stats[job_type_he]['count'] += 1
        job_types_stats[job_type_he]['pages'] += doc.get('totalPages', 0)

    # הצגת כרטיסי סטטיסטיקה
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="stats-card">
            <div class="stats-number">{total_docs:,}</div>
            <div class="stats-label">סה"כ עבודות הדפסה/צילום</div>
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

    cols = st.columns(len(job_types_stats))
    for idx, (job_type, stats) in enumerate(job_types_stats.items()):
        with cols[idx]:
            display_name = job_type_names.get(job_type, job_type)
            count = stats['count']
            pages = stats['pages']
            # חישוב אחוזים לפי עמודים (ולא לפי מספר עבודות)
            percentage = (pages / total_pages * 100) if total_pages > 0 else 0
            st.markdown(f"""
            <div class="stats-card">
                <div class="stats-label">{display_name}</div>
                <div><span class="stats-number">{count:,}</span> <span class="stats-label">עבודות</span></div>
                <div><span class="stats-number">{pages:,}</span> <span class="stats-label">עמודים</span></div>
                <div class="stats-label">{percentage:.1f}%</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # סטטיסטיקות לפי משתמש (Top 10)
    st.markdown("### 👥 משתמשים מובילים (Top 10)")

    # בדיקה אם יש user_cache ב-session state, אם לא - בניית cache
    if 'user_lookup_cache' not in st.session_state:
        with st.spinner("טוען מידע משתמשים..."):
            usernames = [doc.get('userName', '') for doc in documents if doc.get('userName')]
            st.session_state.user_lookup_cache = build_user_lookup_cache(api, usernames)

    user_cache = st.session_state.user_lookup_cache

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

    # מיון לפי מספר עמודים (סדר יורד)
    top_users = sorted(user_stats.items(), key=lambda x: x[1]['pages'], reverse=True)[:10]

    # יצירת טבלה עם שם מלא
    user_df = pd.DataFrame([
        {
            'שם מלא': user_cache.get(user, user),
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
            if port not in port_stats:
                port_stats[port] = {'docs': 0, 'pages': 0}
            port_stats[port]['docs'] += 1
            port_stats[port]['pages'] += doc.get('totalPages', 0)

    if port_stats:
        # מיון לפי מספר עמודים (סדר יורד)
        top_ports = sorted(port_stats.items(), key=lambda x: x[1]['pages'], reverse=True)[:10]

        port_df = pd.DataFrame([
            {'מדפסת': port, 'מסמכים': stats['docs'], 'עמודים': stats['pages']}
            for port, stats in top_ports
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
        # מיון לפי מספר עמודים (סדר יורד)
        dept_df = pd.DataFrame([
            {
                'מחלקה': dept,
                'מסמכים': stats['docs'],
                'עמודים': stats['pages']
            }
            for dept, stats in sorted(dept_stats.items(), key=lambda x: x[1]['pages'], reverse=True)
        ])

        st.dataframe(dept_df, use_container_width=True, hide_index=True)
    else:
        st.info("ℹ️ אין מידע על מחלקות בנתונים")


def prepare_history_dataframe(documents: List[Dict], user_cache: Dict[str, str] = None) -> pd.DataFrame:
    """
    המרת נתוני היסטוריה ל-DataFrame

    Args:
        documents: רשימת מסמכים מה-API
        user_cache: dict של {username: fullName} (אופציונלי)

    Returns:
        pd.DataFrame
    """
    rows = []

    if user_cache is None:
        user_cache = {}

    for doc in documents:
        # המרת timestamp ל-datetime בשעון ישראל
        timestamp = doc.get('dateTime', 0)
        if timestamp:
            # המרה מ-UTC לשעון ישראל (מטפל אוטומטית בשעון חורף/קיץ)
            utc_dt = datetime.fromtimestamp(timestamp / 1000, tz=pytz.UTC)
            israel_tz = pytz.timezone('Asia/Jerusalem')
            israel_dt = utc_dt.astimezone(israel_tz)
            date_str = israel_dt.strftime('%d/%m/%Y %H:%M:%S')  # פורמט dd/mm/yyyy
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

        # תרגום סוג עבודה לעברית
        job_type_en = doc.get('jobType', '')
        job_type_map = {
            'PRINT': 'הדפסה',
            'COPY': 'העתקה',
            'SCAN': 'סריקה',
            'FAX': 'פקס'
        }
        job_type_he = job_type_map.get(job_type_en, job_type_en)

        # הפרדת מחלקות מתגיות אחרות
        tags = doc.get('tags', [])
        departments = [tag.get('name', '') for tag in tags if tag.get('tagType') == 0]

        department_str = ', '.join(departments) if departments else ''

        # זיהוי מקור לפי username (אם יש @ זה Entra, אם לא Local)
        username = doc.get('userName', '')
        source = 'Entra' if '@' in username else 'מקומי'

        # חיפוש שם מלא - קודם ב-cache, אחר כך בשדות המסמך
        full_name = user_cache.get(username, '')

        if not full_name:
            # נסיון למצוא שם מלא במסמך עצמו (למקרה שיש)
            full_name = (
                doc.get('fullName', '') or
                doc.get('userFullName', '') or
                doc.get('displayName', '') or
                doc.get('name', '') or
                ''
            )

        # אם עדיין אין שם מלא, השתמש ב-username
        display_name = full_name.strip() if full_name else username

        row = {
            'תאריך': date_str,
            'שם מלא': display_name,
            'משתמש': username,
            'סוג משתמש': source,
            'מחלקה': department_str,
        #'שם מסמך': doc.get('documentName', ''),
            'סוג': job_type_he,  # תרגום לעברית
            'סטטוס': status,
            'עמודים': doc.get('totalPages', 0),
            'צבע': doc.get('colorPages', 0),
            'עותקים': doc.get('copies', 1),
            'דופלקס': 'כן' if doc.get('duplex') else 'לא',
            'מדפסת': doc.get('outputPortName', ''),
            'גודל נייר': doc.get('paperSize', '')
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
