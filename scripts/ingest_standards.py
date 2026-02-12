#!/usr/bin/env python3
"""
Script to ingest Ghana electrical standards into ChromaDB vector database.
Run this after adding new standards documents to data/knowledge_base/
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.rag import RAGService


async def main():
    """Run the ingestion process"""
    print("=" * 60)
    print("PowerLit Knowledge Base Ingestion")
    print("=" * 60)
    
    # Initialize RAG service
    print("\nInitializing RAG service...")
    rag_service = RAGService()
    
    # Check knowledge base directory
    kb_path = "data/knowledge_base"
    if not os.path.exists(kb_path):
        print(f"ERROR: Knowledge base directory not found: {kb_path}")
        sys.exit(1)
    
    # List PDF files
    pdf_files = [f for f in os.listdir(kb_path) if f.endswith('.pdf')]
    print(f"\nFound {len(pdf_files)} PDF file(s) in {kb_path}:")
    for pdf in pdf_files:
        size = os.path.getsize(os.path.join(kb_path, pdf))
        print(f"  - {pdf} ({size:,} bytes)")
    
    if not pdf_files:
        print("\nWARNING: No PDF files found. Nothing to ingest.")
        sys.exit(0)
    
    # Run ingestion
    print("\nStarting ingestion process...")
    print("-" * 60)
    
    try:
        result = await rag_service.ingest_standards()
        print(f"\n{'=' * 60}")
        print("INGESTION COMPLETE")
        print(f"{'=' * 60}")
        print(f"Result: {result}")
        
        # Verify the collection
        try:
            collection = rag_service.client.get_collection(rag_service.collection_name)
            count = collection.count()
            print(f"\nVector DB Status:")
            print(f"  Collection: {rag_service.collection_name}")
            print(f"  Total chunks: {count}")
            print(f"  Database path: {rag_service.client._persist_directory}")
        except Exception as e:
            print(f"\nWarning: Could not verify collection: {e}")
            
    except Exception as e:
        print(f"\nERROR during ingestion: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
