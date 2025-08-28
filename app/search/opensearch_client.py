from opensearchpy import OpenSearch
import os

HOST = os.getenv("OPENSEARCH_HOST", "opensearch")
PORT = int(os.getenv("OPENSEARCH_PORT", "9200"))
client = OpenSearch(hosts=[{"host": HOST, "port": PORT}], use_ssl=False, verify_certs=False)
