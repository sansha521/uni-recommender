"""
Export SentenceTransformer models to ONNX format.
Run from repo root: python -m ai.export_model
Output: ai/ml_model/models/google_embeddings.onnx
        ai/ml_model/models/wikipedia_embeddings.onnx
"""

import shutil
from pathlib import Path

from optimum.onnxruntime import ORTModelForFeatureExtraction
from transformers import AutoTokenizer

OUTPUT_DIR = Path(__file__).parent / "ml_model" / "models"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODELS = [
    ("sentence-transformers/all-MiniLM-L6-v2", "google_embeddings.onnx"),
    ("sentence-transformers/multi-qa-mpnet-base-dot-v1", "wikipedia_embeddings.onnx"),
]

for model_name, filename in MODELS:
    print(f"Exporting {model_name}...")
    tmp_dir = OUTPUT_DIR / f"_tmp_{filename}"

    model = ORTModelForFeatureExtraction.from_pretrained(model_name, export=True)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model.save_pretrained(tmp_dir)
    tokenizer.save_pretrained(tmp_dir)

    # Move just the onnx file to the final path
    (tmp_dir / "model.onnx").rename(OUTPUT_DIR / filename)
    shutil.rmtree(tmp_dir)

    print(f"  Saved → {OUTPUT_DIR / filename}")

print("Done.")
