"""
SafeQ Manager - Hybrid Authentication & Permissions
מיפוי בין משתמשי Entra ID למשתמשים לוקאליים ב-SafeQ
"""

import re
from typing import Dict, List, Optional
import streamlit as st


def get_entra_username(user_info: dict) -> str:
    """
    חילוץ username מתוך user_info מ-Entra ID

    Args:
        user_info: מידע משתמש מ-Microsoft Graph API

    Returns:
        str: Username מלא (כולל @domain.com)
    """
    return user_info.get('userPrincipalName') or user_info.get('mail') or ''


def get_entra_user_role(user_groups: list, role_mapping: dict) -> Optional[str]:
    """
    קביעת role לפי קבוצות Entra ID

    Args:
        user_groups: רשימת קבוצות משתמש מ-Entra
        role_mapping: מיפוי של שמות קבוצות ל-roles (מ-config)

    Returns:
        str: role (viewer/support/admin/superadmin) או None
    """
    # עדיפות: SuperAdmin > Admin > Support > View
    priority_order = ['SafeQ-SuperAdmin', 'SafeQ-Admin', 'SafeQ-Support', 'SafeQ-View']

    user_group_names = [g.get('displayName', '') for g in user_groups]

    for group_name in priority_order:
        if group_name in user_group_names:
            return role_mapping.get(group_name)

    return None


def fetch_local_user(api, username: str, provider_id: int) -> Optional[dict]:
    """
    חיפוש משתמש לוקאלי ב-SafeQ

    Args:
        api: SafeQAPI instance
        username: שם משתמש לחיפוש (Entra username)
        provider_id: מזהה ספק (12348 ל-Local)

    Returns:
        dict: נתוני משתמש או None אם לא נמצא
    """
    try:
        return api.search_user(username, provider_id=provider_id)
    except Exception as e:
        st.warning(f"שגיאה בחיפוש משתמש לוקאלי: {str(e)}")
        return None


def fetch_local_user_groups(api, username: str) -> list:
    """
    קבלת קבוצות לוקאליות של משתמש מ-SafeQ

    Args:
        api: SafeQAPI instance
        username: שם משתמש

    Returns:
        list: רשימת קבוצות
    """
    try:
        return api.get_user_groups(username)
    except Exception as e:
        st.warning(f"שגיאה בקבלת קבוצות משתמש: {str(e)}")
        return []


def extract_departments_from_groups(groups_list: list) -> list:
    """
    חילוץ שמות מחלקות מלאים מרשימת קבוצות

    פורמט קבוצות: "צפת - 240234", "עלי זהב - 234768", וכו'
    (עם רווחים סביב המקף)
    מחזיר: שמות מלאים של מחלקות בפורמט הנכון

    Args:
        groups_list: רשימת קבוצות (dict או string)

    Returns:
        list: רשימת שמות מחלקות מלאים ייחודיים (["צפת - 240234", "עלי זהב - 234768"])
    """
    departments = []
    # Pattern: כל קבוצה שמסתיימת במקף ומספר (בפורמט המחלקה)
    # תומך ב: "צפת - 240234" או "צפת-240234" או "צפת -240234"
    pattern = re.compile(r'-\s*(\d+)$')

    for group in groups_list:
        # קבוצה יכולה להיות dict או string
        if isinstance(group, dict):
            group_name = group.get('groupName') or group.get('name') or ''
        else:
            group_name = str(group)

        # בדוק אם הקבוצה בפורמט הנכון (מסתיימת במספר)
        match = pattern.search(group_name)
        if match and group_name not in departments:
            departments.append(group_name)

    return departments


