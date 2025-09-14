import streamlit as st
import pandas as pd
import json
import difflib
import re
from dateutil import parser as dateparser
from datetime import datetime
import os
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
import ast
from dotenv import load_dotenv

class SchemaMapperApp:
    def __init__(self):
        load_dotenv()

        # ---------- Config / Files ----------
        self.CANONICAL_PATH = "canonical.json"
        self.PROMOTED_FIXES_PATH = "promoted_fixes.json"
        self.MAPPING_HISTORY = "mapping_history.json"

        self.DEFAULT_CANONICAL = {
            "order_id": ["order id", "order no", "ordernumber"],
            "order_date": ["order date", "orderdate", "invoice date", "bill date"],
            "customer_id": ["customer id", "cust id"],
            "customer_name": ["customer name", "customer"],
            "email": ["email", "e-mail"],
            "phone": ["phone", "phone #"],
            "billing_address": ["billing address", "bill addr"],
            "shipping_address": ["shipping address", "ship addr"],
            "city": ["city", "town"],
            "state": ["state", "state/province"],
            "postal_code": ["postal code", "zip", "zip/postal"],
            "country": ["country", "country/region"],
            "product_sku": ["sku", "product sku"],
            "product_name": ["product name", "item"],
            "category": ["category", "cat."],
            "subcategory": ["subcategory", "subcat"],
            "quantity": ["quantity", "qty"],
            "unit_price": ["unit price", "price per unit"],
            "currency": ["currency", "curr"],
            "discount_pct": ["discount pct", "disc%"],
            "tax_pct": ["tax pct", "tax%"],
            "shipping_fee": ["shipping fee", "ship fee"],
            "total_amount": ["total amount", "total"],
            "tax_id": ["tax id", "tax number", "vat#", "vat number", "gstin", "pan", "reg no", "registration number"],
        }

        self._ensure_file(self.CANONICAL_PATH, self.DEFAULT_CANONICAL)
        self._ensure_file(self.PROMOTED_FIXES_PATH, [])
        self._ensure_file(self.MAPPING_HISTORY, {})

        self.canonical = self._load_json(self.CANONICAL_PATH)
        self.promoted_fixes = self._load_json(self.PROMOTED_FIXES_PATH)
        self.mapping_history = self._load_json(self.MAPPING_HISTORY)

        # ---------- LLM Integration ----------
        llm = HuggingFaceEndpoint(
            repo_id="deepseek-ai/DeepSeek-V3.1",
            task="text-generation",
            max_new_tokens=128,
            temperature=0.0,
        )
        chat_model = ChatHuggingFace(llm=llm)
        parser = StrOutputParser()

        prompt = PromptTemplate(
            template=(
                "You are a schema matching assistant.\n"
                "Given a header name from a CSV file, map it to one of the canonical schema fields below:\n"
                "{canonical_fields}\n\n"
                "Header: {header}\n"
                "Respond as JSON with keys 'suggested' (the closest canonical field or 'unmapped') "
                "and 'confidence' (0 to 1).\n"
            ),
            input_variables=["canonical_fields", "header"]
        )

        self.llm_chain = prompt | chat_model | parser

    # ---------- File Handling ----------
    def _ensure_file(self, path, default):
        if not os.path.exists(path):
            with open(path, "w") as f:
                json.dump(default, f, indent=2)

    def _load_json(self, path):
        with open(path, "r") as f:
            return json.load(f)

    def _save_json(self, path, obj):
        with open(path, "w") as f:
            json.dump(obj, f, indent=2)

    # ---------- Utilities ----------
    def header_similarity(self, a, b):
        return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()

    def infer_type(self, series, n_sample=200):
        s = series.dropna().astype(str).head(n_sample).tolist()
        if not s:
            return "empty"
        date_hits, float_hits, int_hits = 0, 0, 0
        for v in s:
            v = v.strip()
            try:
                _ = dateparser.parse(v, fuzzy=False)
                date_hits += 1
                continue
            except:
                pass
            v2 = v.replace(",", "")
            try:
                if "." in v2:
                    float(v2); float_hits += 1
                else:
                    int(v2); int_hits += 1
            except:
                pass
        if date_hits / len(s) > 0.6:
            return "date"
        if (float_hits + int_hits) / len(s) > 0.6:
            return "numeric"
        return "string"

    # ---------- Normalizers ----------
    def normalize_tax_id(self, v):
        if pd.isna(v): return None
        return re.sub(r'[^A-Za-z0-9]', '', str(v)).upper()

    def normalize_amount(self, v):
        if pd.isna(v): return None
        s = str(v).replace(",", "").replace("₹", "").strip()
        try:
            return round(float(s), 2)
        except:
            return None

    def normalize_date(self, v, alt=False):
        if pd.isna(v): return None
        s = str(v).strip()
        try:
            dt = dateparser.parse(s, dayfirst=alt)
            return dt.date().isoformat()
        except:
            return None

    # ---------- Validators ----------
    def is_valid_for_field(self, field, val):
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return False
        if field == "tax_id":
            return bool(re.match(r'^[A-Z0-9]{5,30}$', str(val)))
        if field == "order_date":
            try:
                datetime.fromisoformat(val); return True
            except: return False
        if field in ("amount", "unit_price", "shipping_fee", "total_amount", "discount_pct", "tax_pct"):
            try: float(val); return True
            except: return False
        return True

    # ---------- LLM ----------
    def llm_header_mapping(self, header: str, canonical_fields: list) -> dict:
        try:
            raw = self.llm_chain.invoke({
                "canonical_fields": ", ".join(canonical_fields),
                "header": header
            })
            result = ast.literal_eval(raw.strip())
            if not isinstance(result, dict):
                raise ValueError("Not dict")
            return result
        except:
            return {"suggested": "unmapped", "confidence": 0.0}

    # ---------- Mapping ----------
    def suggest_mappings(self, df):
        suggestions = {}
        for h in df.columns:
            best, best_score, best_syn = None, 0.0, None
            for canon_key, synonyms in self.canonical.items():
                for syn in [canon_key] + synonyms:
                    s = self.header_similarity(h, syn)
                    if s > best_score:
                        best_score, best, best_syn = s, canon_key, syn

            t = self.infer_type(df[h])
            if t == "date" and best == "order_date":
                best_score += 0.2
            if t == "numeric" and best in ["amount", "unit_price", "shipping_fee", "total_amount"]:
                best_score += 0.2

            if best_score < 0.7:
                llm_result = self.llm_header_mapping(h, list(self.canonical.keys()))
                best = llm_result.get("suggested", "unmapped")
                best_score = llm_result.get("confidence", 0.5)
                best_syn = "LLM"

            suggestions[h] = {
                "suggested": best,
                "synonym": best_syn,
                "confidence": round(min(best_score, 1.0), 2),
                "inferred_type": t,
            }
        return suggestions

    # ---------- Cleaning ----------
    def clean_dataframe(self, df, mapping):
        out = pd.DataFrame(index=df.index)
        for src, canon in mapping.items():
            series = df[src]
            if canon == "tax_id":
                out[canon] = series.apply(self.normalize_tax_id)
            elif canon in ["amount", "unit_price", "shipping_fee", "total_amount", "discount_pct", "tax_pct"]:
                out[canon] = series.apply(self.normalize_amount)
            elif canon == "order_date":
                out[canon] = series.apply(self.normalize_date)
            else:
                out[canon] = series
        return out

    def generate_fix_suggestions(self, cleaned_df):
        suggestions = []
        for col, series in cleaned_df.items():
            for idx, val in series.items():
                if not self.is_valid_for_field(col, val):
                    proposed, reason = None, "no deterministic fix"
                    if col == "tax_id":
                        proposed, reason = self.normalize_tax_id(val), "strip_non_alnum|upper"
                    elif col == "order_date":
                        proposed, reason = self.normalize_date(val, alt=True), "try alternate date parse"
                    elif col in ["amount", "unit_price", "shipping_fee", "total_amount"]:
                        proposed, reason = self.normalize_amount(val), "numeric parse"
                    suggestions.append({
                        "row": int(idx), "col": col,
                        "current": val, "suggested": proposed, "reason": reason
                    })
        return suggestions

    # ---------- Streamlit UI ----------
    def run(self):
        st.set_page_config(page_title="Schema Mapper & Data Quality Fixer", layout="wide")
        st.title("Schema Mapper & Data Quality — Project 6")

        uploaded = st.file_uploader("Upload CSV", type=["csv"])
        if uploaded is None:
            st.info("Upload a CSV to begin. canonical.json and promoted_fixes.json are auto-created.")
            st.stop()

        try:
            df = pd.read_csv(uploaded)
        except Exception as e:
            st.error(f"Could not read CSV: {e}")
            st.stop()

        st.write("Preview of uploaded file (first 10 rows):")
        st.dataframe(df.head(10))

        st.header("1) Suggested header mapping")
        suggestions = self.suggest_mappings(df)
        mapping_cols = {}

        for col, sug in suggestions.items():
            default = sug["suggested"] or "—"
            with st.expander(f"{col} → suggested {default} (conf {sug['confidence']})"):
                st.write("Inferred type:", sug["inferred_type"])
                st.write("Best synonym matched:", sug["synonym"])
                sel = st.selectbox(
                    f"Map `{col}` to:",
                    ["(ignore)"] + list(self.canonical.keys()),
                    index=(list(self.canonical.keys()).index(default) + 1 if default in self.canonical else 0),
                    key=f"map_{col}"
                )
                mapping_cols[col] = sel if sel != "(ignore)" else None
                st.write("Sample values:", df[col].dropna().astype(str).head(5).tolist())

        st.markdown("---")
        st.header("2) Clean & Validate")

        if st.button("Run clean & validate"):
            mapping = {src: tgt for src, tgt in mapping_cols.items() if tgt}
            if not mapping:
                st.warning("No mappings selected.")
            else:
                cleaned = self.clean_dataframe(df, mapping)

                st.subheader("Before / After Summary")
                summary = []
                for src, tgt in mapping.items():
                    before_missing = df[src].isna().sum()
                    after_invalid = sum(1 for v in cleaned[tgt] if not self.is_valid_for_field(tgt, v))
                    summary.append({
                        "field": tgt, "mapped_from": src,
                        "before_missing": int(before_missing),
                        "after_invalid": int(after_invalid),
                        "total_rows": len(df)
                    })
                st.table(pd.DataFrame(summary))

                st.subheader("Cleaned sample")
                st.dataframe(cleaned.head(10))
                st.session_state["cleaned_df"] = cleaned
                st.success("Cleaning finished. Check fixes below if needed.")

        st.markdown("---")
        st.header("3) Targeted Fix Suggestions")
        if "cleaned_df" in st.session_state:
            cleaned = st.session_state["cleaned_df"]
            fixes = self.generate_fix_suggestions(cleaned)
            if not fixes:
                st.success("No issues found. File is clean.")
            else:
                for i, s in enumerate(fixes):
                    with st.expander(f"Row {s['row']} — {s['col']} — {s['current']}"):
                        st.write("Suggested:", s['suggested'])
                        st.write("Reason:", s['reason'])
                        c1, c2, c3 = st.columns([1,1,2])
                        if c1.button("Apply Row", key=f"apply_{i}"):
                            cleaned.at[s['row'], s['col']] = s['suggested']
                        if c2.button("Apply Column", key=f"applycol_{i}"):
                            cleaned[s['col']] = cleaned[s['col']].apply(
                                lambda v: s['suggested'] if not self.is_valid_for_field(s['col'], v) else v
                            )
                        if c3.button("Dismiss", key=f"dismiss_{i}"):
                            pass
                st.session_state["cleaned_df"] = cleaned
                st.subheader("Cleaned after fixes")
                st.dataframe(cleaned.head(10))
                st.download_button("Download Cleaned CSV", cleaned.to_csv(index=False), "cleaned.csv", "text/csv")

        st.sidebar.header("Debug / Management")
        if st.sidebar.button("Show canonical.json"):
            st.sidebar.json(self.canonical)
        if st.sidebar.button("Show promoted_fixes.json"):
            st.sidebar.json(self.promoted_fixes)


if __name__ == "__main__":
    app = SchemaMapperApp()
    app.run()
