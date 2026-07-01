"""
Security Logging Middleware
============================
Captures ALL HTTP requests and writes security-relevant fields to a
structured log file consumed by the Splunk Universal Forwarder.

Log Format (Splunk-friendly key=value):
  timestamp | level | src_ip | method | uri | status | user_agent | params | body
"""

import os
import json
import logging
import datetime
from django.conf import settings


# ─── Configure file handler ───────────────────────────────────────────────────
LOG_FILE = getattr(settings, 'SECURITY_LOG_FILE', r'C:\DjangoApp\logs\security.log')

# Ensure the log directory exists
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

security_logger = logging.getLogger('django_security')
security_logger.setLevel(logging.INFO)

if not security_logger.handlers:
    fh = logging.FileHandler(LOG_FILE, encoding='utf-8')
    fh.setLevel(logging.INFO)
    # Clean, Splunk-ingestible format
    formatter = logging.Formatter('%(message)s')
    fh.setFormatter(formatter)
    security_logger.addHandler(fh)
    security_logger.propagate = False


# ─── Known Attack Signatures (lightweight pattern matching) ───────────────────
SQLI_PATTERNS = [
    "' OR", "' AND", "1=1", "1 = 1", "' --", "' #",
    "UNION SELECT", "UNION ALL SELECT", "DROP TABLE",
    "INSERT INTO", "'; --", "OR 1=1", "OR '1'='1",
    "SLEEP(", "BENCHMARK(", "WAITFOR DELAY", "xp_cmdshell",
]

XSS_PATTERNS = [
    "<script", "</script>", "javascript:", "onerror=",
    "onload=", "onclick=", "alert(", "document.cookie",
    "document.write", "<img", "<svg", "<iframe",
    "eval(", "String.fromCharCode",
]

PATH_TRAVERSAL_PATTERNS = ["../", "..\\", "%2e%2e", "%2f"]

COMMAND_INJECTION_PATTERNS = ["; ls", "; cat", "| id", "| whoami", "&& id", "$("]


def classify_threat(payload: str) -> str:
    """Return the most likely threat category for a given payload string."""
    payload_upper = payload.upper()

    for pattern in SQLI_PATTERNS:
        if pattern.upper() in payload_upper:
            return "SQL_INJECTION"

    for pattern in XSS_PATTERNS:
        if pattern.lower() in payload.lower():
            return "XSS"

    for pattern in PATH_TRAVERSAL_PATTERNS:
        if pattern.lower() in payload.lower():
            return "PATH_TRAVERSAL"

    for pattern in COMMAND_INJECTION_PATTERNS:
        if pattern.lower() in payload.lower():
            return "COMMAND_INJECTION"

    return "BENIGN"


class SecurityLoggingMiddleware:
    """
    Django middleware that intercepts every request/response cycle and
    writes a structured security event to security.log.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # ── Gather request metadata ──────────────────────────────────────────
        timestamp    = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        src_ip       = self._get_client_ip(request)
        method       = request.method
        uri          = request.get_full_path()
        user_agent   = request.META.get('HTTP_USER_AGENT', 'Unknown')
        referer      = request.META.get('HTTP_REFERER', '-')
        host         = request.META.get('HTTP_HOST', '-')

        # ── Extract all parameters ───────────────────────────────────────────
        get_params   = dict(request.GET)
        post_params  = {}
        raw_body     = ''

        try:
            if request.content_type and 'application/json' in request.content_type:
                raw_body = request.body.decode('utf-8', errors='replace')
                post_params = json.loads(raw_body) if raw_body else {}
            else:
                post_params = dict(request.POST)
                raw_body = request.body.decode('utf-8', errors='replace')
        except Exception:
            pass

        # ── Build combined payload string for threat classification ──────────
        all_values = []
        for v in get_params.values():
            all_values.extend(v if isinstance(v, list) else [v])
        for v in post_params.values():
            all_values.extend(v if isinstance(v, list) else [str(v)])
        all_values.append(uri)

        combined_payload = ' '.join(all_values)
        threat_type      = classify_threat(combined_payload)
        severity         = 'HIGH' if threat_type != 'BENIGN' else 'INFO'

        # ── Process request → get response ───────────────────────────────────
        response = self.get_response(request)
        status_code = response.status_code

        # ── Sanitize for single-line log entry ───────────────────────────────
        def safe(val):
            return str(val).replace('\n', ' ').replace('\r', ' ').replace('"', "'")

        # ── Write structured log line (Splunk key=value format) ──────────────
        log_entry = (
            f'timestamp="{timestamp}" '
            f'severity="{severity}" '
            f'threat_type="{threat_type}" '
            f'src_ip="{src_ip}" '
            f'method="{method}" '
            f'host="{safe(host)}" '
            f'uri="{safe(uri)}" '
            f'status="{status_code}" '
            f'user_agent="{safe(user_agent)}" '
            f'referer="{safe(referer)}" '
            f'get_params="{safe(json.dumps(get_params))}" '
            f'post_params="{safe(json.dumps(post_params))}" '
            f'raw_body="{safe(raw_body[:500])}"'   # Truncate body at 500 chars
        )

        if severity == 'HIGH':
            security_logger.warning(log_entry)
        else:
            security_logger.info(log_entry)

        return response

    @staticmethod
    def _get_client_ip(request) -> str:
        """Extract real client IP, respecting X-Forwarded-For (proxy/WAF)."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '0.0.0.0')