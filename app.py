from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import pandas as pd
import io
import os
import json
from openai import OpenAI


# Initialize FastAPI app

app = FastAPI(title="Lead Scoring Backend", description="Scores leads using rule-based + AI logic")
@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <html>
        <head>
            <title>Lead Scoring Backend</title>
        </head>
        <body>
            <h1>Lead Scoring Backend is Running!</h1>
            <p>Available API Endpoints:</p>
            <ul>
                <li>POST /offer → Upload a product/offer</li>
                <li>POST /leads/upload → Upload leads CSV</li>
                <li>POST /score → Score uploaded leads</li>
                <li>GET /results → View scored leads</li>
                <li>GET /results/export → Download scored leads CSV</li>
            </ul>
            <p>Use Postman or cURL to interact with POST endpoints.</p>
        </body>
    </html>
    """


# Pydantic model

class Offer(BaseModel):
    name: str
    value_props: list[str]
    ideal_use_cases: list[str]


# In-memory storage

OFFER_DATA: dict = {}
LEADS_DF: pd.DataFrame | None = None
RESULTS: list[dict] = []


# OpenAI setup

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("WARNING: OPENAI_API_KEY not set. Using fallback reasoning.")
    client = None
else:
    client = OpenAI(api_key=api_key)
    print("OpenAI client initialized successfully.")


# Upload offer

@app.post("/offer")
async def upload_offer(offer: Offer):
    global OFFER_DATA
    OFFER_DATA = offer.dict()
    return {"message": "Offer data uploaded successfully", "offer": OFFER_DATA}


# Upload leads CSV

@app.post("/leads/upload")
async def upload_leads(file: UploadFile = File(...)):
    global LEADS_DF
    try:
        contents = await file.read()
        LEADS_DF = pd.read_csv(io.BytesIO(contents))
        return {"message": "Leads uploaded successfully", "rows": len(LEADS_DF)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading CSV: {e}")


# Rule-based scoring

def rule_based_score(lead: dict, offer: dict) -> int:
    score = 0
    role = str(lead.get("role", "")).lower()
    if any(k in role for k in ["head", "director", "vp", "founder", "ceo"]):
        score += 20
    elif any(k in role for k in ["manager", "lead", "specialist"]):
        score += 10

    industry = str(lead.get("industry", "")).lower()
    if offer and offer.get("ideal_use_cases"):
        icp = offer["ideal_use_cases"][0].lower()
        if icp in industry:
            score += 20
        elif any(word in industry for word in icp.split()):
            score += 10

    if all(lead.get(col) for col in ["name", "role", "company", "industry", "location", "linkedin_bio"]):
        score += 10

    return score


# AI-based scoring (Fixed)

def ai_score_and_reason(lead: dict, offer: dict) -> dict:
    """Return dict: {intent, reasoning}"""
    if not client:
        return {"intent": "Medium", "reasoning": "AI not configured; using default reasoning."}

    prompt = f"""
    You are a B2B sales assistant. Based on the following lead and offer,
    classify the buying intent as High, Medium, or Low,
    and explain in 1–2 short sentences.

    Respond ONLY in valid JSON with keys:
    - intent
    - reasoning

    Offer: {json.dumps(offer, ensure_ascii=False)}
    Lead: {json.dumps(lead, ensure_ascii=False)}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # You can change to gpt-5 if available
            messages=[
                {"role": "system", "content": "You are an expert B2B lead qualification assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
        )

        text = response.choices[0].message.content.strip()

        # Remove markdown if present
        if text.startswith("```json"):
            text = text.replace("```json", "").replace("```", "").strip()

        data = json.loads(text)
        if not isinstance(data, dict) or "intent" not in data or "reasoning" not in data:
            raise ValueError("Invalid AI response format")

        return data

    except Exception as e:
        print(f"AI Error: {e}")
        return {"intent": "Medium", "reasoning": "Default reasoning due to AI error."}


# Combine Rule + AI scoring

@app.post("/score")
async def score_leads():
    global LEADS_DF, OFFER_DATA, RESULTS
    if LEADS_DF is None or not OFFER_DATA:
        raise HTTPException(status_code=400, detail="Please upload both offer and leads first.")

    RESULTS = []
    for _, lead in LEADS_DF.iterrows():
        lead_dict = lead.to_dict()
        rule_score = rule_based_score(lead_dict, OFFER_DATA)
        ai_data = ai_score_and_reason(lead_dict, OFFER_DATA)

        intent = ai_data.get("intent", "Medium")
        reasoning = ai_data.get("reasoning", "")

        # AI layer (max 50 pts)
        ai_points = {"High": 50, "Medium": 30, "Low": 10}.get(intent, 30)
        final_score = rule_score + ai_points

        RESULTS.append({
            "name": lead_dict.get("name"),
            "role": lead_dict.get("role"),
            "company": lead_dict.get("company"),
            "intent": intent,
            "score": final_score,
            "reasoning": reasoning
        })

    return RESULTS


# Get results

@app.get("/results")
async def get_results():
    if not RESULTS:
        raise HTTPException(status_code=400, detail="No scored results available. Run /score first.")
    return RESULTS


# Export results as CSV

@app.get("/results/export")
async def export_results():
    if not RESULTS:
        raise HTTPException(status_code=400, detail="No scored results available to export.")
    df = pd.DataFrame(RESULTS)
    file_path = "scored_leads.csv"
    df.to_csv(file_path, index=False)
    return FileResponse(path=file_path, filename="scored_leads.csv", media_type="text/csv")

