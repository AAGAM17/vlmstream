import streamlit as st
import base64
from PIL import Image
import io
import pandas as pd
import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")

if not API_KEY:
    st.error("❌ API key not found! Check your .env file.")
    st.stop()  

API_URL = "https://openrouter.ai/api/v1/chat/completions"

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
        "Authorization": f"Bearer {API_KEY}",
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
        "Authorization": f"Bearer {API_KEY}",
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
    st.write("Drag and drop or select multiple engineering drawings to process them.")

    # Initialize session state
    initialize_session_state()

    # File uploader and processing section
    uploaded_files = st.file_uploader("Select Files", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

    if uploaded_files:
        # Initial identification step
        if st.button("Identify Drawings", key="identify_button"):
            new_rows = []
            progress_bar = st.progress(0)
            
            for idx, uploaded_file in enumerate(uploaded_files):
                with st.spinner(f'Identifying drawing {idx + 1} of {len(uploaded_files)}...'):
                    uploaded_file.seek(0)
                    image_bytes = uploaded_file.read()
                    
                    # Identify drawing type
                    identification = identify_drawing_type(image_bytes)
                    
                    new_row = {
                        'Drawing Type': identification.get('TYPE', 'Unknown'),
                        'Drawing No.': identification.get('DRAWING_NUMBER', ''),
                        'Processing Status': 'Pending',
                        'Extracted Fields Count': '0/0',
                        'Confidence Score': '0%',
                        'View/Edit': 'Pending'
                    }
                    new_rows.append(new_row)
                    
                    # Update progress bar
                    progress_bar.progress((idx + 1) / len(uploaded_files))
            
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
            
            for idx, uploaded_file in enumerate(uploaded_files):
                with st.spinner(f'Processing drawing {idx + 1} of {len(uploaded_files)}...'):
                    uploaded_file.seek(0)
                    image_bytes = uploaded_file.read()
                    
                    # Get drawing type from processing table
                    drawing_type = st.session_state.processing_table.iloc[idx]['Drawing Type']
                    
                    # Update status to Processing
                    st.session_state.processing_table.loc[idx, 'Processing Status'] = 'Processing...'
                    
                    result = analyze_cylinder_image(image_bytes)  # We'll need to modify this based on drawing type
                    
                    if "❌ API Error" in result or "❌ Processing Error" in result:
                        st.session_state.processing_table.loc[idx, 'Processing Status'] = 'Failed'
                        st.error(f"Error processing {uploaded_file.name}: {result}")
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
                        parsed_results['FILENAME'] = uploaded_file.name
                        all_results.append(parsed_results)
                    
                    # Update progress bar
                    progress_bar.progress((idx + 1) / len(uploaded_files))
            
            if all_results:
                st.session_state.results_df = pd.DataFrame(all_results)
                st.success("✅ All drawings processed successfully!")

        # Display images grid
        if uploaded_files:
            st.write("### Uploaded Technical Drawings")
            cols = st.columns(3)
            for idx, uploaded_file in enumerate(uploaded_files):
                with cols[idx % 3]:
                    image = Image.open(uploaded_file)
                    st.image(image, caption=f"Drawing {idx + 1}: {uploaded_file.name}")

if __name__ == "__main__":
    main()
