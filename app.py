import streamlit as st
import base64
from PIL import Image
import io
import pandas as pd
import os
import requests
from dotenv import load_dotenv
from pdf2image import convert_from_bytes
import PyPDF2
import re
import json

load_dotenv()

# API Configuration
def get_api_key():
    """Get API key from environment or session state."""
    return "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"

def make_api_request(payload):
    """Make API request with proper headers and error handling."""
    api_key = get_api_key()
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://openrouter.ai/docs",
        "X-Title": "JSW Engineering Drawing Extractor",
        "Accept": "application/json"
    }

    try:
        # Print request details for debugging
        st.write("Making API request...")
        st.write("Request Headers:", headers)
        st.write("Request Payload:", payload)
        
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        
        # Print response details for debugging
        st.write(f"Response Status Code: {response.status_code}")
        
        try:
            response_json = response.json()
            if response.status_code == 403:
                error_message = response_json.get('error', {}).get('message', 'Unknown error')
                error_type = response_json.get('error', {}).get('type', '')
                
                # More specific error messages based on common 403 scenarios
                if 'rate limit' in error_message.lower():
                    st.error("❌ API Rate Limit Exceeded. Please wait a few minutes and try again.")
                elif 'credit' in error_message.lower():
                    st.error("❌ Insufficient API Credits. Please check your OpenRouter account balance.")
                elif 'invalid' in error_message.lower() and 'key' in error_message.lower():
                    st.error("❌ Invalid API Key. The API key may be expired or incorrect.")
                elif 'permission' in error_message.lower():
                    st.error("❌ Permission Denied. Your API key may not have access to the requested model.")
                else:
                    st.error(f"❌ API Error: {error_message}")
                    st.error(f"Error Type: {error_type}")
                
                # Print full response for debugging
                st.write("Full API Response:", response_json)
                return None
            elif response.status_code != 200:
                st.error(f"❌ API Error: {response_json.get('error', {}).get('message', 'Unknown error')}")
                return None
            return response_json
        except json.JSONDecodeError:
            st.error(f"Invalid JSON response: {response.text}")
            return None

    except requests.exceptions.Timeout:
        st.error("❌ Request timed out. Please try again.")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Network Error: {str(e)}")
        return None
    except Exception as e:
        st.error(f"❌ Unexpected Error: {str(e)}")
        return None

# Check API key before proceeding
API_KEY = get_api_key()
API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Define parameters for different component types
CYLINDER_PARAMETERS = [
    "CYLINDER ACTION",
    "BORE DIAMETER",
    "OUTSIDE DIAMETER",
    "ROD DIAMETER",
    "STROKE LENGTH",
    "CLOSE LENGTH",
    "OPEN LENGTH",
    "OPERATING PRESSURE",
    "OPERATING TEMPERATURE",
    "MOUNTING",
    "ROD END",
    "FLUID",
    "DRAWING NUMBER"
]

VALVE_PARAMETERS = [
    "VALVE TYPE",
    "PORT SIZE",
    "FLOW RATE",
    "PRESSURE RATING",
    "OPERATING TEMPERATURE",
    "ACTUATION TYPE",
    "BODY MATERIAL",
    "SEAL MATERIAL",
    "MOUNTING",
    "FLUID",
    "DRAWING NUMBER"
]

GEARBOX_PARAMETERS = [
    "GEARBOX TYPE",
    "INPUT SPEED",
    "OUTPUT SPEED",
    "RATIO",
    "INPUT POWER",
    "OUTPUT TORQUE",
    "MOUNTING POSITION",
    "LUBRICATION",
    "OPERATING TEMPERATURE",
    "WEIGHT",
    "DRAWING NUMBER"
]

def convert_to_jpeg(image_bytes):
    """Convert any image format to JPEG."""
    try:
        # Open the image using PIL
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert to RGB if image is in RGBA or other formats
        if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1])
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Save the image as JPEG to a bytes buffer
        jpeg_buffer = io.BytesIO()
        image.save(jpeg_buffer, format='JPEG', quality=95)
        return jpeg_buffer.getvalue()
    except Exception as e:
        st.error(f"Error converting image: {str(e)}")
        return None

