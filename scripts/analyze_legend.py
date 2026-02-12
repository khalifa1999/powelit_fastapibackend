#!/usr/bin/env python3
"""
Legend Analysis and Symbol Mapping Service
Processes blueprint legends to build symbol-to-component mappings
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from pathlib import Path
from datetime import datetime
from PIL import Image
import cv2
import numpy as np
import pytesseract
from typing import Dict, List, Tuple


class LegendAnalyzer:
    """Analyzes blueprint legends to extract symbol definitions"""
    
    def __init__(self):
        self.symbol_mappings = {}
        self.raw_text = ""
        self.lines = []
        
    def load_image(self, image_path: str) -> np.ndarray:
        """Load and return image as numpy array"""
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image: {image_path}")
        return image
    
    def preprocess_for_ocr(self, image: np.ndarray) -> np.ndarray:
        """Enhanced preprocessing for legend text"""
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Resize to improve OCR accuracy (legends often have small text)
        scale_factor = 2.0
        height, width = gray.shape
        resized = cv2.resize(gray, (int(width * scale_factor), int(height * scale_factor)), 
                            interpolation=cv2.INTER_CUBIC)
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(resized)
        
        # Enhance contrast
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)
        
        # Adaptive thresholding
        binary = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY, 11, 2)
        
        return binary
    
    def extract_text(self, image_path: str) -> str:
        """Extract all text from legend image"""
        print(f"\n📄 Loading legend: {Path(image_path).name}")
        
        image = self.load_image(image_path)
        processed = self.preprocess_for_ocr(image)
        
        # Configure Tesseract for better accuracy
        custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789().,:-/='
        
        self.raw_text = pytesseract.image_to_string(processed, config=custom_config)
        self.lines = [line.strip() for line in self.raw_text.split('\n') if line.strip()]
        
        print(f"✓ Extracted {len(self.lines)} lines of text")
        return self.raw_text
    
    def parse_symbol_definitions(self) -> Dict[str, Dict]:
        """
        Parse legend text to find symbol definitions
        Looks for patterns like:
        - Symbol codes with descriptions
        - Abbreviation mappings
        - Component lists
        """
        import re
        
        mappings = {}
        
        # Common electrical symbol patterns
        patterns = [
            # Pattern: Code - Description (e.g., "L - Light", "S = Switch")
            (r'\b([A-Z]{1,3})\s*[-=:]\s*(.+)', 'simple_code'),
            # Pattern: Drawing code (e.g., "00-STB-L2" or "01-STA-P2")
            (r'(\d{2}-[A-Z]{2,4}-[A-Z]\d)', 'drawing_code'),
            # Pattern: Full word descriptions
            (r'\b(LIGHT|LAMP|OUTLET|SOCKET|SWITCH|FAN|AC|AIR.?COND|HVAC|PUMP|MOTOR|DB|DISTRIBUTION)\b', 'keyword'),
        ]
        
        for line in self.lines:
            line_upper = line.upper()
            
            # Look for component keywords
            for comp_type, pattern_info in self._get_component_patterns().items():
                pattern = pattern_info['pattern']
                if re.search(pattern, line_upper):
                    # Try to extract code/abbreviation from the line
                    code = self._extract_code_from_line(line, comp_type)
                    
                    if code and code not in mappings:
                        mappings[code] = {
                            'component_type': comp_type,
                            'description': line.strip(),
                            'default_watts': pattern_info['watts'],
                            'pattern': pattern
                        }
        
        # Also look for drawing reference codes
        drawing_pattern = r'\b(\d{2}-[A-Z]{2,4}-[A-Z]\d)\b'
        for line in self.lines:
            matches = re.findall(drawing_pattern, line.upper())
            for code in matches:
                if code not in mappings:
                    # Try to infer component type from code suffix
                    comp_type = self._infer_component_from_code(code)
                    mappings[code] = {
                        'component_type': comp_type,
                        'description': line.strip(),
                        'default_watts': self._get_watts_for_type(comp_type),
                        'pattern': drawing_pattern,
                        'inferred': True
                    }
        
        self.symbol_mappings = mappings
        return mappings
    
    def _get_component_patterns(self) -> Dict:
        """Return component patterns with default wattages"""
        return {
            'light': {'pattern': r'\b(LIGHT|LAMP|LUMINAIRE|DOWNLIGHT|BULB)\b', 'watts': 12},
            'outlet': {'pattern': r'\b(OUTLET|SOCKET|GPO|RECEPTACLE)\b', 'watts': 100},
            'switch': {'pattern': r'\b(SWITCH|SW)\b', 'watts': 0},
            'fan': {'pattern': r'\b(FAN|CEILING.?FAN|EXHAUST|VENTILATOR)\b', 'watts': 80},
            'ac_unit': {'pattern': r'\b(AC|AIR.?COND|AIRCONDITION|HVAC|COOLER)\b', 'watts': 1500},
            'pump': {'pattern': r'\b(PUMP|MOTOR|CIRCULATOR)\b', 'watts': 750},
            'distribution_board': {'pattern': r'\b(DB|DISTRIBUTION|CONSUMER.?UNIT|DIST.?BOARD)\b', 'watts': 0},
            'water_heater': {'pattern': r'\b(WATER.?HEATER|BOILER|GEYSER)\b', 'watts': 3000},
            'stove': {'pattern': r'\b(STOVE|COOKER|RANGE|HOB)\b', 'watts': 8000},
            'oven': {'pattern': r'\b(OVEN)\b', 'watts': 2500},
            'fridge': {'pattern': r'\b(FRIDGE|REFRIGERATOR|FREEZER)\b', 'watts': 200},
        }
    
    def _extract_code_from_line(self, line: str, comp_type: str) -> str:
        """Try to extract abbreviation code from a legend line"""
        import re
        
        # Look for patterns like "L - Light" or "S = Switch"
        code_pattern = r'^([A-Z]{1,2})\s*[-=:)]'
        match = re.match(code_pattern, line.upper().strip())
        if match:
            return match.group(1)
        
        # Look for single letter at start
        single_letter = r'^([A-Z])\s+'
        match = re.match(single_letter, line.upper().strip())
        if match:
            return match.group(1)
        
        return None
    
    def _infer_component_from_code(self, code: str) -> str:
        """Infer component type from drawing code suffix"""
        import re
        
        # Extract suffix (last part after last hyphen)
        parts = code.split('-')
        if len(parts) >= 2:
            suffix = parts[-1]
            
            # Common suffix mappings
            suffix_map = {
                'L': 'light',
                'S': 'switch',
                'O': 'outlet',
                'F': 'fan',
                'AC': 'ac_unit',
                'P': 'pump',
                'DB': 'distribution_board',
                'M': 'pump',  # Motor
                'WH': 'water_heater',
            }
            
            # Check first letter of suffix
            first_letter = suffix[0] if suffix else ''
            if first_letter in suffix_map:
                return suffix_map[first_letter]
            
            # Check full suffix
            if suffix in suffix_map:
                return suffix_map[suffix]
        
        return 'unknown'
    
    def _get_watts_for_type(self, comp_type: str) -> int:
        """Get default wattage for component type"""
        patterns = self._get_component_patterns()
        if comp_type in patterns:
            return patterns[comp_type]['watts']
        return 100  # Default
    
    def analyze_legend(self, legend_path: str) -> Dict:
        """Complete analysis of a legend file"""
        print(f"\n{'='*70}")
        print("BLUEPRINT LEGEND ANALYSIS")
        print(f"{'='*70}")
        
        # Extract text
        self.extract_text(legend_path)
        
        # Parse symbol definitions
        print("\n🔍 Parsing symbol definitions...")
        mappings = self.parse_symbol_definitions()
        
        # Generate report
        report = self._generate_legend_report(mappings)
        
        # Save results
        self._save_legend_mappings(mappings, legend_path)
        
        return report
    
    def _generate_legend_report(self, mappings: Dict) -> Dict:
        """Generate analysis report"""
        print(f"\n{'='*70}")
        print("LEGEND ANALYSIS RESULTS")
        print(f"{'='*70}")
        
        print(f"\n📊 Statistics:")
        print(f"  Total symbols identified: {len(mappings)}")
        
        # Group by component type
        by_type = {}
        for code, info in mappings.items():
            comp_type = info['component_type']
            if comp_type not in by_type:
                by_type[comp_type] = []
            by_type[comp_type].append(code)
        
        print(f"\n📋 Symbol Mappings by Type:")
        print(f"{'-'*70}")
        
        for comp_type, codes in sorted(by_type.items()):
            print(f"\n{comp_type.upper().replace('_', ' ')}:")
            for code in sorted(codes):
                info = mappings[code]
                inferred = " (inferred)" if info.get('inferred') else ""
                print(f"  • {code:<15} → {info['default_watts']:>5}W{inferred}")
        
        if not mappings:
            print("\n⚠️  No symbol mappings found")
            print("\n💡 Raw text preview:")
            for i, line in enumerate(self.lines[:20], 1):
                print(f"  {i:2d}. {line}")
        
        report = {
            "total_mappings": len(mappings),
            "component_types": list(by_type.keys()),
            "mappings_by_type": by_type,
            "all_mappings": mappings,
            "raw_text_lines": len(self.lines),
            "timestamp": datetime.now().isoformat()
        }
        
        return report
    
    def _save_legend_mappings(self, mappings: Dict, legend_path: str):
        """Save the legend mappings to a JSON file"""
        output_dir = Path("data/training_results")
        output_dir.mkdir(exist_ok=True)
        
        legend_name = Path(legend_path).stem.replace(' ', '_')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f"legend_mappings_{legend_name}_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump({
                "legend_file": legend_path,
                "timestamp": datetime.now().isoformat(),
                "total_mappings": len(mappings),
                "symbol_mappings": mappings,
                "raw_text": self.raw_text
            }, f, indent=2)
        
        print(f"\n💾 Legend mappings saved to: {output_file}")


async def main():
    """Analyze blueprint legend"""
    import sys
    
    # Default to the legend file in training_data
    legend_path = sys.argv[1] if len(sys.argv) > 1 else "data/training_data/blueprint_legends/Blueprint Legends I.png"
    
    if not os.path.exists(legend_path):
        print(f"❌ Error: Legend file not found: {legend_path}")
        print(f"Usage: python analyze_legend.py [path_to_legend_file]")
        sys.exit(1)
    
    # Run analysis
    analyzer = LegendAnalyzer()
    report = analyzer.analyze_legend(legend_path)
    
    print(f"\n{'='*70}")
    print("✅ LEGEND ANALYSIS COMPLETE")
    print(f"{'='*70}")
    
    return report


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
