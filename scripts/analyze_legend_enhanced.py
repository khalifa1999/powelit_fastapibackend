#!/usr/bin/env python3
"""
Enhanced Legend Parser for Blueprint Legends
Handles the specific format found in Blueprint Legends I.png
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import re
from pathlib import Path
from datetime import datetime
from PIL import Image
import cv2
import numpy as np
import pytesseract
from typing import Dict, List, Tuple, Optional


class EnhancedLegendParser:
    """Enhanced parser for blueprint legends with complex formatting"""
    
    def __init__(self):
        self.raw_text = ""
        self.lines = []
        self.symbol_mappings = {}
        
    def extract_text(self, image_path: str) -> str:
        """Extract text with enhanced preprocessing"""
        print(f"\n📄 Loading legend: {Path(image_path).name}")
        
        # Load with PIL first for better quality
        pil_image = Image.open(image_path)
        
        # Convert to OpenCV format
        cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        
        # Enhanced preprocessing
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        
        # Scale up (legends have small text)
        height, width = gray.shape
        scale = 2.5
        resized = cv2.resize(gray, (int(width * scale), int(height * scale)), 
                            interpolation=cv2.INTER_CUBIC)
        
        # Denoise and enhance
        denoised = cv2.fastNlMeansDenoising(resized, None, 10, 7, 21)
        
        # Increase contrast
        clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)
        
        # Binary threshold
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Configure Tesseract for better accuracy
        # PSM 6 = Assume a single uniform block of text
        custom_config = r'--oem 3 --psm 6'
        
        self.raw_text = pytesseract.image_to_string(binary, config=custom_config)
        self.lines = [line.strip() for line in self.raw_text.split('\n') if line.strip()]
        
        print(f"✓ Extracted {len(self.lines)} lines of text")
        return self.raw_text
    
    def parse_detailed(self) -> Dict[str, Dict]:
        """Parse legend with detailed pattern matching"""
        mappings = {}
        
        print("\n🔍 Analyzing symbol patterns...")
        
        for line_num, line in enumerate(self.lines, 1):
            line_upper = line.upper()
            
            # Pattern 1: Component with wattage (e.g., "11W LED DOWNLIGHT")
            watt_match = re.search(r'(\d+)\s*W', line_upper)
            watts = int(watt_match.group(1)) if watt_match else None
            
            # Pattern 2: Extract component type based on keywords
            comp_type = self._identify_component_type(line_upper)
            
            # Pattern 3: Look for symbol codes/abbreviations
            symbol_code = self._extract_symbol_code(line, line_upper)
            
            # Pattern 4: Check for mounting height (e.g., "1200 AFFL")
            height_match = re.search(r'(\d+)\s*AFFL', line_upper)
            height = height_match.group(1) + " AFFL" if height_match else None
            
            if comp_type and comp_type != 'unknown':
                # Create unique key
                if symbol_code:
                    key = symbol_code
                else:
                    # Generate key from component type + line number
                    key = f"{comp_type}_{line_num}"
                
                mappings[key] = {
                    'component_type': comp_type,
                    'description': line.strip(),
                    'raw_line': line,
                    'line_number': line_num,
                    'symbol_code': symbol_code,
                    'watts': watts if watts else self._default_watts(comp_type),
                    'mounting_height': height,
                    'keywords_found': self._get_matched_keywords(line_upper)
                }
        
        self.symbol_mappings = mappings
        return mappings
    
    def _identify_component_type(self, line: str) -> str:
        """Identify component type from line content"""
        
        # Define patterns with priority (more specific first)
        patterns = [
            # Light fixtures
            (r'\b(LED\s+(RECESSED|SURFACE|TRACK)\s*(DOWN)?LIGHT|DOWNLIGHT|SPOTLIGHT)\b', 'light'),
            (r'\b(LED\s+LIGHT|LIGHT\s+FIXTURE|LUMINAIRE)\b', 'light'),
            
            # Switches
            (r'\b(\d+GANG\s*\d+WAY\s*SWITCH|1GANG\s*SWITCH|2GANG\s*SWITCH|3GANG\s*SWITCH)\b', 'switch'),
            (r'\b(INTERMEDIATE\s*SWITCH|2WAY\s*SWITCH)\b', 'switch'),
            
            # Outlets/Sockets
            (r'\b(SWITCHED\s*SOCKET|DOUBLE\s*SOCKET|SHAVERSOCKET|13A\s*SOCKET)\b', 'outlet'),
            (r'\b(\d+A\s*SOCKET|GPO|RECEPTACLE)\b', 'outlet'),
            
            # Fans
            (r'\b(\d+W\s*FAN|CEILING\s*FAN|EXHAUST\s*FAN|FAN\s*REGULATOR)\b', 'fan'),
            
            # AC/HVAC
            (r'\b(AIR\s*CONDITION|HVAC|COOLING|AC\s+UNIT)\b', 'ac_unit'),
            
            # Detectors (Fire/Safety)
            (r'\b(SMOKE\s*DETECTOR|HEAT\s*DETECTOR|FIRE\s*ALARM|CALL\s*POINT)\b', 'detector'),
            (r'\b(FIRE\s*PANEL|SOUNDER|BELL)\b', 'detector'),
            
            # Distribution
            (r'\b(DISTRIBUTION\s*BOARD|CONSUMER\s*UNIT|DB|MCCB|MCB|PANEL)\b', 'distribution_board'),
            
            # Motors/Pumps
            (r'\b(MOTOR|PUMP|CIRCULATOR)\b', 'pump'),
            
            # Water heating
            (r'\b(WATER\s*HEATER|BOILER|GEYSER)\b', 'water_heater'),
            
            # Cooking
            (r'\b(COOKER|STOVE|RANGE|OVEN)\b', 'stove'),
            
            # Earthing
            (r'\b(EARTH|GROUND|TERMINAL\s*ROD|EARTH\s*CHAMBER)\b', 'earthing'),
            
            # Cable/Materials
            (r'\b(CABLE|TAPE|CONDUIT|TRUNKING)\b', 'cable'),
        ]
        
        for pattern, comp_type in patterns:
            if re.search(pattern, line):
                return comp_type
        
        return 'unknown'
    
    def _extract_symbol_code(self, line: str, line_upper: str) -> Optional[str]:
        """Extract symbol/abbreviation code from line"""
        
        # Pattern 1: Symbol in parentheses (e.g., "(A)" or "[A]")
        paren_match = re.search(r'[\(\[]([A-Z\d]{1,3})[\)\]]', line_upper)
        if paren_match:
            return paren_match.group(1)
        
        # Pattern 2: Starting letter/number sequence
        start_match = re.match(r'^([A-Z])\s+', line_upper)
        if start_match:
            return start_match.group(1)
        
        # Pattern 3: Drawing reference codes (e.g., "00-STB-L2")
        drawing_match = re.search(r'\b(\d{2}-[A-Z]{2,4}-[A-Z]\d)\b', line_upper)
        if drawing_match:
            return drawing_match.group(1)
        
        return None
    
    def _default_watts(self, comp_type: str) -> int:
        """Get default wattage for component type"""
        defaults = {
            'light': 12,
            'switch': 0,
            'outlet': 100,
            'fan': 80,
            'ac_unit': 1500,
            'detector': 5,
            'distribution_board': 0,
            'pump': 750,
            'water_heater': 3000,
            'stove': 8000,
            'earthing': 0,
            'cable': 0,
        }
        return defaults.get(comp_type, 100)
    
    def _get_matched_keywords(self, line: str) -> List[str]:
        """Return list of keywords matched in the line"""
        keywords = []
        keyword_patterns = [
            'LED', 'RECESSED', 'SURFACE', 'DOWNLIGHT', 'TRACK', 'SWITCH', 
            'SOCKET', 'OUTLET', 'FAN', 'AC', 'AIR', 'CONDITION', 'DETECTOR',
            'SMOKE', 'HEAT', 'FIRE', 'ALARM', 'PANEL', 'DB', 'MOTOR', 'PUMP'
        ]
        
        for keyword in keyword_patterns:
            if keyword in line:
                keywords.append(keyword)
        
        return keywords
    
    def generate_report(self) -> Dict:
        """Generate comprehensive analysis report"""
        print(f"\n{'='*70}")
        print("LEGEND ANALYSIS REPORT")
        print(f"{'='*70}")
        
        mappings = self.symbol_mappings
        
        print(f"\n📊 Summary Statistics:")
        print(f"  Total symbols identified: {len(mappings)}")
        print(f"  Raw text lines processed: {len(self.lines)}")
        
        # Group by component type
        by_type = {}
        for key, info in mappings.items():
            comp_type = info['component_type']
            if comp_type not in by_type:
                by_type[comp_type] = []
            by_type[comp_type].append(info)
        
        print(f"\n📋 Symbol Definitions by Type:")
        print(f"{'-'*70}")
        
        for comp_type in sorted(by_type.keys()):
            items = by_type[comp_type]
            print(f"\n🔹 {comp_type.upper().replace('_', ' ')} ({len(items)} symbols):")
            
            for item in items:
                symbol = item.get('symbol_code') or 'N/A'
                watts = item.get('watts', 0)
                height = item.get('mounting_height', '') or ''
                desc = item['description'][:60] + '...' if len(item['description']) > 60 else item['description']
                
                print(f"  • {symbol:<12} {watts:>4}W  {height:<12} {desc}")
        
        # List unknown items
        if 'unknown' in by_type:
            print(f"\n⚠️  Unidentified Items ({len(by_type['unknown'])}):")
            for item in by_type['unknown'][:5]:
                print(f"  • {item['description'][:70]}")
            if len(by_type['unknown']) > 5:
                print(f"    ... and {len(by_type['unknown']) - 5} more")
        
        # Calculate totals
        total_watts = sum(item['watts'] * item.get('quantity', 1) for item in mappings.values())
        print(f"\n📈 Total Power Capacity (if all active):")
        print(f"  {total_watts:,}W ({total_watts/1000:.2f}kW)")
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_mappings": len(mappings),
            "component_types": list(by_type.keys()),
            "mappings_by_type": {k: len(v) for k, v in by_type.items()},
            "detailed_mappings": mappings,
            "raw_text": self.raw_text
        }
    
    def save_mappings(self, output_path: str = None):
        """Save mappings to JSON file"""
        output_dir = Path("data/training_results")
        output_dir.mkdir(exist_ok=True)
        
        if not output_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = output_dir / f"enhanced_legend_mappings_{timestamp}.json"
        
        report = self.generate_report()
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n💾 Detailed report saved to: {output_path}")
        return output_path
    
    def analyze(self, image_path: str) -> Dict:
        """Complete legend analysis pipeline"""
        print(f"\n{'='*70}")
        print("BLUEPRINT LEGEND ANALYZER")
        print(f"{'='*70}")
        
        # Extract text
        self.extract_text(image_path)
        
        # Parse mappings
        self.parse_detailed()
        
        # Generate report
        report = self.generate_report()
        
        # Save results
        self.save_mappings()
        
        return report


def main():
    """Run legend analysis"""
    import sys
    
    # Default legend path
    legend_path = sys.argv[1] if len(sys.argv) > 1 else "data/training_data/blueprint_legends/Blueprint Legends I.png"
    
    if not os.path.exists(legend_path):
        print(f"❌ Error: Legend file not found: {legend_path}")
        sys.exit(1)
    
    # Run analysis
    parser = EnhancedLegendParser()
    report = parser.analyze(legend_path)
    
    print(f"\n{'='*70}")
    print("✅ LEGEND ANALYSIS COMPLETE")
    print(f"{'='*70}")
    
    return report


if __name__ == "__main__":
    main()
