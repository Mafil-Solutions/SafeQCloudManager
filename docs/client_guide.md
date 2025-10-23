מסמך הנחיה ללקוח - הכנת תשתית למערכת ניהול הרשאות SafeQ

תקציר מנהלים
מסמך זה מפרט את הדרישות וההכנות הנדרשות מצד הארגון להטמעת מערכת ניהול הרשאות מבוססת Entra ID עבור SafeQ Manager.
מטרת המערכת:

לאפשר לכל בית ספר/מחלקה לנהל באופן עצמאי את המשתמשים שלו
למנוע גישה בלתי מורשית למידע של בתי ספר אחרים
לשמור על ביקורת ואבטחה מלאה

זמן הכנה משוער: 2-4 שעות עבור ארגון בינוני (50-100 בתי ספר)

1. סקירה כללית - מבנה ההרשאות
1.1 עקרונות המערכת
המערכת מבוססת על קבוצות Entra ID שמגדירות:

איזה בית ספר המשתמש רשאי לנהל
רמת ההרשאה של המשתמש (צפייה/עריכה/מחיקה)

1.2 היררכיית הרשאות
┌─────────────────────────────────────┐
│      Super Admin (מנהל מערכת)       │
│   רואה ומנהל את כל בתי הספר         │
└─────────────────────────────────────┘
            │
    ┌───────┴───────┬───────────┐
    │               │           │
┌───▼────┐    ┌────▼───┐   ┌───▼────┐
│ בי"ס א │    │ בי"ס ב │   │ בי"ס ג │
└────────┘    └────────┘   └────────┘
    │
    ├─► Admin (מחיקה + עריכה + צפייה)
    ├─► Editor (עריכה + צפייה)
    └─► Viewer (צפייה בלבד)
```

---

## 2. דרישות טכניות

### 2.1 תשתית Entra ID
- ✅ חשבון Entra ID (Azure AD) פעיל
- ✅ הרשאות ליצירת קבוצות אבטחה
- ✅ הרשאות להוספת משתמשים לקבוצות

### 2.2 מידע נדרש לכל בית ספר

עבור כל בית ספר/מחלקה, יש להכין:

| שדה | תיאור | דוגמה | חובה |
|-----|--------|--------|------|
| **שם בית הספר** | שם ברור ומזהה | "תיכון הרצליה" | ✅ |
| **סמל מוסד** | מספר ייחודי 6 ספרות | "240234" | ✅ |
| **מחלקה (Department)** | ערך זהה ב-SafeQ | "תיכון הרצליה-240234" | ✅ |
| **מנהלי המערכת** | רשימת מנהלים + רמות הרשאה | ראה טבלה למטה | ✅ |

---

## 3. הקמת קבוצות Entra ID

### 3.1 פורמט שמות קבוצות (חובה!)

**תבנית:** `[שם_בית_ספר]-[סמל_מוסד]-[רמת_הרשאה]`

#### דוגמאות נכונות:
```
✅ תיכון_הרצליה-240234-Admin
✅ צפת-240234-Editor
✅ יסודי_רמות-330145-Viewer
✅ ביה"ס_חדש-150022-Admin
```

#### דוגמאות שגויות:
```
❌ תיכון הרצליה 240234 Admin    (רווחים במקום מקפים)
❌ הרצליה-Admin                 (חסר סמל מוסד)
❌ 240234-הרצליה-Admin           (סדר שגוי)
❌ הרצליה-24023-Admin            (סמל מוסד לא 6 ספרות)
3.2 רמות הרשאה זמינות
רמהשם באנגליתהרשאותמומלץ עבור🔍Viewerצפייה בלבדמזכירות, תמיכה טכנית בסיסית✏️Editorצפייה + יצירה + עריכהטכנאים, מנהלי בית ספר🗑️Adminהכל כולל מחיקהמנהל IT בית הספר, מנהל מערכות
3.3 קבוצת Super Admin
שם קבוצה: SafeQ-SuperAdmin
מי צריך להיות בקבוצה:

מנהל IT ארצי
צוות התמיכה המרכזי
ספק המערכת (זמני)

הרשאות:

גישה לכל בתי הספר
כל רמות ההרשאה
ניהול מערכת