def initialize_user_permissions(api, user_info: dict, entra_groups: list, config: dict) -> dict:
    """
    הפונקציה המרכזית - אתחול הרשאות משתמש (Hybrid Authentication)

    תהליך:
    1. חילוץ username מ-Entra
    2. קביעת role מקבוצות Entra
    3. חיפוש local user ב-SafeQ
    4. טעינת קבוצות לוקאליות
    5. חילוץ departments מהקבוצות

    Args:
        api: SafeQAPI instance
        user_info: מידע משתמש מ-Entra
        entra_groups: קבוצות Entra של המשתמש
        config: הגדרות מ-config.py

    Returns:
        dict: {
            'success': bool,
            'error_message': str,
            'entra_username': str,
            'local_username': str or None,
            'role': str,
            'local_groups': list,
            'allowed_departments': list
        }
    """
    result = {
        'success': False,
        'error_message': '',
        'entra_username': '',
        'local_username': None,
        'role': '',
        'local_groups': [],
        'allowed_departments': []
    }

    try:
        # 1. חילוץ username מ-Entra
        entra_username = get_entra_username(user_info)
        if not entra_username:
            result['error_message'] = "לא ניתן לחלץ שם משתמש מ-Entra ID"
            return result

        result['entra_username'] = entra_username

        # 2. קביעת role מקבוצות Entra
        role_mapping = config['ACCESS_CONTROL']['ROLE_MAPPING']
        role = get_entra_user_role(entra_groups, role_mapping)

        if not role:
            result['error_message'] = "לא נמצאה קבוצת הרשאות מתאימה ב-Entra ID (SafeQ-View/Support/Admin/SuperAdmin)"
            return result

        result['role'] = role

        # 3. חיפוש local user ב-SafeQ (Provider ID 12348)
        local_provider_id = config['PROVIDERS']['LOCAL']
        local_user = fetch_local_user(api, entra_username, local_provider_id)

        if not local_user:
            result['error_message'] = (
                "לא נמצא משתמש לוקאלי תואם במערכת SafeQ.\n\n"
                "אנא פנה לספק המערכת לצורך בירור נוסף."
            )
            return result

        result['local_username'] = local_user.get('userName') or local_user.get('username')

        # 4. טעינת קבוצות לוקאליות
        local_groups = fetch_local_user_groups(api, result['local_username'])
        result['local_groups'] = local_groups

        # 5. חילוץ departments
        if role == 'superadmin':
            # SuperAdmin מקבל גישה לכל המחלקות
            result['allowed_departments'] = ["ALL"]
        else:
            # שאר המשתמשים: חלץ departments מהקבוצות
            departments = extract_departments_from_groups(local_groups)

            if not departments:
                # לא נמצאו departments - ייתכן שהמשתמש לא משויך לאף בית ספר
                result['error_message'] = (
                    "לא נמצאו הרשאות מחלקה עבור משתמש זה.\n\n"
                    "המשתמש לא משויך לאף בית ספר. אנא פנה לספק המערכת."
                )
                return result

            result['allowed_departments'] = departments

        result['success'] = True
        return result

    except Exception as e:
        result['error_message'] = f"שגיאה באתחול הרשאות: {str(e)}"
        return result


def filter_users_by_departments(users: list, allowed_departments: list) -> list:
    """
    סינון רשימת משתמשים לפי מחלקות מורשות

    Args:
        users: רשימת משתמשים
        allowed_departments: רשימת שמות מחלקות מלאים (["צפת - 240234", ...]) או ["ALL"]

    Returns:
        list: רשימה מסוננת של משתמשים
    """
    if not users:
        return []

    # SuperAdmin רואה הכל
    if allowed_departments == ["ALL"]:
        return users

    filtered_users = []

    for user in users:
        # חילוץ department מהמשתמש
        user_dept = user.get('department', '')

        # אם אין department בשדה הראשי, נסה לחלץ מ-details
        if not user_dept:
            for detail in user.get('details', []):
                if isinstance(detail, dict) and detail.get('detailType') == 11:
                    user_dept = detail.get('detailData', '')
                    break

        # אם עדיין אין department, דלג על המשתמש
        if not user_dept:
            continue

        # השוואה ישירה של שמות מחלקות
        if user_dept in allowed_departments:
            filtered_users.append(user)

    return filtered_users


def filter_groups_by_departments(groups: list, allowed_departments: list) -> list:
    """
    סינון רשימת קבוצות לפי מחלקות מורשות
    מסנן גם את "Local Users" (אלא אם SuperAdmin)

    Args:
        groups: רשימת קבוצות
        allowed_departments: רשימת שמות מחלקות מלאים (["צפת - 240234", ...]) או ["ALL"]

    Returns:
        list: רשימה מסוננת של קבוצות
    """
    if not groups:
        return []

    is_superadmin = allowed_departments == ["ALL"]
    filtered_groups = []

    for group in groups:
        group_name = group.get('groupName') or group.get('name') or str(group)

        # סינון "Local Users" (אלא אם SuperAdmin)
        if not is_superadmin and group_name == "Local Users":
            continue

        # SuperAdmin רואה הכל
        if is_superadmin:
            filtered_groups.append(group)
            continue

        # עבור משתמשים רגילים: השוואה ישירה של שמות קבוצות
        if group_name in allowed_departments:
            filtered_groups.append(group)

    return filtered_groups


