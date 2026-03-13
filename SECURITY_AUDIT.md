# PlanO Security Audit Report

**Date:** 2026-03-11
**Auditor:** Automated (Bandit, pip-audit, npm audit) + Manual code review
**Scope:** All PlanO source code across `plano_master/` and `plano-raster-engine/`

---

## Executive Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 3 |
| HIGH | 8 |
| MEDIUM | 9 |
| LOW | 6 |
| **Total** | **26** |

**Tools installed on C4ISR GPU server:**
- `bandit` 1.9.4 — Python static analysis (OWASP, CWE)
- `pip-audit` 2.10.0 — Python dependency CVE scanner
- `safety` 3.7.0 — Python dependency vulnerability checker
- npm audit — Node.js dependency scanner

---

## CRITICAL Findings

### C1. Hardcoded API Key in .env
- **File:** `01_raster/.env`
- **CWE:** CWE-798 (Use of Hard-coded Credentials)
- **Detail:** `RASTERSCAN_API_KEY=sk-5f772ff8a89eb07299645a2cc923a0594fe56b07`
- **Impact:** Full API access if leaked; key visible in plaintext
- **Fix:** Rotate key immediately, use environment variables, add `.env` to `.gitignore`

### C2. No Authentication on Any API Endpoint
- **Files:** `plano-raster-engine/server/app.py`, `01_raster/server/app_local.py`
- **CWE:** CWE-306 (Missing Authentication for Critical Function)
- **Detail:** All endpoints (`/api/upload`, `/api/upload-plan`, `/api/result/*`, `/api/metrics`) are fully open
- **Impact:** Anyone with network access can upload files, consume GPU resources, extract results
- **Fix:** Add API key middleware or JWT authentication

### C3. Wildcard CORS on app_local.py
- **File:** `01_raster/server/app_local.py:32`
- **CWE:** CWE-942 (Permissive CORS Policy)
- **Detail:** `allow_origins=["*"]` with `allow_credentials=True`
- **Impact:** Any website can make authenticated cross-origin requests
- **Fix:** Restrict to specific origins

---

## HIGH Findings

### H1. PostMessage with Wildcard targetOrigin
- **File:** `00_frontend_skeleton/plano-ui/src/components/planner/PlannerFrame.tsx:61`
- **CWE:** CWE-345 (Insufficient Verification of Data Authenticity)
- **Detail:** `w.postMessage(msg, "*")` sends to any origin
- **Impact:** Malicious parent/frame could intercept messages
- **Mitigated by:** Origin check on receive (line 113)
- **Fix:** Use specific origin: `w.postMessage(msg, ENGINE_URL)`

### H2. SHA1 Used for ID Generation (Bandit B324)
- **Files:** `rasterscan_to_reactplanner.py:5`, `plano-raster-engine/workers/scene_converter.py:13`
- **CWE:** CWE-327 (Use of Broken Crypto Algorithm)
- **Detail:** `hashlib.sha1()` for stable element IDs
- **Impact:** Low (not used for security, just deterministic IDs)
- **Fix:** Add `usedforsecurity=False` parameter or switch to SHA-256

### H3. Python Dependency CVEs (pip-audit)
- **Package:** `filelock 3.20.0` — CVE-2025-68146, CVE-2026-22701
- **Fix available:** Upgrade to 3.20.3
- **Package:** `setuptools 70.2.0` — PYSEC-2025-49
- **Fix available:** Upgrade to 78.1.1

### H4. NPM: serialize-javascript RCE (react-planner)
- **Severity:** HIGH
- **Advisory:** GHSA-5c6j-r48x-rmvq
- **Detail:** RCE via RegExp.flags and Date.prototype.toISOString()
- **Fix:** `npm audit fix` in `02_react_planner/react-planner/`

### H5. NPM: Rollup Path Traversal (plano-ui)
- **Severity:** HIGH
- **Advisory:** GHSA-mw96-cpmx-2vgc
- **Detail:** Arbitrary file write via path traversal in Rollup 4.0.0-4.58.0
- **Fix:** `npm audit fix` in `00_frontend_skeleton/plano-ui/`

### H6. NPM: Webpack SSRF (react-planner)
- **Severity:** HIGH
- **Advisory:** GHSA-8fgc-7cc6-rx7x, GHSA-38r7-794h-5758
- **Detail:** buildHttp allowedUris bypass leading to SSRF + cache persistence
- **Fix:** `npm audit fix`

### H7. NPM: minimatch ReDoS (plano-ui)
- **Severity:** HIGH
- **Advisory:** GHSA-3ppc-4f35-3m26, GHSA-7r86-cg39-jmmj, GHSA-23c5-xmqv-rm74
- **Fix:** `npm audit fix`

### H8. Internal IP Addresses in CORS Whitelist
- **File:** `plano-raster-engine/server/app.py:80-82`
- **CWE:** CWE-200 (Information Exposure)
- **Detail:** `192.168.50.226`, `192.168.50.187` hardcoded
- **Fix:** Use environment variable for allowed origins

---

## MEDIUM Findings

### M1. Binding to All Interfaces (Bandit B104)
- **File:** `plano-raster-engine/server/config.py:43`
- **Detail:** Default `0.0.0.0` binding exposes to all network interfaces
- **Fix:** Bind to `127.0.0.1` behind reverse proxy