4. מדריך שלב-אחר-שלב
שלב 1: איסוף מידע (30-60 דקות)
צור טבלת Excel עם המבנה הבא:
שם בית ספרסמל מוסדשם מנהל 1אימייל מנהל 1רמה 1שם מנהל 2אימייל מנהל 2רמה 2תיכון הרצליה240234משה כהןmoshe@school.gov.ilAdminדנה לויdana@school.gov.ilEditorצפת240235יוסי ישראליyossi@school.gov.ilAdmin---
המלצה: התחל עם 3-5 בתי ספר פיילוט לפני הטמעה מלאה.

שלב 2: יצירת קבוצות ב-Entra ID (10 דקות לבית ספר)
דרך 1: ידנית דרך Azure Portal

היכנס ל-Azure Portal
נווט ל: Azure Active Directory → Groups → New Group
מלא את הפרטים:

Group type: Security
Group name: לפי הפורמט (לדוגמה: תיכון_הרצליה-240234-Admin)
Group description: "מנהלי SafeQ - תיכון הרצליה"
Membership type: Assigned


לחץ Create
הוסף חברים לקבוצה: Members → Add members

חזור על התהליך עבור כל רמת הרשאה לכל בית ספר.

דרך 2: PowerShell (מהיר יותר)
powershell# התקנת מודול (פעם אחת בלבד)
Install-Module AzureAD
Connect-AzureAD

# סקריפט ליצירת קבוצות
$schools = @(
    @{Name="תיכון_הרצליה"; Code="240234"; Managers=@(
        @{Email="moshe@school.gov.il"; Level="Admin"},
        @{Email="dana@school.gov.il"; Level="Editor"}
    )},
    @{Name="צפת"; Code="240235"; Managers=@(
        @{Email="yossi@school.gov.il"; Level="Admin"}
    )}
)

