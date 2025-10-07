# leadscoringbackend
This repository contains a FastAPI backend for scoring B2B leads using a combination of rule-based logic and AI reasoning. It classifies leads as High, Medium, or Low intent and assigns a numerical score (0–100) to help sales teams prioritize prospects efficiently.
Lead Scoring Backend – Scores leads using rule-based logic + AI reasoning.


Live Deployment URL
https://leadscoringbackend.onrender.com

//Set Up Instructions

# Cloning the repository
git clone <https://github.com/bharathkumar89/leadscoringbackend>
cd lead_scoring_backend

# Creating virtual environment
python -m venv venv
venv\Scripts\activate     

# Installing dependencies
pip install -r requirements.txt

# Set OpenAI API key in environment variable
setx OPENAI_API_KEY "my_key"    

# Running the app locally
uvicorn app:app --host 0.0.0.0 --port 8000


//API usage examples (cURL/Postman)

Upload Offer:
curl -X POST https://leadscoringbackend.onrender.com/offer \
-H "Content-Type: application/json" \
-d '{
    "name": "AI Outreach Automation",
    "value_props": ["24/7 outreach", "6x more meetings"],
    "ideal_use_cases": ["B2B SaaS mid-market"]
}'

Upload leads csv:
curl -X POST https://leadscoringbackend.onrender.com/leads/upload \
-F "file=@leads.csv"

Score leads:
curl -X POST https://leadscoringbackend.onrender.com/score

Get Results:
curl -X GET https://leadscoringbackend.onrender.com/results

rule logic & ai prompts:

rule-based scoring :
role relevance: decision maker (+20), influencer (+10), else 0
industry match: exact icp (+20), adjacent (+10), else 0
data completeness: all fields present (+10)

ai scoring:
send lead + offer to openai, classify intent (high/medium/low)
high = 50, medium = 30, low = 10

final score = rule_score + ai_points



