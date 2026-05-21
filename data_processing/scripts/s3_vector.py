import numpy as np
import boto3
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

REGION = "us-east-1"
VECTOR_BUCKET = "uni-rec-s3-vector-bucket"
INDEX_NAME = "uni-rec-index"
NPY_FILE = "rag/reviews/embeddings.npy"
ADD_METADATA = True
BATCH_SIZE = 500


print("Loading embeddings...")
embeddings = np.load(NPY_FILE)

embeddings = embeddings.astype(np.float32)

num_vectors, dimension = embeddings.shape

print(f"Loaded {num_vectors} vectors")
print(f"Dimension: {dimension}")

s3vectors = boto3.client("s3vectors", region_name=REGION)

for start in tqdm(range(0, num_vectors, BATCH_SIZE)):
    end = min(start + BATCH_SIZE, num_vectors)

    batch = []

    for i in range(start, end):
        vector = {"key": f"vec-{i}", "data": {"float32": embeddings[i].tolist()}}

        if ADD_METADATA:
            vector["metadata"] = {"source": "reviews", "row_id": str(i)}

        batch.append(vector)

    response = s3vectors.put_vectors(
        vectorBucketName=VECTOR_BUCKET, indexName=INDEX_NAME, vectors=batch
    )

print("Upload complete.")

