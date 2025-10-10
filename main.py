#!/usr/bin/env python3
import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from invoice_parser import InvoiceParser
from config import Config
from utils.logging_setup import setup_logging
from excel_exporter import ExcelExporter

def main():
    """Main entry point for the invoice parsing application"""
    parser = argparse.ArgumentParser(
        description="Parse beverage distributor invoices to structured JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py invoice.pdf lakeshore
  python main.py invoice.png breakthru --excel
  python main.py invoice.jpg southern_glazers
  python main.py --batch file1.pdf file2.png breakthru --excel
        """
    )
    
    parser.add_argument(
        "--api-key",
        help="OpenAI API key (overrides .env file)"
    )
    
    parser.add_argument(
        "--batch",
        nargs="+",
        help="Process multiple files with the same vendor"
    )
    
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show parsing statistics"
    )
    
    parser.add_argument(
        "--excel",
        action="store_true",
        help="Export results to Excel file"
    )
    
    # Make file_path and vendor conditional
    parser.add_argument(
        "file_path",
        nargs="?",
        help="Path to the invoice file (PDF, PNG, or JPG) - required when not using --batch"
    )
    
    parser.add_argument(
        "vendor",
        nargs="?",
        choices=["lakeshore", "breakthru", "southern_glazers"],
        help="Vendor type for the invoice - required when not using --batch"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        config = Config(api_key=args.api_key)
        
        # Initialize invoice parser and Excel exporter
        invoice_parser = InvoiceParser(config)
        excel_exporter = ExcelExporter()
        
        if args.batch:
            # Process multiple files
            logger.info(f"Batch mode: args.batch={args.batch}, args.vendor={args.vendor}")
            # The vendor should be the last argument after batch files
            batch_files = args.batch[:-1] if len(args.batch) > 1 else []
            vendor = args.batch[-1] if args.batch else None
            
            if not vendor or vendor not in ["lakeshore", "breakthru", "southern_glazers"]:
                raise ValueError("Last argument after --batch must be a valid vendor")
            
            results = process_batch(batch_files, vendor, invoice_parser, logger)
            
            # Export to Excel if requested
            if args.excel and results:
                excel_file = export_batch_to_excel(results, vendor, excel_exporter, logger)
                print(f"📊 Excel file created: {excel_file}")
        else:
            # Process single file
            if not args.file_path or not args.vendor:
                raise ValueError("Both file_path and vendor are required when not using --batch")
            result = process_single_file(args.file_path, args.vendor, invoice_parser, logger)
            
            # Export to Excel if requested
            if args.excel:
                excel_file = export_single_to_excel(result, args.file_path, args.vendor, excel_exporter, logger)
                print(f"📊 Excel file created: {excel_file}")
            
        if args.stats:
            show_stats(invoice_parser)
            
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

def process_single_file(file_path: str, vendor: str, parser: InvoiceParser, logger: logging.Logger):
    """Process a single invoice file"""
    logger.info(f"Starting invoice parsing for {vendor} from {file_path}")
    
    try:
        # Parse the invoice
        result = parser.parse_invoice(file_path, vendor)
        
        # Save result to disk
        output_file = save_result(result, file_path, vendor)
        
        logger.info(f"Successfully parsed invoice. Output saved to: {output_file}")
        
        # Print summary
        print(f"\n✅ Invoice parsed successfully!")
        print(f"📁 Output saved to: {output_file}")
        print(f"📊 Items extracted: {len(result.get('items', []))}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error during invoice parsing: {e}")
        raise

def process_batch(file_paths: list, vendor: str, parser: InvoiceParser, logger: logging.Logger):
    """Process multiple invoice files"""
    logger.info(f"Processing batch of {len(file_paths)} files for vendor: {vendor}")
    
    results = []
    for file_path in file_paths:
        try:
            logger.info(f"Processing: {file_path}")
            result = parser.parse_invoice(file_path, vendor)
            output_file = save_result(result, file_path, vendor)
            results.append(result)  # Store the parsed data, not the file info
            print(f"✅ {file_path} -> {output_file}")
        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")
            print(f"❌ {file_path} -> Failed")
    
    # Summary
    successful = len(results)
    print(f"\n📊 Batch processing complete: {successful}/{len(file_paths)} successful")
    
    return results

def save_result(result: Dict[str, Any], input_file: str, vendor: str) -> str:
    """Save the parsing result to a JSON file"""
    from pathlib import Path
    import json
    from datetime import datetime
    
    # Create output directory
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    input_name = Path(input_file).stem
    output_file = output_dir / f"invoice_{vendor}_{input_name}_{timestamp}.json"
    
    # Save JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    return str(output_file)

def export_single_to_excel(result: Dict[str, Any], input_file: str, vendor: str, exporter: ExcelExporter, logger: logging.Logger) -> str:
    """Export single invoice result to Excel"""
    try:
        # Create output directory
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        input_name = Path(input_file).stem
        excel_file = output_dir / f"invoice_{vendor}_{input_name}_{timestamp}.xlsx"
        
        # Export to Excel
        exporter.export_invoice(result, str(excel_file))
        
        logger.info(f"Excel file exported successfully: {excel_file}")
        return str(excel_file)
        
    except Exception as e:
        logger.error(f"Error exporting to Excel: {e}")
        raise

def export_batch_to_excel(results: List[Dict[str, Any]], vendor: str, exporter: ExcelExporter, logger: logging.Logger) -> str:
    """Export batch results to Excel"""
    try:
        # Create output directory
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        # Export batch to Excel
        excel_file = exporter.export_batch(results, str(output_dir), vendor)
        
        logger.info(f"Batch Excel file exported successfully: {excel_file}")
        return excel_file
        
    except Exception as e:
        logger.error(f"Error exporting batch to Excel: {e}")
        raise

def show_stats(parser: InvoiceParser):
    """Display parsing statistics"""
    # This would show statistics from the parser if implemented
    print("\n📈 Parsing Statistics")
    print("Feature not yet implemented")

if __name__ == "__main__":
    main()

