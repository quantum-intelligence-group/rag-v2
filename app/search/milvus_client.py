from pymilvus import connections
import os

HOST = os.getenv("MILVUS_HOST", "milvus-standalone")
PORT = os.getenv("MILVUS_PORT", "19530")
connections.connect(alias="default", host=HOST, port=PORT)
