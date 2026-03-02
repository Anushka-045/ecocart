from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv()
api_key = os.getenv("OPENROUTER_API_KEY")

if not api_key:
    raise Exception("OPENROUTER_API_KEY not found. Check environment variables")

app = Flask(__name__)
CORS(app)


# ----------------------------------
# HOME
# ----------------------------------
@app.route("/")
def home():
    return "EcoScan Backend Running"


# ----------------------------------
# AUTO WEB SCRAPER
# ----------------------------------
def scrape_product_data(product_url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        response = requests.get(product_url, headers=headers, timeout=10)

        if response.status_code != 200:
            return "", ""

        soup = BeautifulSoup(response.text, "html.parser")

        # Extract title
        title = ""
        if soup.title:
            title = soup.title.string.strip()

        # Extract meta description
        description = ""
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            description = meta_desc["content"]

        return title, description

    except:
        return "", ""


# ----------------------------------
# ECO ANALYZE API
# ----------------------------------
@app.route("/eco-analyze", methods=["POST"])
def eco_analyze():
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    product_url = data.get("url", "")
    title = data.get("title", "")
    description = data.get("description", "")

    # Auto scrape if URL provided but no text
    if product_url and not title and not description:
        scraped_title, scraped_desc = scrape_product_data(product_url)
        title = scraped_title
        description = scraped_desc

    if not title and not description:
        return jsonify({"error": "Unable to fetch product data"}), 400

    result = eco_analysis(title, description, product_url)
    return jsonify(result)


# ----------------------------------
# ECO AI FUNCTION
# ----------------------------------
def eco_analysis(title, description, product_url):
    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    prompt = f"""
You are an Eco Product Analysis system.

Product URL: {product_url}
Title: {title}
Description: {description}

Return ONLY valid JSON:

{{
  "eco_score": 0-100,
  "verdict": "Eco Approved / Use With Caution / Not Eco Friendly",
  "impact_level": "Low / Moderate / High",
  "confidence": "High / Medium / Low",
  "positive_signals": [],
  "negative_signals": [],
  "recommendation": ""
}}
"""

    data = {
        "model": "deepseek/deepseek-chat",
        "messages": [{"role": "user", "content": prompt}]
    }

    response = requests.post(url, headers=headers, json=data, timeout=30)
    result = response.json()

    if "choices" not in result:
        return {"error": "AI service failed"}

    ai_reply = result["choices"][0]["message"]["content"]
    ai_reply = ai_reply.replace("```json", "").replace("```", "").strip()

    try:
        eco_json = json.loads(ai_reply)
    except:
        eco_json = {
            "eco_score": 50,
            "verdict": "Use With Caution",
            "impact_level": "Moderate",
            "confidence": "Low",
            "positive_signals": [],
            "negative_signals": ["Analysis failed"],
            "recommendation": "Check product details manually"
        }

    eco_json["status"] = "EcoScan Complete"
    eco_json["product_url"] = product_url

    return eco_json


# ----------------------------------
# RUN SERVER
# ----------------------------------
if __name__ == "__main__":
    print("EcoScan Server Starting")
    app.run(host="0.0.0.0", port=5000, debug=True)