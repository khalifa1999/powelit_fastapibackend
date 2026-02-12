#!/usr/bin/env python3
"""
Symbol Recognition Service for Electrical Blueprints
Detects graphical symbols (circles, squares, crosses) used in electrical drawings
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np
from PIL import Image
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path
import json


@dataclass
class DetectedSymbol:
    """Represents a detected electrical symbol"""
    symbol_type: str  # 'circle', 'square', 'cross', 'triangle', etc.
    x: int
    y: int
    width: int
    height: int
    confidence: float
    potential_component: str  # Mapped component type based on legend


class SymbolRecognitionService:
    """
    Detects electrical symbols in blueprint images using computer vision
    
    Common electrical symbols:
    - Circle: Light fixture, outlet, junction box
    - Square/Rectangle: Switch, distribution board
    - Cross (+): Fan, motor
    - Triangle: Ground/earth
    - Arc: Door/window (architectural)
    """
    
    def __init__(self):
        self.legend_mappings = self._load_legend_mappings()
        self.symbol_templates = self._create_symbol_templates()
        
    def _load_legend_mappings(self) -> Dict:
        """Load symbol definitions from legend analysis"""
        mappings = {}
        results_dir = Path("data/training_results")
        
        if results_dir.exists():
            legend_files = sorted(results_dir.glob("enhanced_legend_mappings_*.json"))
            if legend_files:
                try:
                    with open(legend_files[-1], 'r') as f:
                        data = json.load(f)
                        mappings = data.get('detailed_mappings', {})
                except Exception as e:
                    print(f"⚠ Could not load legend mappings: {e}")
        
        return mappings
    
    def _create_symbol_templates(self) -> Dict:
        """Create templates for common electrical symbols"""
        templates = {
            'circle_light': {
                'shape': 'circle',
                'min_area': 50,
                'max_area': 2000,
                'circularity': (0.7, 1.0),
                'component_map': 'light',
                'description': 'Light fixture (ceiling/wall)'
            },
            'circle_outlet': {
                'shape': 'circle',
                'min_area': 30,
                'max_area': 500,
                'circularity': (0.7, 1.0),
                'component_map': 'outlet',
                'description': 'Power outlet/socket'
            },
            'square_switch': {
                'shape': 'rectangle',
                'min_area': 100,
                'max_area': 1500,
                'aspect_ratio': (0.7, 1.3),
                'component_map': 'switch',
                'description': 'Light switch'
            },
            'square_db': {
                'shape': 'rectangle',
                'min_area': 500,
                'max_area': 5000,
                'aspect_ratio': (0.5, 2.0),
                'component_map': 'distribution_board',
                'description': 'Distribution board/consumer unit'
            },
            'cross_fan': {
                'shape': 'cross',
                'min_area': 100,
                'max_area': 2000,
                'component_map': 'fan',
                'description': 'Ceiling fan'
            },
            'triangle_ground': {
                'shape': 'triangle',
                'min_area': 50,
                'max_area': 1000,
                'component_map': 'earthing',
                'description': 'Ground/earth symbol'
            }
        }
        return templates
    
    def preprocess_for_symbol_detection(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess image for optimal symbol detection
        """
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Resize to standard size for consistent detection
        height, width = gray.shape
        scale = 1500 / max(height, width)
        if scale < 1.0:
            new_width = int(width * scale)
            new_height = int(height * scale)
            gray = cv2.resize(gray, (new_width, new_height))
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        
        # Enhance contrast
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)
        
        return enhanced
    
    def detect_circles(self, image: np.ndarray) -> List[DetectedSymbol]:
        """Detect circular symbols (lights, outlets)"""
        detected = []
        
        # Edge detection
        edges = cv2.Canny(image, 50, 150)
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            
            # Filter by area
            if area < 30 or area > 3000:
                continue
            
            # Calculate circularity
            perimeter = cv2.arcLength(contour, True)
            if perimeter == 0:
                continue
            
            circularity = 4 * np.pi * area / (perimeter ** 2)
            
            # Check if circular (circularity close to 1)
            if 0.6 <= circularity <= 1.0:
                x, y, w, h = cv2.boundingRect(contour)
                
                # Determine if it's a light or outlet based on size
                if area > 300:
                    component = 'light'
                    symbol_type = 'circle_light'
                else:
                    component = 'outlet'
                    symbol_type = 'circle_outlet'
                
                detected.append(DetectedSymbol(
                    symbol_type=symbol_type,
                    x=x,
                    y=y,
                    width=w,
                    height=h,
                    confidence=circularity,
                    potential_component=component
                ))
        
        return detected
    
    def detect_rectangles(self, image: np.ndarray) -> List[DetectedSymbol]:
        """Detect rectangular symbols (switches, distribution boards)"""
        detected = []
        
        # Threshold to binary
        _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Morphological operations to clean up
        kernel = np.ones((3, 3), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)
        
        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            
            # Filter by area
            if area < 80 or area > 8000:
                continue
            
            # Approximate polygon
            epsilon = 0.04 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            # Check if rectangle (4 corners)
            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = float(w) / h if h > 0 else 0
                
                # Determine component type based on size and aspect ratio
                if area > 1000:
                    component = 'distribution_board'
                    symbol_type = 'square_db'
                else:
                    component = 'switch'
                    symbol_type = 'square_switch'
                
                # Filter reasonable aspect ratios
                if 0.4 <= aspect_ratio <= 2.5:
                    detected.append(DetectedSymbol(
                        symbol_type=symbol_type,
                        x=x,
                        y=y,
                        width=w,
                        height=h,
                        confidence=0.8,
                        potential_component=component
                    ))
        
        return detected
    
    def detect_crosses(self, image: np.ndarray) -> List[DetectedSymbol]:
        """Detect cross/plus symbols (fans)"""
        detected = []
        
        # Threshold
        _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Use template matching for crosses
        # Create a simple cross template
        cross_template = np.zeros((40, 40), dtype=np.uint8)
        cv2.line(cross_template, (20, 5), (20, 35), 255, 3)
        cv2.line(cross_template, (5, 20), (35, 20), 255, 3)
        
        # Template matching at multiple scales
        for scale in [0.5, 0.75, 1.0, 1.25, 1.5]:
            resized_template = cv2.resize(cross_template, None, fx=scale, fy=scale)
            if resized_template.shape[0] > binary.shape[0] or resized_template.shape[1] > binary.shape[1]:
                continue
            
            result = cv2.matchTemplate(binary, resized_template, cv2.TM_CCOEFF_NORMED)
            threshold = 0.7
            
            locations = np.where(result >= threshold)
            for pt in zip(*locations[::-1]):
                # Check if this location is already detected (non-maximum suppression)
                is_duplicate = False
                for det in detected:
                    if abs(det.x - pt[0]) < 20 and abs(det.y - pt[1]) < 20:
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    h, w = resized_template.shape
                    detected.append(DetectedSymbol(
                        symbol_type='cross_fan',
                        x=pt[0],
                        y=pt[1],
                        width=w,
                        height=h,
                        confidence=float(result[pt[1], pt[0]]),
                        potential_component='fan'
                    ))
        
        return detected
    
    def detect_lines_and_wires(self, image: np.ndarray) -> List[Dict]:
        """Detect electrical lines and wiring paths"""
        lines_detected = []
        
        # Edge detection
        edges = cv2.Canny(image, 50, 150, apertureSize=3)
        
        # Hough Line Transform
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, 
                                minLineLength=30, maxLineGap=10)
        
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                length = np.sqrt((x2-x1)**2 + (y2-y1)**2)
                
                if length > 50:  # Filter short segments
                    lines_detected.append({
                        'x1': int(x1),
                        'y1': int(y1),
                        'x2': int(x2),
                        'y2': int(y2),
                        'length': float(length)
                    })
        
        return lines_detected
    
    def analyze_blueprint(self, image_path: str) -> Dict:
        """
        Complete blueprint analysis with symbol recognition
        """
        print(f"\n🔍 Analyzing blueprint: {Path(image_path).name}")
        
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image: {image_path}")
        
        # Preprocess
        processed = self.preprocess_for_symbol_detection(image)
        
        # Detect all symbol types
        print("  Detecting circular symbols...")
        circles = self.detect_circles(processed)
        
        print("  Detecting rectangular symbols...")
        rectangles = self.detect_rectangles(processed)
        
        print("  Detecting cross symbols...")
        crosses = self.detect_crosses(processed)
        
        print("  Detecting wiring lines...")
        lines = self.detect_lines_and_wires(processed)
        
        # Combine all symbols
        all_symbols = circles + rectangles + crosses
        
        # Remove duplicates (overlapping detections)
        filtered_symbols = self._remove_duplicate_detections(all_symbols)
        
        # Aggregate by component type
        component_counts = {}
        for symbol in filtered_symbols:
            comp_type = symbol.potential_component
            if comp_type not in component_counts:
                component_counts[comp_type] = {
                    'count': 0,
                    'symbols': [],
                    'total_watts': 0
                }
            
            component_counts[comp_type]['count'] += 1
            component_counts[comp_type]['symbols'].append({
                'type': symbol.symbol_type,
                'position': (symbol.x, symbol.y),
                'confidence': round(symbol.confidence, 2)
            })
            
            # Add wattage from legend
            watts = self._get_wattage_for_component(comp_type)
            component_counts[comp_type]['total_watts'] += watts
        
        # Generate report
        report = {
            'filename': Path(image_path).name,
            'total_symbols_detected': len(filtered_symbols),
            'symbol_breakdown': {
                'circles': len(circles),
                'rectangles': len(rectangles),
                'crosses': len(crosses),
                'lines': len(lines)
            },
            'components': component_counts,
            'wiring_segments': len(lines),
            'detections': [
                {
                    'type': s.symbol_type,
                    'component': s.potential_component,
                    'position': {'x': s.x, 'y': s.y},
                    'size': {'w': s.width, 'h': s.height},
                    'confidence': round(s.confidence, 2)
                }
                for s in filtered_symbols
            ]
        }
        
        return report
    
    def _remove_duplicate_detections(self, symbols: List[DetectedSymbol], 
                                     min_distance: int = 30) -> List[DetectedSymbol]:
        """Remove overlapping symbol detections"""
        if not symbols:
            return []
        
        # Sort by confidence (highest first)
        sorted_symbols = sorted(symbols, key=lambda s: s.confidence, reverse=True)
        
        filtered = []
        for symbol in sorted_symbols:
            # Check if too close to already filtered symbols
            is_duplicate = False
            for kept in filtered:
                distance = np.sqrt((symbol.x - kept.x)**2 + (symbol.y - kept.y)**2)
                if distance < min_distance:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                filtered.append(symbol)
        
        return filtered
    
    def _get_wattage_for_component(self, component_type: str) -> int:
        """Get default wattage for component type from legend or defaults"""
        # Check legend mappings
        for key, mapping in self.legend_mappings.items():
            if mapping.get('component_type') == component_type:
                return mapping.get('watts', 100)
        
        # Fallback defaults
        defaults = {
            'light': 12,
            'switch': 0,
            'outlet': 100,
            'fan': 80,
            'ac_unit': 1500,
            'distribution_board': 0,
            'detector': 5,
            'water_heater': 3000,
            'stove': 8000,
        }
        
        return defaults.get(component_type, 100)
    
    def visualize_detections(self, image_path: str, output_path: str = None):
        """Create visualization of detected symbols"""
        image = cv2.imread(image_path)
        processed = self.preprocess_for_symbol_detection(image)
        
        # Detect symbols
        circles = self.detect_circles(processed)
        rectangles = self.detect_rectangles(processed)
        crosses = self.detect_crosses(processed)
        
        all_symbols = circles + rectangles + crosses
        filtered = self._remove_duplicate_detections(all_symbols)
        
        # Draw detections on original image
        vis_image = image.copy()
        
        colors = {
            'circle_light': (0, 255, 0),      # Green
            'circle_outlet': (255, 255, 0),    # Cyan
            'square_switch': (0, 0, 255),      # Red
            'square_db': (255, 0, 255),        # Magenta
            'cross_fan': (0, 165, 255),        # Orange
        }
        
        for symbol in filtered:
            color = colors.get(symbol.symbol_type, (128, 128, 128))
            
            # Draw bounding box
            cv2.rectangle(vis_image, 
                         (symbol.x, symbol.y), 
                         (symbol.x + symbol.width, symbol.y + symbol.height),
                         color, 2)
            
            # Draw label
            label = f"{symbol.potential_component} ({symbol.confidence:.2f})"
            cv2.putText(vis_image, label, 
                       (symbol.x, symbol.y - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        if output_path:
            cv2.imwrite(output_path, vis_image)
            print(f"✓ Visualization saved: {output_path}")
        
        return vis_image


def main():
    """Test symbol recognition on blueprints"""
    import sys
    
    # Get blueprint directory
    blueprint_dir = sys.argv[1] if len(sys.argv) > 1 else "data/training_data/blueprints/"
    
    print("="*70)
    print("ELECTRICAL SYMBOL RECOGNITION SYSTEM")
    print("="*70)
    
    # Initialize service
    recognizer = SymbolRecognitionService()
    
    # Find all blueprint files
    blueprint_files = []
    for ext in ['*.png', '*.jpg', '*.jpeg', '*.pdf']:
        blueprint_files.extend(Path(blueprint_dir).glob(ext))
    
    if not blueprint_files:
        print(f"\n❌ No blueprint files found in: {blueprint_dir}")
        return
    
    print(f"\n📁 Found {len(blueprint_files)} blueprint(s)")
    print("="*70)
    
    # Process each blueprint
    all_results = []
    
    for i, blueprint_file in enumerate(sorted(blueprint_files), 1):
        print(f"\n[{i}/{len(blueprint_files)}] Processing: {blueprint_file.name}")
        
        try:
            # Analyze blueprint
            report = recognizer.analyze_blueprint(str(blueprint_file))
            all_results.append(report)
            
            # Print summary
            print(f"  ✓ Total symbols detected: {report['total_symbols_detected']}")
            print(f"    - Circles: {report['symbol_breakdown']['circles']}")
            print(f"    - Rectangles: {report['symbol_breakdown']['rectangles']}")
            print(f"    - Crosses: {report['symbol_breakdown']['crosses']}")
            print(f"    - Wiring lines: {report['symbol_breakdown']['lines']}")
            
            if report['components']:
                print(f"\n  📋 Components identified:")
                for comp_type, data in report['components'].items():
                    print(f"    • {comp_type}: {data['count']} ({data['total_watts']}W)")
            
            # Generate visualization
            output_dir = Path("data/training_results/visualizations")
            output_dir.mkdir(parents=True, exist_ok=True)
            vis_path = output_dir / f"detected_{blueprint_file.stem}.png"
            recognizer.visualize_detections(str(blueprint_file), str(vis_path))
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            import traceback
            traceback.print_exc()
    
    # Save comprehensive report
    print("\n" + "="*70)
    print("GENERATING COMPREHENSIVE REPORT")
    print("="*70)
    
    output_dir = Path("data/training_results")
    output_dir.mkdir(exist_ok=True)
    
    import datetime
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = output_dir / f"symbol_recognition_report_{timestamp}.json"
    
    # Convert numpy types to Python types for JSON serialization
    def convert_to_serializable(obj):
        if isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, tuple):
            return [convert_to_serializable(item) for item in obj]
        elif isinstance(obj, dict):
            return {k: convert_to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_to_serializable(item) for item in obj]
        return obj
    
    serializable_results = convert_to_serializable(all_results)
    
    with open(report_file, 'w') as f:
        json.dump({
            'timestamp': datetime.datetime.now().isoformat(),
            'total_blueprints': len(serializable_results),
            'results': serializable_results
        }, f, indent=2)
    
    print(f"✓ Report saved: {report_file}")
    
    # Print overall summary
    print("\n" + "="*70)
    print("OVERALL SUMMARY")
    print("="*70)
    
    total_symbols = sum(r['total_symbols_detected'] for r in all_results)
    total_components = {}
    
    for result in all_results:
        for comp_type, data in result['components'].items():
            if comp_type not in total_components:
                total_components[comp_type] = {'count': 0, 'watts': 0}
            total_components[comp_type]['count'] += data['count']
            total_components[comp_type]['watts'] += data['total_watts']
    
    print(f"\nTotal blueprints analyzed: {len(all_results)}")
    print(f"Total symbols detected: {total_symbols}")
    
    if total_components:
        print(f"\nComponent Summary:")
        print(f"{'-'*70}")
        grand_total_watts = 0
        for comp_type, data in sorted(total_components.items()):
            print(f"  {comp_type:<25} {data['count']:>5} units  {data['watts']:>8}W")
            grand_total_watts += data['watts']
        print(f"{'-'*70}")
        print(f"  {'TOTAL':<25} {sum(d['count'] for d in total_components.values()):>5} units  {grand_total_watts:>8}W")
    
    print("\n" + "="*70)
    print("✅ SYMBOL RECOGNITION COMPLETE")
    print("="*70)


if __name__ == "__main__":
    main()
