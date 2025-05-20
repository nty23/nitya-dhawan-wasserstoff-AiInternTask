

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import uuid
import re

from services.qa import build_vector_db_from_text, answer_question
import pytesseract
from PIL import Image
import pdfplumber

UPLOAD_FOLDER = "backend/app/data"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
CORS(app)

vector_dbs = {}
document_store = []

def extract_metadata_from_filename(filename):
    parts = filename.replace(".pdf", "").split("_")
    year = next((p for p in parts if p.isdigit()), "Unknown")
    author = next((p for p in parts if p.lower().startswith("author")), "Unknown")
    doc_type = next((p for p in parts if p.lower() in ["report", "case", "policy"]), "Unknown")
    return year, author, doc_type

def extract_text(file_path):
    if file_path.endswith(".pdf"):
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        return text
    else:
        image = Image.open(file_path)
        return pytesseract.image_to_string(image)

@app.route("/upload", methods=["POST"])
def upload_file():
    global vector_dbs, document_store

    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "No files uploaded"}), 400

    uploaded = []
    for file in files:
        filename = file.filename
        doc_id = f"DOC{str(uuid.uuid4())[:6].upper()}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        text = extract_text(filepath)
        vector_db = build_vector_db_from_text(text, doc_id=doc_id)

        year, author, doc_type = extract_metadata_from_filename(filename)

        vector_dbs[doc_id] = vector_db
        document_store.append({
            "id": doc_id,
            "filename": filename,
            "text": text,
            "year": year,
            "author": author,
            "type": doc_type
        })

        uploaded.append({
            "id": doc_id,
            "filename": filename,
            "text": text,
            "year": year,
            "author": author,
            "type": doc_type
        })

    return jsonify({"message": "Upload successful", "documents": uploaded}), 200

@app.route("/ask", methods=["POST"])
def ask_question():
    global vector_dbs, document_store

    data = request.get_json()
    question = data.get("question", "")

    if not question:
        return jsonify({"error": "No question provided"}), 400
    if not vector_dbs or not document_store:
        return jsonify({"error": "No documents available"}), 400

    results = []

    for doc in document_store:
        doc_id = doc["id"]
        filename = doc["filename"]
        vector_db = vector_dbs.get(doc_id)

        if not vector_db:
            continue

        result = answer_question(vector_db, question)
        if result["answer"].strip():
            results.append({
                "doc_id": doc_id,
                "filename": filename,
                "answer": result["answer"],
                "citations": result["citations"],
                "year": doc.get("year"),
                "author": doc.get("author"),
                "type": doc.get("type")
            })

    return jsonify({"results": results}), 200

if __name__ == "__main__":
    app.run(debug=True)
