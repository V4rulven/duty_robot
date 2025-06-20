"""
duty_robot.py  –  micro-servizio FastAPI per calcolare il dazio
────────────────────────────────────────────────────────────────
• GET /duty?code=4011101020&country=Thailand → JSON con base_rate,
  surcharge_301 e total_rate
• Richiede: pip install fastapi "uvicorn[standard]" requests
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import requests, time, datetime, typing as t

app = FastAPI(title="Fortuny Duty Robot", version="1.1.0")

# ──────────────────────────────────────────────
#  Config
# ──────────────────────────────────────────────
HTS_API = "https://hts.usitc.gov/api/export?format=json&from={c}&to={c}"
FR_API  = "https://www.federalregister.gov/api/v1/documents.json"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0 Safari/537.36 FortunyDutyRobot/1.1"
    ),
    "Accept":       "application/json",
    "Referer":      "https://hts.usitc.gov/",
}
CACHE_TTL_SECONDS = 24 * 60 * 60            # 24 h

# Memoria-cache semplice {code: (timestamp, data_dict)}
_cache: dict[str, tuple[float, dict]] = {}

# ──────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────
def _cache_get(code: str) -> t.Optional[dict]:
    rec = _cache.get(code)
    if rec and (time.time() - rec[0] < CACHE_TTL_SECONDS):
        return rec[1]
    return None

def _cache_set(code: str, data: dict) -> None:
    _cache[code] = (time.time(), data)

def extra_s301(code: str) -> int:
    """Restituisce 25 se l'ultimo avviso Section 301 cita il codice, altrimenti 0."""
    try:
        r = requests.get(
            FR_API,
            params={
                "conditions[term]": f"Section 301 {code[:4]}",
                "order": "newest",
                "per_page": 1,
            },
            timeout=5,
            headers=HEADERS,
        )
        if r.ok and r.json().get("count", 0):
            return 25
    except Exception as e:
        print("Section 301 lookup failed:", e)
    return 0

def fetch_base_rate(code: str) -> float:
    """Interroga l'API USITC; ritorna l'aliquota base oppure solleva HTTPException."""
    # 1. cache
    cached = _cache_get(code)
    if cached:
        return cached["base_rate"]

    url = HTS_API.format(c=code[:10])
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
    except requests.exceptions.RequestException as e:
        print("HTS API network error:", e)
        raise HTTPException(502, detail="HTS API non raggiungibile")

    # Controllo status-code
    if r.status_code == 403:
        raise HTTPException(502, detail="HTS API blocca la richiesta (403)")
    if not r.ok:
        raise HTTPException(502, detail=f"HTS API status {r.status_code}")

    # Controllo Content-Type
    if "application/json" not in r.headers.get("content-type", ""):
        print("HTS API returned non-JSON, first 200 chars:", r.text[:200])
        raise HTTPException(502, detail="HTS API ha restituito HTML")

    try:
        data = r.json()
    except ValueError as e:
        print("HTS API JSON decode error:", e)
        raise HTTPException(502, detail="HTS API JSON non valido")

    if not data:
        raise HTTPException(404, detail="Codice HTS non trovato")

    base_str = data[0].get("general_rate_of_duty", "0%").strip().rstrip("%")
    base_rate = float(base_str or 0.0)

    # salva in cache
    _cache_set(code, {"base_rate": base_rate})

    return base_rate

# ──────────────────────────────────────────────
#  Endpoint principale
# ──────────────────────────────────────────────
@app.get("/duty", response_class=JSONResponse)
def duty(code: str, country: str):
    """
    Esempio: /duty?code=4011101020&country=Thailand
    Ritorna: {
        "hts_code": "4011101020",
        "country": "Thailand",
        "base_rate": 4.0,
        "surcharge_301": 25,
        "total_rate": 29.0,
        "timestamp": "2025-06-20T13:45:00Z"
    }
    """
    # 1. Valida input
    if not code.isdigit():
        raise HTTPException(400, "code deve essere numerico (4-10 cifre)")
    if len(code) < 4 or len(code) > 10:
        raise HTTPException(400, "code deve avere 4-10 cifre")

    # 2. Aliquota base + Section 301
    base_rate   = fetch_base_rate(code)
    surcharge   = extra_s301(code)
    total_rate  = base_rate + surcharge

    return {
        "hts_code":     code,
        "country":      country,
        "base_rate":    base_rate,
        "surcharge_301": surcharge,
        "total_rate":   total_rate,
        "timestamp":    datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }

# ──────────────────────────────────────────────
#  (Opzionale) CORS per test via browser
# ──────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)