foreach ($school in $schools) {
    foreach ($manager in $school.Managers) {
        $groupName = "$($school.Name)-$($school.Code)-$($manager.Level)"
        
        # יצירת קבוצה
        $group = New-AzureADGroup -DisplayName $groupName `
                                   -MailEnabled $false `
                                   -SecurityEnabled $true `
                                   -MailNickName $groupName.Replace(" ","")
        
        Write-Host "✓ Created group: $groupName" -ForegroundColor Green
        
        # הוספת משתמש
        $user = Get-AzureADUser -Filter "UserPrincipalName eq '$($manager.Email)'"
        if ($user) {
            Add-AzureADGroupMember -ObjectId $group.ObjectId -RefObjectId $user.ObjectId
            Write-Host "  ✓ Added $($manager.Email) to $groupName" -ForegroundColor Cyan
        }
    }
}

Write-Host "`n✓ Setup complete!" -ForegroundColor Green
שמור את הסקריפט כ-Create-SafeQGroups.ps1 והרץ אותו.

שלב 3: יצירת קבוצת Super Admin (5 דקות)
powershell# יצירת קבוצת מנהלי-על
$superAdminGroup = New-AzureADGroup -DisplayName "SafeQ-SuperAdmin" `
                                     -MailEnabled $false `
                                     -SecurityEnabled $true `
                                     -MailNickName "SafeQSuperAdmin" `
                                     -Description "SafeQ System Administrators - Full Access"

# הוספת מנהלי מערכת
$superAdmins = @("admin1@domain.com", "admin2@domain.com")
foreach ($email in $superAdmins) {
    $user = Get-AzureADUser -Filter "UserPrincipalName eq '$email'"
    Add-AzureADGroupMember -ObjectId $superAdminGroup.ObjectId -RefObjectId $user.ObjectId
    Write-Host "✓ Added $email to Super Admin group" -ForegroundColor Green
}
```

---

### שלב 4: הגדרת שדה Department במשתמשי SafeQ (נעשה על ידי הספק)

**חשוב:** הערך בשדה Department של כל משתמש ב-SafeQ חייב להיות **זהה** לפורמט:
```
[שם_בית_ספר]-[סמל_מוסד]
דוגמאות:

תיכון_הרצליה-240234
צפת-240235

הערה: הספק יבצע את ההגדרה הראשונית. בהמשך, כל יצירת משתמש חדש תקבל אוטומטית את ה-Department הנכון.

5. בדיקה ואימות
5.1 Checklist לפני השקה

 כל בתי הספר רשומים בטבלת Excel
 לכל בית ספר יש סמל מוסד ייחודי (6 ספרות)
 נוצרו קבוצות Entra ID לפי הפורמט הנכון
 כל מנהל משויך לקבוצה המתאימה
 נוצרה קבוצת SafeQ-SuperAdmin
 מנהלי המערכת המרכזיים בקבוצת SuperAdmin
 כל משתמשי SafeQ המקומיים עם שדה Department מוגדר

5.2 בדיקת שמות קבוצות
הרץ סקריפט בדיקה:
powershellConnect-AzureAD

# קבלת כל קבוצות SafeQ
$groups = Get-AzureADGroup -All $true | Where-Object {$_.DisplayName -like "*-*-*"}

Write-Host "`nSafeQ Groups Found:" -ForegroundColor Cyan
Write-Host "====================`n" -ForegroundColor Cyan

foreach ($group in $groups) {
    $name = $group.DisplayName
    
    # בדיקת פורמט
    if ($name -match '^(.+?)-(\d{6})-(Admin|Editor|Viewer)$') {
        $school = $matches[1]
        $code = $matches[2]
        $level = $matches[3]
        
        $members = Get-AzureADGroupMember -ObjectId $group.ObjectId
        $memberCount = $members.Count
        
        Write-Host "✓ $name" -ForegroundColor Green
        Write-Host "  School: $school | Code: $code | Level: $level | Members: $memberCount" -ForegroundColor Gray
    }
    else {
        Write-Host "❌ $name - INVALID FORMAT!" -ForegroundColor Red
    }
}

# בדיקת Super Admin
$superAdmin = Get-AzureADGroup -Filter "DisplayName eq 'SafeQ-SuperAdmin'"
if ($superAdmin) {
    $members = Get-AzureADGroupMember -ObjectId $superAdmin.ObjectId
    Write-Host "`n✓ Super Admin Group Found - Members: $($members.Count)" -ForegroundColor Green
} else {
    Write-Host "`n❌ Super Admin Group NOT FOUND!" -ForegroundColor Red
}

6. תרחישי שימוש נפוצים
תרחיש 1: הוספת בית ספר חדש
זמן: 10 דקות

קבע סמל מוסד (6 ספרות, ייחודי)
צור 3 קבוצות Entra:

[שם_בית_ספר]-[סמל]-Admin
[שם_בית_ספר]-[סמל]-Editor
[שם_בית_ספר]-[סמל]-Viewer


הוסף מנהלים לקבוצות
הודע לספק על הסמל החדש (אם נדרש)

הערה: מרגע יצירת הקבוצות, המערכת תזהה אותן אוטומטית!

תרחיש 2: החלפת מנהל בית ספר
זמן: 2 דקות

הסר את המנהל הישן מהקבוצה הרלוונטית
הוסף את המנהל החדש לאותה קבוצה
אין צורך בהגדרות נוספות


תרחיש 3: שינוי רמת הרשאה למנהל
זמן: 3 דקות
דוגמה: העלאת טכנאי מ-Editor ל-Admin

הסר מקבוצת [בית_ספר]-[סמל]-Editor
הוסף לקבוצת [בית_ספר]-[סמל]-Admin


תרחיש 4: מנהל עם גישה למספר בתי ספר
דוגמה: מנהל אזורי שאחראי על 3 בתי ספר
פתרון: הוסף את המשתמש ל-3 קבוצות:

בית_ספר_א-240234-Admin
בית_ספר_ב-240235-Admin
בית_ספר_ג-240236-Admin

המערכת תאפשר לו לראות משתמשים מכל 3 בתי הספר.

7. שאלות ותשובות נפוצות
ש: האם חייב להשתמש בסמל מוסד רשמי?
ת: לא חובה, אבל מומלץ מאוד. אפשר להשתמש בכל מספר ייחודי בן 6 ספרות. החשוב שיהיה עקבי ויציב.
ש: מה קורה אם משתמש לא שייך לאף קבוצה?
ת: המשתמש לא יוכל להיכנס למערכת (חוץ מאם הוא Super Admin).
ש: האם אפשר לשנות את שם בית הספר אחרי היצירה?
ת: כן, אבל לא מומלץ. אם חייבים:

צור קבוצות חדשות עם השם החדש
העבר את החברים
מחק את הקבוצות הישנות
עדכן את ה-Department של המשתמשים ב-SafeQ

ש: כמה זמן לוקח עד שהשינויים נכנסים לתוקף?
ת: מיידי. שינויים בקבוצות Entra מתעדכנים בכניסה הבאה של המשתמש (או תוך דקה בממוצע).
ש: האם אפשר לתת גישה זמנית?
ת: כן. הוסף משתמש לקבוצה לתקופה מוגבלת ואז הסר אותו.
ש: מה קורה אם יש טעות בסמל המוסד?
ת: המערכת לא תמצא התאמה והמנהל לא יראה משתמשים. צריך לתקן את הסמל בקבוצות Entra או בשדה Department של המשתמשים.

8. תמיכה ופתרון בעיות
בעיה: מנהל לא רואה משתמשים
פתרונות אפשריים:

בדוק שהמנהל בקבוצה הנכונה:

powershell   $user = Get-AzureADUser -Filter "UserPrincipalName eq 'user@domain.com'"
   Get-AzureADUserMembership -ObjectId $user.ObjectId | Select DisplayName

בדוק שהסמל מוסד תואם:

סמל בקבוצת Entra: צפת-240234-Admin
Department במשתמשי SafeQ: צפת-240234
חייבים להיות זהים!


בדוק שהמשתמשים ב-SafeQ עם Department מוגדר:

השתמש בטאב Users לבדיקה
אם ריק - הספק צריך לעדכן




בעיה: שגיאת כניסה
סיבות אפשריות:

המשתמש לא בקבוצה מורשית בכלל
שם הקבוצה לא בפורמט הנכון
הגדרת ACCESS_CONTROL במערכת

פתרון:
פנה למנהל המערכת עם פרטי המשתמש.

9. טבלת עלויות ומשאבים
משאבכמותזמןהערותאיסוף מידעחד-פעמי1-2 שעותתלוי בגודל הארגוןיצירת קבוצותלכל בית ספר10 דקותניתן לאוטומציההוספת משתמשים לקבוצותלכל מנהל2 דקות-בדיקותחד-פעמי30 דקות-סה"כ לארגון בינוני (50 בתי ספר)-3-4 שעות-תחזוקה שוטפתחודשי15-30 דקותשינויים/תוספות

10. המלצות והנחיות best practice
✅ DO - מומלץ

התחל קטן: פיילוט עם 3-5 בתי ספר
תיעוד: שמור רשימת קבוצות מעודכנת ב-Excel
מוסכמות שמות: החלט על פורמט אחיד והחל אותו בעקביות
גיבויים: יצא רשימת קבוצות וחברים לפני שינויים גדולים
הדרכה: הסבר למנהלים מה הם רואים ומה לא

❌ DON'T - לא מומלץ

לא לשנות סמלי מוסדות אחרי ההקמה
לא להשתמש ברווחים בשמות קבוצות (השתמש ב-_ או -)
לא לתת הרשאות Admin ללא צורך ממשי
לא לשכוח לעדכן קבוצות כשמנהל עוזב
לא להסתמך על שמות - תמיד השתמש בסמלי מוסד


11. סיכום והמלצות
מה חשוב לזכור:

הפורמט הוא הכל - [שם]-[סמל_6_ספרות]-[רמה]
סמל מוסד = מפתח ההתאמה בין Entra ל-SafeQ
שלוש רמות הרשאה - Viewer, Editor, Admin
Super Admin - לשימוש מנהלי מערכת בלבד
קל להוסיף בתי ספר - פשוט צור קבוצות חדשות

יתרונות המערכת:
✅ אבטחה - כל בית ספר רואה רק את שלו
✅ גמישות - קל לשנות הרשאות
✅ סקלביליות - מאות בתי ספר ללא מאמץ
✅ ניהול מרכזי - הכל דרך Entra ID
✅ ביקורת - כל פעולה מתועדת

12. צור קשר
לשאלות טכניות:

📧 Email: support@yourcompany.com
📞 טלפון: 03-1234567

לשאלות על ההקמה:

השאר את הפרטים שלך ונחזור אליך תוך 24 שעות


נספחים
נספח א': תבנית Excel לאיסוף מידע
[קישור להורדה: SafeQ_Schools_Template.xlsx]
נספח ב': סקריפטים מוכנים לשימוש
[קישור להורדה: SafeQ_Setup_Scripts.zip]
נספח ג': מדריך PowerShell מפורט
[קישור למדריך מלא]

גרסה: 1.0
תאריך עדכון אחרון: [תאריך]
מוכן על ידי: SafeQ Implementation Team