def encode_image_to_base64(image_bytes):
    return "data:image/jpeg;base64," + base64.b64encode(image_bytes).decode("utf-8")

def parse_ai_response(response_text):
    """Parse the AI response into a structured format. If a value is missing, return an empty string."""
    results = {}
    lines = response_text.split('\n')
    for line in lines:
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip().upper()
            value = value.strip()
            results[key] = value if value else "" 
    return results

def identify_component(image_bytes):
    """Identify whether the drawing is of a cylinder, valve, or gearbox."""
    jpeg_image_bytes = convert_to_jpeg(image_bytes)
    if jpeg_image_bytes is None:
        return "❌ Error: Failed to convert image to JPEG format"
    
    base64_image = encode_image_to_base64(jpeg_image_bytes)
    
    payload = {
        "model": "qwen/qwen2.5-vl-72b-instruct:free",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Analyze this engineering drawing and identify if it's a:\n"
                            "1. HYDRAULIC/PNEUMATIC CYLINDER\n"
                            "2. VALVE\n"
                            "3. GEARBOX\n\n"
                            "RESPOND ONLY with one of these exact words: CYLINDER, VALVE, or GEARBOX"
                        )
                    },
                    {
                        "type": "image_url",
                        "image_url": base64_image
                    }
                ]
            }
        ]
    }

    response_json = make_api_request(payload)
    if not response_json:
        return "UNKNOWN"
    
    component_type = response_json["choices"][0]["message"]["content"].strip().upper()
    if component_type in ["CYLINDER", "VALVE", "GEARBOX"]:
        return component_type
    return "UNKNOWN"

def get_analysis_prompt(component_type):
    """Get the appropriate analysis prompt based on component type."""
    if component_type == "CYLINDER":
        return (
            "Analyze the engineering drawing of this CYLINDER and extract only the values that are clearly visible in the image.\n"
                            "STRICT RULES:\n"
                            "1) If a value is missing or unclear, return an empty string. DO NOT estimate any values.\n"
                            "2) Convert values to the specified units where applicable.\n"
                            "3) Determine whether the cylinder is SINGLE-ACTION or DOUBLE-ACTION and set it under CYLINDER ACTION.\n"
                            "4) Extract and return data in this format:\n"
                            "CYLINDER ACTION: [value]\n"
                            "BORE DIAMETER: [value] MM\n"
                            "OUTSIDE DIAMETER: \n"
                            "ROD DIAMETER: [value] MM\n"
                            "STROKE LENGTH: [value] MM\n"
                            "CLOSE LENGTH: [value] MM\n"
                            "OPEN LENGTH: \n"
                            "OPERATING PRESSURE: [value] BAR\n"
                            "OPERATING TEMPERATURE: [value] DEG C\n"
                            "MOUNTING: \n"
                            "ROD END: \n"
                            "FLUID: [Determine and Extract] \n"
                            "DRAWING NUMBER: [Extract from Image]"
                        )
    elif component_type == "VALVE":
        return (
            "Analyze the engineering drawing of this VALVE and extract only the values that are clearly visible in the image.\n"
            "STRICT RULES:\n"
            "1) If a value is missing or unclear, return an empty string. DO NOT estimate any values.\n"
            "2) Convert values to the specified units where applicable.\n"
            "3) Extract and return data in this format:\n"
            "VALVE TYPE: [value]\n"
            "PORT SIZE: [value]\n"
            "FLOW RATE: [value]\n"
            "PRESSURE RATING: [value] BAR\n"
            "OPERATING TEMPERATURE: [value] DEG C\n"
            "ACTUATION TYPE: [value]\n"
            "BODY MATERIAL: [value]\n"
            "SEAL MATERIAL: [value]\n"
            "MOUNTING: [value]\n"
            "FLUID: [value]\n"
            "DRAWING NUMBER: [Extract from Image]"
        )
    elif component_type == "GEARBOX":
        return (
            "Analyze the engineering drawing of this GEARBOX and extract only the values that are clearly visible in the image.\n"
            "STRICT RULES:\n"
            "1) If a value is missing or unclear, return an empty string. DO NOT estimate any values.\n"
            "2) Convert values to the specified units where applicable.\n"
            "3) Extract and return data in this format:\n"
            "GEARBOX TYPE: [value]\n"
            "INPUT SPEED: [value] RPM\n"
            "OUTPUT SPEED: [value] RPM\n"
            "RATIO: [value]\n"
            "INPUT POWER: [value] KW\n"
            "OUTPUT TORQUE: [value] NM\n"
            "MOUNTING POSITION: [value]\n"
            "LUBRICATION: [value]\n"
            "OPERATING TEMPERATURE: [value] DEG C\n"
            "WEIGHT: [value] KG\n"
            "DRAWING NUMBER: [Extract from Image]"
        )
    else:
        return None

