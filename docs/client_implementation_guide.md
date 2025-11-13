# מדריך יישום - SafeQ Cloud Manager
## מסמך טכני מפורט ללקוח

**תאריך:** 2025-11-13
**גרסה:** 2.0
**נושא:** מערכת ניהול SafeQ Cloud עם מערכת הרשאות היברידית

---

## תוכן עניינים

1. [סקירה כללית](#סקירה-כללית)
2. [פלטפורמת Streamlit Cloud - אבטחה ופריסה](#פלטפורמת-streamlit-cloud)
3. [ארכיטקטורה ומבנה מערכת](#ארכיטקטורה-ומבנה-מערכת)
4. [סוגי משתמשים ושיטות אימות](#סוגי-משתמשים-ושיטות-אימות)
5. [רמות הרשאה ויכולות](#רמות-הרשאה-ויכולות)
6. [הכנות בצד הלקוח - Microsoft Entra ID](#הכנות-בצד-הלקוח)
7. [ניהול דוחות עם סינון מחלקתי](#ניהול-דוחות-עם-סינון-מחלקתי)
8. [אבטחת מידע וניהול Secrets](#אבטחת-מידע-וניהול-secrets)
9. [תהליך התקנה ופריסה](#תהליך-התקנה-ופריסה)
10. [שאלות ותשובות](#שאלות-ותשובות)

---

## 1. סקירה כללית

### מה זה SafeQ Cloud Manager?

SafeQ Cloud Manager הוא ממשק ניהול מבוסס-web לניהול מערכת YSoft SafeQ Cloud. המערכת מספקת:

- ✅ **ניהול משתמשים** - צפייה, יצירה, עריכה ומחיקה
- ✅ **ניהול קבוצות** - הוספה והסרה של משתמשים מקבוצות
- ✅ **דוחות מתקדמים** - דוחות הדפסות וצילומים עם סינון חכם
- ✅ **מערכת הרשאות היברידית** - שילוב Entra ID ואימות מקומי
- ✅ **Audit Log** - רישום מלא של כל הפעולות במערכת
- ✅ **סינון מחלקתי** - הגבלת גישה לפי בתי ספר/מחלקות

### טכנולוגיות בשימוש

| רכיב | טכנולוגיה |
|------|-----------|
| **Backend Framework** | Python 3.9+ |
| **Web Framework** | Streamlit 1.28+ |
| **Platform** | Streamlit Cloud (AWS) |
| **אימות** | Microsoft Entra ID (OAuth 2.0) + Local Auth |
| **API** | SafeQ Cloud REST API |
| **אחסון** | SQLite (Audit Log) |

---

## 2. פלטפורמת Streamlit Cloud - אבטחה ופריסה

### 2.1 מהי Streamlit Cloud?

**Streamlit Cloud** היא פלטפורמה מנוהלת (PaaS) המיועדת לאירוח אפליקציות Python/Streamlit.

#### מאפיינים עיקריים:
- 🌐 **אירוח ב-AWS** - תשתית ענן מאובטחת של Amazon Web Services
- 🔄 **Deploy אוטומטי** - חיבור ישיר ל-GitHub, כל push מעלה גרסה חדשה
- 🔒 **HTTPS מובנה** - כל התעבורה מוצפנת באופן אוטומטי
- 📦 **חינמי לשימוש ציבורי** או בתשלום לאפליקציות פרטיות
- 🚀 **Zero DevOps** - אין צורך בניהול שרתים, DB, או תשתיות

### 2.2 רמת אבטחה - מה זה אומר ללקוח?

#### ✅ יתרונות אבטחה:

1. **הפרדת קוד מסודות (Secrets)**
   - הקוד באפליקציה **לא מכיל** סיסמאות, מפתחות API, או נתונים רגישים
   - כל המידע הרגיש נמצא ב**Secrets Management** של Streamlit Cloud
   - Secrets מוצפנים בשרתי Streamlit ו**לא נחשפים** בקוד או ב-GitHub

2. **אימות דו-שלבי (Entra ID + SafeQ)**
   - המערכת דורשת אימות מול **Microsoft Entra ID** (רמת אבטחה ארגונית)
   - בנוסף, המשתמש חייב להיות **קיים גם ב-SafeQ Cloud** (אימות כפול)
   - אין אפשרות לגישה ללא שני השלבים

3. **הצפנת תעבורה**
   - כל התקשורת דרך **HTTPS מוצפן (TLS 1.3)**
   - Streamlit Cloud מספק תעודת SSL/TLS אוטומטית

4. **Audit Log מלא**
   - כל פעולה במערכת נרשמת עם:
     - מי ביצע (username + email)
     - מתי (timestamp)
     - מה בוצע (action + details)
     - האם הצליח (success/failed)

#### ⚠️ שיקולים חשובים:

1. **חשיפת קוד בגיטהאב**
   - הקוד **חשוף** ב-GitHub אם ה-repository הוא **public**
   - **המלצה:** להפוך את הrepository ל-**Private** (דורש חשבון GitHub בתשלום)
   - **חשוב:** גם אם הקוד חשוף, אין בו מידע רגיש - כל ה-Secrets נמצאים במנגנון נפרד

2. **גישה ל-Secrets**
   - רק **בעלי הזכויות באפליקציה** ב-Streamlit Cloud יכולים לראות/לערוך Secrets
   - הלקוח **לא** יכול לנהל את ה-Secrets ישירות - זה דורש גישה ל-Streamlit Cloud Account

### 2.3 אפשרויות פריסה חלופיות (אם הלקוח לא רוצה Streamlit Cloud)

אם הלקוח דורש **שליטה מלאה** על התשתית והסודות:

| אפשרות | יתרונות | חסרונות | עלות |
|--------|---------|----------|------|
| **Streamlit Cloud (Private)** | ללא DevOps, אבטחה מובנית, Secrets מנוהלים | Secrets מנוהלים ע"י Streamlit | ~$20/חודש |
| **Docker + AWS/Azure** | שליטה מלאה, Secrets מנוהלים ע"י הלקוח | דורש DevOps, תחזוקה שוטפת | ~$50-200/חודש |
| **On-Premise (שרת פנימי)** | שליטה מוחלטת, ללא תלות חיצונית | דורש תשתית פיזית, תחזוקה, עדכוני אבטחה | עלות תשתית + משאבי IT |

**המלצתנו:** Streamlit Cloud (Private) - מאוזן בין אבטחה, נוחות ועלות.

---

## 3. ארכיטקטורה ומבנה מערכת

### 3.1 תרשים ארכיטקטורה

```
┌─────────────────────────────────────────────────────────────────┐
│                         משתמש קצה (Browser)                      │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS (TLS 1.3)
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Streamlit Cloud (AWS)                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              SafeQ Cloud Manager App                      │  │
│  │                                                            │  │
│  │  ┌──────────────┐    ┌──────────────┐    ┌────────────┐ │  │
│  │  │ Auth Module  │    │ Permissions  │    │  Reports   │ │  │
│  │  │ (Entra ID +  │◄───┤   Module     │◄───┤   Module   │ │  │
│  │  │  Local Auth) │    │              │    │            │ │  │
│  │  └──────┬───────┘    └──────┬───────┘    └─────┬──────┘ │  │
│  │         │                    │                   │        │  │
│  │         └────────────────────┴───────────────────┘        │  │
│  │                              ↓                             │  │
│  │                    ┌──────────────────┐                   │  │
│  │                    │  SafeQ API       │                   │  │
│  │                    │  Client          │                   │  │
│  │                    └────────┬─────────┘                   │  │
│  └─────────────────────────────┼──────────────────────────────┘  │
│                                │                                 │
│  ┌─────────────────────────────┼──────────────────────────────┐ │
│  │          Secrets Management (Encrypted)                    │ │
│  │  • API Keys  • Entra ID Credentials  • Emergency Users   │ │
│  └────────────────────────────────────────────────────────────┘ │
└────────────────────────────┬────────────────────────────────────┘
                             │ API Calls (HTTPS)
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│               YSoft SafeQ Cloud API (Customer)                   │
│  • Users Management  • Groups  • Documents History              │
└─────────────────────────────────────────────────────────────────┘
                             ↑
                             │
┌────────────────────────────┴────────────────────────────────────┐
│                    Microsoft Entra ID                            │
│  • User Authentication  • Groups & Roles                         │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 רכיבי המערכת

#### 3.2.1 Authentication Module
**תפקיד:** ניהול כניסת משתמשים למערכת

**שיטות אימות:**
1. **Entra ID (OAuth 2.0)** - אימות עם Microsoft (SSO)
2. **Local Authentication** - אימות מקומי עם username + Card ID/password

#### 3.2.2 Permissions Module
**תפקיד:** ניהול הרשאות והגבלות גישה

**פונקציות:**
- קביעת role לפי קבוצות Entra/Local
- חילוץ departments מקבוצות SafeQ
- סינון משתמשים/קבוצות/דוחות לפי allowed_departments

#### 3.2.3 SafeQ API Client
**תפקיד:** תקשורת עם SafeQ Cloud API

**פעולות:**
- CRUD משתמשים (Create, Read, Update, Delete)
- ניהול קבוצות (הוספה/הסרה של משתמשים)
- שליפת דוחות (Documents History)

---

## 4. סוגי משתמשים ושיטות אימות

המערכת תומכת ב-**3 סוגי משתמשים**:

### 4.1 משתמשי Entra ID (SSO)

#### תהליך אימות:
```
1. משתמש לוחץ "התחבר עם Entra ID"
   ↓
2. מועבר ל-Microsoft Login Page
   ↓
3. מזין username + password (של הארגון)
   ↓
4. Microsoft מאמת ומחזיר אסימון (Token)
   ↓
5. המערכת מקבלת: username, email, קבוצות Entra
   ↓
6. בדיקה: האם שייך לקבוצה SafeQ-View/Support/Admin/SuperAdmin?
   ├─ לא → גישה נדחית ❌
   └─ כן → ממשיך ↓
7. חיפוש משתמש תואם ב-SafeQ Cloud (Provider 12348 - Local)
   ├─ לא נמצא → גישה נדחית ❌
   └─ נמצא → ממשיך ↓
8. שליפת קבוצות מקומיות מ-SafeQ
   ↓
9. חילוץ departments (בתי ספר) מהקבוצות
   ↓
10. קביעת allowed_departments
    ├─ SuperAdmin → ["ALL"]
    └─ View/Support/Admin → רשימת בתי ספר
   ↓
11. ✅ כניסה מוצלחת!
```

#### דרישות:
- ✅ קיום חשבון ב-Microsoft Entra ID
- ✅ שייכות לקבוצה: `SafeQ-View`, `SafeQ-Support`, `SafeQ-Admin`, או `SafeQ-SuperAdmin`
- ✅ משתמש תואם ב-SafeQ Cloud (Provider Local - 12348)
- ✅ שייכות לקבוצות מחלקה ב-SafeQ (אלא אם כן SuperAdmin)

---

### 4.2 משתמשי חירום (Emergency Users)

#### תהליך אימות:
```
1. משתמש לוחץ "התחברות מנהל מקומי"
   ↓
2. מזין username + password
   ↓
3. המערכת בודקת מול secrets.toml → [EMERGENCY_USERS]
   ├─ לא תואם → גישה נדחית ❌
   └─ תואם → ממשיך ↓
4. ✅ כניסה מוצלחת כ-SuperAdmin!
   • allowed_departments = ["ALL"]
   • גישה מלאה למערכת
```

#### מאפיינים:
- 🔴 **SuperAdmin בלבד** - גישה מלאה ללא הגבלות
- 🔒 **אימות מקומי** - לא תלוי ב-SafeQ Cloud או Entra ID
- 🚨 **לשימוש חירום** - כשמערכות חיצוניות לא פועלות
- 📝 **מוגדר ב-Secrets** - `[EMERGENCY_USERS]` בקובץ secrets.toml

#### דוגמה:
```toml
[EMERGENCY_USERS]
admin = "SecurePassword123!"
backup = "BackupPass456!"
```

---

### 4.3 School Managers (מנהלי בתי ספר)

#### תהליך אימות:
```
1. משתמש לוחץ "התחברות מנהל מקומי"
   ↓
2. מזין username + password
   ↓
3. המערכת בודקת האם זה Emergency User?
   ├─ כן → כניסה כ-SuperAdmin
   └─ לא → ממשיך לאימות מול SafeQ Cloud ↓
4. חיפוש משתמש ב-SafeQ Cloud (Provider 12348)
   ├─ לא נמצא → גישה נדחית ❌
   └─ נמצא → ממשיך ↓
5. בדיקת Card ID (Password) מול SafeQ
   ├─ לא תואם → גישה נדחית ❌
   └─ תואם → ממשיך ↓
6. שליפת קבוצות המשתמש מ-SafeQ
   ↓
7. בדיקה: האם שייך לקבוצה "Reports-View"?
   ├─ לא → גישה נדחית ❌
   └─ כן → ממשיך ↓
8. חילוץ בתי ספר מהקבוצות (פורמט: "שם - מספר")
   ├─ לא נמצאו → גישה נדחית ❌
   └─ נמצאו → ממשיך ↓
9. ✅ כניסה מוצלחת כ-School Manager!
   • Role: school_manager
   • Allowed_departments: רשימת בתי ספר
   • גישה: רק דוחות (Reports)
```

#### מאפיינים:
- 🏫 **גישה לדוחות בלבד** - לא יכול לנהל משתמשים/קבוצות
- 🔍 **סינון אוטומטי** - רואה רק דוחות של בתי הספר שלו
- 🔑 **אימות מול SafeQ** - שימוש ב-Card ID כסיסמא
- 👥 **דורש קבוצות** - חייב להיות ב-"Reports-View" + קבוצות בתי ספר

#### דרישות:
- ✅ משתמש קיים ב-SafeQ Cloud (Provider 12348)
- ✅ Card ID מוגדר ב-SafeQ (שדה cards)
- ✅ שייכות לקבוצה `Reports-View`
- ✅ שייכות לקבוצת בית ספר (פורמט: "צפת - 240234")

---

## 5. רמות הרשאה ויכולות

### 5.1 טבלת השוואה

| תכונה / פעולה | Viewer | Support | Admin | SuperAdmin | School Manager |
|---------------|--------|---------|-------|------------|----------------|
| **גישה למערכת** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **צפייה במשתמשים** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **צפייה בקבוצות** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **עריכת משתמשים** | ❌ | ✅ | ✅ | ✅ | ❌ |
| **יצירת משתמשים** | ❌ | ✅ | ✅ | ✅ | ❌ |
| **מחיקת משתמשים** | ❌ | ❌ | ✅ | ✅ | ❌ |
| **הוספה/הסרה מקבוצות** | ❌ | ✅ | ✅ | ✅ | ❌ |
| **פעולות Bulk** | ❌ | ❌ | ✅ | ✅ | ❌ |
| **גישה לכל המחלקות** | ❌ | ❌ | ❌ | ✅ | ❌ |
| **גישה למחלקות מוגבלות** | ✅ | ✅ | ✅ | - | ✅ |
| **צפייה בדוחות** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **סינון דוחות אוטומטי** | ✅ | ✅ | ✅ | ❌ | ✅ |
| **Audit Log** | ✅ | ✅ | ✅ | ✅ | ✅ |

### 5.2 פירוט מפורט לכל רמה

#### 🔵 Viewer (צופה)
**קבוצת Entra ID:** `SafeQ-View`

**יכולות:**
- ✅ צפייה במשתמשים של המחלקות המורשות
- ✅ צפייה בקבוצות של המחלקות המורשות
- ✅ צפייה בדוחות (מסוננים לפי מחלקות)
- ✅ חיפוש משתמשים
- ❌ אין אפשרות לעריכה, יצירה או מחיקה

**מתאים ל:**
- צוות צפייה ודיווח
- מנהלים שצריכים מעקב בלבד

---

#### 🟢 Support (תמיכה)
**קבוצת Entra ID:** `SafeQ-Support`

**יכולות:**
- ✅ כל יכולות ה-Viewer
- ✅ **עריכת משתמשים קיימים** (שם, אימייל, מחלקה, PIN, סיסמא)
- ✅ **יצירת משתמשים חדשים** (רק במחלקות המורשות)
- ✅ **הוספה/הסרה של משתמשים מקבוצות**
- ❌ לא יכול למחוק משתמשים

**מתאים ל:**
- צוות תמיכה טכנית
- מנהלי IT ברמת מחלקה/בית ספר

---

#### 🟡 Admin (מנהל)
**קבוצת Entra ID:** `SafeQ-Admin`

**יכולות:**
- ✅ כל יכולות ה-Support
- ✅ **מחיקת משתמשים** (רק במחלקות המורשות)
- ✅ **פעולות Bulk** (פעולות קבוצתיות על מספר משתמשים)
- ✅ ניהול מלא של משתמשים וקבוצות
- ⚠️ **הגבלה:** רק במחלקות המוגדרות עבור המשתמש

**מתאים ל:**
- מנהלי IT ראשיים
- מנהלי מחלקות עם הרשאות מלאות

---

#### 🔴 SuperAdmin (מנהל על)
**קבוצת Entra ID:** `SafeQ-SuperAdmin` או **Emergency Users**

**יכולות:**
- ✅ **גישה בלתי מוגבלת לכל המערכת**
- ✅ צפייה ועריכה של **כל המשתמשים והקבוצות**
- ✅ גישה ל-"Local Users" (Provider 12348)
- ✅ פעולות Bulk על כל המחלקות
- ✅ ניהול מלא ללא הגבלות מחלקתיות
- ✅ **רואה את כל הדוחות ללא סינון**

**מתאים ל:**
- צוות IT ארגוני
- מנהלי מערכת ראשיים
- חשבונות חירום

---

#### 🏫 School Manager (מנהל בית ספר)
**אימות:** Local Authentication (username + password מול SafeQ Cloud)

**יכולות:**
- ✅ **גישה לדוחות בלבד** (Reports page)
- ✅ צפייה בדוחות של בתי הספר המשויכים
- ✅ סינון אוטומטי של דוחות
- ❌ **לא** יכול לראות/לערוך משתמשים
- ❌ **לא** יכול לראות/לערוך קבוצות

**UI מוגבל:**
- ניווט מציג **רק** עמוד "דוחות"
- כל שאר העמודים מוסתרים

**מתאים ל:**
- מנהלי בתי ספר שצריכים רק דוחות
- משתמשים שאין להם חשבון Entra ID

---

## 6. הכנות בצד הלקוח - Microsoft Entra ID

### 6.1 תהליך ההכנה - שלב אחרי שלב

#### שלב 1: יצירת App Registration ב-Entra ID

**מה זה?**
App Registration הוא "אישור" למערכת SafeQ Manager להשתמש ב-Entra ID לצורך אימות משתמשים.

**צעדים:**

1. **היכנסו ל-Azure Portal**
   - כתובת: https://portal.azure.com
   - התחברו עם חשבון בעל הרשאות Admin

2. **נווטו ל-Microsoft Entra ID**
   - לחצו על תפריט השירותים (☰)
   - בחרו "Microsoft Entra ID"

3. **צרו App Registration חדש**
   - לחצו על "App registrations" בתפריט השמאלי
   - לחצו "+ New registration"
   - מלאו את הפרטים:
     ```
     Name: SafeQ Cloud Manager
     Supported account types: Accounts in this organizational directory only
     Redirect URI:
       - Platform: Web
       - URL: https://YOUR-APP-NAME.streamlit.app
     ```
   - לחצו "Register"

4. **שימרו את המזהים החשובים**

   לאחר היצירה, **העתיקו** את הערכים הבאים (תצטרכו אותם בהמשך):

   | שדה | היכן למצוא | דוגמה |
   |-----|-----------|--------|
   | **Application (client) ID** | Overview → Application (client) ID | `12345678-1234-1234-1234-123456789012` |
   | **Directory (tenant) ID** | Overview → Directory (tenant) ID | `87654321-4321-4321-4321-210987654321` |

5. **צרו Client Secret**
   - לחצו על "Certificates & secrets" בתפריט השמאלי
   - לחצו "+ New client secret"
   - מלאו:
     ```
     Description: SafeQ Manager Secret
     Expires: 24 months (המלצה)
     ```
   - לחצו "Add"
   - **⚠️ חשוב!** העתיקו את ה-**Value** מיד (זה מוצג רק פעם אחת!)
   - שימרו אותו במקום מאובטח

6. **הגדירו הרשאות API (Permissions)**
   - לחצו על "API permissions" בתפריט השמאלי
   - ודאו שההרשאות הבאות קיימות:
     ```
     Microsoft Graph:
     ✓ User.Read (Delegated) - קריאת פרופיל המשתמש
     ✓ GroupMember.Read.All (Delegated) - קריאת שייכות לקבוצות
     ```
   - אם חסרות, לחצו "+ Add a permission" והוסיפו אותן
   - לחצו "Grant admin consent for [Your Organization]"

---

#### שלב 2: יצירת קבוצות Security ב-Entra ID

**מה זה?**
קבוצות שמגדירות את רמת ההרשאה של כל משתמש במערכת.

**צעדים:**

1. **נווטו לניהול קבוצות**
   - Microsoft Entra ID → Groups → All groups
   - לחצו "+ New group"

2. **צרו 4 קבוצות**

   הקבוצות שצריך ליצור:

   | שם קבוצה | תיאור | רמת הרשאה |
   |----------|-------|-----------|
   | `SafeQ-View` | הרשאות צפייה במערכת SafeQ Cloud Manager | Viewer |
   | `SafeQ-Support` | הרשאות תמיכה ועריכה במערכת | Support |
   | `SafeQ-Admin` | הרשאות ניהול מלא במחלקות ספציפיות | Admin |
   | `SafeQ-SuperAdmin` | הרשאות מנהל על - גישה לכל המערכת | SuperAdmin |

   **הגדרות ליצירה:**
   ```
   Group type: Security
   Group name: SafeQ-View (לדוגמה)
   Group description: הרשאות צפייה במערכת SafeQ Cloud Manager
   Membership type: Assigned
   ```

3. **הוסיפו משתמשים לקבוצות**
   - לחצו על הקבוצה שנוצרה
   - לחצו "Members" → "+ Add members"
   - חפשו את המשתמשים והוסיפו אותם

   **⚠️ חשוב:**
   - הוסיפו כל משתמש **רק לקבוצה אחת** (הקבוצה עם רמת ההרשאה הגבוהה ביותר שנדרשת לו)
   - דוגמה:
     ```
     john@example.com → SafeQ-View
     sarah@example.com → SafeQ-Support
     admin@example.com → SafeQ-SuperAdmin
     ```

---

#### שלב 3: (אופציונלי) שמות קבוצות מותאמים אישית

אם הלקוח רוצה להשתמש בשמות קבוצות אחרים (לדוגמה: "MyOrg-Viewer" במקום "SafeQ-View"):

**אפשר!** יש להגדיר בקובץ הסודות (Secrets):

```toml
# התאמה אישית של שמות קבוצות
ROLE_VIEW_GROUP = "MyOrg-Viewer"
ROLE_SUPPORT_GROUP = "MyOrg-HelpDesk"
ROLE_ADMIN_GROUP = "MyOrg-Manager"
ROLE_SUPERADMIN_GROUP = "MyOrg-ITAdmin"
```

---

#### שלב 4: סיכום - מה צריך למסור לצוות הטכני?

לאחר השלמת כל השלבים, העבירו את המידע הבא:

| שדה | ערך | היכן למצוא |
|-----|-----|-----------|
| **TENANT_ID** | `87654321-...` | App Registration → Overview |
| **CLIENT_ID** | `12345678-...` | App Registration → Overview |
| **CLIENT_SECRET** | `abc123...` | Certificates & secrets → Value |
| **REDIRECT_URI** | `https://app-name.streamlit.app` | App Registration → Redirect URIs |

**⚠️ שמירת מידע רגיש:**
- אל תשלחו את ה-Client Secret באימייל רגיל!
- השתמשו בערוץ מאובטח (מכשיר מוצפן, Password Manager, וכו')

---

## 7. ניהול דוחות עם סינון מחלקתי

### 7.1 איך עובד הסינון?

המערכת מבצעת **סינון אוטומטי** של דוחות לפי בתי הספר/מחלקות שהמשתמש מורשה לראות.

#### תהליך:

```
1. משתמש נכנס למערכת
   ↓
2. המערכת קובעת את ה-allowed_departments שלו:
   • SuperAdmin → ["ALL"] (רואה הכל)
   • Viewer/Support/Admin → חילוץ מקבוצות SafeQ (לדוגמה: ["צפת - 240234", "קדומים - 440909"])
   • School Manager → חילוץ מקבוצות SafeQ
   ↓
3. משתמש מבקש דוח (לדוגמה: הדפסות לשבוע האחרון)
   ↓
4. המערכת שולפת את כל המסמכים מ-SafeQ API
   ↓
5. סינון אוטומטי:
   • אם allowed_departments = ["ALL"] → מציג הכל
   • אם allowed_departments = ["צפת - 240234", ...] →
     מסנן רק מסמכים שה-tag שלהם (department) נמצא ברשימה
   ↓
6. הצגת הדוח המסונן למשתמש
```

### 7.2 מבנה ה-Tags בדוקומנטים

כל מסמך (הדפסה/צילום) ב-SafeQ מכיל שדה `tags`:

```json
{
  "uuid": "abc123",
  "userName": "208853218",
  "jobType": "PRINT",
  "totalPages": 5,
  "tags": [
    {
      "tagType": 0,     ← Department tag
      "name": "צפת - 240234"
    }
  ]
}
```

**הסינון:**
- המערכת עוברת על כל המסמכים
- בודקת אם `tag.name` (כש-`tagType = 0`) נמצא ב-`allowed_departments`
- אם כן → מציג
- אם לא → מסתיר

### 7.3 פורמט קבוצות בתי ספר ב-SafeQ

כדי שהסינון יעבוד, **חובה** שבתי הספר ב-SafeQ יהיו בפורמט:

```
<שם בית הספר> - <מספר>
```

**דוגמאות תקינות:**
- ✅ `צפת - 240234`
- ✅ `קדומים - 440909`
- ✅ `Zefat - 240234`
- ✅ `עלי זהב - 234768`

**דוגמאות לא תקינות:**
- ❌ `צפת240234` (ללא מקף)
- ❌ `צפת-240234` (ללא רווחים)
- ❌ `צפת` (ללא מספר)

**⚠️ חשוב:** המערכת משתמשת ב-regex pattern: `-\s*(\d+)$` לזיהוי קבוצות בתי ספר.

---

## 8. אבטחת מידע וניהול Secrets

### 8.1 מה זה Secrets?

**Secrets** = מידע רגיש שהאפליקציה צריכה אבל **לא** צריך להיות בקוד:

- 🔑 API Keys (SafeQ Cloud API Key)
- 🔐 Entra ID Credentials (Client ID, Client Secret, Tenant ID)
- 👤 Emergency Users (username + password)
- 🌐 URLs (SafeQ Server URL, Redirect URI)

### 8.2 איפה ה-Secrets נשמרים?

#### ב-Streamlit Cloud:

1. **Settings → Secrets**
   - מנוהל דרך ממשק Streamlit Cloud
   - מוצפן בשרתי Streamlit
   - נגיש רק לבעלי הזכויות באפליקציה

2. **פורמט: TOML**
   ```toml
   # SafeQ Cloud API
   SERVER_URL = "https://safeq-server.example.com"
   API_KEY = "your-api-key-here"

   # Microsoft Entra ID
   TENANT_ID = "your-tenant-id"
   CLIENT_ID = "your-client-id"
   CLIENT_SECRET = "your-client-secret"
   REDIRECT_URI = "https://your-app.streamlit.app"

   # Emergency Users (SuperAdmin)
   [EMERGENCY_USERS]
   admin = "SecurePassword123!"
   backup = "BackupPass456!"

   # Providers
   PROVIDER_LOCAL = "12348"
   PROVIDER_ENTRA = "12351"

   # Reports
   REPORTS_VIEW_GROUP = "Reports-View"
   ```

#### בפיתוח מקומי (Local Development):

1. **קובץ:** `.streamlit/secrets.toml`
   - **⚠️ חשוב:** הקובץ הזה **לא** נדחף ל-GitHub (נמצא ב-`.gitignore`)
   - שמור במחשב המפתח בלבד

### 8.3 מי יכול לגשת ל-Secrets?

| סביבה | מי יכול לראות/לערוך |
|-------|---------------------|
| **Streamlit Cloud** | רק בעלי חשבון Streamlit עם הרשאות Admin לאפליקציה |
| **GitHub (קוד)** | אף אחד (Secrets **לא** בקוד) |
| **משתמשי האפליקציה** | אף אחד (הסודות לא נחשפים ב-UI) |

### 8.4 האם הלקוח יכול לנהל Secrets בעצמו?

**תלוי בסוג הפריסה:**

| סוג פריסה | האם הלקוח יכול לנהל? | הסבר |
|-----------|---------------------|-------|
| **Streamlit Cloud** | ❌ לא ישירות | דורש גישה לחשבון Streamlit Cloud |
| **Docker (Self-hosted)** | ✅ כן | הלקוח שולט ב-secrets.toml בשרת שלו |
| **On-Premise** | ✅ כן | הלקוח שולט במלוא התשתית |

**אם הלקוח רוצה שליטה מלאה:**
- מומלץ Docker או On-Premise
- נספק מדריך התקנה מפורט

---

## 9. תהליך התקנה ופריסה

### 9.1 אפשרות 1: Streamlit Cloud (מומלץ)

**יתרונות:**
- ✅ התקנה מהירה (10-15 דקות)
- ✅ ללא צורך בשרתים
- ✅ עדכונים אוטומטיים (כל push ל-GitHub)
- ✅ HTTPS מובנה
- ✅ גיבויים אוטומטיים

**שלבים:**

1. **הכנת GitHub Repository**
   ```bash
   # שכפול הקוד
   git clone https://github.com/your-org/SafeQCloudManager.git
   cd SafeQCloudManager

   # (אופציונלי) הפיכת הrepo לפרטי
   # Settings → Danger Zone → Change visibility → Private
   ```

2. **הרשמה/כניסה ל-Streamlit Cloud**
   - https://streamlit.io/cloud
   - התחברו עם חשבון GitHub

3. **Create New App**
   - לחצו "New app"
   - בחרו:
     ```
     Repository: your-org/SafeQCloudManager
     Branch: main
     Main file path: app/main.py
     ```

4. **הגדרת Secrets**
   - Settings → Secrets
   - העתיקו את התוכן של `secrets.toml.example`
   - מלאו את הערכים האמיתיים

5. **Deploy**
   - לחצו "Deploy"
   - המערכת תעלה אוטומטית (2-3 דקות)

6. **בדיקה**
   - גשו לכתובת: `https://your-app-name.streamlit.app`
   - בדקו כניסה עם Entra ID

---

### 9.2 אפשרות 2: Docker (Self-Hosted)

**יתרונות:**
- ✅ שליטה מלאה
- ✅ הלקוח מנהל Secrets
- ✅ יכול לרוץ ברשת פנימית

**דרישות:**
- 🖥️ שרת Linux/Windows עם Docker
- 🌐 חיבור לאינטרנט (לגישה ל-SafeQ Cloud ו-Entra ID)
- 📦 2GB RAM, 10GB Storage

**שלבים:**

1. **התקנת Docker**
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install docker.io docker-compose
   sudo systemctl start docker
   sudo systemctl enable docker
   ```

2. **שכפול הקוד**
   ```bash
   git clone https://github.com/your-org/SafeQCloudManager.git
   cd SafeQCloudManager
   ```

3. **הכנת secrets.toml**
   ```bash
   mkdir -p .streamlit
   cp secrets.toml.example .streamlit/secrets.toml
   nano .streamlit/secrets.toml  # ערכו את הערכים
   ```

4. **יצירת Dockerfile** (אם לא קיים)
   ```dockerfile
   FROM python:3.9-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY . .
   EXPOSE 8501
   CMD ["streamlit", "run", "app/main.py", "--server.port=8501"]
   ```

5. **Build & Run**
   ```bash
   docker build -t safeq-manager .
   docker run -d -p 8501:8501 \
     -v $(pwd)/.streamlit:/app/.streamlit \
     --name safeq-manager \
     safeq-manager
   ```

6. **הגדרת HTTPS (מומלץ)**
   ```bash
   # באמצעות Nginx + Let's Encrypt
   sudo apt install nginx certbot python3-certbot-nginx
   sudo certbot --nginx -d your-domain.com
   ```

---

## 10. שאלות ותשובות

### Q1: האם הקוד חשוף ב-GitHub?

**תשובה:**
- **אם הrepository הוא Public** → כן, הקוד חשוף לכולם
- **אם הrepository הוא Private** → לא, רק משתמשים עם הרשאות יכולים לראות

**חשוב:**
גם אם הקוד חשוף, **אין בו מידע רגיש**. כל ה-Secrets (API Keys, סיסמאות, וכו') נמצאים במנגנון נפרד (Secrets Management) ו**לא** בקוד.

**המלצה:**
הפכו את הrepository ל-**Private** (דורש GitHub Pro - $4/חודש).

---

### Q2: מה קורה אם שוכחים את סיסמת Emergency User?

**תשובה:**
- Emergency Users מוגדרים ב-**Secrets**
- מי שיש לו גישה ל-Streamlit Cloud יכול לערוך את ה-Secrets ולשנות את הסיסמה
- אם אין גישה → יצירת קשר עם ספק המערכת

**מניעה:**
- שמרו את פרטי ה-Emergency Users במקום מאובטח (Password Manager)
- צרו לפחות 2 Emergency Users (admin + backup)

---

### Q3: האם ניתן להגביל גישה למערכת לפי IP?

**תשובה:**
- ב-**Streamlit Cloud** → לא נתמך מובנה
- ב-**Docker/On-Premise** → כן, דרך Firewall או Nginx

**חלופה:**
- אימות דו-שלבי (Entra ID + SafeQ) מספק רמת אבטחה גבוהה גם ללא הגבלת IP

---

### Q4: כמה משתמשים המערכת תומכת?

**תשובה:**
- **Streamlit Cloud (Free)** → מוגבל ל-1 concurrent user
- **Streamlit Cloud (Team/Enterprise)** → ללא הגבלה
- **Docker/On-Premise** → תלוי במשאבי השרת

**בפועל:**
- המערכת מיועדת ל-**עד 50 concurrent users** (בו-זמנית)
- SafeQ API עצמו יכול להיות הגורם המגביל

---

### Q5: איך מעדכנים את המערכת?

**תשובה:**

**Streamlit Cloud:**
```bash
git pull origin main  # משיכת עדכונים
git push              # דחיפה לGitHub
# Streamlit Cloud יעדכן אוטומטית תוך 1-2 דקות
```

**Docker:**
```bash
git pull origin main
docker build -t safeq-manager .
docker stop safeq-manager
docker rm safeq-manager
docker run -d -p 8501:8501 \
  -v $(pwd)/.streamlit:/app/.streamlit \
  --name safeq-manager \
  safeq-manager
```

---

### Q6: מה קורה אם SafeQ Cloud API לא זמין?

**תשובה:**
- המערכת תציג הודעת שגיאה למשתמש
- Emergency Users עדיין יכולים להתחבר (אימות מקומי)
- לאחר ששרת SafeQ חוזר, המערכת תמשיך לעבוד

**Monitoring:**
- כדאי להגדיר מעקב (Monitoring) על זמינות SafeQ API
- אפשר לשלב עם כלים כמו UptimeRobot, Pingdom

---

### Q7: האם יש גיבוי למידע?

**תשובה:**

**Audit Log:**
- נשמר בקובץ SQLite מקומי
- ב-Streamlit Cloud: מתאפס כל פעם שהאפליקציה עולה מחדש
- **המלצה:** ייצוא תקופתי של ה-Audit Log למקום מאובטח

**נתוני SafeQ:**
- כל הנתונים נמצאים ב-SafeQ Cloud
- המערכת לא שומרת נתונים מעבר ל-Audit Log

**Secrets:**
- Streamlit Cloud מגבה אוטומטית
- מומלץ לשמור עותק ידני במקום מאובטח

---

### Q8: כיצד מוסיפים משתמש חדש?

**תשובה:**

**משתמש Entra ID:**
1. ✅ צרו משתמש ב-Microsoft Entra ID
2. ✅ הוסיפו אותו לקבוצת SafeQ מתאימה (View/Support/Admin/SuperAdmin)
3. ✅ צרו משתמש תואם ב-SafeQ Cloud (Provider 12348)
4. ✅ שייכו את המשתמש לקבוצות מחלקה ב-SafeQ (אם לא SuperAdmin)
5. ✅ המשתמש יכול להתחבר!

**School Manager:**
1. ✅ צרו משתמש ב-SafeQ Cloud (Provider 12348)
2. ✅ הגדירו Card ID (סיסמא) למשתמש
3. ✅ שייכו אותו לקבוצה "Reports-View"
4. ✅ שייכו אותו לקבוצות בתי ספר
5. ✅ המשתמש יכול להתחבר דרך "התחברות מנהל מקומי"

---

## סיכום ומסקנות

### ✅ מה הלקוח מקבל?

1. **מערכת ניהול מתקדמת** לSafeQ Cloud
2. **אבטחה ברמה ארגונית** (Entra ID + SSL + Audit Log)
3. **סינון חכם** של דוחות לפי מחלקות
4. **4 רמות הרשאה** גמישות
5. **ממשק ידידותי** בעברית
6. **תחזוקה מינימלית** (אם ב-Streamlit Cloud)

### 📋 צ'קליסט להתקנה

- [ ] יצירת App Registration ב-Entra ID
- [ ] יצירת 4 קבוצות Security (SafeQ-View/Support/Admin/SuperAdmin)
- [ ] הוספת משתמשים לקבוצות
- [ ] קבלת Client ID, Client Secret, Tenant ID
- [ ] העברת הסודות לצוות הטכני
- [ ] בחירת שיטת פריסה (Streamlit Cloud / Docker / On-Premise)
- [ ] התקנה והגדרת Secrets
- [ ] בדיקת כניסה ראשונית
- [ ] הדרכת משתמשים

### 📞 תמיכה

לשאלות נוספות או בעיות טכניות:
- צור קשר עם צוות התמיכה
- פתיחת issue ב-GitHub (אם הrepository פרטי)
- תיעוד מלא: https://docs.claude.com/safeq-manager

---

**מסמך זה עודכן:** 2025-11-13
**גרסה:** 2.0
**מחבר:** צוות הפיתוח SafeQ Manager
