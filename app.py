import streamlit as st
# Must be the first Streamlit command
st.set_page_config(
    page_title="JSW Engineering Drawing DataSheet Extractor",
    layout="wide"
)

import base64
from PIL import Image
import io
import pandas as pd
import os
import requests
from dotenv import load_dotenv
import json

load_dotenv()

API_KEY = os.getenv("API_KEY")

# Debug information
st.write("Debug Info:")
st.write(f"API Key loaded: {'Yes' if API_KEY else 'No'}")
st.write(f"API Key first 10 chars: {API_KEY[:10] if API_KEY else 'None'}")

if not API_KEY:
    st.error("❌ API key not found! Check your .env file.")
    st.stop()  

API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Initialize session state for processed drawings
if 'processed_drawings' not in st.session_state:
    st.session_state.processed_drawings = pd.DataFrame(
        columns=['Drawing Type', 'Drawing No.', 'Processing Status', 
                'Extracted Fields Count', 'Confidence Score', 'View/Edit']
    )

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
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/AAGAM17",
        "X-Title": "JSW Engineering Drawing Extractor"
    }

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
                        "image_url": {
                            "url": base64_image
                        }
                    }
                ]
            }
        ]
    }

    try:
        response = requests.post(
            url=API_URL,
            headers=headers,
            data=json.dumps(payload)
        )
        response_json = response.json()
        
        if response.status_code == 200 and "choices" in response_json:
            return response_json["choices"][0]["message"]["content"]
        else:
            return f"❌ API Error: {response_json}"

    except Exception as e:
        return f"❌ Processing Error: {str(e)}"

def identify_component_type(image_bytes):
    """Identify whether the drawing is of a cylinder, valve, or gearbox."""
    base64_image = encode_image_to_base64(image_bytes)
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/AAGAM17",
        "X-Title": "JSW Engineering Drawing Extractor"
    }

    payload = {
        "model": "qwen/qwen2.5-vl-72b-instruct:free",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Look at this engineering drawing and identify what type of component it is.\n"
                            "STRICT RULES:\n"
                            "1) Only identify if it's one of these components: CYLINDER, VALVE, or GEARBOX\n"
                            "2) Return ONLY the component type in capital letters, nothing else\n"
                            "3) If you cannot clearly identify the component type, return 'UNKNOWN'"
                        )
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": base64_image
                        }
                    }
                ]
            }
        ]
    }

    try:
        response = requests.post(
            url=API_URL,
            headers=headers,
            data=json.dumps(payload)
        )
        response_json = response.json()
        
        if response.status_code == 200 and "choices" in response_json:
            return response_json["choices"][0]["message"]["content"].strip()
        else:
            return f"❌ API Error: {response_json}"

    except Exception as e:
        return f"❌ Processing Error: {str(e)}"

def update_processing_table(drawing_type, drawing_number, status, fields_count=0, confidence=0):
    """Update the processing history table with new drawing information."""
    new_row = pd.DataFrame([{
        'Drawing Type': drawing_type,
        'Drawing No.': drawing_number,
        'Processing Status': status,
        'Extracted Fields Count': f"{fields_count}/13" if fields_count > 0 else "",
        'Confidence Score': f"{confidence}%" if confidence > 0 else "",
        'View/Edit': "View"
    }])
    
    # Check if drawing number already exists
    existing_idx = st.session_state.processed_drawings[
        st.session_state.processed_drawings['Drawing No.'] == drawing_number
    ].index
    
    if len(existing_idx) > 0:
        # Update existing row
        st.session_state.processed_drawings.loc[existing_idx] = new_row.iloc[0]
    else:
        # Append new row
        st.session_state.processed_drawings = pd.concat(
            [st.session_state.processed_drawings, new_row], 
            ignore_index=True
        )

def calculate_confidence(parsed_results):
    """Calculate overall confidence based on filled fields."""
    filled_fields = sum(1 for value in parsed_results.values() if value.strip())
    total_fields = len(parsed_results)
    return round((filled_fields / total_fields) * 100)

def main():
    # Title
    st.title("JSW Engineering Drawing DataSheet Extractor")

    # Show processing history table
    if not st.session_state.processed_drawings.empty:
        st.write("### Processing History")
        st.dataframe(
            st.session_state.processed_drawings,
            column_config={
                "View/Edit": st.column_config.ButtonColumn(
                    "View/Edit",
                    help="Click to view or edit the drawing details"
                )
            },
            hide_index=True
        )

    # Define expected parameters in the new order
    parameters = [
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

    # File uploader and processing section
    uploaded_file = st.file_uploader("Select File", type=['png', 'jpg', 'jpeg'])

    if uploaded_file is not None:
        col1, col2 = st.columns([3, 2])
        
        with col1:
            if 'results_df' not in st.session_state:
                st.session_state.results_df = None

            if st.button("Process Drawing", key="process_button"):
                with st.spinner('Identifying component type...'):
                    uploaded_file.seek(0)
                    image_bytes = uploaded_file.read()
                    
                    # First identify the component type
                    component_type = identify_component_type(image_bytes)
                    
                    if "❌" in component_type:
                        st.error(component_type)
                    else:
                        st.info(f"Identified component type: {component_type}")
                        
                        # Update table with initial status
                        update_processing_table(
                            component_type,
                            "Processing...",
                            "Processing.."
                        )
                        
                        if component_type == "CYLINDER":
                            with st.spinner('Processing cylinder drawing...'):
                                result = analyze_cylinder_image(image_bytes)
                                
                                if "❌" in result:
                                    st.error(result)
                                    update_processing_table(
                                        component_type,
                                        "Error",
                                        "Failed"
                                    )
                                else:
                                    parsed_results = parse_ai_response(result)
                                    drawing_number = parsed_results.get("DRAWING NUMBER", "Unknown")
                                    confidence = calculate_confidence(parsed_results)
                                    fields_count = sum(1 for v in parsed_results.values() if v.strip())
                                    
                                    status = "Completed" if confidence == 100 else "Needs Review!"
                                    
                                    update_processing_table(
                                        component_type,
                                        drawing_number,
                                        status,
                                        fields_count,
                                        confidence
                                    )
                                    
                                    st.session_state.results_df = pd.DataFrame([
                                        {"Parameter": k, "Value": parsed_results.get(k, "")}
                                        for k in parameters
                                    ])
                                    st.success("✅ Drawing processed successfully!")
                        else:
                            update_processing_table(
                                component_type,
                                "Not Implemented",
                                "Not Supported"
                            )
                            st.warning(f"Processing for {component_type} is not yet implemented.")

            if st.session_state.results_df is not None:
                st.write("### Extracted Parameters")
                st.table(st.session_state.results_df)
            
                csv = st.session_state.results_df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name="cylinder_parameters.csv",
                    mime="text/csv"
                )

        with col2:
            image = Image.open(uploaded_file)
            st.image(image, caption="Uploaded Technical Drawing")

if __name__ == "__main__":
    main()
