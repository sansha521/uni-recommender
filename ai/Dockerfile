# Stage 1 — export embedding models to ONNX + int8 dynamic quantization
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

# Lambda Web Adapter — turns this into a Lambda-compatible image
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.8.4 /lambda-adapter /opt/extensions/lambda-adapter
# Tell the adapter which port your app listens on (you use 8000)
ENV AWS_LWA_PORT=8000
# Point the adapter's readiness check at a path your app returns 200 on
ENV AWS_LWA_READINESS_CHECK_PATH=/health

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
    && pip install --no-cache-dir -r requirements.txt \
    && find /usr/local/lib/python3.13 -name '__pycache__' -type d -exec rm -rf {} + \
    && find /usr/local/lib/python3.13 -name 'tests' -type d -exec rm -rf {} + \
    && find /usr/local/lib/python3.13 -name '*.pyc' -delete \
    && rm -rf /root/.cache

# Copy the rest of the application code
COPY . .

# Copy only the ONNX model
COPY --from=builder /build/ml_model/models  /app/ml_model/models/

# Expose the port FastAPI will run on
EXPOSE 8000

# Run the FastAPI application using the official CLI (FastAPI CLI)
CMD ["fastapi", "run", "main.py", "--host", "0.0.0.0", "--port", "8000"]
