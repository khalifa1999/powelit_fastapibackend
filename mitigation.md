 PowerLit Vision System - Mitigation Plan
 Addressing Detection Accuracy Issues
**Date:** 2026-02-11  
**Status:** Analysis Phase  
**Severity:** High - Production Impact
---
 Executive Summary
**Problem Statement:**  
The current symbol recognition system shows significant inaccuracies:
- Visualizations show detections in wrong locations
- Components misclassified or missed entirely  
- Inconsistent results between training and production endpoints
- False positive rate appears high
**Root Cause Hypothesis:**
1. **Lack of ground truth validation** - No annotated baseline to compare against
2. **Overly permissive detection thresholds** - Catching architectural elements as symbols
3. **Scale inconsistencies** - Different preprocessing between training and analyze endpoints
4. **No geometric validation** - Not checking if detected "circles" are actually electrical symbols
5. **Missing context awareness** - Not using legend position/context information
---
 Phase 1: Data Annotation & Ground Truth Creation (Priority: CRITICAL)
 1.1 Annotation Strategy
**Your Task:** Annotate the 6 blueprints with actual component locations
**Tools Required:**
- LabelImg (free, open source) - `pip install labelImg`
- Or CVAT (online) - cvat.org
- Or manual JSON creation
**Annotation Format:**
{
  "image": "plan_a.png",
  "annotations": [
    {
      "label": "light",
      "x": 450,
      "y": 320,
      "width": 25,
      "height": 25,
      "legend_reference": "Symbol L"
    },
    {
      "label": "outlet",
      "x": 680,
      "y": 450,
      "width": 20,
      "height": 20,
      "legend_reference": "Symbol O"
    }
  ]
}
What to Annotate:
- ✅ Electrical symbols (circles with wires)
- ✅ Light fixtures (ceiling lights)
- ✅ Power outlets (wall sockets)
- ✅ Switches (toggle symbols)
- ✅ Fans (cross/circle symbols)
- ❌ Architectural elements (doors, windows, furniture)
- ❌ Text labels (drawing codes, measurements)
- ❌ Dimension lines
Minimum Viable Set:
- Annotate 1-2 blueprints completely (all symbols)
- This gives us ground truth for validation
- Target: 50-100 symbols annotated
1.2 Deliverables from You
1. Annotated JSON files for each blueprint
2. Manual count report:
   - How many lights?
   - How many outlets?
   - How many switches?
   - How many fans?
   - How many other symbols?
3. Visual reference: Marked-up image showing what IS vs ISN'T a symbol
Format: data/annotations/plan_a_annotations.json
---
Phase 2: Validation Framework (Priority: HIGH)
2.1 Accuracy Metrics
Metrics to Track:
Precision = True Positives / (True Positives + False Positives)
Recall = True Positives / (True Positives + False Negatives)  
F1-Score = 2 * (Precision * Recall) / (Precision + Recall)
IoU (Intersection over Union) = Area of overlap / Area of union
Current (estimated from visualizations):
- Precision: ~40% (many false positives)
- Recall: ~60% (missing actual symbols)
- F1: ~48%
Target:
- Precision: >85%
- Recall: >85%
- F1: >85%
- IoU threshold: >0.5 (50% overlap)
2.2 Validation Script
Create automated validation that compares detections vs ground truth.
2.3 Confusion Matrix
Track which symbols get confused for optimization.
---
Phase 3: Parameter Tuning (Priority: HIGH)
3.1 Detection Thresholds
Current Issues:
1. Circle detection - Detecting window corners as circles
2. Cross detection - Finding door hinges as crosses
3. Area thresholds - Too broad, catching architectural details
Proposed Adjustments:
# Circle Detection (Lights/Outlets)
current = {'min_area': 30, 'max_area': 3000, 'circularity': (0.6, 1.0)}
proposed = {'min_area': 50, 'max_area': 800, 'circularity': (0.75, 1.0)}
# Rectangle Detection (Switches/DBs)  
current = {'min_area': 80, 'max_area': 8000, 'aspect_ratio': (0.4, 2.5)}
proposed = {'min_area': 100, 'max_area': 2000, 'aspect_ratio': (0.8, 1.5)}

# Cross Detection (Fans)
current = {'threshold': 0.7}
proposed = {'threshold': 0.8}

3.2 Size-Based Classification Refinement
Add validation to ensure detected shapes are actual electrical symbols, not just architectural features.
3.3 Context Validation
Add geometric context:
- Electrical symbols usually have wire lines connected
- Outlets appear on walls (horizontal lines)
- Lights appear in ceiling areas (no walls above)
- Switches appear near doors
---
Phase 4: Training vs Production Consistency (Priority: HIGH)
4.1 Root Cause Analysis
Why different results between training and analyze?
Suspected causes:
1. Different image loading
   - Training: cv2.imread() 
   - Analyze: FastAPI UploadFile → bytes → temp file
   - May have different color spaces or compression
