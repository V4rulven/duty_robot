from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import requests, json

app = FastAPI()
HTS_API = "https://hts.usitc.gov/api/export?format=json&from={c}&to={c}"
FR_API  = "https://www.federalregister.gov/api/v1/documents.json"

def extra_s301(code: str) -> int:
    try:
        r = requests.get(
            FR_API,
            params={
                "conditions[term]": f"Section 301 {code[:4]}",
                "order": "newest",
                "per_page": 1},
            timeout=5,
            headers={"User-Agent": "FortunyDutyRobot/1.0"})
        if r.ok and r.json().get("count"):
            return 25
    except Exception as e:
        print("Section 301 lookup failed:", e)
    return 0   # fallback: nessuna sovrattassa

import random

HEADERS = {
    "User-Agent": "Mozilla/5.0 (FortunyDutyRobot)",
    "Accept": "application/json",
    "Referer": "https://hts.usitc.gov/",
}

@app.get("/duty")
def duty(code: str, country: str):
    url = HTS_API.format(c=code[:10])
    try:
       r = requests.get(url, headers=HEADERS, timeout=10)
print("HTS status", r.status_code, r.headers.get("content-type"))
print(r.text[:250])          # primi 250 caratteri di risposta
r.raise_for_status()
data = r.json()
        if not data:
            raise HTTPException(404, "Codice HTS non trovato")
        # ... come prima
    except requests.exceptions.JSONDecodeError:
        print("HTS API ha restituito HTML, retry fra 1-2 s")
        raise HTTPException(502, "HTS API ha restituito HTML invece di JSON")
    except Exception as e:
        print("HTS API error:", e)
        # Fallback d’emergenza: restituisci un numero “sconosciuto”
        return {
            "hts_code": code,
            "country": country,
            "base_rate": None,
            "surcharge_301": None,
            "total_rate": None,
            "note": "HTS API non disponibile"
        }
        "hts_code": code,
        "country": country,
        "base_rate": base,
        "surcharge_301": s301,
        "total_rate": base + s301
    }
