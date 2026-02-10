from typing import List
from app.models.schemas import (
    ElectricalComponent, 
    LoadCalculation, 
    BuildingType,
    PowerSourceRecommendation
)

class LoadCalculator:
    """Deterministic load calculation service"""
    
    # Diversity factors per Ghana standards
    DIVERSITY_FACTORS = {
        BuildingType.RESIDENTIAL: 0.6,
        BuildingType.COMMERCIAL: 0.8,
        BuildingType.INDUSTRIAL: 0.9
    }
    
    def calculate_load(
        self, 
        inventory: List[ElectricalComponent], 
        building_type: BuildingType
    ) -> LoadCalculation:
        """
        Calculate Total Connected Load and Maximum Demand.
        
        TCL = Σ(Rating × Quantity)
        MD = TCL × Diversity Factor
        """
        # Calculate Total Connected Load
        total_connected_load = sum(
            item.total_watts for item in inventory
        )
        
        # Get diversity factor
        diversity_factor = self.DIVERSITY_FACTORS.get(building_type, 0.7)
        
        # Calculate Maximum Demand
        maximum_demand = total_connected_load * diversity_factor
        
        return LoadCalculation(
            total_connected_load=total_connected_load,
            diversity_factor=diversity_factor,
            maximum_demand=maximum_demand,
            building_type=building_type
        )
    
    def get_power_recommendations(
        self, 
        calculations: LoadCalculation
    ) -> List[PowerSourceRecommendation]:
        """
        Recommend power sources based on load calculations.
        
        This is a simplified recommendation logic.
        In production, this would consider:
        - Grid availability and reliability
        - Load criticality
        - Cost analysis
        - Solar irradiance data for location
        """
        recommendations = []
        md_kw = calculations.maximum_demand / 1000  # Convert to kW
        
        if calculations.building_type == BuildingType.RESIDENTIAL:
            # For residential, grid + solar backup
            recommendations.append(
                PowerSourceRecommendation(
                    source="grid",
                    percentage=70.0,
                    capacity_kw=md_kw * 0.7,
                    reasoning="Primary power from ECG grid"
                )
            )
            recommendations.append(
                PowerSourceRecommendation(
                    source="solar",
                    percentage=30.0,
                    capacity_kw=md_kw * 0.3,
                    reasoning="Solar backup for essential loads"
                )
            )
        elif calculations.building_type == BuildingType.COMMERCIAL:
            # For commercial, grid + generator backup
            recommendations.append(
                PowerSourceRecommendation(
                    source="grid",
                    percentage=80.0,
                    capacity_kw=md_kw * 0.8,
                    reasoning="Primary commercial power from ECG"
                )
            )
            recommendations.append(
                PowerSourceRecommendation(
                    source="generator",
                    percentage=20.0,
                    capacity_kw=md_kw * 0.2,
                    reasoning="Backup generator for business continuity"
                )
            )
        else:  # Industrial
            # For industrial, hybrid approach
            recommendations.append(
                PowerSourceRecommendation(
                    source="grid",
                    percentage=60.0,
                    capacity_kw=md_kw * 0.6,
                    reasoning="Primary industrial power"
                )
            )
            recommendations.append(
                PowerSourceRecommendation(
                    source="generator",
                    percentage=30.0,
                    capacity_kw=md_kw * 0.3,
                    reasoning="Heavy-duty backup generators"
                )
            )
            recommendations.append(
                PowerSourceRecommendation(
                    source="solar",
                    percentage=10.0,
                    capacity_kw=md_kw * 0.1,
                    reasoning="Supplementary solar for non-critical loads"
                )
            )
        
        return recommendations
