import streamlit as st
import base64
from PIL import Image
import io
import pandas as pd
import os
import requests
from dotenv import load_dotenv
from pdf2image import convert_from_bytes
import tempfile

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    st.error("❌ API key not found! Check your .env file.")
    st.stop()  

API_URL = "https://openrouter.ai/api/v1/chat/completions"

def convert_pdf_to_images(pdf_bytes):
    """Convert PDF bytes to a list of PIL Images."""
    try:
        # Create images from PDF bytes
        images = convert_from_bytes(
            pdf_bytes,
            dpi=200,  # Adjust DPI as needed for quality vs performance
            fmt='jpeg'
        )
        return images
    except Exception as e:
        st.error(f"Error converting PDF: {str(e)}")
        return []

def process_uploaded_file(uploaded_file):
    """Process uploaded file (PDF or Image) and return list of PIL Images."""
    try:
        if uploaded_file.type == "application/pdf":
            # Handle PDF
            pdf_bytes = uploaded_file.read()
            images = convert_pdf_to_images(pdf_bytes)
            if not images:
                st.error(f"Failed to convert PDF {uploaded_file.name}")
                return []
            return images
        else:
            # Handle image
            image = Image.open(uploaded_file)
            return [image]
    except Exception as e:
        st.error(f"Error processing file {uploaded_file.name}: {str(e)}")
        return []

def pil_image_to_bytes(pil_image):
    """Convert PIL Image to bytes."""
    img_byte_arr = io.BytesIO()
    pil_image.save(img_byte_arr, format='JPEG')
    img_byte_arr = img_byte_arr.getvalue()
    return img_byte_arr

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

def analyze_cylinder_image(image_bytes):
    base64_image = encode_image_to_base64(image_bytes)
    
    payload = {
        "model": "qwen/qwen2.5-vl-72b-instruct:free",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Analyze the engineering drawing and extract only the values that are clearly visible in the image.\n"
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
                    },
                    {
                        "type": "image_url",
                        "image_url": base64_image
                    }
                ]
            }
        ]
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        response_json = response.json()
        
        if response.status_code == 200 and "choices" in response_json:
            return response_json["choices"][0]["message"]["content"]
        else:
            return f"❌ API Error: {response_json}"  # Returns error details

    except Exception as e:
        return f"❌ Processing Error: {str(e)}"