2. Different preprocessing
   - Training: May resize differently
   - Analyze: Different scaling factor
3. Different symbol detection order
   - Training: May run in different sequence
   - Analyze: Different code path
4. Randomness in detection
   - OpenCV contour detection order varies
   - Non-deterministic results
4.2 Fix: Standardized Pipeline
Create single preprocessing function that is used identically in both training and production.
4.3 Deterministic Results
Sort contours and use consistent random seed to ensure reproducible results.
---
Phase 5: False Positive Reduction (Priority: MEDIUM)
5.1 Architectural Element Filtering
Problem: System detects windows, doors, furniture as electrical symbols
Solution 1: Shape Analysis
- Check solidity (electrical symbols are solid, not irregular)
- Validate aspect ratio (switches are roughly square)
- Verify electrical context (wires nearby)
Solution 2: Legend Context
- Compare detected symbols against legend symbols
- Only keep detections that match legend patterns
5.2 Confidence Scoring
Instead of binary detection, use confidence scores with thresholding:
- Shape score (0-1)
- Context score (0-1)  
- Legend match score (0-1)
- Overall confidence = weighted average
- Only keep detections with confidence > 0.7
---
Phase 6: Iterative Improvement Workflow (Priority: MEDIUM)
6.1 Feedback Loop
Process:
1. Annotate 1-2 blueprints (ground truth)
2. Run detection on annotated images
3. Compare detections vs annotations
4. Calculate precision/recall metrics
5. Adjust parameters based on errors
6. Repeat until target metrics achieved
6.2 Regression Testing
Before each change:
- Run detection on all 6 blueprints
- Compare against previous results
- Ensure no degradation in accuracy
---
Phase 7: Immediate Quick Fixes (Priority: HIGH)
While you prepare annotations, implement these quick fixes immediately:
7.1 Tighten Detection Thresholds
Reduce false positives by making detection more selective:
- Increase minimum area from 30 to 50 pixels
- Increase circularity threshold from 0.6 to 0.75
- Reduce maximum area from 3000 to 800 pixels
7.2 Add Visual Deduplication
Remove overlapping detections that represent the same symbol:
- Minimum distance threshold: 50 pixels
- Keep highest confidence detection
7.3 Standardize Preprocessing
Ensure training and analyze use identical code paths:
- Single preprocessing function
- Same resize logic
- Same denoising parameters
---
Recommended Implementation Order
Week 1: Quick Fixes
1. ✅ Tighten detection thresholds
2. ✅ Add deduplication logic
3. ✅ Standardize preprocessing pipeline
4. ✅ Test on 6 blueprints
Week 2: Validation Framework
1. You annotate 1-2 blueprints
2. I create validation script
3. Calculate baseline metrics
4. Identify specific error patterns
Week 3: Parameter Optimization
1. Adjust thresholds based on errors
2. Add context validation
3. Implement confidence scoring
4. Re-validate with new metrics
Week 4: Production Hardening
1. Regression testing
2. Performance optimization
3. Documentation
4. Deploy to production
---
Questions for You
1. Would you like me to start with the quick fixes (Phase 7) immediately?
   - This should reduce false positives significantly
   - No annotation required
   - Can implement today
2. Which blueprint would you like to annotate first?
   - Plan A, B, C, D, E, or F?
   - Choose one with clear symbols
   - I'll provide annotation template
3. Do you have access to the legend image?
   - data/training_data/blueprint_legends/Blueprint Legends I.png
   - Can use it for symbol template matching
   - Would improve accuracy significantly
4. What's the acceptable accuracy threshold for production?
   - 80% precision/recall?
   - 90% precision/recall?
   - This determines how much tuning we need
---
Expected Outcomes
After implementing this plan:
Short-term (1 week):
- 50% reduction in false positives
- Consistent results between training and analyze
- Visualizations aligned with actual symbols
Medium-term (2-3 weeks):
- >85% precision and recall
- Validated against ground truth
- Production-ready accuracy
Long-term (1 month):
- Fully trained system on annotated data
- Handles various blueprint styles
- Ghana electrical code compliance verified
---
Next Steps
Option 1: Start with Quick Fixes
- I implement Phase 7 immediately
- You test and provide feedback
- Then proceed to annotation
Option 2: Annotation First
- You annotate 1-2 blueprints
- I create validation framework
- Then implement targeted fixes
Option 3: Hybrid Approach
- I implement quick fixes today
- You annotate in parallel
- We validate together
Which option would you prefer?