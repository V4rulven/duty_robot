# duty_robot.py
from fastapi import FastAPI
import requests

app = FastAPI()

# Due “librerie pubbliche” dove andiamo a leggere i dazi
HTS_API = "https://hts.usitc.gov/api/export?format=json&from={c}&to={c}"
FR_API  = "https://www.federalregister.gov/api/v1/documents.json"

def extra_s301(code):
    r = requests.get(FR_API, params={
        "conditions[term]": f"Section 301 {code[:4]}",
        "order":"newest", "per_page":1 })
    return 25 if r.ok and r.json().get("count") else 0

@app.get("/duty")
def duty(code:str, country:str):
    base_r = requests.get(HTS_API.format(c=code)).json()[0]["general_rate_of_duty"]
    base = float(base_r.rstrip("%"))
    return {
        "hts_code": code,
        "country":  country,
        "base_rate": base,
        "surcharge_301": extra_s301(code),
        "total_rate": base + extra_s301(code)
    }