def get_department_options(allowed_departments: list, local_groups: list) -> list:
    """
    קבלת רשימת אפשרויות מחלקה לשדה department בטופס יצירת משתמש
    מחזיר שמות מלאים בפורמט: "צפת - 240234"

    Args:
        allowed_departments: רשימת שמות מחלקות מלאים (["צפת - 240234", ...]) או ["ALL"]
        local_groups: קבוצות לוקאליות של המשתמש

    Returns:
        list: רשימת שמות מחלקות מלאים ["צפת - 240234", "עלי זהב - 234768"]
    """
    if allowed_departments == ["ALL"]:
        return []  # SuperAdmin יכול להזין כל מחלקה

    # פשוט מחזיר את allowed_departments (שהם כבר השמות המלאים מהקבוצות)
    return allowed_departments


def authenticate_local_cloud_user(api, username: str, card_id: str, config: dict) -> dict:
    """
    אימות משתמש מקומי מול הענן - לגישה לדוחות בלבד

    תהליך:
    1. בדוק אם המשתמש קיים בענן (SafeQ Cloud)
    2. בדוק אם Card ID תואם
    3. בדוק אם שייך לקבוצה "Reports-View"
    4. שלוף את הקבוצות שלו (בתי הספר)
    5. מפה קבוצות → departments
    6. החזר role + allowed_departments

    Args:
        api: SafeQAPI instance
        username: שם משתמש מקומי
        card_id: מזהה כרטיס (משמש כסיסמה)
        config: הגדרות מ-config.py

    Returns:
        dict: {
            'success': bool,
            'error_message': str,
            'role': str ('school_manager' או None),
            'allowed_departments': list,
            'user_groups': list
        }
    """
    result = {
        'success': False,
        'error_message': '',
        'role': None,
        'allowed_departments': [],
        'user_groups': []
    }

    try:
        # קבלת provider_id עבור משתמשים מקומיים
        local_provider_id = config.get('PROVIDERS', {}).get('LOCAL', 12348)

        # 1. בדוק אם המשתמש קיים בענן
        cloud_user = api.get_single_user(username, provider_id=local_provider_id)

        if not cloud_user:
            result['error_message'] = (
                f"❌ המשתמש '{username}' לא נמצא במערכת הענן.\n\n"
                "רק משתמשים שקיימים בענן יכולים להתחבר."
            )
            return result

        # 2. בדוק Card ID (משמש כסיסמה)
        # Card ID נמצא במערך cards (לוקחים את הראשון)
        cards = cloud_user.get('cards', [])
        user_card_id = cards[0] if cards else ""

        if not user_card_id:
            result['error_message'] = (
                f"❌ למשתמש '{username}' אין מזהה כרטיס מוגדר במערכת.\n\n"
                "נדרש להגדיר מזהה כרטיס במערכת SafeQ לצורך התחברות."
            )
            return result

        if user_card_id != card_id:
            result['error_message'] = (
                "❌ מזהה כרטיס שגוי.\n\n"
                "אנא וודא שהזנת את מזהה הכרטיס הנכון."
            )
            return result

        # 3. שלוף קבוצות
        user_groups = api.get_user_groups(username)

        if not user_groups:
            result['error_message'] = (
                f"❌ המשתמש '{username}' לא משויך לאף קבוצה.\n\n"
                "נדרשת שיוך לקבוצה 'Reports-View' לצורך גישה למערכת."
            )
            return result

        result['user_groups'] = user_groups

        # 4. בדוק אם שייך ל-"Reports-View"
        reports_view_group = config.get('REPORTS_VIEW_GROUP', 'Reports-View')
        group_names = [g.get('groupName') or g.get('name') or str(g) for g in user_groups]

        if reports_view_group not in group_names:
            result['error_message'] = (
                f"❌ אין לך הרשאה לגשת למערכת.\n\n"
                f"נדרשת שיוך לקבוצה '{reports_view_group}'.\n"
                f"הקבוצות שלך: {', '.join(group_names)}"
            )
            return result

        # 5. חלץ departments מהקבוצות (מחלקות = קבוצות)
        departments = extract_departments_from_groups(user_groups)

        if not departments:
            result['error_message'] = (
                "❌ לא נמצאו בתי ספר משוייכים למשתמש זה.\n\n"
                "המשתמש צריך להיות משויך לפחות לקבוצת בית ספר אחת.\n"
                "פורמט: 'שם בית ספר - מספר' (לדוגמא: 'צפת - 240324')"
            )
            return result

        # 6. הצלחה!
        result['success'] = True
        result['role'] = 'school_manager'
        result['allowed_departments'] = departments

        return result

    except Exception as e:
        result['error_message'] = f"❌ שגיאה באימות משתמש: {str(e)}"
        return result