### M2. Bare except:pass (Bandit B110)
- **File:** `plano-raster-engine/server/app.py:181,226`
- **CWE:** CWE-703 (Improper Check or Handling of Exceptional Conditions)
- **Detail:** Silent exception swallowing on file cleanup
- **Fix:** Use `except OSError: pass` or log the exception

### M3. No Rate Limiting
- **Files:** All FastAPI endpoints
- **CWE:** CWE-770 (Allocation of Resources Without Limits)
- **Detail:** Upload endpoints have no rate limiting
- **Fix:** Add `slowapi` rate limiter

### M4. No Content-Security-Policy
- **File:** `plano-raster-engine/web/index.html`
- **CWE:** CWE-1021 (Improper Restriction of Rendered UI Layers)
- **Fix:** Add CSP meta tag or header via reverse proxy

### M5. Hardcoded Absolute Paths
- **Files:** `plano-raster-engine/server/config.py`, `run.sh`
- **Detail:** `/home/hadrienm/` hardcoded, breaks portability, leaks username
- **Fix:** Use `Path(__file__).resolve().parent` or env vars

### M6. Redis No Authentication
- **File:** `plano-raster-engine/server/config.py` (REDIS_URL = localhost:6379 no password)
- **CWE:** CWE-306
- **Fix:** Set `requirepass` in Redis config

### M7. No HTTPS on API Server
- **Detail:** Uvicorn on port 8020 is plain HTTP
- **Fix:** Terminate TLS at reverse proxy (Apache/Caddy)

### M8. Error Messages Leak Internals
- **File:** `plano-raster-engine/server/app.py:186`
- **Detail:** `str(e)[:200]` stored in job status — may reveal stack traces
- **Fix:** Return generic error to client, log details server-side

### M9. sys.path Manipulation
- **Files:** `server/app.py:57,122`, `01_raster/server/app_local.py:19`
- **CWE:** CWE-426 (Untrusted Search Path)
- **Detail:** `sys.path.insert(0, ...)` could load unintended modules
- **Fix:** Use proper package structure with `__init__.py` and relative imports

---

## LOW Findings

### L1. No File Magic Byte Validation
- **Detail:** Only extension-based file type checking
- **Fix:** Add `python-magic` for MIME type validation

### L2. localStorage for Client State
- **File:** `plannerState.tsx` — key `plano:plannerSelections:v1`
- **Detail:** Sensitive selections stored in localStorage (XSS-accessible)

### L3. Unimplemented Admin Routes
- **File:** `App.tsx` — `/admin`, `/super-admin` routes defined but no auth guards

### L4. No Audit Logging
- **Detail:** No structured audit trail for uploads, job completions, errors

### L5. Job ID Not Validated
- **Detail:** `/api/status/{job_id}` and `/api/result/{job_id}` accept any string
- **Fix:** Validate hex format (32 chars)

### L6. Result Files Accessible Without Auth
- **Detail:** Anyone with a job_id can retrieve results via `/api/result/{job_id}`

---

## Dependency Vulnerability Summary

### Python (pip-audit on C4ISR GPU venv)
| Package | Version | CVE | Fix Version |
|---------|---------|-----|-------------|
| filelock | 3.20.0 | CVE-2025-68146 | 3.20.1 |
| filelock | 3.20.0 | CVE-2026-22701 | 3.20.3 |
| setuptools | 70.2.0 | PYSEC-2025-49 | 78.1.1 |

### NPM — plano-ui (3 vulnerabilities: 1 moderate, 2 high)
| Package | Severity | Advisory |
|---------|----------|----------|
| ajv | moderate | Schema validation |
| minimatch | high | ReDoS (3 advisories) |
| rollup | high | Path traversal |

### NPM — react-planner (13 vulnerabilities: 3 low, 4 moderate, 6 high)
| Package | Severity | Advisory |
|---------|----------|----------|
| serialize-javascript | high | RCE |
| webpack | high | SSRF (2 advisories) |
| express/body-parser | moderate | Multiple |
| postcss | moderate | Line return parsing |
| nth-check | moderate | ReDoS |

---

## Remediation Priority

### Immediate (do now)
1. Rotate RasterScan API key
2. Add `.env` to `.gitignore`
3. `npm audit fix` on both frontend projects
4. `pip install --upgrade filelock setuptools` on GPU venv

### Short-term (this week)
5. Add API key authentication middleware to FastAPI
6. Fix CORS: remove wildcard, use env-based origins
7. Fix postMessage targetOrigin in PlannerFrame.tsx
8. Add `usedforsecurity=False` to SHA1 calls
9. Replace bare `except: pass` with specific exception handling

### Medium-term
10. Add rate limiting (slowapi)
11. Add CSP headers
12. Set Redis password
13. Enable TLS termination
14. Add file magic byte validation
15. Validate job_id format
16. Sanitize error messages

---

## Tools Installed on C4ISR GPU Server

```
Location: /home/hadrienm/plano-raster-engine/.venv/
- bandit 1.9.4          (Python SAST)
- pip-audit 2.10.0      (CVE scanner)
- safety 3.7.0          (vulnerability DB)
```

Run scans:
```bash
# Bandit (static analysis)
source .venv/bin/activate
bandit -r server/ workers/ -ll

# pip-audit (dependency CVEs)
pip-audit

# Safety (vulnerability check)
safety check
```
