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

@app.get("/duty")
def duty(code: str, country: str):
    try:
        r = requests.get(
            HTS_API.format(c=code[:10]),
            timeout=5,
            headers={"User-Agent": "FortunyDutyRobot/1.0"})
        r.raise_for_status()
        data = r.json()
        if not data:
            raise HTTPException(status_code=404, detail="Codice HTS non trovato")
        base_str = data[0].get("general_rate_of_duty", "0%").rstrip("%")
        base = float(base_str or 0)
    except HTTPException as e:
        raise e
    except Exception as e:          # include timeout, JSON error, ecc.
        print("HTS API error:", e)
        raise HTTPException(status_code=502, detail="Errore upstream HTS")

    s301 = extra_s301(code)
    return {
        "hts_code": code,
        "country": country,
        "base_rate": base,
        "surcharge_301": s301,
        "total_rate": base + s301
    }
