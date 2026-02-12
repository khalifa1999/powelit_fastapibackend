"""
Gemini-powered Blueprint Analysis Service
Analyzes electrical blueprints and legends using Google's Gemini API
"""
from typing import List, Dict, Optional, Tuple
import base64
import json
import re
from pathlib import Path
from google import genai
from google.genai import types
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable, DeadlineExceeded
from app.config import settings
from app.models.schemas import ElectricalComponent


class GeminiBlueprintService:
    """Service for analyzing electrical blueprints using Gemini API"""
    
    def __init__(self):
        self.client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        self.model = 'gemini-3-flash-preview'
        
    async def analyze_blueprint(
        self, 
        blueprint_file: bytes,
        legend_file: Optional[bytes] = None,
        filename: str = "blueprint"
    ) -> List[ElectricalComponent]:
        """
        Analyze blueprint using Gemini API
        
        Args:
            blueprint_file: Blueprint image/PDF as bytes
            legend_file: Optional legend file as bytes (if separate)
            filename: Name of the blueprint file
            
        Returns:
            List of ElectricalComponent objects
        """
        if legend_file:
            legend_data = await self._parse_legend(legend_file)
            components = await self._analyze_with_legend(
                blueprint_file, 
                legend_data,
                filename
            )
        else:
            components = await self._analyze_combined(blueprint_file, filename)
            
        return components
    
    async def _parse_legend(self, legend_file: bytes) -> Dict[str, Dict]:
        """
        Parse legend file to extract symbol mappings
        
        Returns dict like:
        {
            "P1": {"type": "Power Outlet", "watts": 100},
            "AC1": {"type": "Air Conditioner", "watts": 1500},
            ...
        }
        """
        legend_b64 = base64.b64encode(legend_file).decode('utf-8')
        
        prompt = """You are an expert electrical engineer analyzing an electrical legend/drawing schedule.

Analyze this legend image and extract ALL electrical symbols and their meanings.

For each symbol entry, extract:
1. Symbol code (e.g., "P1", "AC1", "WH1", "S", "CCU1")
2. Component type/description
3. Rating/wattage if specified

Return the data in this exact JSON format:
{
  "symbols": [
    {
      "code": "P1",
      "description": "13A Single Socket Outlet",
      "watts": 100,
      "category": "power_outlet"
    },
    {
      "code": "AC1", 
      "description": "Air Conditioner Outlet",
      "watts": 1500,
      "category": "climate_control"
    }
  ]
}

Categories should be: power_outlet, lighting, climate_control, water_heating, cooking, distribution, safety, communication

If wattage is not specified, estimate based on the component type:
- Power outlets: 100W
- Lighting: 12W  
- AC units: 1500W
- Water heaters: 3000W
- Cookers: 8000W
- Smoke/heat detectors: 5W
- Distribution boards: 0W

Return ONLY valid JSON, no markdown formatting or explanations."""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    prompt,
                    types.Part.from_bytes(data=legend_file, mime_type="image/png")
                ]
            )
            
            response_text = response.text or ""
            result = self._extract_json_from_response(response_text)
            
            legend_dict = {}
            for symbol in result.get("symbols", []):
                code = symbol.get("code", "")
                if code:
                    legend_dict[code] = {
                        "type": symbol.get("description", ""),
                        "watts": symbol.get("watts", 100),
                        "category": symbol.get("category", "unknown")
                    }
                    
            return legend_dict
            
        except ResourceExhausted:
            raise Exception("RATE_LIMIT_EXCEEDED")
        except ServiceUnavailable:
            raise Exception("SERVICE_UNAVAILABLE")
        except DeadlineExceeded:
            raise Exception("REQUEST_TIMEOUT")
        except Exception as e:
            print(f"Error parsing legend: {e}")
            return {}
    
    async def _analyze_with_legend(
        self, 
        blueprint_file: bytes,
        legend_data: Dict[str, Dict],
        filename: str
    ) -> List[ElectricalComponent]:
        """Analyze blueprint with known legend data"""
        
        legend_summary = json.dumps(legend_data, indent=2)
        
        prompt = f"""You are an expert electrical engineer analyzing an electrical blueprint.

Here is the LEGEND data showing what each symbol means:
{legend_summary}

Now analyze this blueprint image and:
1. Count ALL occurrences of each symbol code from the legend
2. Note the locations (rooms/areas) where they appear
3. Verify the counts match what you see

Return results in this exact JSON format:
{{
  "components": [
    {{
      "symbol_code": "P1",
      "description": "13A Single Socket Outlet", 
      "quantity": 5,
      "watts": 100,
      "locations": ["Kitchen", "Living Room", "Bedroom"]
    }},
    {{
      "symbol_code": "AC1",
      "description": "Air Conditioner Outlet",
      "quantity": 3, 
      "watts": 1500,
      "locations": ["Living Room", "Master Bedroom"]
    }}
  ],
  "total_components": 8,
  "notes": "Any observations about the electrical layout"
}}

Important:
- Only count symbols that exist in the legend provided above
- Be precise with quantities - count carefully
- Include the symbol_code exactly as it appears in the legend
- Return ONLY valid JSON, no markdown or explanations"""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    prompt,
                    types.Part.from_bytes(data=blueprint_file, mime_type="image/png")
                ]
            )
            
            response_text = response.text or ""
            result = self._extract_json_from_response(response_text)
            
            components = []
            for comp in result.get("components", []):
                qty = comp.get("quantity", 0)
                watts = comp.get("watts", 100)
                if qty > 0:
                    components.append(ElectricalComponent(
                        name=comp.get("description", comp.get("symbol_code", "Unknown")),
                        quantity=qty,
                        rating_watts=watts,
                        total_watts=qty * watts
                    ))
                    
            return components
            
        except ResourceExhausted:
            raise Exception("RATE_LIMIT_EXCEEDED")
        except ServiceUnavailable:
            raise Exception("SERVICE_UNAVAILABLE")
        except DeadlineExceeded:
            raise Exception("REQUEST_TIMEOUT")
        except Exception as e:
            print(f"Error analyzing blueprint with legend: {e}")
            return []
    
    async def _analyze_combined(
        self, 
        blueprint_file: bytes,
        filename: str
    ) -> List[ElectricalComponent]:
        """Analyze blueprint without separate legend (legend is in the same file or not provided)"""
        
        blueprint_b64 = base64.b64encode(blueprint_file).decode('utf-8')
        
        prompt = """You are an expert electrical engineer analyzing an electrical blueprint.

This blueprint may contain:
1. A legend/drawing schedule section (usually at the top or side)
2. The actual floor plan with electrical symbols

Your task:
1. First, locate and read the LEGEND section if present
2. Identify all electrical symbols and their meanings
3. Count ALL electrical components shown on the blueprint
4. Determine the wattage/power rating for each component type

Common Ghana electrical symbols to look for:
- P1, P2, P3: Power outlets (13A sockets) - 100W each
- AC1, AC2: Air conditioner outlets - 1500W each  
- WH1, WH2: Water heater outlets - 3000W each
- CCU1: Cooker control unit - 8000W
- S: Smoke detector - 5W
- H: Heat detector - 5W
- DB: Distribution board - 0W
- L1, L2: Lighting points - 12W each

Return results in this exact JSON format:
{
  "legend_found": true,
  "components": [
    {
      "name": "13A Single Socket Outlet",
      "symbol_code": "P1",
      "quantity": 5,
      "watts": 100,
      "category": "power_outlet"
    },
    {
      "name": "Air Conditioner Outlet",
      "symbol_code": "AC1",
      "quantity": 3,
      "watts": 1500,
      "category": "climate_control"
    }
  ],
  "total_components": 8,
  "analysis_notes": "Legend was found at top of page. Multi-unit residential building."
}

Categories: power_outlet, lighting, climate_control, water_heating, cooking, distribution, safety, communication

Important:
- Count carefully and be accurate with quantities
- If no legend is visible, use your knowledge of standard electrical symbols
- Include symbol_code if visible (e.g., "P1", "AC1")
- Return ONLY valid JSON, no markdown or explanations"""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    prompt,
                    types.Part.from_bytes(data=blueprint_file, mime_type="image/png")
                ]
            )
            
            response_text = response.text or ""
            result = self._extract_json_from_response(response_text)
            
            components = []
            for comp in result.get("components", []):
                qty = comp.get("quantity", 0)
                watts = comp.get("watts", 100)
                if qty > 0:
                    name = comp.get("name", comp.get("symbol_code", "Unknown"))
                    components.append(ElectricalComponent(
                        name=name,
                        quantity=qty,
                        rating_watts=watts,
                        total_watts=qty * watts
                    ))
                    
            return components
            
        except ResourceExhausted:
            raise Exception("RATE_LIMIT_EXCEEDED")
        except ServiceUnavailable:
            raise Exception("SERVICE_UNAVAILABLE")
        except DeadlineExceeded:
            raise Exception("REQUEST_TIMEOUT")
        except Exception as e:
            print(f"Error analyzing combined blueprint: {e}")
            return []
    
    def _extract_json_from_response(self, text: str) -> Dict:
        """Extract JSON from Gemini response, handling markdown formatting"""
        json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            text = json_match.group(1)
        
        if not text.strip().startswith('{'):
            json_match = re.search(r'(\{.*\})', text, re.DOTALL)
            if json_match:
                text = json_match.group(1)
        
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON: {e}")
            print(f"Raw text: {text[:500]}...")
            return {}


