import chromadb
import boto3
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

CHROMA_PATH = "rag/wikipedia"
COLLECTION_NAME = "universities"

AWS_REGION = "us-east-1"
VECTOR_BUCKET = "uni-rec-s3-vector-bucket"
INDEX_NAME = "uni-rec-wikipedia"

BATCH_SIZE = 500

client = chromadb.PersistentClient(path=CHROMA_PATH)

collection = client.get_collection(COLLECTION_NAME)
count = collection.count()
print(f"Collection size: {count}")

sample = collection.get(limit=1, include=["embeddings"])
print(len(sample["embeddings"][0]))


s3vectors = boto3.client("s3vectors", region_name=AWS_REGION)

try:
    for offset in tqdm(range(0, count, BATCH_SIZE)):
        result = collection.get(
            include=["embeddings", "metadatas", "documents"],
            limit=BATCH_SIZE,
            offset=offset,
        )

        ids = result["ids"]
        embeddings = result["embeddings"]
        metadatas = result.get("metadatas", [])
        documents = result.get("documents", [])

        vectors = []

        for i in range(len(ids)):
            embedding = embeddings[i]

            if hasattr(embedding, "tolist"):
                embedding = embedding.astype("float32").tolist()

            vector = {"key": str(ids[i]), "data": {"float32": embedding}}

            vectors.append(vector)

        s3vectors.put_vectors(
            vectorBucketName=VECTOR_BUCKET, indexName=INDEX_NAME, vectors=vectors
        )

except Exception as e:
    print(str(e))

print("Migration complete.")

