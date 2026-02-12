# Training Service for PowerLit

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List, Dict, Tuple
import json
from pathlib import Path
from datetime import datetime
from PIL import Image
import cv2
import numpy as np
from app.services.vision import VisionService
from app.models.schemas import ElectricalComponent


class TrainingService:
    """Service for training the vision model on blueprint data"""
    
    def __init__(self):
        self.vision_service = VisionService()
        self.training_results = []
        
    async def train_on_blueprint(self, blueprint_path: str) -> Dict:
        """Train on a single blueprint file"""
        filename = Path(blueprint_path).name
        print(f"\n📄 Processing: {filename}")
        
        try:
            # Extract components using vision service
            components = await self.vision_service.extract_from_image(blueprint_path)
            
            # Convert to ElectricalComponent objects
            electrical_components = []
            for comp in components:
                electrical_components.append(ElectricalComponent(
                    name=comp['name'],
                    quantity=comp['quantity'],
                    rating_watts=comp['watts'],
                    total_watts=comp['quantity'] * comp['watts']
                ))
            
            # Calculate statistics
            total_components = sum(comp.quantity for comp in electrical_components)
            unique_types = len(electrical_components)
            total_watts = sum(comp.total_watts for comp in electrical_components)
            
            result = {
                "filename": filename,
                "status": "success",
                "components_found": unique_types,
                "total_instances": total_components,
                "total_watts": total_watts,
                "components": [
                    {
                        "name": comp.name,
                        "quantity": comp.quantity,
                        "watts": comp.rating_watts,
                        "total": comp.total_watts
                    }
                    for comp in electrical_components
                ],
                "timestamp": datetime.now().isoformat()
            }
            
            self.training_results.append(result)
            
            print(f"  ✓ Found {unique_types} component types ({total_components} total instances)")
            print(f"  ✓ Total connected load: {total_watts:,.0f}W ({total_watts/1000:.2f}kW)")
            
            return result
            
        except Exception as e:
            error_result = {
                "filename": filename,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            self.training_results.append(error_result)
            print(f"  ✗ Error: {e}")
            return error_result
    
    async def train_on_directory(self, directory_path: str) -> Dict:
        """Train on all blueprints in a directory"""
        print(f"\n{'='*70}")
        print("POWERLIT VISION MODEL TRAINING")
        print(f"{'='*70}")
        print(f"\nTraining directory: {directory_path}")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Find all supported files
        supported_exts = {'.png', '.jpg', '.jpeg', '.pdf'}
        files = []
        for ext in supported_exts:
            files.extend(Path(directory_path).glob(f'*{ext}'))
            files.extend(Path(directory_path).glob(f'*{ext.upper()}'))
        
        files = sorted(files)
        print(f"\nFound {len(files)} blueprint files")
        
        if not files:
            return {
                "status": "error",
                "message": "No blueprint files found",
                "files_processed": 0
            }
        
        # Process each file
        successful = 0
        failed = 0
        
        for i, file_path in enumerate(files, 1):
            print(f"\n[{i}/{len(files)}] ", end="")
            result = await self.train_on_blueprint(str(file_path))
            
            if result['status'] == 'success':
                successful += 1
            else:
                failed += 1
        
        # Generate training report
        report = self._generate_report(successful, failed)
        
        # Save training results
        self._save_results()
        
        return report
    
    def _generate_report(self, successful: int, failed: int) -> Dict:
        """Generate training summary report"""
        print(f"\n\n{'='*70}")
        print("TRAINING SUMMARY")
        print(f"{'='*70}")
        
        # Aggregate all components
        all_components = {}
        total_files_success = 0
        total_files_failed = 0
        
        for result in self.training_results:
            if result['status'] == 'success':
                total_files_success += 1
                for comp in result['components']:
                    name = comp['name']
                    if name in all_components:
                        all_components[name]['count'] += 1
                        all_components[name]['total_quantity'] += comp['quantity']
                        all_components[name]['avg_watts'] = (
                            (all_components[name]['avg_watts'] * (all_components[name]['count'] - 1)) + 
                            comp['watts']
                        ) / all_components[name]['count']
                    else:
                        all_components[name] = {
                            'count': 1,
                            'total_quantity': comp['quantity'],
                            'avg_watts': comp['watts']
                        }
            else:
                total_files_failed += 1
        
        # Print component summary
        print(f"\n📊 Component Detection Summary:")
        print(f"{'-'*70}")
        print(f"{'Component Type':<25} {'Files Found':<15} {'Total Qty':<12} {'Avg Watts':<12}")
        print(f"{'-'*70}")
        
        sorted_components = sorted(all_components.items(), key=lambda x: x[1]['count'], reverse=True)
        for name, stats in sorted_components:
            print(f"{name:<25} {stats['count']:<15} {stats['total_quantity']:<12} {stats['avg_watts']:<12.0f}")
        
        print(f"\n📈 Training Statistics:")
        print(f"{'-'*70}")
        print(f"  Total files processed: {len(self.training_results)}")
        print(f"  Successful: {total_files_success}")
        print(f"  Failed: {total_files_failed}")
        print(f"  Success rate: {(total_files_success/len(self.training_results)*100):.1f}%")
        print(f"  Unique component types detected: {len(all_components)}")
        
        report = {
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "total_files": len(self.training_results),
            "successful": total_files_success,
            "failed": total_files_failed,
            "success_rate": total_files_success / len(self.training_results) if self.training_results else 0,
            "unique_component_types": len(all_components),
            "component_summary": all_components,
            "detailed_results": self.training_results
        }
        
        return report
    
    def _save_results(self):
        """Save training results to file"""
        output_dir = Path("data/training_results")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f"training_results_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "results": self.training_results
            }, f, indent=2)
        
        print(f"\n💾 Results saved to: {output_file}")


async def main():
    """Run training on blueprints directory"""
    import sys
    
    # Default to training_data/blueprints
    blueprint_dir = sys.argv[1] if len(sys.argv) > 1 else "data/training_data/blueprints"
    
    if not os.path.exists(blueprint_dir):
        print(f"Error: Directory not found: {blueprint_dir}")
        print(f"Usage: python train_vision.py [directory_path]")
        sys.exit(1)
    
    # Run training
    trainer = TrainingService()
    report = await trainer.train_on_directory(blueprint_dir)
    
    print(f"\n{'='*70}")
    print("✅ TRAINING COMPLETE")
    print(f"{'='*70}")
    
    return report


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
