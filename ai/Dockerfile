# Stage 1 — ColBERT v2 and export to ONNX + int8 quantization
FROM python:3.13-slim AS builder

WORKDIR /build

RUN pip install --no-cache-dir \
    torch --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir \
    transformers \
    onnxruntime \
    onnxscript \
    optimum[onnxruntime]

COPY export_model.py .
RUN python export_model.py

# Stage 2 - The FastAPI service
# Use an official lightweight Python image
FROM python:3.13-slim

# Prevent Python from writing pyc files to disc
ENV PYTHONDONTWRITEBYTECODE=1

# Prevent Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /app

# Copy only the requirements file first to leverage Docker cache
COPY requirements.txt .


# Install dependencies without saving cache to keep image small
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Copy only the ONNX model
COPY --from=builder /build/ml_model/models  /app/ml_model/models/

# Expose the port FastAPI will run on
EXPOSE 8000

# Run the FastAPI application using the official CLI (FastAPI CLI)
CMD ["fastapi", "run", "main.py", "--host", "0.0.0.0", "--port", "8000"]
