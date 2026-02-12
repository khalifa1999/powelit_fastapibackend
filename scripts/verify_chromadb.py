#!/usr/bin/env python3
"""
Quick verification script to check ChromaDB contents
"""

import chromadb
from app.config import settings

client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)

print("ChromaDB Collections:")
print("-" * 40)

try:
    collection = client.get_collection(settings.COLLECTION_NAME)
    count = collection.count()
    print(f"✓ Collection: {settings.COLLECTION_NAME}")
    print(f"  Documents: {count} chunks")
    
    # Show a sample query
    print("\nSample Query Test:")
    print("-" * 40)
    results = collection.query(
        query_texts=["electrical installation standards"],
        n_results=3
    )
    
    if results and results.get('documents'):
        for i, (doc, meta) in enumerate(zip(results['documents'][0], results['metadatas'][0]), 1):
            source = meta.get('source', 'Unknown')
            preview = doc[:150].replace('\n', ' ')
            print(f"\n{i}. Source: {source}")
            print(f"   Preview: {preview}...")
    else:
        print("No results found")
        
except Exception as e:
    print(f"✗ Error: {e}")
