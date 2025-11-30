#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SafeQ Cloud Manager - Users Overview Page
דף סקירה - ניהול משתמשים
"""

import streamlit as st

def create_overview_page(users_list_page, users_search_page, users_add_page, users_groups_page):
    """יוצר את דף הסקירה עם גישה לאובייקטי Page"""

    def show():
        """הצגת דף סקירה לניהול משתמשים"""

        # CSS לכפתורים - מעוצבים בדיוק כמו home
        st.markdown("""
        <style>
            /* ביטול עיצוב DIV החיצוני - מונע "ריבוע בתוך ריבוע" */
            div[data-testid="stPageLink"] {
               padding: 0.0rem 0.0rem !important;
               margin: 0 !important;
               border:none ;
               transition: none !important;
               background: none;
               width:90% !important;
            }
            div[data-testid="stPageLink"]:hover {
               padding: 0.0rem 0.0rem !important;
               margin: 0 !important;
               border: none !important ;
               transition: none !important;
               background: none;
               box-shadow:none;
            }
            .stPageLink {
            background: none !important;
            }
            .stPageLink:hover {
                background: none !important;
                transform: none;
                box-shadow: none !important;
                border:none;
            }

            /* כפתורי st.page_link - מעוצבים בדיוק כמו st.button */
            a[data-testid="stPageLink-NavLink"] {
                background: linear-gradient(45deg, #D71F27, #FF6B6B) !important;
                color: white !important;
                padding: 0.3rem 0.4rem !important;
                border-radius: 0.9rem !important;
                font-weight: 600 !important;
                border: none !important;
                text-decoration: none !important;
                display: inline-block !important;
                width: 100% !important;
                box-sizing: border-box !important;
                text-align: -webkit-center !important;
                line-height: 1.5 !important;
            }
            a[data-testid="stPageLink-NavLink"]:hover {
                opacity: 0.9 !important;
                color: white;
                transform: translateY(-1px);
                transition: all 0.3s ease;
                background: linear-gradient(45deg, #FF6B6B, #D71F27 ) !important;
                box-shadow: 0 4px 8px rgba(0,0,0,0.2) !important;
            }

             /* הסתרת כל ה-span container שמכיל את האימוג'י - כך המקום ממש משתחרר */
            a[data-testid="stPageLink-NavLink"] > span:first-child {
                display: none !important;
            }

            /* וידוא שהטקסט בתוך page_link לבן */
            a[data-testid="stPageLink-NavLink"] span,
            a[data-testid="stPageLink-NavLink"] p {
                color: white !important;
            }

            /* כפתור מנועל - נראה כמו page_link אבל מעומעם */
            .disabled-page-link {
                background: linear-gradient(45deg, #999, #bbb) !important;
                color: white !important;
                padding: 0.3rem 0.4rem !important;
                border-radius: 0.9rem !important;
                font-weight: 600 !important;
                border: none !important;
                text-decoration: none !important;
                display: inline-block !important;
                width: 90% !important;
                box-sizing: border-box !important;
                text-align: center !important;
                line-height: 1.5 !important;
                cursor: not-allowed !important;
                opacity: 0.6 !important;
            }
        </style>
        """, unsafe_allow_html=True)

        st.header("👥 ניהול משתמשים")
        st.caption("בחר פעולה מהאפשרויות למטה")

        st.markdown("---")

        # בדיקת הרשאות לרשימת משתמשים
        role = st.session_state.get('role', st.session_state.get('access_level', 'viewer'))
        local_username = st.session_state.get('local_username', None)
        can_view_user_list = (role == 'superadmin') or (role == 'admin' and local_username)

        # כרטיסים לניווט
        col1, col2 = st.columns(2)

        with col1:
            # כרטיס 1: רשימת משתמשים - תלוי בהרשאות
            with st.container():
                st.subheader("📋 רשימת משתמשים")
                if can_view_user_list:
                    st.markdown("""
                    צפייה בכל המשתמשים במערכת, סינון לפי מקור (מקומי/Entra),
                    וייצוא לאקסל.

                    **תכונות:**
                    - צפייה במשתמשים מקומיים
                    - צפייה במשתמשי Entra (superadmin)
                    - סינון לפי מחלקות
                    - ייצוא Excel
                    """)
                    st.page_link(users_list_page, label="📋➡️ עבור לרשימת משתמשים", use_container_width=True)
                else:
                    st.markdown("""
                    צפייה בכל המשתמשים במערכת, סינון לפי מקור (מקומי/Entra),
                    וייצוא לאקסל.

                    **🔒 זמין רק עבור הרשאות SuperAdmin**
                    - תכונה מוגבלת למנהלי מערכת
                    - נדרשות הרשאות מנהל על
                    - פנה למנהל המערכת לקבלת גישה
                    """)
                    st.markdown('<div class="disabled-page-link">🔒 זמין רק ל-SuperAdmin</div>', unsafe_allow_html=True)

            st.markdown("---")

            # כרטיס 2: הוספת משתמש
            with st.container():
                st.subheader("➕ הוספת משתמש")
                st.markdown("""
                יצירת משתמש חדש במערכת SafeQ Cloud.

                **תכונות:**
                - טופס יצירת משתמש
                - הגדרת פרטים אישיים
                - קוד PIN
                - הרשאות ומחלקות
                """)
                st.page_link(users_add_page, label="➕➡️ עבור להוספת משתמש", use_container_width=True)

        with col2:
            # כרטיס 3: חיפוש ועריכה
            with st.container():
                st.subheader("🔍 חיפוש ועריכה")
                st.markdown("""
                חיפוש מתקדם ועריכת פרטי משתמשים קיימים.

                **תכונות:**
                - חיפוש לפי שם, אימייל, מחלקה
                - התאמה חלקית או מדויקת
                - עריכת פרטי משתמש
                - מחיקת משתמש (admin)
                """)
                st.page_link(users_search_page, label="🔍➡️ עבור לחיפוש ועריכה", use_container_width=True)

            st.markdown("---")

            # כרטיס 4: קבוצות
            with st.container():
                st.subheader("👨‍👩‍👧‍👦 קבוצות")
                st.markdown("""
                ניהול קבוצות משתמשים במערכת.

                **תכונות:**
                - רשימת קבוצות
                - יצירת קבוצה חדשה
                - הוספת/הסרת משתמשים
                - הגדרות הרשאות
                """)
                st.page_link(users_groups_page, label="👨‍👩‍👧‍👦➡️ עבור לניהול קבוצות", use_container_width=True)

        st.markdown("---")

        # טיפים
        st.info("""
        💡 **טיפ:** לחץ על אחד מהכפתורים למעלה, או השתמש בתפריט הימני (צד ימין) כדי לנווט בין המודולים השונים.
        """)

    return st.Page(show, title="סקירה", icon="👥", url_path="users_overview")

if __name__ == "__main__":
    st.info("This page requires Page objects from main.py")
