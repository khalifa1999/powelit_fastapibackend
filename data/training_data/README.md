# Training Data Structure

This directory contains training data for the PowerLit AI model, organized into two categories:

## Directory Structure

```
data/training_data/
├── blueprint_legends/          # Blueprint legend files
│   ├── legends_page_1.pdf      # Individual legend pages
│   ├── legends_page_2.pdf
│   ├── legends_page_3.png
│   └── ...
├── blueprints/                 # Blueprint drawings
│   ├── plan_a.png              # Individual plan pages
│   ├── plan_b.png
│   ├── plan_c.png
│   └── ...
└── ghana_electrical_code/      # Ghana electrical code standards
    ├── gs1009_section_1.pdf    # GS1009 standard sections
    ├── gs1009_section_2.pdf
    ├── wiring_regulations.pdf
    └── ...
```

## Blueprints

Actual electrical blueprint drawings for training the vision model on component detection and symbol recognition.

**Supported formats:** PDF, PNG, JPG, JPEG
**Constraint:** One page per file for training

### Naming Convention
```
plan_{identifier}.{ext}
{project_name}_plan_{identifier}.{ext}
```

Examples:
- `plan_a.png`
- `plan_b.png`
- `osu_project_plan_1.pdf`

### Contents
Each blueprint should contain:
- Electrical symbols and components
- Circuit layouts
- Load schedules (if present)
- Legend references

## Blueprint Legends

Blueprint legends define the symbols used in electrical drawings. Each file should contain:
- Symbol representations (icons/drawings)
- Corresponding labels/names
- Technical specifications (if available)

**Supported formats:** PDF, PNG, JPG, JPEG
**Constraint:** One page per file for training

### Naming Convention
```
{project_name}_legends_page_{number}.{ext}
```

Examples:
- `osu_project_legends_page_1.pdf`
- `osu_project_legends_page_2.png`

## Ghana Electrical Code

Ghana electrical standards and wiring regulations for compliance checking.

**Standards included:**
- GS1009: Ghana Electrical Wiring Regulations
- L.I. 2478: Energy Commission Act regulations
- Ghana Grid Code requirements

**Supported formats:** PDF
**Constraint:** One page per file for training

### Naming Convention
```
{standard_code}_section_{number}.{ext}
{standard_code}_{topic}.{ext}
```

Examples:
- `gs1009_section_1.pdf`
- `gs1009_load_calculations.pdf`
- `li2478_safety_requirements.pdf`

## Usage

The training data is used for different purposes:

**Blueprints & Legends (Vision Training):**
- Train the vision model on electrical symbols and component recognition
- Improve accuracy of detecting outlets, lights, switches, etc.
- Learn blueprint layouts and symbol interpretations

**Ghana Electrical Code (RAG Knowledge Base):**
- Build compliance checking database
- Reference standards during load calculations
- Generate regulatory audit reports
- Stored in ChromaDB vector database for semantic search

## Adding New Training Data

1. Place files in the appropriate subdirectory
2. Follow the naming convention
3. Ensure one page per file
4. Run the ingestion endpoint to update the vector database

```bash
curl -X POST http://localhost:8000/ingest-standards
```
