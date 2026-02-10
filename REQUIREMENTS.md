# PowerLit Backend Requirements

**Project Name:** PowerLit  
**Version:** 1.0  
**Target Region:** Accra, Ghana  
**Standards:** Ghana Energy Commission (GS1009)

---

## 1. Project Overview
**PowerLit** is a specialized API backend designed to automate the analysis of electrical blueprints and technical documents. It utilizes a **Modular Monolith** architecture to process structured data (blueprints) and unstructured data (regulations) to generate accurate, code-compliant electrical load profiles and sourcing recommendations.

## 2. Problem Statement
* **Inefficiency:** Manual counting of electrical symbols from PDF/Image drawings is time-consuming.
* **Error Prone:** Manual transcription leads to errors in Total Connected Load (TCL) and Maximum Demand (MD).
* **Compliance Gap:** Difficulty in real-time cross-referencing of calculations with GS1009 safety standards.

---

## 3. Functional Requirements

### 3.1 Multimodal Ingestion (Input)
The system must expose API endpoints to handle:
* **File Formats:** `.pdf`, `.png`, `.jpg`, `.jpeg`.
* **Document Types:**
    * Architectural Floor Plans.
    * Electrical Circuit Diagrams.
    * Legend Keys / Symbol Charts.
    * Unstructured Text (e.g., Project Specifications).
* **Metadata:** User input for Building Type (Residential, Industrial, Commercial).

### 3.2 AI Analysis Engines

#### A. Vision Engine (Gemini Integration)
* **Symbol Extraction:** Identify electrical symbols from the legend.
* **Spatial Mapping:** Locate and count symbols on the floor plan.
* **Attribute Estimation:** Estimate wattage ratings based on standard 230V Ghanaian voltage if not explicitly stated in the legend.

#### B. RAG Engine (Context & Compliance)
* **Knowledge Base:** Ingest and index the Ghana Energy Commission (GS1009) standards.
* **Chunking Strategy:** Split documents into ~1000 character chunks with overlap to preserve context.
* **Vector Search:** Retrieve relevant regulatory clauses using semantic search to validate calculations.

### 3.3 Analytical Core (Deterministic Logic)
The system must **not** use LLMs for math. It must use Python functions for the following:

1.  **Total Connected Load (TCL):**
    $$TCL = \sum (Rating_{unit} \times Quantity)$$

2.  **Maximum Demand (MD):**
    $$MD = TCL \times DiversityFactor$$
    *(Diversity Factor determined by Building Type, e.g., Residential = 0.6)*

3.  **Redundancy Planning:**
    * Calculate $N+1$ or $N+2$ requirements for critical loads.

### 3.4 Output & Reporting
The API must return a JSON response containing:
* **Inventory:** List of detected components (Name, Qty, Rating).
* **Calculations:** TCL, MD, and Diversity Factor used.
* **Compliance Audit:** Relevant text snippets from GS1009 explaining the safety logic.
* **Recommendations:** Optimal mix of Grid (ECG), Solar PV, or Backup Generators.

---

## 4. Technical Architecture

### 4.1 Technology Stack
* **Language:** Python 3.10+
* **Framework:** FastAPI (Async)
* **Orchestration:** LangChain
* **Vector Database:** ChromaDB (Persistent Local Storage)
* **Embeddings:** `sentence-transformers/all-MiniLM-L6-v2` (HuggingFace)
* **Vision Model:** Gemini 1.5 Flash (via Google GenAI SDK)
* **PDF Processing:** `pypdf`, `unstructured`

### 4.2 Data Pipeline
1.  **Ingestion:** Scans `/data/knowledge_base` for PDFs.
2.  **Processing:** Text splitting and vector embedding upon startup or API trigger.
3.  **Storage:** Vectors stored in `./chromadb_store`.

### 4.3 Deployment
* **Containerization:** Docker (must include `poppler-utils` and `tesseract-ocr`).
* **Hosting:** Compatible with Hugging Face Spaces or Render.
* **Environment:** Managed via `.env` files (API Keys, Config).

---

## 5. Non-Functional Requirements
* **Determinism:** Calculations must be reproducible and mathematically exact.
* **Latency:** Vision analysis < 15s; RAG retrieval < 200ms.
* **Data Privacy:** Uploaded blueprints are processed in memory and cleared after the transaction.
* **Scalability:** Modular design to allow swapping of Embedding models or Vector Stores.

---

## 6. Future Roadmap
* **Frontend:** React/Next.js dashboard.
* **Costing:** Integration with local market pricing for cabling/components.
* **Multi-Page Stitching:** Analyzing whole-building blueprints across multiple files.