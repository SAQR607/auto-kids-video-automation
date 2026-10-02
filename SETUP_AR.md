# SETUP_AR.md — دليل الإعداد (بالعربية)

ستقوم بإنشاء مستودع GitHub، وإضافة الأسرار (Secrets)، وتشغيل خطوات OAuth لليوتيوب مرة واحدة، ثم تشغيل أول دفعة إنتاجية. يستغرق الأمر نحو 30 دقيقة، وكل الخطوات في المتصفح عدا ذلك.

> **قاعدة الجهاز المحلي:** كل ما يلي يعمل على **GitHub Actions** باستثناء أداة OAuth (`youtube-oauth`) التي تحتاج متصفحك مرة واحدة. لا تشغِّ أبدًا الإنتاج الكامل (توليد الصوت/الفيديو/النشر) على حاسوبك الشخصي.

## 1. المتطلبات الأولية

- حساب GitHub (المستودع العام = Actions مجاني بلا حدود)
- مفتاح Groq API: https://console.groq.com → API Keys
- بوت تيليجرام: تواصل مع [@BotFather](https://t.me/BotFather) → `/newbot`
- مشروع Google Cloud (لـ OAuth الخاص باليوتيوب)
- جهاز محلي ببايثون 3.12 (للاختبارات وأداة OAuth فقط)

## 2. رفع الكود

```bash
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin master
```

## 3. أسرار GitHub (Secrets)

المستودع → **Settings → Secrets and variables → Actions → New repository secret**:

| الاسم | القيمة |
|---|---|
| `GROQ_API_KEYS` | مفتاح Groq (مع مفتاحين أو أكثر مفصولة بفواصل يعمل تدوير الأخطاء تلقائيًا) |
| `TELEGRAM_BOT_TOKEN` | من BotFather (`123456:ABC...`) |
| `TELEGRAM_CHAT_ID` | معرّف المحادثة/القناة (الخطوة 4) |
| `YOUTUBE_CLIENT_ID` | من Google Cloud (الخطوة 5) |
| `YOUTUBE_CLIENT_SECRET` | من Google Cloud (الخطوة 5) |
| `YOUTUBE_REFRESH_TOKEN` | من `python -m app youtube-oauth` (الخطوة 5) |

`GROQ_API_KEYS` إلزامي، وتيليجرام موصى بشدة به، وثلاثة أسرار يوتيوب تصبح إلزامية وقت النشر (يُنبه `doctor` بتحذير حتى ذلك الحين).

## 4. معرّف محادثة تيليجرام

1. أرسل أي رسالة إلى بوتك (أو أضفه إلى قناة كمشرف).
2. افتح `https://api.telegram.org/bot<TOKEN>/getUpdates` في المتصفح.
3. اقرأ `result[].message.chat.id` (قنوات بأرقام سالبة).

## 5. OAuth لليوتيوب (مرة واحدة، بمحركك المحلي)

1. Google Cloud Console → أنشئ مشروعًا → **فعّل YouTube Data API v3**.
2. **OAuth consent screen**: نوع External، وأضف حسابك في Test users.
3. **Credentials → Create → OAuth client ID → Desktop app** → انسخ Client ID و Client Secret.
4. محليًا:

   ```bash
   python -m app init
   # ضع YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET في ملف .env ثم:
   python -m app youtube-oauth
   ```

5. افتح الرابط المطبوع، ووافق على الوصول، والصق الرمز في الطرفية. ستظهر لك قيمة
   `YOUTUBE_REFRESH_TOKEN` — ضعها في أسرار GitHub (وإن أردت في `.env` أيضًا).

## 6. التحقق قبل أول دفعة حقيقية

شغّل بالترتيب (Actions → workflow → **Run workflow**):

1. **`health_check`** → يشغّل كامل الاختبارات + doctor. يجب أن يكون أخضر.
2. **`production`** بوضع `mode=sample` → يبني ثوانٍ من حلقة كاملة
   (Groq → صوت → فيديو → فحص جودة، دون نشر).
3. **`production`** بوضع `mode=dry-run` → بناء بطول كامل + فحص جودة، دون نشر؛
   تتوقف الحالة عند `RENDER_QC`.
4. دفعة حقيقية: `mode=production`، أو انتظر الجدولة (الاثنين–السبت 16:05 بتوقيت UTC).

راقب محادثة تيليجرام: رسالة **SUCCESS** برابط اليوتيوب تعني اكتمال الحلقة،
ورسالة **RED ALERT** تذكر المرحلة التي فشلت.

## 7. إعدادات القناة (YouTube Studio، مرة واحدة)

- اضبط إعداد القناة للأطفال (المحتوى الموجّه للأطفال) — الواجهة البرمجية ترسل أيضًا
  `selfDeclaredMadeForKids=true` لكل فيديو.
- أكِّل تحقق القناة (مطلوب قبل مقاطع أطول من 15 دقيقة — مقاطعنا ≤10 دقائق،
  لكن التحقق يتيح أيضًا الصور المصغّرة المخصصة).

## قائمة التحقق

- [ ] تم رفع المستودع، والفرع الافتراضي `master`
- [ ] الأسرار: `GROQ_API_KEYS` (+ تيليجرام، + يوتيوب ×3)
- [ ] `health_check` أخضر
- [ ] `production` بوضع `mode=sample` أخضر
- [ ] `production` بوضع `mode=dry-run` أخضر (الحالة `RENDER_QC`)
- [ ] أول دفعة حقيقية تنشر وتبثّ SUCCESS على تيليجرام
