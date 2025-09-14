# Schema Mapper & Data Quality Fixer (Project 6)

A **Streamlit-based application** for automatically mapping CSV headers to a **canonical schema**, validating and cleaning data, and suggesting targeted fixes for invalid entries.  
The tool integrates with **Hugging Face LLMs** (via LangChain) for intelligent header mapping when string similarity is not enough.

---

## 🚀 Features

- 📂 Upload any CSV file for analysis
- 🧩 **Header Mapping**
  - Suggests canonical fields based on synonyms and LLM reasoning
  - Allows manual override of mapping in the UI
- 🧹 **Data Cleaning**
  - Normalizes tax IDs (alphanumeric, uppercase)
  - Standardizes amounts (floats with 2 decimals)
  - Parses dates into ISO format
  - Preserves unmapped fields
- ✅ **Validation**
  - Detects invalid or missing values
  - Flags numeric, date, and tax ID inconsistencies
- 🔧 **Fix Suggestions**
  - Row-level and column-level repair actions
  - Deterministic fixes (strip non-alphanumeric, numeric parsing, alt date parsing)
- 📊 **Summary Reports**
  - Before/After invalid & missing value counts
- 💾 Download cleaned CSV
- 🛠 Debug tools for viewing and persisting:
  - `canonical.json` (schema definitions)
  - `promoted_fixes.json` (custom fixes)
  - `mapping_history.json` (past decisions)

---

## 📦 Installation

1. Clone the repo or copy the project files:

   ```bash
   git clone https://github.com/yourusername/schema-mapper.git
   cd schema-mapper

## Create a virtual environment:

python -m venv venv
source venv/bin/activate   # Linux/Mac
.\venv\Scripts\activate    # Windows


## Install dependencies:

pip install -r requirements.txt


Typical dependencies include:

streamlit

pandas

python-dateutil

langchain

langchain-huggingface

huggingface_hub

python-dotenv

## 🔑 Hugging Face Setup

This app uses the Hugging Face Inference API for LLM-based header mapping.

Create an account at Hugging Face
.

## Generate a new API token with read access from
👉 https://huggingface.co/settings/tokens
.

Create a .env file in your project root:

HUGGINGFACEHUB_API_TOKEN=hf_your_new_token_here


⚠️ The free-tier Hugging Face account has limited monthly credits.
If you exceed them, either:

Upgrade to Hugging Face Pro
, or

Swap the LLM backend to a local model (e.g., via Ollama
).

## ▶️ Usage

Run the Streamlit app:

streamlit run app.py


Open your browser at http://localhost:8501

Upload a CSV file.

Review suggested header mappings (edit if needed).

Run Clean & Validate to apply normalizations.

Inspect targeted fix suggestions (apply row, column, or dismiss).

Download the cleaned CSV.