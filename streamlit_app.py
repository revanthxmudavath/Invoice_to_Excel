"""
Streamlit Web Interface for Invoice-to-Excel Parser
AI-powered invoice parsing with OpenAI Vision API
"""

import streamlit as st
import pandas as pd
import logging
import tempfile
import io
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
import openpyxl

# Import existing modules
from config import Config
from invoice_parser import InvoiceParser
from excel_exporter import ExcelExporter
from utils.logging_setup import setup_logging

# Page configuration
st.set_page_config(
    page_title="Invoice Parser - AI-Powered Extraction",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)

# Custom CSS for better UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3rem;
        font-weight: 600;
    }
    .success-box {
        padding: 1rem;
        border-radius: 5px;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 5px;
        border: 1px solid #dee2e6;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

def initialize_session_state():
    """Initialize all session state variables"""
    if 'api_key' not in st.session_state:
        st.session_state.api_key = None
    if 'api_key_validated' not in st.session_state:
        st.session_state.api_key_validated = False
    if 'selected_vendor' not in st.session_state:
        st.session_state.selected_vendor = None
    if 'uploaded_file' not in st.session_state:
        st.session_state.uploaded_file = None
    if 'parsed_data' not in st.session_state:
        st.session_state.parsed_data = None
    if 'excel_path' not in st.session_state:
        st.session_state.excel_path = None
    if 'excel_dataframes' not in st.session_state:
        st.session_state.excel_dataframes = None
    if 'processing_complete' not in st.session_state:
        st.session_state.processing_complete = False
    if 'temp_file_path' not in st.session_state:
        st.session_state.temp_file_path = None

def reset_processing_state():
    """Reset processing state for new upload"""
    st.session_state.uploaded_file = None
    st.session_state.parsed_data = None
    st.session_state.excel_path = None
    st.session_state.excel_dataframes = None
    st.session_state.processing_complete = False
    st.session_state.temp_file_path = None

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def validate_api_key(api_key: str) -> bool:
    """
    Basic API key format validation

    Args:
        api_key: OpenAI API key to validate

    Returns:
        True if format looks valid, False otherwise
    """
    # Basic format check - OpenAI keys start with 'sk-'
    if not api_key or not isinstance(api_key, str):
        return False

    # Check if it starts with 'sk-' and has reasonable length
    if api_key.startswith('sk-') and len(api_key) > 20:
        return True

    return False

def process_invoice(uploaded_file, vendor: str, api_key: str) -> Dict[str, Any]:
    """
    Process invoice file and return parsed data

    Args:
        uploaded_file: Streamlit uploaded file object
        vendor: Vendor type
        api_key: OpenAI API key

    Returns:
        Dictionary containing parsed invoice data
    """
    try:
        # Create temporary file
        suffix = Path(uploaded_file.name).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name
            st.session_state.temp_file_path = tmp_path

        logger.info(f"Processing invoice: {uploaded_file.name} for vendor: {vendor}")

        # Create config with user's API key
        config = Config(api_key=api_key)

        # Initialize parser
        parser = InvoiceParser(config)

        # Parse invoice
        parsed_data = parser.parse_invoice(tmp_path, vendor)

        logger.info("Invoice parsed successfully")
        return parsed_data

    except Exception as e:
        logger.error(f"Error processing invoice: {e}")
        raise

def generate_excel_and_preview(parsed_data: Dict[str, Any], vendor: str) -> tuple[str, Dict[str, pd.DataFrame]]:
    """
    Generate Excel file and create preview dataframes

    Args:
        parsed_data: Parsed invoice data
        vendor: Vendor type

    Returns:
        Tuple of (excel_path, dict of dataframes)
    """
    try:
        # Create temporary Excel file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            excel_path = tmp_file.name

        # Generate Excel
        exporter = ExcelExporter()
        exporter.export_invoice(parsed_data, excel_path)

        logger.info(f"Excel file generated: {excel_path}")

        # Read Excel file and create preview dataframes
        excel_file = openpyxl.load_workbook(excel_path, data_only=True)
        dataframes = {}

        for sheet_name in excel_file.sheetnames:
            # Read each sheet as dataframe
            df = pd.read_excel(excel_path, sheet_name=sheet_name, header=None)
            dataframes[sheet_name] = df

        excel_file.close()

        return excel_path, dataframes

    except Exception as e:
        logger.error(f"Error generating Excel: {e}")
        raise

def format_summary_data(parsed_data: Dict[str, Any]) -> pd.DataFrame:
    """Format summary data for display"""
    summary_items = []

    # Invoice details
    fields = [
        ("Invoice Number", parsed_data.get("invoice_number")),
        ("Invoice Date", parsed_data.get("invoice_date")),
        ("Vendor", parsed_data.get("vendor_name")),
        ("Customer Number", parsed_data.get("customer_number") or parsed_data.get("account_number")),
        ("Route", parsed_data.get("route")),
        ("Stop", parsed_data.get("stop")),
        ("Terms", parsed_data.get("terms")),
        ("Due Date", parsed_data.get("due_date")),
        ("PO Number", parsed_data.get("po_number")),
    ]

    for field, value in fields:
        if value is not None and value != "" and value != "None":
            summary_items.append({"Field": field, "Value": str(value)})

    return pd.DataFrame(summary_items)

def format_items_data(parsed_data: Dict[str, Any]) -> pd.DataFrame:
    """Format items data for display"""
    items = parsed_data.get("items", [])
    if not items:
        return pd.DataFrame()

    # Convert items to dataframe
    df = pd.DataFrame(items)

    # Replace None and "None" with pd.NA for proper type handling
    df = df.fillna(pd.NA)
    df = df.replace("None", pd.NA)
    df = df.replace("", pd.NA)

    # Convert numeric columns to proper numeric types
    numeric_columns = [
        'qty', 'bottles', 'cases', 'unit_price', 'discount',
        'extended_amount', 'net_amount', 'deposit', 'cs_price',
        'cs_disc', 'cs_net', 'cnty_tax', 'city_tax', 'ext_w/o_tax',
        'ext_w_o_tax', 'net_bottle_price', 'unit_discount', 'Case'
    ]

    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    return df

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main application logic"""

    # Initialize session state
    initialize_session_state()

    # ========================================================================
    # SIDEBAR - API KEY MANAGEMENT
    # ========================================================================

    with st.sidebar:
        st.markdown("### 🔑 API Configuration")

        if not st.session_state.api_key_validated:
            st.info("Enter your OpenAI API key to get started")

            api_key_input = st.text_input(
                "OpenAI API Key",
                type="password",
                placeholder="sk-...",
                help="Your API key will be validated when processing invoices"
            )

            if st.button("✅ Save API Key", type="primary"):
                if api_key_input:
                    if validate_api_key(api_key_input):
                        st.session_state.api_key = api_key_input
                        st.session_state.api_key_validated = True
                        st.success("✅ API key saved successfully!")
                        st.rerun()
                    else:
                        st.error("❌ Invalid API key format. OpenAI keys should start with 'sk-'")
                else:
                    st.warning("Please enter an API key")
        else:
            st.success("✅ API Key Connected")
            st.caption("API key is active for this session")

            if st.button("🔄 Change API Key"):
                st.session_state.api_key = None
                st.session_state.api_key_validated = False
                reset_processing_state()
                st.rerun()

        st.divider()

        # Info section
        st.markdown("### ℹ️ About")
        st.caption("AI-powered invoice parser using OpenAI Vision API")
        st.caption("Supports: Lakeshore, Breakthru, Southern Glazer's")

    # ========================================================================
    # MAIN PANEL
    # ========================================================================

    # Header
    st.markdown('<p class="main-header">📄 Invoice Parser</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">AI-Powered Invoice Extraction & Excel Export</p>', unsafe_allow_html=True)

    # Check if API key is set
    if not st.session_state.api_key_validated:
        st.info("👈 Please enter your OpenAI API key in the sidebar to continue")
        return

    # ========================================================================
    # STEP 1: VENDOR SELECTION
    # ========================================================================

    if not st.session_state.processing_complete:
        st.markdown("### Step 1: Select Vendor")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("🏢 Lakeshore Beverage", use_container_width=True, type="primary" if st.session_state.selected_vendor == "lakeshore" else "secondary"):
                st.session_state.selected_vendor = "lakeshore"
                reset_processing_state()

        with col2:
            if st.button("🏢 Breakthru Beverage", use_container_width=True, type="primary" if st.session_state.selected_vendor == "breakthru" else "secondary"):
                st.session_state.selected_vendor = "breakthru"
                reset_processing_state()

        with col3:
            if st.button("🏢 Southern Glazer's", use_container_width=True, type="primary" if st.session_state.selected_vendor == "southern_glazers" else "secondary"):
                st.session_state.selected_vendor = "southern_glazers"
                reset_processing_state()

        if st.session_state.selected_vendor:
            vendor_display = {
                "lakeshore": "Lakeshore Beverage",
                "breakthru": "Breakthru Beverage Illinois",
                "southern_glazers": "Southern Glazer's of Illinois"
            }
            st.success(f"✅ Selected: **{vendor_display[st.session_state.selected_vendor]}**")

    # ========================================================================
    # STEP 2: FILE UPLOAD
    # ========================================================================

    if st.session_state.selected_vendor and not st.session_state.processing_complete:
        st.markdown("---")
        st.markdown("### Step 2: Upload Invoice")

        uploaded_file = st.file_uploader(
            "Choose an invoice file (PDF, PNG, JPG, JPEG)",
            type=["pdf", "png", "jpg", "jpeg"],
            help="Maximum file size: 10MB"
        )

        if uploaded_file:
            # Display file info
            col1, col2 = st.columns([2, 1])
            with col1:
                st.info(f"📎 **File:** {uploaded_file.name}")
                file_size_mb = uploaded_file.size / (1024 * 1024)
                st.caption(f"Size: {file_size_mb:.2f} MB")

            with col2:
                # Preview image if it's an image file
                if uploaded_file.type.startswith('image/'):
                    st.image(uploaded_file, caption="Preview", use_container_width=True)

            # Process button
            st.markdown("---")

            if st.button("🚀 Process Invoice", type="primary", use_container_width=True):
                try:
                    # Processing stages
                    with st.status("Processing invoice...", expanded=True) as status:
                        st.write("⏳ Converting file to images...")

                        st.write("⏳ Calling OpenAI Vision API...")

                        # Process invoice
                        parsed_data = process_invoice(
                            uploaded_file,
                            st.session_state.selected_vendor,
                            st.session_state.api_key
                        )
                        st.session_state.parsed_data = parsed_data

                        st.write("⏳ Validating data...")

                        st.write("⏳ Generating Excel file...")

                        # Generate Excel
                        excel_path, dataframes = generate_excel_and_preview(
                            parsed_data,
                            st.session_state.selected_vendor
                        )
                        st.session_state.excel_path = excel_path
                        st.session_state.excel_dataframes = dataframes

                        st.write("✅ Processing complete!")
                        status.update(label="✅ Processing complete!", state="complete", expanded=False)

                    st.session_state.processing_complete = True
                    st.rerun()

                except Exception as e:
                    st.error(f"❌ Error processing invoice: {str(e)}")
                    logger.error(f"Processing error: {e}", exc_info=True)

    # ========================================================================
    # STEP 3: RESULTS DISPLAY
    # ========================================================================

    if st.session_state.processing_complete and st.session_state.parsed_data:
        st.markdown("---")
        st.markdown("### 🎉 Results")

        parsed_data = st.session_state.parsed_data

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                label="Invoice Number",
                value=parsed_data.get("invoice_number", "N/A")
            )

        with col2:
            st.metric(
                label="Invoice Date",
                value=parsed_data.get("invoice_date", "N/A")
            )

        with col3:
            items_count = len(parsed_data.get("items", []))
            st.metric(
                label="Items Extracted",
                value=items_count
            )

        with col4:
            total = parsed_data.get("net_amount") or parsed_data.get("gross_total") or parsed_data.get("total_sales")
            if total and str(total).replace('.', '').replace('-', '').isdigit():
                st.metric(
                    label="Total Amount",
                    value=f"${float(total):,.2f}"
                )
            else:
                st.metric(label="Total Amount", value="N/A")

        # Validation flags
        meta = parsed_data.get("meta", {})
        validation_flags = meta.get("validation_flags", [])

        if validation_flags:
            st.warning(f"⚠️ **Validation Flags:** {len(validation_flags)} issues detected")
            with st.expander("View Validation Details"):
                for flag in validation_flags:
                    st.caption(f"• {flag}")
        else:
            st.success("✅ **Validation:** All checks passed!")

        st.markdown("---")

        # Excel preview with tabs
        st.markdown("### 📊 Excel Preview")

        tab1, tab2, tab3, tab4 = st.tabs(["📋 Invoice Summary", "📦 Items", "🏢 Vendor Info", "✅ Validation"])

        with tab1:
            st.markdown("#### Invoice Summary")
            summary_df = format_summary_data(parsed_data)
            if not summary_df.empty:
                st.dataframe(summary_df, use_container_width=True, hide_index=True)

            # Totals section
            st.markdown("#### Totals")
            total_fields = [
                ("Total Bottles", parsed_data.get("total_bottles")),
                ("Total Liquor Gallons", parsed_data.get("total_liquor_gallons")),
                ("Total Beer Gallons", parsed_data.get("total_beer_gallons")),
                ("Total Sales", parsed_data.get("total_sales")),
                ("Gross Total", parsed_data.get("gross_total")),
                ("Total Discount", parsed_data.get("total_discount")),
                ("Net Amount", parsed_data.get("net_amount")),
            ]

            totals_data = []
            for field, value in total_fields:
                if value is not None and value != "" and value != "None":
                    totals_data.append({"Field": field, "Value": value})

            if totals_data:
                totals_df = pd.DataFrame(totals_data)
                st.dataframe(totals_df, use_container_width=True, hide_index=True)

        with tab2:
            st.markdown("#### Line Items")
            items_df = format_items_data(parsed_data)
            if not items_df.empty:
                st.dataframe(items_df, use_container_width=True, hide_index=True)
            else:
                st.info("No items extracted")

        with tab3:
            st.markdown("#### Vendor Information")
            vendor_fields = [
                ("Vendor Name", parsed_data.get("vendor_name")),
                ("Vendor Address", parsed_data.get("vendor_address")),
                ("Vendor Phone", parsed_data.get("vendor_phone")),
                ("Remit To Address", parsed_data.get("remit_to_address")),
                ("Barcode", parsed_data.get("barcode")),
                ("Special Instructions", parsed_data.get("special_instructions")),
            ]

            vendor_data = []
            for field, value in vendor_fields:
                if value is not None and value != "" and value != "None":
                    vendor_data.append({"Field": field, "Value": str(value)})

            if vendor_data:
                vendor_df = pd.DataFrame(vendor_data)
                st.dataframe(vendor_df, use_container_width=True, hide_index=True)

        with tab4:
            st.markdown("#### Validation & Metadata")
            meta_fields = [
                ("Source File", meta.get("source_file", "")),
                ("Vendor Detected", meta.get("vendor_detected", "")),
                ("Parse Confidence", meta.get("parse_confidence", "")),
                ("Validation Flags", ", ".join(validation_flags) if validation_flags else "None"),
                ("Export Date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            ]

            meta_data = []
            for field, value in meta_fields:
                if value is not None and value != "" and value != "None":
                    meta_data.append({"Field": field, "Value": str(value)})

            meta_df = pd.DataFrame(meta_data)
            st.dataframe(meta_df, use_container_width=True, hide_index=True)

        st.markdown("---")

        # Action buttons
        st.markdown("### 🎯 Actions")

        col1, col2 = st.columns(2)

        with col1:
            # Download Excel button
            if st.session_state.excel_path:
                with open(st.session_state.excel_path, 'rb') as f:
                    excel_bytes = f.read()

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                vendor_name = st.session_state.selected_vendor
                invoice_num = parsed_data.get("invoice_number", "invoice")
                filename = f"invoice_{vendor_name}_{invoice_num}_{timestamp}.xlsx"

                st.download_button(
                    label="📥 Download as Excel",
                    data=excel_bytes,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                    use_container_width=True
                )

        with col2:
            # Process another invoice
            if st.button("🔄 Process Another Invoice", use_container_width=True):
                reset_processing_state()
                st.rerun()

if __name__ == "__main__":
    main()
