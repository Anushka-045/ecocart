from flask import Flask, request, jsonify
from flask_cors import CORS
print ("FILE STARTED")
import requests
import json
import os
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from docx import Document
import pytesseract
import io
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

load_dotenv()
api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    raise Exception("OPENROUTER_API_KEY not found. Check your .env file")

app = Flask(__name__)
CORS(app)

app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
MAX_CHARS = 8000


@app.route("/")
def home():
    return "EcoCart + BRD Backend Running"


@app.route("/generate", methods=["POST"])
def generate():
    data = request.json
    if not data or "text" not in data:
        return jsonify({"error": "No text provided"}), 400

    user_text = data.get("text")
    if len(user_text) > MAX_CHARS:
        user_text = user_text[:MAX_CHARS]

    result = generate_from_text(user_text)
    return jsonify(result)


@app.route("/upload-file", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    filename = file.filename.lower()

    if filename.endswith(".txt"):
        try:
            file_content = file.read().decode("utf-8")
        except:
            return jsonify({"error": "Unable to read TXT file"}), 400

    elif filename.endswith(".pdf"):
        try:
            pdf_bytes = file.read()
            pdf_stream = io.BytesIO(pdf_bytes)
            reader = PdfReader(pdf_stream)

            text = ""
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"

            if not text.strip():
                return jsonify({"error": "PDF has no readable text"}), 400

            if len(text) > MAX_CHARS:
                text = text[:MAX_CHARS]

            file_content = text

        except Exception as e:
            return jsonify({"error": f"Unable to read PDF: {str(e)}"}), 400

    elif filename.endswith(".docx"):
        try:
            document = Document(file)
            text = ""
            for para in document.paragraphs:
                text += para.text + "\n"

            if not text.strip():
                return jsonify({"error": "DOCX has no readable text"}), 400

            file_content = text

        except Exception as e:
            return jsonify({"error": f"Unable to read DOCX: {str(e)}"}), 400

    elif filename.endswith((".png", ".jpg", ".jpeg")):
        try:
            image = Image.open(file)
            text = pytesseract.image_to_string(image)
            if not text.strip():
                return jsonify({"error": "No readable text found in image"}), 400
            file_content = text
        except Exception as e:
            return jsonify({"error": f"Unable to read image: {str(e)}"}), 400
    else:
        return jsonify({"error": "Unsupported file type"}), 400

    result = generate_from_text(file_content)
    return jsonify(result)


@app.route("/edit", methods=["POST"])
def edit():
    data_input = request.json
    if not data_input:
        return jsonify({"error": "Invalid request"}), 400

    current_brd = data_input.get("current_brd")
    instruction = data_input.get("instruction")

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    prompt = f"""
    Update the following BRD JSON based on the instruction.
    Return only valid JSON.

    BRD:
    {json.dumps(current_brd)}

    Instruction:
    {instruction}
    """

    data = {
        "model": "deepseek/deepseek-chat",
        "messages": [{"role": "user", "content": prompt}]
    }

    response = requests.post(url, headers=headers, json=data, timeout=30)
    result = response.json()

    if "choices" not in result:
        return jsonify({"error": "AI service failed"}), 500

    ai_reply = result["choices"][0]["message"]["content"]
    ai_reply = ai_reply.replace("```json", "").replace("```", "").strip()

    try:
        updated_json = json.loads(ai_reply)
    except:
        updated_json = {"error": "Invalid JSON from AI"}

    return jsonify(updated_json)


@app.route("/eco-analyze", methods=["POST"])
def eco_analyze():
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    product_url = data.get("url", "")
    title = data.get("title", "")
    description = data.get("description", "")

    if not title and not description:
        return jsonify({"error": "Product title or description required"}), 400

    result = eco_analysis(title, description, product_url)
    return jsonify(result)


def eco_analysis(title, description, product_url):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    prompt = f"""
    You are an EcoScan system.

    Product URL: {product_url}
    Title: {title}
    Description: {description}

    Return only valid JSON in this format:

    {{
      "scan_result": {{
        "eco_score": 0-100,
        "verdict": "Eco Approved / Use With Caution / Not Eco Friendly",
        "impact_level": "Low / Moderate / High",
        "confidence": "High / Medium / Low"
      }},
      "signals": {{
        "positive": [],
        "negative": []
      }},
      "impact_insight": "",
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
            "scan_result": {
                "eco_score": 50,
                "verdict": "Use With Caution",
                "impact_level": "Moderate",
                "confidence": "Low"
            },
            "signals": {
                "positive": [],
                "negative": ["Unable to analyze properly"]
            },
            "impact_insight": "Analysis uncertainty due to limited data.",
            "recommendation": "Check product material and packaging details."
        }

    eco_json["status"] = "EcoScan Complete"
    eco_json["product_url"] = product_url

    return eco_json


def generate_from_text(user_text):
    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    prompt = f"""
    Extract project information and return valid JSON.
    Text:
    {user_text}
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
        ai_json = json.loads(ai_reply)
    except:
        ai_json = {"error": "Invalid JSON from AI"}

    return ai_json


if __name__ == "__main__":
    print("SERVER STARTING")
    app.run(host="0.0.0.0", port=5000, debug=True)