def get_parameters_for_component(component_type):
    """Get the appropriate parameter list based on component type."""
    if component_type == "CYLINDER":
        return CYLINDER_PARAMETERS
    elif component_type == "VALVE":
        return VALVE_PARAMETERS
    elif component_type == "GEARBOX":
        return GEARBOX_PARAMETERS
    return []

def analyze_cylinder_image(image_bytes):
    # First identify the component type
    component_type = identify_component(image_bytes)
    if component_type == "UNKNOWN":
        return "❌ Error: Unable to identify the component type. Please ensure the drawing is clearly visible."
    
    # Get the appropriate analysis prompt
    analysis_prompt = get_analysis_prompt(component_type)
    if not analysis_prompt:
        return "❌ Error: Unable to generate analysis prompt for the identified component."
    
    # Convert the image to JPEG format
    jpeg_image_bytes = convert_to_jpeg(image_bytes)
    if jpeg_image_bytes is None:
        return "❌ Error: Failed to convert image to JPEG format"
    
    base64_image = encode_image_to_base64(jpeg_image_bytes)
    
    payload = {
        "model": "qwen/qwen2.5-vl-72b-instruct:free",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": analysis_prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": base64_image
                    }
                ]
            }
        ]
    }

    response_json = make_api_request(payload)
    if not response_json:
        return "❌ Error: API request failed"
    
    return response_json["choices"][0]["message"]["content"]

def calculate_confidence_score(results_df):
    """Calculate confidence score based on non-empty fields."""
    if results_df is None:
        return 0
    total_fields = len(results_df)
    non_empty_fields = results_df['Value'].str.strip().str.len().gt(0).sum()
    return round((non_empty_fields / total_fields) * 100)

def get_processing_status(confidence_score):
    """Determine processing status based on confidence score."""
    if confidence_score == 0:
        return "Processing.."
    elif confidence_score == 100:
        return "Completed"
    elif confidence_score >= 80:
        return "Needs Review!"
    else:
        return "Needs Review!"

def create_summary_table():
    """Create or update the summary table in session state."""
    if 'summary_df' not in st.session_state:
        st.session_state.summary_df = pd.DataFrame(columns=[
            'Drawing Type',
            'Drawing No.',
            'Processing Status',
            'Extracted Fields Count',
            'Confidence Score',
            'View/Edit'
        ])

def update_summary_row(idx, drawing_type=None, drawing_no=None, results_df=None):
    """Update a row in the summary table."""
    if 'summary_df' not in st.session_state:
        create_summary_table()
    
    # Calculate metrics
    confidence_score = calculate_confidence_score(results_df) if results_df is not None else 0
    status = get_processing_status(confidence_score)
    
    # Calculate extracted fields count
    if results_df is not None:
        total_fields = len(results_df)
        filled_fields = results_df['Value'].str.strip().str.len().gt(0).sum()
        fields_count = f"{filled_fields}/{total_fields}"
    else:
        fields_count = ""
    
    # Create or update row
    new_row = pd.DataFrame([{
        'Drawing Type': drawing_type if drawing_type else "",
        'Drawing No.': drawing_no if drawing_no else "",
        'Processing Status': status,
        'Extracted Fields Count': fields_count,
        'Confidence Score': f"{confidence_score}%" if confidence_score > 0 else "",
        'View/Edit': "View" if confidence_score > 0 else ""
    }])
    
    # Update the summary dataframe
    if len(st.session_state.summary_df) <= idx:
        st.session_state.summary_df = pd.concat([st.session_state.summary_df, new_row], ignore_index=True)
    else:
        st.session_state.summary_df.iloc[idx] = new_row.iloc[0]

