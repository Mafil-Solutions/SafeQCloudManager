# 🚂 Railway Deployment Guide - SafeQ Cloud Manager

## שלבי הגדרה והעלאה ל-Railway

### 1️⃣ הכנה ראשונית

#### א. קבצי התצורה שנוצרו
הפרויקט מוכן כעת להרצה ב-Railway עם הקבצים הבאים:
- ✅ `Procfile` - הגדרת פקודת ההרצה
- ✅ `railway.toml` - תצורת Railway
- ✅ `.streamlit/config.toml` - הגדרות Streamlit לפרודקשן

---

### 2️⃣ יצירת פרויקט ב-Railway

1. **היכנס ל-Railway**
   - גש ל-https://railway.app/
   - התחבר עם GitHub

2. **צור פרויקט חדש**
   - לחץ על "New Project"
   - בחר "Deploy from GitHub repo"
   - בחר את הרפוזיטורי `SafeQCloudManager`
   - Railway יזהה אוטומטית שזו אפליקציית Python

---

### 3️⃣ הגדרת משתני סביבה (Environment Variables)

**חשוב מאוד!** צריך להגדיר את כל המשתנים הבאים ב-Railway:

#### 📍 איך להגדיר משתני סביבה ב-Railway:
1. בפרויקט שלך, לחץ על השירות (Service)
2. עבור ללשונית **Variables**
3. הוסף את כל המשתנים הבאים:

#### 🔧 API Configuration
```
SERVER_URL=https://your-safeq-server.com:7300
API_KEY=your_api_key_here
```

#### 🔐 Entra ID Configuration
```
TENANT_ID=your-tenant-id
CLIENT_ID=your-client-id
CLIENT_SECRET=your-client-secret
AUTHORITY=https://login.microsoftonline.com/YOUR_TENANT_ID
```

#### ⚠️ **שים לב מאוד!**
```
REDIRECT_URI=https://YOUR-APP-NAME.up.railway.app
```
**חשוב:** אחרי שהאפליקציה תעלה, תקבל URL מ-Railway.
- עדכן את `REDIRECT_URI` ל-URL האמיתי שקיבלת
- עדכן גם ב-**Entra ID App Registration** (Azure Portal):
  - Redirect URIs → הוסף את ה-URL החדש של Railway

#### 👥 Access Control
```
ENABLE_GROUP_RESTRICTION=True

ROLE_VIEW_GROUP=SafeQ-View
ROLE_SUPPORT_GROUP=SafeQ-Support
ROLE_ADMIN_GROUP=SafeQ-Admin
ROLE_SUPERADMIN_GROUP=SafeQ-SuperAdmin
```

#### 🔌 Providers
```
PROVIDER_LOCAL=12348
PROVIDER_ENTRA=12351
```

#### ⏱️ Session
```
SESSION_TIMEOUT=120
USE_ENTRA_ID=True
LOG_TO_FILE=True
LOG_TO_DATABASE=True
```

#### 🆘 Emergency Users (אופציונלי)
אם רוצה משתמשי חירום:
```
EMERGENCY_USER_admin=YourSecurePassword123
EMERGENCY_USER_backup=AnotherPassword456
```

---

### 4️⃣ הגדרת Entra ID (Azure Portal)

**חובה לעדכן ב-Azure Portal!**

1. עבור ל-Azure Portal → Entra ID → App registrations
2. בחר את האפליקציה שלך
3. עבור ל-**Authentication**
4. ב-**Redirect URIs** הוסף:
   ```
   https://YOUR-APP-NAME.up.railway.app
   ```
5. שמור

---

### 5️⃣ הפעלת האפליקציה

1. **Railway יתחיל לבנות אוטומטית**
   - תראה logs של ה-build process
   - זה ייקח כמה דקות

2. **בדיקת ה-Deployment**
   - לחץ על "View Logs" כדי לראות את התהליך
   - וודא שאין שגיאות

3. **קבלת URL**
   - Railway יקצה לך URL: `https://your-app-name.up.railway.app`
   - אפשר גם להגדיר Custom Domain

---

### 6️⃣ בדיקות אחרי העלייה

✅ **בדוק שהכל עובד:**
1. פתח את ה-URL שקיבלת
2. נסה להתחבר עם Entra ID
3. וודא שההרשאות עובדות
4. בדוק שהחיבור ל-SafeQ API עובד

---

### 7️⃣ הבדלים מ-Streamlit Cloud

| תכונה | Streamlit Cloud | Railway |
|--------|----------------|---------|
| **Secrets** | `secrets.toml` | Environment Variables |
| **Port** | קבוע | `$PORT` (דינמי) |
| **URL** | `.streamlit.app` | `.up.railway.app` |
| **התצורה** | אוטומטי | `Procfile`/`railway.toml` |
| **Logs** | מוגבל | מלא (מומלץ) |
| **Databases** | מוגבל | תמיכה מלאה |
| **Custom Domains** | Pro בלבד | חינם |

---

### 8️⃣ שינויים בקוד

**✨ הקוד שלך כבר מוכן!**

הקוד שלך משתמש ב-`config.py` שמזהה אוטומטית:
- ב-Streamlit Cloud: קורא מ-`st.secrets`
- ב-Railway/Local: קורא מ-Environment Variables
- **אין צורך בשינויים!** 🎉

---

### 9️⃣ Tips למעבר חלק

#### 🔄 עדכון אוטומטי
- כל push ל-branch `main` יעדכן אוטומטית את Railway
- Railway יבנה מחדש ויפרוס

#### 📊 Monitoring
- Railway מספק:
  - CPU/Memory usage
  - Logs בזמן אמת
  - Metrics

#### 💾 Persistent Storage
- ה-SQLite database (`safeq_audit.db`) יישמר בין deployments
- Railway מספק volumes אם צריך

#### 🔒 Security
- כל ה-secrets ב-Environment Variables (מוצפן)
- HTTPS אוטומטי
- אין חשיפה של credentials

---

### 🆘 פתרון בעיות נפוצות

#### ❌ שגיאת "Port already in use"
Railway מגדיר את `$PORT` אוטומטית - הקוד שלנו מטפל בזה.

#### ❌ שגיאת Redirect URI
1. וודא ש-`REDIRECT_URI` ב-Railway תואם ל-URL שקיבלת
2. וודא שהוספת את ה-URI גם ב-Azure Portal

#### ❌ שגיאת API Connection
1. בדוק ש-`SERVER_URL` נכון
2. וודא ש-`API_KEY` תקין
3. בדוק ש-Railway יכול להגיע לשרת SafeQ (firewall)

#### ❌ Entra ID לא עובד
1. וודא שכל המשתנים (`CLIENT_ID`, `TENANT_ID`, `CLIENT_SECRET`) מוגדרים
2. בדוק שה-Redirect URI תואם
3. וודא שהאפליקציה ב-Azure מאושרת

---

### 📞 תמיכה

- **Railway Docs**: https://docs.railway.app/
- **Streamlit Docs**: https://docs.streamlit.io/
- **Railway Discord**: https://discord.gg/railway

---

## ✅ Checklist לפני Go-Live

- [ ] כל משתני הסביבה מוגדרים ב-Railway
- [ ] Redirect URI מעודכן ב-Railway וב-Azure
- [ ] האפליקציה עולה בהצלחה (בדיקת logs)
- [ ] התחברות עם Entra ID עובדת
- [ ] חיבור ל-SafeQ API עובד
- [ ] הרשאות משתמשים עובדות כראוי
- [ ] בדיקת כל הפונקציות הקריטיות

---

**בהצלחה! 🚀**