def identify_drawing_type(image_bytes):
    base64_image = encode_image_to_base64(image_bytes)
    
    payload = {
        "model": "qwen/qwen2.5-vl-72b-instruct:free",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Analyze this engineering drawing and tell me if this is a CYLINDER, VALVE, or GEARBOX drawing.\n"
                            "Also extract the drawing number if visible.\n"
                            "Return ONLY in this format:\n"
                            "TYPE: [CYLINDER/VALVE/GEARBOX]\n"
                            "DRAWING_NUMBER: [number if visible, else empty]"
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

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        response_json = response.json()
        
        if response.status_code == 200 and "choices" in response_json:
            return parse_ai_response(response_json["choices"][0]["message"]["content"])
        else:
            return {"TYPE": "ERROR", "DRAWING_NUMBER": ""}

    except Exception as e:
        return {"TYPE": "ERROR", "DRAWING_NUMBER": ""}

def initialize_session_state():
    if 'processing_table' not in st.session_state:
        st.session_state.processing_table = pd.DataFrame(columns=[
            'Drawing Type',
            'Drawing No.',
            'Processing Status',
            'Extracted Fields Count',
            'Confidence Score',
            'View/Edit'
        ])
    if 'results_df' not in st.session_state:
        st.session_state.results_df = None

def main():
    # Set page config
    st.set_page_config(
        page_title="JSW Engineering Drawing DataSheet Extractor",
        layout="wide"
    )

    # Title
    st.title("JSW Engineering Drawing DataSheet Extractor")
    st.write("Drag and drop or select multiple engineering drawings (PDF or Images)")

    # Initialize session state
    initialize_session_state()

    # File uploader and processing section
    uploaded_files = st.file_uploader(
        "Select Files",
        type=['png', 'jpg', 'jpeg', 'pdf'],
        accept_multiple_files=True
    )

    if uploaded_files:
        # Initial identification step
        if st.button("Identify Drawings", key="identify_button"):
            new_rows = []
            all_images = []  # Store all processed images
            file_page_map = {}  # Map to track which file and page each image came from
            
            progress_bar = st.progress(0)
            total_files = len(uploaded_files)
            current_progress = 0
            
            for file_idx, uploaded_file in enumerate(uploaded_files):
                images = process_uploaded_file(uploaded_file)
                
                for page_idx, image in enumerate(images):
                    # Convert PIL Image to bytes for API
                    image_bytes = pil_image_to_bytes(image)
                    
                    # Identify drawing type
                    identification = identify_drawing_type(image_bytes)
                    
                    # Create page suffix for multi-page PDFs
                    page_suffix = f" (Page {page_idx + 1})" if len(images) > 1 else ""
                    file_name = f"{uploaded_file.name}{page_suffix}"
                    
                    new_row = {
                        'Drawing Type': identification.get('TYPE', 'Unknown'),
                        'Drawing No.': identification.get('DRAWING_NUMBER', ''),
                        'Processing Status': 'Pending',
                        'Extracted Fields Count': '0/0',
                        'Confidence Score': '0%',
                        'View/Edit': 'Pending'
                    }
                    new_rows.append(new_row)
                    
                    # Store image and mapping
                    all_images.append(image)
                    file_page_map[len(all_images) - 1] = {
                        'file_name': file_name,
                        'original_file': uploaded_file,
                        'page': page_idx
                    }
                
                # Update progress
                current_progress = (file_idx + 1) / total_files
                progress_bar.progress(current_progress)
            
            # Store images and mapping in session state
            st.session_state.processed_images = all_images
            st.session_state.file_page_map = file_page_map
            
            # Update processing table
            st.session_state.processing_table = pd.DataFrame(new_rows)
            st.success("✅ Drawing identification completed!")

        # Display processing table
        if not st.session_state.processing_table.empty:
            st.write("### Processing Status")
            st.dataframe(
                st.session_state.processing_table,
                column_config={
                    "View/Edit": st.column_config.ButtonColumn(
                        "View/Edit",
                        help="Click to view or edit the drawing details"
                    )
                },
                hide_index=True
            )

        # Process button for detailed analysis
        if not st.session_state.processing_table.empty and st.button("Process Drawings", key="process_button"):
            all_results = []
            progress_bar = st.progress(0)
            
            for idx in range(len(st.session_state.processed_images)):
                image = st.session_state.processed_images[idx]
                file_info = st.session_state.file_page_map[idx]
                
                with st.spinner(f'Processing drawing {idx + 1} of {len(st.session_state.processed_images)}...'):
                    # Convert PIL Image to bytes for API
                    image_bytes = pil_image_to_bytes(image)
                    
                    # Get drawing type from processing table
                    drawing_type = st.session_state.processing_table.iloc[idx]['Drawing Type']
                    
                    # Update status to Processing
                    st.session_state.processing_table.loc[idx, 'Processing Status'] = 'Processing...'
                    
                    result = analyze_cylinder_image(image_bytes)  # We'll need to modify this based on drawing type
                    
                    if "❌ API Error" in result or "❌ Processing Error" in result:
                        st.session_state.processing_table.loc[idx, 'Processing Status'] = 'Failed'
                        st.error(f"Error processing {file_info['file_name']}: {result}")
                    else:
                        parsed_results = parse_ai_response(result)
                        # Count non-empty fields
                        field_count = sum(1 for v in parsed_results.values() if v.strip())
                        total_fields = len(parsed_results)
                        confidence_score = (field_count / total_fields) * 100
                        
                        # Update processing table
                        st.session_state.processing_table.loc[idx, 'Processing Status'] = 'Completed'
                        st.session_state.processing_table.loc[idx, 'Extracted Fields Count'] = f"{field_count}/{total_fields}"
                        st.session_state.processing_table.loc[idx, 'Confidence Score'] = f"{confidence_score:.0f}%"
                        st.session_state.processing_table.loc[idx, 'View/Edit'] = 'View'
                        
                        # Add results to collection
                        parsed_results['FILENAME'] = file_info['file_name']
                        all_results.append(parsed_results)
                    
                    # Update progress bar
                    progress_bar.progress((idx + 1) / len(st.session_state.processed_images))
            
            if all_results:
                st.session_state.results_df = pd.DataFrame(all_results)
                st.success("✅ All drawings processed successfully!")

        # Display images grid
        if hasattr(st.session_state, 'processed_images'):
            st.write("### Uploaded Technical Drawings")
            cols = st.columns(3)
            for idx, image in enumerate(st.session_state.processed_images):
                with cols[idx % 3]:
                    file_info = st.session_state.file_page_map[idx]
                    st.image(image, caption=file_info['file_name'])

if __name__ == "__main__":
    main()