class FileTypeDetector:
    """Helper class to detect file types and content"""
    
    @staticmethod
    def is_likely_legend(filename: str, content: bytes) -> bool:
        """Detect if file is likely a legend based on filename and content"""
        legend_keywords = ['legend', 'schedule', 'symbol', 'abbreviation', 'drawing schedule']
        filename_lower = filename.lower()
        
        for keyword in legend_keywords:
            if keyword in filename_lower:
                return True
        
        return False
    
    @staticmethod
    def is_likely_blueprint(filename: str, content: bytes) -> bool:
        """Detect if file is likely a blueprint"""
        blueprint_keywords = ['plan', 'layout', 'drawing', 'blueprint', 'floor', 'elevation']
        filename_lower = filename.lower()
        
        for keyword in blueprint_keywords:
            if keyword in filename_lower:
                return True
                
        return not FileTypeDetector.is_likely_legend(filename, content)
    
    @staticmethod
    def detect_file_types(files: List[Tuple[str, bytes]]) -> Dict[str, List[Tuple[str, bytes]]]:
        """
        Sort files into legends and blueprints
        
        Returns:
            {
                "legends": [(filename, content), ...],
                "blueprints": [(filename, content), ...]
            }
        """
        legends = []
        blueprints = []
        
        print(f"🔍 Detecting file types for {len(files)} files...")
        
        for filename, content in files:
            is_legend = FileTypeDetector.is_likely_legend(filename, content)
            print(f"   {filename}: {'LEGEND' if is_legend else 'BLUEPRINT'}")
            if is_legend:
                legends.append((filename, content))
            else:
                blueprints.append((filename, content))
        
        print(f"✓ Categorized: {len(legends)} legends, {len(blueprints)} blueprints")
                
        return {
            "legends": legends,
            "blueprints": blueprints
        }
