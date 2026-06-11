import torch
import torch.nn as nn
import torch.nn.functional as F

from sentence_transformers import SentenceTransformer

EMBED_MODEL = "multi-qa-mpnet-base-dot-v1"

model_google = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
model_wikipedia = SentenceTransformer(EMBED_MODEL)

onnx_google = torch.onnx.export(model_google, dynamo=True)
onnx_wikipedia = torch.onnx.export(model_wikipedia, dynamo=True)

onnx_google.save("google_embeddings.onnx")
onnx_wikipedia.save('wikipedia_embeddings.onnx')