def get_field_confidence(value):
    """Calculate confidence score for a single field based on value characteristics."""
    if not value or str(value).strip() == "":
        return 0
    
    # Add more sophisticated confidence scoring logic here
    # For now, using a simple scoring system
    if len(str(value)) > 2:  # More detailed values get higher confidence
        return 100
    elif value.isdigit():  # Numeric values get medium confidence
        return 95
    else:
        return 80

def get_field_action(confidence_score, value):
    """Determine action required for a field based on confidence score and value."""
    if not value or str(value).strip() == "":
        return "Manual Input Required"
    elif confidence_score == 100:
        return "Auto-filled"
    else:
        return "Review Required"

def render_detailed_view(idx):
    """Render detailed parameter view for a specific drawing."""
    if f'results_df_{idx}' not in st.session_state or st.session_state[f'results_df_{idx}'] is None:
        st.warning("No processed data available. Please process the drawing first.")
        return

    results_df = st.session_state[f'results_df_{idx}']
    component_type = st.session_state[f'component_type_{idx}']
    
    # Create detailed view DataFrame
    detailed_data = []
    for _, row in results_df.iterrows():
        value = row['Value']
        confidence = get_field_confidence(value)
        action = get_field_action(confidence, value)
        
        detailed_data.append({
            'Field Name': row['Parameter'],
            'Value': value,
            'Action': action,
            'Confidence Score': confidence
        })
    
    detailed_df = pd.DataFrame(detailed_data)
    
    # Display the drawing and its details
    col1, col2 = st.columns([2, 3])
    
    with col1:
        # Display the image
        image = Image.open(st.session_state.uploaded_files[idx])
        st.image(image, caption=f"Drawing {idx + 1}", use_column_width=True)
    
    with col2:
        # Create an editable dataframe with proper styling
        st.write(f"### Parameter Details ({component_type})")
        
        # Create editable interface for each parameter
        for _, row in detailed_df.iterrows():
            col_param, col_value, col_action, col_conf = st.columns([2, 2, 2, 1])
            
            with col_param:
                st.write(f"**{row['Field Name']}**")
            
            with col_value:
                if row['Action'] == "Manual Input Required":
                    new_value = st.text_input(
                        f"Value for {row['Field Name']}", 
                        value=row['Value'] if row['Value'] else "",
                        key=f"input_{idx}_{row['Field Name']}",
                        label_visibility="collapsed"
                    )
                    # Update the value in session state if changed
                    if new_value != row['Value']:
                        mask = results_df['Parameter'] == row['Field Name']
                        results_df.loc[mask, 'Value'] = new_value
                        st.session_state[f'results_df_{idx}'] = results_df
                else:
                    st.write(row['Value'])
            
            with col_action:
                if row['Action'] == "Auto-filled":
                    st.success("✓ Auto-filled")
                elif row['Action'] == "Review Required":
                    st.warning("⚠ Review Required")
                else:
                    st.error("○ Manual Input Required")
            
            with col_conf:
                confidence = row['Confidence Score']
                if confidence == 100:
                    st.success(f"{confidence}%")
                elif confidence >= 90:
                    st.warning(f"{confidence}%")
                else:
                    st.error(f"{confidence}%")
        
        # Add save button
        if st.button("Save Changes", key=f"save_{idx}"):
            # Update summary table
            update_summary_row(
                idx,
                drawing_type=component_type,
                drawing_no=results_df.loc[results_df['Parameter'] == 'DRAWING NUMBER', 'Value'].iloc[0],
                results_df=results_df
            )
            st.success("✅ Changes saved successfully!")

