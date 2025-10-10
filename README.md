# Invoice-to-JSON Extraction Workflow

A local function that takes in a PDF/PNG/JPG invoice, calls an OpenAI 4o mini model with vendor-specific prompts, and saves the extracted invoice as JSON. No server or API layer; just direct model calls + local JSON storage for verification.

## Supported Vendors

- **Lakeshore Beverage** - Illinois beverage distributor
- **Breakthru Beverage Illinois** - Illinois beverage distributor  
- **Southern Glazer's of Illinois** - Illinois beverage distributor

## Features

- 🖼️ **Multi-format Support**: PDF, PNG, JPG, JPEG
- 🤖 **AI-Powered Parsing**: Uses OpenAI Vision API for accurate extraction
- 📊 **Structured Output**: Consistent JSON schema across all vendors
- ✅ **Validation**: Pydantic-based data validation with business rules
- 📁 **Local Storage**: Saves results to disk for verification
- 🔄 **Batch Processing**: Process multiple files at once
- 📝 **Comprehensive Logging**: Detailed logging for debugging

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd Invoice_to_Excel
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   Create a `.env` file in the project root:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   OPENAI_MODEL=gpt-4o-mini
   LOG_LEVEL=INFO
   ```

## Usage

### Basic Usage

Parse a single invoice:
```bash
python main.py invoice.pdf lakeshore
python main.py invoice.png breakthru
python main.py invoice.jpg southern_glazers
```

### Command Line Options

```bash
python main.py [OPTIONS] FILE_PATH VENDOR

Arguments:
  FILE_PATH              Path to the invoice file (PDF, PNG, or JPG)
  VENDOR                 Vendor type: lakeshore, breakthru, or southern_glazers

Options:
  --api-key API_KEY      OpenAI API key (overrides .env file)
  --batch BATCH [BATCH ...]  Process multiple files with the same vendor
  --stats                Show parsing statistics
  -h, --help            Show help message
```

### Examples

**Single file processing**:
```bash
# Parse a Lakeshore invoice
python main.py lakeshore_invoice.pdf lakeshore

# Parse a Breakthru invoice with custom API key
python main.py --api-key sk-... breakthru_invoice.png breakthru
```

**Batch processing**:
```bash
# Process multiple Southern Glazer invoices
python main.py --batch invoice1.pdf invoice2.png invoice3.jpg southern_glazers
```

**Show statistics**:
```bash
python main.py invoice.pdf lakeshore --stats
```

## Output

The application creates an `output/` directory and saves parsed invoices as JSON files with the naming convention:
```
invoice_{vendor}_{filename}_{timestamp}.json
```

### Example Output Structure

```json
{
  "vendor_name": "Lakeshore Beverage",
  "invoice_number": "INV-001",
  "invoice_date": "2025-01-15",
  "items": [
    {
      "description": "Bud Light 12oz Can",
      "qty": 24,
      "unit_price": 12.99,
      "extended_amount": 311.76
    }
  ],
  "total_sales": 311.76,
  "meta": {
    "source_file": "invoice.pdf",
    "vendor_detected": "lakeshore",
    "parse_confidence": 0.95,
    "validation_flags": []
  }
}
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | Required | Your OpenAI API key |
| `OPENAI_MODEL` | `gpt-4.1-mini` | OpenAI model to use |
| `OPENAI_MAX_TOKENS` | `4000` | Maximum tokens for response |
| `OPENAI_TEMPERATURE` | `0.1` | Response creativity (0.0-1.0) |
| `LOG_LEVEL` | `INFO` | Logging level |
| `MAX_FILE_SIZE_MB` | `10` | Maximum file size in MB |

### Vendor-Specific Prompts

Each vendor has a carefully crafted prompt that ensures consistent extraction:

- **Lakeshore**: Focuses on invoice header fields and item details
- **Breakthru**: Emphasizes table alignment and numeric columns
- **Southern Glazer's**: Captures detailed totals and delivery information

## Validation

The application includes comprehensive validation:

- **Schema Validation**: Ensures data structure matches expected format
- **Business Rules**: Validates totals, UPC formats, and quantities
- **Data Types**: Converts and validates numeric fields
- **Flagging**: Reports validation issues for manual review

## Error Handling

- **File Validation**: Checks format, size, and existence
- **API Errors**: Handles OpenAI API failures gracefully
- **JSON Parsing**: Robust handling of malformed responses
- **Logging**: Detailed error logs for debugging

## Development

### Project Structure

```
Invoice_to_Excel/
├── main.py                 # Main entry point
├── config.py              # Configuration management
├── invoice_parser.py      # Core parsing logic
├── openai_client.py       # OpenAI API client
├── file_processor.py      # File handling and conversion
├── validators.py          # Data validation
├── schemas.py             # Data schemas
├── utils/
│   └── logging_setup.py  # Logging configuration
├── requirements.txt       # Python dependencies
├── README.md             # This file
└── output/               # Generated JSON files
```

### Adding New Vendors

1. Add vendor to `config.py` vendor prompts
2. Create vendor-specific schema in `schemas.py`
3. Add validation rules in `validators.py`
4. Update main.py vendor choices

### Testing

```bash
# Run tests
pytest

# Format code
black .

# Lint code
flake8
```

## Troubleshooting

### Common Issues

**"OpenAI API key is required"**
- Set `OPENAI_API_KEY` in your `.env` file
- Or use `--api-key` command line argument

**"File too large"**
- Increase `MAX_FILE_SIZE_MB` in `.env`
- Or compress/resize your invoice images

**"Invalid JSON response"**
- Check that your OpenAI API key is valid
- Ensure you have sufficient API credits
- Try with a different invoice image

**"Unsupported file format"**
- Convert your file to PDF, PNG, or JPG
- Ensure file extension matches actual format

### Logs

Check `invoice_parser.log` for detailed error information and debugging details.

## Performance

- **Processing Time**: ~10-30 seconds per invoice (depends on image complexity)
- **API Costs**: ~$0.01-0.05 per invoice (using gpt-4o-mini)
- **Memory Usage**: ~50-200MB per invoice (depends on image size)

## Future Enhancements

- [ ] Excel export functionality
- [ ] Auto vendor detection
- [ ] Batch file support with progress bars
- [ ] Correction UI for manual fixes
- [ ] ERP integration capabilities
- [ ] Web interface



