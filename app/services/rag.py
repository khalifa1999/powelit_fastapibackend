from typing import List, Dict
import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
import os
import asyncio
from app.models.schemas import LoadCalculation, ComplianceAudit, BuildingType
from app.config import settings


class RAGService:
    """RAG service for GS1009 and Ghana Electrical Standards compliance checking"""

    # Hardcoded compliance rules based on Ghana Electrical Standards
    COMPLIANCE_RULES = {
        "voltage_standard": {
            "description": "Ghana standard voltage is 230V ±6%",
            "standard": "230V",
            "tolerance": 0.06,
            "clause": "GS1009-1:2019 Clause 4.2"
        },
        "diversity_factors": {
            BuildingType.RESIDENTIAL: {
                "factor": 0.6,
                "description": "Residential diversity factor",
                "clause": "GS1009-2:2019 Annex C"
            },
            BuildingType.COMMERCIAL: {
                "factor": 0.8,
                "description": "Commercial diversity factor",
                "clause": "GS1009-2:2019 Annex C"
            },
            BuildingType.INDUSTRIAL: {
                "factor": 0.9,
                "description": "Industrial diversity factor",
                "clause": "GS1009-2:2019 Annex C"
            }
        },
        "maximum_demand_limits": {
            BuildingType.RESIDENTIAL: {
                "single_phase_max": 12000,  # 12kW
                "three_phase_threshold": 15000,  # 15kW
                "clause": "ECG Technical Standards"
            },
            BuildingType.COMMERCIAL: {
                "typical_range": "20-100kW",
                "clause": "ECG Commercial Standards"
            },
            BuildingType.INDUSTRIAL: {
                "typical_range": "100kW+",
                "clause": "ECG Industrial Standards"
            }
        },
        "cable_sizing": {
            "current_carrying_capacity": "Must not exceed 80% of cable rating",
            "voltage_drop": "Maximum 4% from origin to final circuit",
            "clause": "GS1009-5:2019 Clause 5.2"
        },
        "earthing_requirements": {
            "earth_electrode_resistance": "Maximum 10 ohms",
            "earth_continuity": "Maximum 1 ohm",
            "clause": "GS1009-7:2019 Clause 7.3"
        }
    }

    def __init__(self):
        self.client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
        self.collection_name = settings.COLLECTION_NAME
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )

    async def ingest_standards(self) -> str:
        """
        Ingest GS1009 and other standards PDFs into the vector database.
        Run this when standards are updated.
        """
        kb_path = "data/knowledge_base"

        if not os.path.exists(kb_path):
            os.makedirs(kb_path)
            return "Knowledge base directory created. Please add standards PDF files."

        pdf_files = [
            f for f in os.listdir(kb_path)
            if f.endswith('.pdf')
        ]

        if not pdf_files:
            return "No PDF files found in knowledge_base directory"

        documents = []
        metadatas = []
        ids = []

        for idx, pdf_file in enumerate(pdf_files):
            pdf_path = os.path.join(kb_path, pdf_file)
            try:
                reader = PdfReader(pdf_path)
                text = ""
                for page_num, page in enumerate(reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text += f"\n--- Page {page_num + 1} ---\n{page_text}"

                if text.strip():
                    # Split text into chunks
                    chunks = self.text_splitter.split_text(text)

                    for chunk_idx, chunk in enumerate(chunks):
                        documents.append(chunk)
                        metadatas.append({
                            "source": pdf_file,
                            "page": chunk_idx,
                            "total_pages": len(reader.pages)
                        })
                        ids.append(f"{pdf_file}_{chunk_idx}")

            except Exception as e:
                print(f"Error processing {pdf_file}: {e}")
                continue

        if documents:
            try:
                # Get or create collection
                try:
                    collection = self.client.get_collection(self.collection_name)
                    # Delete existing to avoid duplicates
                    self.client.delete_collection(self.collection_name)
                except:
                    pass

                collection = self.client.create_collection(self.collection_name)

                # Add documents
                collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )

                return f"Successfully ingested {len(pdf_files)} PDFs with {len(documents)} chunks into vector database"
            except Exception as e:
                return f"Error storing in vector DB: {str(e)}"
        else:
            return f"No text extracted from {len(pdf_files)} PDFs (may be scanned images)"

    def query_standards(self, query: str, n_results: int = 5) -> Dict:
        """Query the standards database for relevant clauses"""
        try:
            collection = self.client.get_collection(self.collection_name)
            results = collection.query(
                query_texts=[query],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            return results
        except Exception as e:
            print(f"Error querying standards: {e}")
            return {}

    async def check_compliance(
        self,
        calculations: LoadCalculation
    ) -> List[ComplianceAudit]:
        """
        Check calculations against Ghana Electrical Standards (GS1009).
        Returns a list of compliance audit results.
        """
        compliance_results = []

        # Check 1: Diversity Factor
        expected_df = self.COMPLIANCE_RULES["diversity_factors"][calculations.building_type]["factor"]
        df_rule = self.COMPLIANCE_RULES["diversity_factors"][calculations.building_type]

        if abs(calculations.diversity_factor - expected_df) < 0.01:
            compliance_results.append(ComplianceAudit(
                standard_clause=df_rule["clause"],
                description=f"Diversity factor ({calculations.diversity_factor}) matches standard for {calculations.building_type.value} buildings",
                compliance_status="compliant"
            ))
        else:
            compliance_results.append(ComplianceAudit(
                standard_clause=df_rule["clause"],
                description=f"Diversity factor mismatch. Expected: {expected_df}, Got: {calculations.diversity_factor}",
                compliance_status="review_required"
            ))

        # Check 2: Maximum Demand Limits
        md_kw = calculations.maximum_demand / 1000
        tcl_kw = calculations.total_connected_load / 1000

        if calculations.building_type == BuildingType.RESIDENTIAL:
            limits = self.COMPLIANCE_RULES["maximum_demand_limits"][BuildingType.RESIDENTIAL]
            if calculations.maximum_demand > limits["three_phase_threshold"]:
                compliance_results.append(ComplianceAudit(
                    standard_clause=limits["clause"],
                    description=f"Maximum demand ({md_kw:.1f}kW) exceeds single-phase threshold ({limits['three_phase_threshold']/1000:.1f}kW). Three-phase supply required.",
                    compliance_status="compliant"
                ))
            elif calculations.maximum_demand > limits["single_phase_max"]:
                compliance_results.append(ComplianceAudit(
                    standard_clause=limits["clause"],
                    description=f"Maximum demand ({md_kw:.1f}kW) exceeds typical single-phase limit ({limits['single_phase_max']/1000:.1f}kW). Review supply type.",
                    compliance_status="review_required"
                ))
            else:
                compliance_results.append(ComplianceAudit(
                    standard_clause=limits["clause"],
                    description=f"Maximum demand ({md_kw:.1f}kW) within single-phase limits",
                    compliance_status="compliant"
                ))

        # Check 3: Load Assessment Reasonableness
        if calculations.maximum_demand > calculations.total_connected_load:
            compliance_results.append(ComplianceAudit(
                standard_clause="GS1009-2:2019 Clause 3.1",
                description="ERROR: Maximum demand cannot exceed total connected load",
                compliance_status="non_compliant"
            ))
        else:
            utilization = (calculations.maximum_demand / calculations.total_connected_load * 100) if calculations.total_connected_load > 0 else 0
            compliance_results.append(ComplianceAudit(
                standard_clause="GS1009-2:2019 Clause 3.1",
                description=f"Load calculation valid. Diversity utilization: {utilization:.1f}%",
                compliance_status="compliant"
            ))

        # Check 4: Building Type Appropriateness
        if calculations.building_type == BuildingType.RESIDENTIAL and tcl_kw > 100:
            compliance_results.append(ComplianceAudit(
                standard_clause="GS1009-1:2019",
                description=f"Total load ({tcl_kw:.1f}kW) unusually high for residential. Verify building classification.",
                compliance_status="review_required"
            ))
        elif calculations.building_type == BuildingType.COMMERCIAL and tcl_kw < 10:
            compliance_results.append(ComplianceAudit(
                standard_clause="GS1009-1:2019",
                description=f"Total load ({tcl_kw:.1f}kW) unusually low for commercial. Verify building classification.",
                compliance_status="review_required"
            ))

        # Check 5: Query vector DB for additional relevant standards
        try:
            query = f"{calculations.building_type.value} electrical installation {md_kw:.1f}kW demand"
            vector_results = self.query_standards(query, n_results=3)

            if vector_results and vector_results.get('documents'):
                # Add a generic audit entry for vector DB results
                sources = set()
                for meta in vector_results.get('metadatas', [[]])[0]:
                    if meta and 'source' in meta:
                        sources.add(meta['source'])

                if sources:
                    compliance_results.append(ComplianceAudit(
                        standard_clause="GS1009 Standards",
                        description=f"Additional standards referenced: {', '.join(sources)}",
                        compliance_status="compliant"
                    ))
        except Exception as e:
            # Vector DB check is optional
            pass

        return compliance_results