def convert_pdf_to_images(pdf_bytes):
    """Convert PDF pages to images."""
    try:
        # For macOS, poppler path is typically in /usr/local/bin
        poppler_path = "/usr/local/bin"
        
        # Convert PDF pages to images with explicit poppler path
        images = convert_from_bytes(
            pdf_bytes,
            poppler_path=poppler_path,
            fmt='jpeg',
            dpi=200
        )
        
        # Convert PIL images to bytes
        image_bytes_list = []
        for img in images:
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG', quality=95)
            image_bytes_list.append(img_byte_arr.getvalue())
        
        return image_bytes_list
    except Exception as e:
        st.error(f"Error converting PDF: {str(e)}")
        st.error("If the error persists, please try converting your PDF to images before uploading.")
        return None

def process_uploaded_file(uploaded_file):
    """Process uploaded file whether it's an image or PDF."""
    file_extension = uploaded_file.name.split('.')[-1].lower()
    
    if file_extension == 'pdf':
        # Convert PDF to images
        pdf_bytes = uploaded_file.read()
        return convert_pdf_to_images(pdf_bytes)
    else:
        # Regular image file
        return [uploaded_file.read()]

def main():
    # Set page config
    st.set_page_config(
        page_title="JSW Engineering Drawing DataSheet Extractor",
        layout="wide"
    )

    # Title and description
    st.title("JSW Engineering Drawing DataSheet Extractor")
    st.write("Upload your engineering drawings (Cylinders, Valves, or Gearboxes) to extract key parameters automatically.")

    # Initialize session state for navigation
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "Upload"

    # Navigation tabs instead of radio buttons for better UX
    tabs = st.tabs(["📤 Upload", "🔄 Process", "📋 Results"])

    with tabs[0]:  # Upload Tab
        st.header("Upload Engineering Drawings")
        st.write("Drag and drop or select multiple engineering drawing files.")
        
        # File uploader with expanded file type support including PDF
        uploaded_files = st.file_uploader(
            "Select Files", 
            type=['png', 'jpg', 'jpeg', 'bmp', 'tiff', 'webp', 'gif', 'pdf'],
            accept_multiple_files=True,
            help="Supports various formats: PNG, JPG, JPEG, BMP, TIFF, WebP, GIF, PDF"
        )

        if uploaded_files:
            with st.spinner("Processing uploaded files..."):
                # Process all uploaded files and store their images
                all_images = []
                all_image_names = []
                
                for uploaded_file in uploaded_files:
                    image_bytes_list = process_uploaded_file(uploaded_file)
                    if image_bytes_list:
                        for i, img_bytes in enumerate(image_bytes_list):
                            all_images.append(img_bytes)
                            if uploaded_file.name.lower().endswith('.pdf') and len(image_bytes_list) > 1:
                                all_image_names.append(f"{uploaded_file.name}_page_{i+1}")
                            else:
                                all_image_names.append(uploaded_file.name)

                if all_images:
                    st.session_state.image_bytes = all_images
                    st.session_state.image_names = all_image_names
                    st.session_state.uploaded_files = uploaded_files
                    
                    # Initialize summary table with basic info
                    create_summary_table()
                    for idx, image_name in enumerate(all_image_names):
                        update_summary_row(idx, drawing_type="Ready for Processing")
                    
                    st.success(f"✅ Successfully uploaded {len(all_images)} drawing(s)")
                    
                    # Show preview in a grid
                    st.subheader("Uploaded Drawings Preview")
                    cols = st.columns(3)
                    for idx, image_bytes in enumerate(all_images):
                        with cols[idx % 3]:
                            image = Image.open(io.BytesIO(image_bytes))
                            st.image(image, caption=all_image_names[idx], use_column_width=True)
                    
                    # Auto-switch to process tab
                    st.session_state.current_page = "Process"
                    st.rerun()

    with tabs[1]:  # Process Tab
        if 'image_bytes' not in st.session_state or not st.session_state.image_bytes:
            st.info("👆 Please upload your drawings in the Upload tab first.")
            return

        st.header("Process Drawings")
        
        # Display summary table
        if 'summary_df' in st.session_state and len(st.session_state.summary_df) > 0:
            st.subheader("Processing Status")
            
            # Add a "Process All" button at the top
            if st.button("🚀 Process All Drawings", key="process_all"):
                for idx, (image_bytes, image_name) in enumerate(zip(st.session_state.image_bytes, st.session_state.image_names)):
                    if f'component_type_{idx}' not in st.session_state:
                        with st.spinner(f'Identifying component type for {image_name}...'):
                            component_type = identify_component(image_bytes)
                            if not "❌" in component_type and component_type != "UNKNOWN":
                                st.session_state[f'component_type_{idx}'] = component_type
                                update_summary_row(idx, drawing_type=component_type)
                                
                                # Automatically extract parameters
                                result = analyze_cylinder_image(image_bytes)
                                if not "❌" in result:
                                    parsed_results = parse_ai_response(result)
                                    parameters = get_parameters_for_component(component_type)
                                    st.session_state[f'results_df_{idx}'] = pd.DataFrame([
                                        {"Parameter": k, "Value": parsed_results.get(k, "")}
                                        for k in parameters
                                    ])
                                    drawing_no = parsed_results.get('DRAWING NUMBER', '')
                                    update_summary_row(
                                        idx,
                                        drawing_type=component_type,
                                        drawing_no=drawing_no,
                                        results_df=st.session_state[f'results_df_{idx}']
                                    )
                st.success("✅ All drawings processed!")
                st.rerun()
            
            # Display the summary table with progress indicators
            st.dataframe(
                st.session_state.summary_df,
                hide_index=True,
                column_config={
                    'View/Edit': st.column_config.Column(width='small'),
                    'Processing Status': st.column_config.Column(width='medium'),
                    'Confidence Score': st.column_config.Column(width='small')
                }
            )
            
            # Individual drawing processing
            for idx, (image_bytes, image_name) in enumerate(zip(st.session_state.image_bytes, st.session_state.image_names)):
                with st.expander(f"Drawing {idx + 1}: {image_name}", expanded=False):
                    col1, col2 = st.columns([2, 3])
                    
                    with col1:
                        image = Image.open(io.BytesIO(image_bytes))
                        st.image(image, caption=image_name, use_column_width=True)

        with col2:
                        if f'component_type_{idx}' not in st.session_state:
                            if st.button("🔍 Identify & Process", key=f"process_{idx}"):
                                with st.spinner('Processing...'):
                                    # Identify component
                                    component_type = identify_component(image_bytes)
                                    if not "❌" in component_type and component_type != "UNKNOWN":
                                        st.session_state[f'component_type_{idx}'] = component_type
                                        update_summary_row(idx, drawing_type=component_type)
                                        
                                        # Extract parameters
                                        result = analyze_cylinder_image(image_bytes)
                                        if not "❌" in result:
                                            parsed_results = parse_ai_response(result)
                                            parameters = get_parameters_for_component(component_type)
                                            st.session_state[f'results_df_{idx}'] = pd.DataFrame([
                                                {"Parameter": k, "Value": parsed_results.get(k, "")}
                                                for k in parameters
                                            ])
                                            drawing_no = parsed_results.get('DRAWING NUMBER', '')
                                            update_summary_row(
                                                idx,
                                                drawing_type=component_type,
                                                drawing_no=drawing_no,
                                                results_df=st.session_state[f'results_df_{idx}']
                                            )
                                            st.success("✅ Processing complete!")
                                            st.rerun()
                        
                        elif st.session_state[f'results_df_{idx}'] is not None:
                            st.write(f"### Parameters ({st.session_state[f'component_type_{idx}']})")
                            st.dataframe(st.session_state[f'results_df_{idx}'], hide_index=True)
                            
                            # Add edit button
                            if st.button("✏️ Edit Parameters", key=f"edit_{idx}"):
                                st.session_state.selected_drawing = idx
                                st.session_state.current_page = "Results"
                                st.rerun()

    with tabs[2]:  # Results Tab
        if 'selected_drawing' not in st.session_state:
            if 'image_bytes' in st.session_state and st.session_state.image_bytes:
                st.info("👈 Select a drawing to edit from the Process tab")
            else:
                st.info("👆 Please upload and process your drawings first")
            return
        
        # Render detailed view with back button
        idx = st.session_state.selected_drawing
        if st.button("← Back to Processing"):
            del st.session_state.selected_drawing
            st.rerun()
        
        render_detailed_view(idx)

if __name__ == "__main__":
    main()
