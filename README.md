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
5. AI filters out branded keywords (2-stage verification)
6. View results in table
7. Results auto-saved to `results/` folder

## Brand Filtering

The system uses two AI agents to filter branded keywords:

1. **Detection Agent**: Identifies potentially branded keywords (conservative approach)
   - Marks as branded if contains brand names
   - Marks as branded if unsure or doesn't recognize
   
2. **Verification Agent**: Cross-checks and verifies classifications
   - Reviews keywords marked as branded
   - Corrects over-conservative classifications
   - Provides reasoning for each decision

Output files:
- `brand_classification_*.csv` - All keywords with status (Branded/Non-Branded)
- `keyword_evaluations_*.csv` - Final results (non-branded only)

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
