from typing import List, Dict, Tuple, Optional, Union
import re
import os
import tempfile
import shutil
from pathlib import Path
from starlette.datastructures import UploadFile
import pytesseract
from PIL import Image
import cv2
import numpy as np
from pypdf import PdfReader
from pdf2image import convert_from_path
from app.models.schemas import ElectricalComponent
from app.config import settings


class VisionService:
    """Service for extracting electrical components from blueprints using open-source OCR"""

    def __init__(self):
        self.common_electrical_symbols = {
            'outlet': {'pattern': r'\b(GPO|SOCKET|OUTLET)\b', 'watts': 100},
            'light': {'pattern': r'\b(LIGHT|LUMINAIRE|LAMP|DOWNLIGHT)\b', 'watts': 12},  # LED lights typically 10-15W
            'switch': {'pattern': r'\b(SWITCH|SW)\b', 'watts': 0},
            'ac_unit': {'pattern': r'\b(AC|AIR.?COND|HVAC|AIRCONDITION)\b', 'watts': 1500},
            'fan': {'pattern': r'\b(FAN|CEILING.?FAN|EXHAUST.?FAN)\b', 'watts': 80},
            'water_heater': {'pattern': r'\b(WATER.?HEATER|BOILER|GEYSER)\b', 'watts': 3000},
            'stove': {'pattern': r'\b(STOVE|COOKER|RANGE)\b', 'watts': 8000},
            'oven': {'pattern': r'\b(OVEN)\b', 'watts': 2500},
            'fridge': {'pattern': r'\b(FRIDGE|REFRIGERATOR|FREEZER)\b', 'watts': 200},
            'pump': {'pattern': r'\b(PUMP|MOTOR|CIRCULATOR)\b', 'watts': 750},
            'distribution_board': {'pattern': r'\b(DB|DISTRIBUTION|CONSUMER.?UNIT|DISTRIBUTION.?BOARD)\b', 'watts': 0},
            'meter': {'pattern': r'\b(METER|KWH.?METER)\b', 'watts': 0},
            'tv': {'pattern': r'\b(TV|TELEVISION|HDMI)\b', 'watts': 150},
            'shaver_socket': {'pattern': r'\b(SHAVER)\b', 'watts': 50},
            'cooker_unit': {'pattern': r'\b(COOKER.?CONTROL|COOKER.?UNIT)\b', 'watts': 0},
        }

    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Enhance image quality for better OCR"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        denoised = cv2.fastNlMeansDenoising(gray)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary

    def detect_electrical_symbols(self, image: np.ndarray, text: str) -> List[Dict]:
        """Detect electrical symbols using contour analysis and text matching"""
        components = []
        lines = text.split('\n')

        for line in lines:
            line_upper = line.upper().strip()
            for symbol_name, config in self.common_electrical_symbols.items():
                if re.search(config['pattern'], line_upper):
                    qty = self._extract_quantity(line_upper)
                    if qty > 0:
                        component_name = symbol_name.replace('_', ' ').title()
                        # Try to extract actual wattage from the line, fallback to default
                        actual_watts = self._extract_wattage(line, config['watts'], component_name)
                        components.append({
                            'name': component_name,
                            'quantity': qty,
                            'watts': actual_watts,
                            'raw_text': line
                        })
        return components

    def _extract_quantity(self, text: str) -> int:
        """Extract quantity from text line"""
        patterns = [
            r'\b(\d+)\s*(?:NO|NOS|NOS?\.|PCS|EA)\b',
            r'\bQTY[:\s]*(\d+)',
            r'\b(\d+)\s+(?:X|TIMES)\b',
            r'\b(?:X|×)\s*(\d+)',
            r'\b(\d{1,3})\s+(?:OUTLET|SOCKET|LIGHT|SWITCH|FAN)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return 1

    def _extract_wattage(self, text: str, default_watts: int, component_name: str = "") -> float:
        """Extract wattage rating from text, falling back to default if not found
        
        Looks for patterns like:
        - 3000W, 3kW, 3KW
        - 15A (converts to watts at 230V) - only for high-power devices
        - 3.5kVA (converts to watts)
        """
        text_upper = text.upper()
        comp_upper = component_name.upper()
        
        # These are socket/outlet ratings, not connected loads - don't convert amps
        socket_devices = ['OUTLET', 'SOCKET', 'GPO']
        is_socket = any(x in comp_upper for x in socket_devices)
        
        # Don't extract amps for these low-power/non-consuming devices
        no_amp_conversion = ['SWITCH', 'DISTRIBUTION', 'DB', 'METER', 'MCB', 'BREAKER', 'ISOLATOR']
        should_convert_amps = not any(x in comp_upper for x in no_amp_conversion + socket_devices)
        
        # Pattern 1: LED wattage (e.g., "11W LED", "12W LED")
        led_pattern = r'(\d+)\s*W\s+LED'
        match = re.search(led_pattern, text_upper)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        
        # Pattern 2: Direct wattage (3000W, 3000 W, 3,000W, 3000 WATT)
        # But avoid matching things like "6A" or "1200 AFFL"
        watt_patterns = [
            r'\b(\d{3,4}(?:,\d{3})*)\s*W\b',  # 3000W or 3,000W (at least 3 digits)
            r'\b(\d{3,4})\s*WATT',  # 3000WATT (at least 3 digits)
        ]
        for pattern in watt_patterns:
            match = re.search(pattern, text_upper)
            if match:
                watts_str = match.group(1).replace(',', '')
                try:
                    watts = float(watts_str)
                    # Reasonable range check (10W to 20kW)
                    if 10 <= watts <= 20000:
                        return watts
                except ValueError:
                    pass
        
        # Pattern 3: Kilowatts (3kW, 3.5 kW)
        kw_patterns = [
            r'\b(\d+\.?\d*)\s*KW\b',
            r'\b(\d+\.?\d*)\s*KILOWATT',
        ]
        for pattern in kw_patterns:
            match = re.search(pattern, text_upper)
            if match:
                try:
                    kw = float(match.group(1))
                    # Reasonable range (0.1kW to 20kW)
                    if 0.1 <= kw <= 20:
                        return kw * 1000
                except ValueError:
                    pass
        
        # Pattern 4: Amps - convert to watts at 230V (Ghana standard)
        # Only for actual load devices (not sockets, switches, DBs, etc.)
        if should_convert_amps:
            # Look for higher amperage ratings (typically > 10A for significant loads)
            amp_patterns = [
                r'\b(\d{2,3})\s*A\b',  # 10A, 20A, 100A (2-3 digits to avoid "6A" in "6A SWITCH")
                r'(\d+)\s*AMP',
            ]
            for pattern in amp_patterns:
                match = re.search(pattern, text_upper)
                if match:
                    try:
                        amps = float(match.group(1))
                        # Only convert if amps >= 10 (significant loads like AC, heaters, pumps)
                        if amps >= 10:
                            watts = amps * 230  # P = V * I
                            return watts
                    except ValueError:
                        pass
        
        # Pattern 5: kVA - convert to watts (assume 0.9 power factor)
        kva_pattern = r'\b(\d+\.?\d*)\s*KVA\b'
        match = re.search(kva_pattern, text_upper)
        if match:
            try:
                kva = float(match.group(1))
                return kva * 1000 * 0.9  # W = kVA * 1000 * PF
            except ValueError:
                pass
        
        # Pattern 6: Horsepower to watts (1 HP = 746W)
        hp_pattern = r'(\d+\.?\d*)\s*HP\b'
        match = re.search(hp_pattern, text_upper)
        if match:
            try:
                hp = float(match.group(1))
                return hp * 746
            except ValueError:
                pass
        
        return float(default_watts)

    async def extract_from_pdf(self, pdf_path: str, dpi: int = 300) -> List[Dict]:
        """Extract components from PDF blueprint - uses pypdf text extraction"""
        components = []
        try:
            # First try direct text extraction (faster, no dependencies)
            reader = PdfReader(pdf_path)
            all_text = ""
            for page in reader.pages:
                all_text += page.extract_text() + "\n"
            
            # If we got meaningful text, process it
            if all_text.strip():
                for line in all_text.split('\n'):
                    line_upper = line.upper().strip()
                    for symbol_name, config in self.common_electrical_symbols.items():
                        if re.search(config['pattern'], line_upper):
                            qty = self._extract_quantity(line_upper)
                            if qty > 0:
                                component_name = symbol_name.replace('_', ' ').title()
                                # Try to extract actual wattage from the line
                                actual_watts = self._extract_wattage(line, config['watts'], component_name)
                                components.append({
                                    'name': component_name,
                                    'quantity': qty,
                                    'watts': actual_watts,
                                    'raw_text': line
                                })
            

                    
        except Exception as e:
            print(f"Error processing PDF {pdf_path}: {e}")
        return components

    async def extract_from_image(self, image_input) -> List[Dict]:
        """Extract electrical components from image"""
        if isinstance(image_input, Image.Image):
            image = cv2.cvtColor(np.array(image_input), cv2.COLOR_RGB2BGR)
        elif isinstance(image_input, np.ndarray):
            image = image_input
        elif isinstance(image_input, str):
            image = cv2.imread(image_input)
            if image is None:
                raise ValueError(f"Could not read image from path: {image_input}")
        else:
            raise TypeError(f"Unsupported image type: {type(image_input)}")

        processed = self.preprocess_image(image)
        text = pytesseract.image_to_string(processed)
        components = self.detect_electrical_symbols(processed, text)

        h, w = processed.shape[:2]
        data = pytesseract.image_to_data(processed, output_type=pytesseract.Output.DICT)
        for i, text_item in enumerate(data['text']):
            if text_item.strip():
                x, y, w_box, h_box = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                confidence = data['conf'][i]
                if confidence > 50:
                    print(f"Text: '{text_item}' at ({x},{y}) conf={confidence}")

        return components

    async def extract_components(self, files: List[Union[str, UploadFile]]) -> List[ElectricalComponent]:
        """Extract electrical components from blueprint files (PDFs or images)
        
        Accepts:
        - List of file paths (strings) - for testing/local processing
        - List of UploadFile objects - for FastAPI file uploads
        """
        all_components = []
        temp_files = []

        try:
            for file_input in files:
                if isinstance(file_input, UploadFile):
                    # Handle FastAPI UploadFile
                    if not file_input.filename:
                        continue
                    file_ext = Path(file_input.filename).suffix.lower()
                    content = await file_input.read()
                    
                    # Create temp file
                    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
                        tmp.write(content)
                        temp_path = tmp.name
                        temp_files.append(temp_path)
                    
                    # Process based on file type
                    if file_ext == '.pdf':
                        components = await self.extract_from_pdf(temp_path)
                    else:
                        components = await self.extract_from_image(temp_path)
                    all_components.extend(components)
                    
                elif isinstance(file_input, str):
                    # Handle file path (for local testing)
                    ext = Path(file_input).suffix.lower()
                    if ext == '.pdf':
                        components = await self.extract_from_pdf(file_input)
                    else:
                        components = await self.extract_from_image(file_input)
                    all_components.extend(components)

            # Aggregate components by name
            aggregated = {}
            for comp in all_components:
                name = comp['name']
                if name in aggregated:
                    aggregated[name]['quantity'] += comp['quantity']
                else:
                    aggregated[name] = comp

            # Convert to ElectricalComponent objects
            result = []
            for comp_data in aggregated.values():
                result.append(ElectricalComponent(
                    name=comp_data['name'],
                    quantity=comp_data['quantity'],
                    rating_watts=comp_data['watts'],
                    total_watts=comp_data['quantity'] * comp_data['watts']
                ))

            return result
            
        finally:
            # Clean up temp files
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except Exception:
                    pass

    async def extract_from_directory(self, directory_path: str) -> List[ElectricalComponent]:
        """Extract components from all supported files in a directory"""
        supported_exts = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp'}
        files = []
        for ext in supported_exts:
            files.extend(Path(directory_path).glob(f'*{ext}'))
            files.extend(Path(directory_path).glob(f'*{ext.upper()}'))
        return await self.extract_components([str(f) for f in files])
