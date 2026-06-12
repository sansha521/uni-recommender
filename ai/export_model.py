"""
Export SentenceTransformer models to ONNX format.
Run from repo root: python -m ai.export_model
Output: ai/ml_model/models/google_embeddings.onnx
        ai/ml_model/models/google_tokenizer.json
        ai/ml_model/models/wikipedia_embeddings.onnx
        ai/ml_model/models/wikipedia_tokenizer.json
"""

import shutil
from pathlib import Path

from optimum.onnxruntime import ORTModelForFeatureExtraction
from transformers import AutoTokenizer

OUTPUT_DIR = Path(__file__).parent / "ml_model" / "models"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODELS = [
    (
        "sentence-transformers/all-MiniLM-L6-v2",
        "google_embeddings.onnx",
        "google_tokenizer.json",
    ),
    (
        "sentence-transformers/multi-qa-mpnet-base-dot-v1",
        "wikipedia_embeddings.onnx",
        "wikipedia_tokenizer.json",
    ),
]

for model_name, onnx_filename, tokenizer_filename in MODELS:
    print(f"Exporting {model_name}...")
    tmp_dir = OUTPUT_DIR / f"_tmp_{onnx_filename}"

    model = ORTModelForFeatureExtraction.from_pretrained(model_name, export=True)
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    model.save_pretrained(tmp_dir)
    tokenizer.save_pretrained(tmp_dir)

    # Move the ONNX file to the final path
    (tmp_dir / "model.onnx").rename(OUTPUT_DIR / onnx_filename)

    # Copy the fast tokenizer JSON to the final path (renamed per-model)
    src_tokenizer = tmp_dir / "tokenizer.json"
    if not src_tokenizer.exists():
        raise FileNotFoundError(
            f"{model_name} did not produce a tokenizer.json (no fast tokenizer). "
            "Cannot use tokenizers.Tokenizer.from_file for this model."
        )
    shutil.copy2(src_tokenizer, OUTPUT_DIR / tokenizer_filename)

    shutil.rmtree(tmp_dir)
    print(f"  Saved → {OUTPUT_DIR / onnx_filename}")
    print(f"  Saved → {OUTPUT_DIR / tokenizer_filename}")

print("Done.")
