import pytest
from fastapi.testclient import TestClient
from main import app
from pathlib import Path
import json

client = TestClient(app)


class TestRootEndpoints:
    """Test basic API endpoints"""
    
    def test_read_main(self):
        """Test root endpoint returns API info"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "PowerLit API"
        assert "version" in data
        assert "docs" in data

    def test_health_check(self):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestDiversityFactors:
    """Test diversity factors endpoint"""
    
    def test_diversity_factors(self):
        """Test diversity factors are returned correctly"""
        response = client.get("/api/v1/analysis/diversity-factors")
        assert response.status_code == 200
        data = response.json()
        assert data["residential"] == 0.6
        assert data["commercial"] == 0.8
        assert data["industrial"] == 0.9
        assert "description" in data


class TestAnalyzeEndpoint:
    """Test the analyze blueprint endpoint"""
    
    def test_analyze_without_files(self):
        """Test analyze endpoint fails without files"""
        response = client.post(
            "/api/v1/analysis/analyze",
            data={"building_type": "residential"}
        )
        assert response.status_code == 422  # Validation error

    def test_analyze_with_single_pdf(self):
        """Test analyze endpoint with single PDF file"""
        test_file = Path("data/knowledge_base/Prep'd Drawings Osu Project Legends.pdf")
        
        if not test_file.exists():
            pytest.skip("Test file not found")
        
        with open(test_file, "rb") as f:
            response = client.post(
                "/api/v1/analysis/analyze",
                data={"building_type": "commercial", "project_name": "Test Project"},
                files={"files": ("test.pdf", f, "application/pdf")}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "inventory" in data
        assert "calculations" in data
        assert "compliance_audit" in data
        assert "recommendations" in data
        assert "processing_time_ms" in data
        
        # Check inventory is a list
        assert isinstance(data["inventory"], list)
        
        # Check calculations structure
        calc = data["calculations"]
        assert "total_connected_load" in calc
        assert "diversity_factor" in calc
        assert "maximum_demand" in calc
        assert "building_type" in calc
        assert calc["building_type"] == "commercial"
        
        # Check recommendations
        assert isinstance(data["recommendations"], list)
        for rec in data["recommendations"]:
            assert "source" in rec
            assert "percentage" in rec
            assert "capacity_kw" in rec
            assert "reasoning" in rec

    def test_analyze_invalid_building_type(self):
        """Test analyze endpoint with invalid building type"""
        test_file = Path("data/knowledge_base/Prep'd Drawings Osu Project Legends.pdf")
        
        if not test_file.exists():
            pytest.skip("Test file not found")
        
        with open(test_file, "rb") as f:
            response = client.post(
                "/api/v1/analysis/analyze",
                data={"building_type": "invalid_type"},
                files={"files": ("test.pdf", f, "application/pdf")}
            )
        
        assert response.status_code == 422  # Validation error

    def test_analyze_residential_building(self):
        """Test analyze endpoint with residential building type"""
        test_file = Path("data/knowledge_base/Prep'd Drawings Osu Project Legends.pdf")
        
        if not test_file.exists():
            pytest.skip("Test file not found")
        
        with open(test_file, "rb") as f:
            response = client.post(
                "/api/v1/analysis/analyze",
                data={"building_type": "residential"},
                files={"files": ("test.pdf", f, "application/pdf")}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["calculations"]["diversity_factor"] == 0.6

    def test_analyze_industrial_building(self):
        """Test analyze endpoint with industrial building type"""
        test_file = Path("data/knowledge_base/Prep'd Drawings Osu Project Legends.pdf")
        
        if not test_file.exists():
            pytest.skip("Test file not found")
        
        with open(test_file, "rb") as f:
            response = client.post(
                "/api/v1/analysis/analyze",
                data={"building_type": "industrial"},
                files={"files": ("test.pdf", f, "application/pdf")}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["calculations"]["diversity_factor"] == 0.9
        
        # Industrial should have 3 recommendations (grid, generator, solar)
        assert len(data["recommendations"]) == 3

    def test_analyze_multiple_files(self):
        """Test analyze endpoint with multiple files"""
        test_files = [
            Path("data/knowledge_base/Prep'd Drawings Osu Project Legends.pdf"),
            Path("data/knowledge_base/L.I.2478.pdf")
        ]
        
        if not all(f.exists() for f in test_files):
            pytest.skip("Test files not found")
        
        files = []
        for i, test_file in enumerate(test_files):
            files.append(("files", (f"file{i}.pdf", open(test_file, "rb"), "application/pdf")))
        
        try:
            response = client.post(
                "/api/v1/analysis/analyze",
                data={"building_type": "commercial"},
                files=files
            )
            assert response.status_code == 200
            data = response.json()
            assert len(data["inventory"]) > 0
        finally:
            for _, file_tuple in files:
                file_tuple[1].close()


class TestComplianceAudit:
    """Test compliance checking functionality"""
    
    def test_compliance_audit_structure(self):
        """Test that compliance audit has correct structure"""
        test_file = Path("data/knowledge_base/Prep'd Drawings Osu Project Legends.pdf")
        
        if not test_file.exists():
            pytest.skip("Test file not found")
        
        with open(test_file, "rb") as f:
            response = client.post(
                "/api/v1/analysis/analyze",
                data={"building_type": "commercial"},
                files={"files": ("test.pdf", f, "application/pdf")}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data["compliance_audit"], list)
        
        for audit in data["compliance_audit"]:
            assert "standard_clause" in audit
            assert "description" in audit
            assert "compliance_status" in audit
            assert audit["compliance_status"] in ["compliant", "non_compliant", "review_required"]

    def test_diversity_factor_compliance(self):
        """Test that diversity factor is checked for compliance"""
        test_file = Path("data/knowledge_base/Prep'd Drawings Osu Project Legends.pdf")
        
        if not test_file.exists():
            pytest.skip("Test file not found")
        
        with open(test_file, "rb") as f:
            response = client.post(
                "/api/v1/analysis/analyze",
                data={"building_type": "commercial"},
                files={"files": ("test.pdf", f, "application/pdf")}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check for diversity factor compliance entry
        diversity_audit = [a for a in data["compliance_audit"] if "diversity factor" in a["description"].lower()]
        assert len(diversity_audit) > 0
        assert diversity_audit[0]["compliance_status"] == "compliant"


class TestVisionExtraction:
    """Test vision service extraction"""
    
    def test_component_extraction_from_legends(self):
        """Test that components are extracted from legends PDF"""
        test_file = Path("data/knowledge_base/Prep'd Drawings Osu Project Legends.pdf")
        
        if not test_file.exists():
            pytest.skip("Test file not found")
        
        with open(test_file, "rb") as f:
            response = client.post(
                "/api/v1/analysis/analyze",
                data={"building_type": "commercial"},
                files={"files": ("test.pdf", f, "application/pdf")}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have extracted some components
        assert len(data["inventory"]) > 0
        
        # Check for expected components
        component_names = [c["name"].lower() for c in data["inventory"]]
        assert any("switch" in name or "light" in name or "outlet" in name for name in component_names)

    def test_component_ratings_are_numbers(self):
        """Test that component ratings are numeric"""
        test_file = Path("data/knowledge_base/Prep'd Drawings Osu Project Legends.pdf")
        
        if not test_file.exists():
            pytest.skip("Test file not found")
        
        with open(test_file, "rb") as f:
            response = client.post(
                "/api/v1/analysis/analyze",
                data={"building_type": "commercial"},
                files={"files": ("test.pdf", f, "application/pdf")}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        for component in data["inventory"]:
            assert isinstance(component["rating_watts"], (int, float))
            assert isinstance(component["quantity"], int)
            assert isinstance(component["total_watts"], (int, float))
            assert component["total_watts"] == component["quantity"] * component["rating_watts"]


class TestLoadCalculations:
    """Test load calculation accuracy"""
    
    def test_load_calculation_math(self):
        """Test that load calculations are mathematically correct"""
        test_file = Path("data/knowledge_base/Prep'd Drawings Osu Project Legends.pdf")
        
        if not test_file.exists():
            pytest.skip("Test file not found")
        
        with open(test_file, "rb") as f:
            response = client.post(
                "/api/v1/analysis/analyze",
                data={"building_type": "commercial"},
                files={"files": ("test.pdf", f, "application/pdf")}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        calc = data["calculations"]
        
        # Verify calculations
        expected_tcl = sum(c["total_watts"] for c in data["inventory"])
        assert abs(calc["total_connected_load"] - expected_tcl) < 0.01
        
        expected_md = calc["total_connected_load"] * calc["diversity_factor"]
        assert abs(calc["maximum_demand"] - expected_md) < 0.01

    def test_load_calculation_validation(self):
        """Test that load calculations are validated"""
        test_file = Path("data/knowledge_base/Prep'd Drawings Osu Project Legends.pdf")
        
        if not test_file.exists():
            pytest.skip("Test file not found")
        
        with open(test_file, "rb") as f:
            response = client.post(
                "/api/v1/analysis/analyze",
                data={"building_type": "commercial"},
                files={"files": ("test.pdf", f, "application/pdf")}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        calc = data["calculations"]
        
        # Maximum demand should never exceed total connected load
        assert calc["maximum_demand"] <= calc["total_connected_load"]
        
        # Load calculation should be validated
        load_valid_audit = [a for a in data["compliance_audit"] if "load calculation valid" in a["description"].lower()]
        assert len(load_valid_audit) > 0


class TestErrorHandling:
    """Test error handling"""
    
    def test_invalid_file_extension(self):
        """Test that invalid file extensions are rejected"""
        response = client.post(
            "/api/v1/analysis/analyze",
            data={"building_type": "commercial"},
            files={"files": ("test.txt", b"not a pdf", "text/plain")}
        )
        assert response.status_code == 400

    def test_empty_file(self):
        """Test handling of empty files"""
        response = client.post(
            "/api/v1/analysis/analyze",
            data={"building_type": "commercial"},
            files={"files": ("empty.pdf", b"", "application/pdf")}
        )
        # Should still succeed but with empty inventory
        assert response.status_code == 200
        data = response.json()
        assert len(data["inventory"]) == 0


class TestProcessingTime:
    """Test processing performance"""
    
    def test_processing_time_recorded(self):
        """Test that processing time is recorded"""
        test_file = Path("data/knowledge_base/Prep'd Drawings Osu Project Legends.pdf")
        
        if not test_file.exists():
            pytest.skip("Test file not found")
        
        with open(test_file, "rb") as f:
            response = client.post(
                "/api/v1/analysis/analyze",
                data={"building_type": "commercial"},
                files={"files": ("test.pdf", f, "application/pdf")}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "processing_time_ms" in data
        assert isinstance(data["processing_time_ms"], int)
        assert data["processing_time_ms"] > 0
        assert data["processing_time_ms"] < 60000  # Should complete within 60 seconds
