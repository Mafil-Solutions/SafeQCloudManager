# 🚀 Railway Quick Start - 5 דקות להרצה

## מהירות מקסימלית - צעדים בסיסיים

### 1. העלה לGitHub (אם עדיין לא)
```bash
git add .
git commit -m "Ready for Railway deployment"
git push
```

### 2. צור פרויקט ב-Railway
1. https://railway.app/ → Login with GitHub
2. New Project → Deploy from GitHub repo
3. בחר `SafeQCloudManager`

### 3. הגדר משתני סביבה
לחץ על Service → Variables → Raw Editor והדבק:

```
SERVER_URL=https://your-safeq-server.com:7300
API_KEY=your_api_key
TENANT_ID=your-tenant-id
CLIENT_ID=your-client-id
CLIENT_SECRET=your-client-secret
AUTHORITY=https://login.microsoftonline.com/YOUR_TENANT_ID
REDIRECT_URI=https://YOUR-APP.up.railway.app
ENABLE_GROUP_RESTRICTION=True
ROLE_VIEW_GROUP=SafeQ-View
ROLE_SUPPORT_GROUP=SafeQ-Support
ROLE_ADMIN_GROUP=SafeQ-Admin
ROLE_SUPERADMIN_GROUP=SafeQ-SuperAdmin
PROVIDER_LOCAL=12348
PROVIDER_ENTRA=12351
SESSION_TIMEOUT=120
USE_ENTRA_ID=True
LOG_TO_FILE=True
LOG_TO_DATABASE=True
```

### 4. קבל את ה-URL
- Railway יבנה ויפרוס אוטומטית
- Settings → Domains → תראה את ה-URL שלך

### 5. עדכן Redirect URI
**ב-Railway:**
- עדכן את `REDIRECT_URI` ל-URL האמיתי

**ב-Azure Portal:**
- Entra ID → App registrations → Authentication
- הוסף Redirect URI: `https://YOUR-APP.up.railway.app`

### ✅ זהו! האפליקציה אמורה לרוץ

---

## ✨ מה קרה מאחורי הקלעים?

הקבצים שנוצרו:
- `Procfile` - אומר ל-Railway איך להריץ את Streamlit
- `railway.toml` - תצורת deployment
- `.streamlit/config.toml` - הגדרות production
- `RAILWAY_DEPLOYMENT.md` - מדריך מפורט
- `.env.railway` - תבנית למשתני סביבה

**הקוד שלך לא השתנה!**
ה-`config.py` כבר תומך ב-Environment Variables מלכתחילה.

---

## 🔍 בדיקת תקינות

```bash
# בדוק logs ב-Railway
# לחץ על Deployments → הבחר ב-deployment האחרון → View Logs
```

אמור לראות:
```
You can now view your Streamlit app in your browser.
```

---

## 📚 לפרטים נוספים
ראה `RAILWAY_DEPLOYMENT.md`
