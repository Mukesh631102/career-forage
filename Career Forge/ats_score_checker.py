# pip install transformers torch PyMuPDF scikit-learn

import fitz  # PyMuPDF
import re
import torch
import numpy as np
from transformers import AutoTokenizer, AutoModel
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from torch import nn
from datetime import datetime
import unicodedata

# ✅ Remove all non-ASCII characters
def sanitize_text(text):
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r'[^\x00-\x7F]+', '', text)  # Remove non-ASCII
    text = re.sub(r'[^\w\s]', '', text)        # Remove punctuation
    text = re.sub(r'\s+', ' ', text)           # Collapse whitespace
    return text.lower()

# ✅ Safe print for Windows terminal
def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="ignore").decode())

# ✅ Load tokenizer and model
tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")
model = AutoModel.from_pretrained("distilbert-base-uncased")

# ✅ Extract text from PDF
def extract_text_from_pdf(path):
    doc = fitz.open(path)
    text = ""
    for page in doc:
        page_text = page.get_text()
        if isinstance(page_text, bytes):
            page_text = page_text.decode("utf-8", errors="ignore")
        text += page_text
    return sanitize_text(text)

# ✅ Embedding using DistilBERT
def get_embedding(text):
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        outputs = model(**inputs)
    return outputs.last_hidden_state.mean(dim=1).squeeze().numpy()

# ✅ Semantic similarity
def semantic_similarity(text1, text2):
    emb1 = get_embedding(text1)
    emb2 = get_embedding(text2)
    return cosine_similarity([emb1], [emb2])[0][0]

# ✅ Keyword overlap
def keyword_overlap(text1, text2):
    vectorizer = CountVectorizer(stop_words='english')
    vectors = vectorizer.fit_transform([text1, text2]).toarray()
    overlap = np.minimum(vectors[0], vectors[1]).sum()
    total = np.maximum(vectors[0], vectors[1]).sum()
    return overlap / total if total > 0 else 0

# ✅ Section extraction
def extract_section(text, keyword):
    lines = text.lower().split('\n')
    section = [line for line in lines if keyword.lower() in line]
    return ' '.join(section)

def section_score(resume, job, section):
    r_sec = extract_section(resume, section)
    j_sec = extract_section(job, section)
    if not r_sec or not j_sec:
        return 0.0
    return semantic_similarity(r_sec, j_sec)

# ✅ Simple neural model
class ATSModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(5, 16),
            nn.ReLU(),
            nn.Linear(16, 8),
            nn.ReLU(),
            nn.Linear(8, 1),
            nn.Sigmoid()
        )
    def forward(self, x):
        return self.net(x)

ats_model = ATSModel()

# ✅ Main function
def ats_score(resume_pdf, job_pdf):
    resume = extract_text_from_pdf(resume_pdf)
    job = extract_text_from_pdf(job_pdf)

    sim = semantic_similarity(resume, job)
    kw = keyword_overlap(resume, job)
    skills = section_score(resume, job, "skills")
    exp = section_score(resume, job, "experience")
    edu = section_score(resume, job, "education")

    features = torch.tensor([[sim, kw, skills, exp, edu]], dtype=torch.float32)
    score = ats_model(features).item()
    percentage = round(score * 100, 2)

    # ✅ Print result safely
    safe_print(f"ATS Match Score: {percentage}%")

    # ✅ Log result safely
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = (
        f"[{timestamp}] {resume_pdf} vs {job_pdf} - Score: {percentage}%\n"
        f"  - Semantic Similarity: {round(sim, 3)}\n"
        f"  - Keyword Overlap: {round(kw, 3)}\n"
        f"  - Skills Match: {round(skills, 3)}\n"
        f"  - Experience Match: {round(exp, 3)}\n"
        f"  - Education Match: {round(edu, 3)}\n\n"
    )

    with open("ats_score_log.txt", "a", encoding="utf-8", errors="ignore") as log_file:
        log_file.write(log_entry)

# ✅ Run the comparison
ats_score("resume.pdf", "job_description.pdf")
