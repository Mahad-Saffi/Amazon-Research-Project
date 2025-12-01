# Amazon Product Research API

## Quick Start

### Windows
```cmd
run.bat
```

### Mac/Linux
```bash
chmod +x run.sh
./run.sh
```

The script will:
1. Check Docker installation
2. Create `.env` file (add your OpenAI API key)
3. Build and start container
4. Open http://localhost:8000

## Usage

1. Upload Design CSV and Revenue CSV files
2. Enter Amazon ASIN or URL
3. Click "Analyze Product"
4. Watch real-time progress
5. AI filters out branded keywords
6. AI evaluates keyword relevance (1-10 score)
7. AI categorizes keywords (Irrelevant/Outlier/Relevant/Design-Specific)
8. View results with filters and sorting
9. Results auto-saved to `results/` folder

## Features

### Brand Filtering
AI agent identifies branded keywords anywhere in the phrase:
- Detects brand names (Nike, Apple, Amazon, etc.)
- Conservative approach: marks uncertain keywords as branded
- Branded keywords excluded from relevance evaluation
- All keywords saved with brand status

### Keyword Categorization
AI categorizes keywords into four levels:
- **IRRELEVANT (1-4)**: Completely different product
- **OUTLIER (5-6)**: Too general or broader category
- **RELEVANT (7-8)**: Accurately describes product
- **DESIGN-SPECIFIC (9-10)**: Exact product with specific details

### Language Detection
Identifies keywords with issues:
- Misspelled keywords
- Spanish, French, German, etc.
- Dual tagging (e.g., RELEVANT + MISSPELLED)

### UI Controls
- **Sort by**: Relevance Score or Search Volume
- **Filter by Brand**: All / Non-Branded / Branded
- **Filter by Category**: All / Design-Specific / Relevant / Outlier / Irrelevant

Output files:
- `brand_classification_*.csv` - All keywords with brand status
- `keyword_evaluations_*.csv` - Full results with categories and scores

See [CATEGORIZATION_GUIDE.md](CATEGORIZATION_GUIDE.md) for detailed examples.

## Requirements

- Docker Desktop
- OpenAI API key

## CSV Format

Required columns:
- `Keyword Phrase`
- `Search Volume`
- `Position (Rank)`
- `Title Density`
- `B0*` columns (ASINs)

## Output

Results saved to `results/` folder with:
- Keyword evaluations
- Relevance scores (1-10)
- AI rationale
- All original CSV data
- UTF-8 encoding

## Troubleshooting

**Container won't start:**
```bash
docker-compose logs
```

**Port already in use:**
Edit `docker-compose.yml` and change port `8000` to another port.

**View logs:**
```bash
docker-compose logs -f
```

**Stop container:**
```bash
docker-compose down
```

**Rebuild:**
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```
