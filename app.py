import streamlit as st
import base64
from PIL import Image
import io
import pandas as pd
import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY") or "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"

if not API_KEY:
    st.error("❌ API key not found! Check your .env file.")
    st.stop()  

API_URL = "https://openrouter.ai/api/v1/chat/completions"

def encode_image_to_base64(image_bytes):
    return "data:image/jpeg;base64," + base64.b64encode(image_bytes).decode("utf-8")

def identify_drawing_type(image_bytes):
    """Identify if the drawing is a Cylinder, Valve, or Gearbox"""
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
                            "Analyze this engineering drawing and identify if it is a Cylinder, Valve, or Gearbox.\n"
                            "Also extract the drawing number if visible.\n"
                            "Return ONLY in this format:\n"
                            "TYPE: [Cylinder/Valve/Gearbox]\n"
                            "DRAWING_NUMBER: [number if visible]"
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
            return f"❌ API Error: {response_json}"

    except Exception as e:
        return f"❌ Processing Error: {str(e)}"

def parse_identification_response(response_text):
    """Parse the identification response into a dictionary"""
    results = {}
    lines = response_text.split('\n')
    for line in lines:
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            results[key] = value
    return results

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

def analyze_valve_image(image_bytes):
    """Analyze valve drawing and extract parameters"""
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
                            "Analyze the valve drawing and extract only the values that are clearly visible.\n"
                            "STRICT RULES:\n"
                            "1) If a value is missing or unclear, return an empty string.\n"
                            "2) Extract and return data in this format:\n"
                            "VALVE TYPE: [value]\n"
                            "VALVE SIZE: [value] MM\n"
                            "PRESSURE RATING: [value] BAR\n"
                            "MATERIAL: [value]\n"
                            "CONNECTION TYPE: [value]\n"
                            "OPERATING TEMPERATURE: [value] DEG C\n"
                            "FLUID: [value]\n"
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
            return f"❌ API Error: {response_json}"

    except Exception as e:
        return f"❌ Processing Error: {str(e)}"

def analyze_gearbox_image(image_bytes):
    """Analyze gearbox drawing and extract parameters"""
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
                            "Analyze the gearbox drawing and extract only the values that are clearly visible.\n"
                            "STRICT RULES:\n"
                            "1) If a value is missing or unclear, return an empty string.\n"
                            "2) Extract and return data in this format:\n"
                            "GEARBOX TYPE: [value]\n"
                            "RATIO: [value]\n"
                            "INPUT SPEED: [value] RPM\n"
                            "OUTPUT SPEED: [value] RPM\n"
                            "POWER RATING: [value] KW\n"
                            "MOUNTING: [value]\n"
                            "LUBRICATION: [value]\n"
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
            return f"❌ API Error: {response_json}"

    except Exception as e:
        return f"❌ Processing Error: {str(e)}"

def get_parameters_for_type(drawing_type):
    """Return the expected parameters for each drawing type"""
    if drawing_type.lower() == 'cylinder':
        return [
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
    elif drawing_type.lower() == 'valve':
        return [
            "VALVE TYPE",
            "VALVE SIZE",
            "PRESSURE RATING",
            "MATERIAL",
            "CONNECTION TYPE",
            "OPERATING TEMPERATURE",
            "FLUID",
            "DRAWING NUMBER"
        ]
    elif drawing_type.lower() == 'gearbox':
        return [
            "GEARBOX TYPE",
            "RATIO",
            "INPUT SPEED",
            "OUTPUT SPEED",
            "POWER RATING",
            "MOUNTING",
            "LUBRICATION",
            "DRAWING NUMBER"
        ]
    return []

def process_drawing(image_bytes, drawing_type):
    """Process drawing based on its type"""
    if drawing_type.lower() == 'cylinder':
        return analyze_cylinder_image(image_bytes)
    elif drawing_type.lower() == 'valve':
        return analyze_valve_image(image_bytes)
    elif drawing_type.lower() == 'gearbox':
        return analyze_gearbox_image(image_bytes)
    return "❌ Unknown drawing type"

def main():
    # Set page config
    st.set_page_config(
        page_title="JSW Engineering Drawing DataSheet Extractor",
        layout="wide"
    )

    # Title and description
    st.title("JSW Engineering Drawing DataSheet Extractor")
    st.write("Upload your engineering drawings to extract key parameters automatically.")

    # Initialize session state for the drawings table
    if 'drawings_data' not in st.session_state:
        st.session_state.drawings_data = pd.DataFrame(
            columns=['Drawing Type', 'Drawing No.', 'Processing Status', 
                    'Extracted Fields Count', 'Confidence Score', 'View/Edit']
        )

    # Create two pages using radio buttons
    page = st.radio("Navigation", ["Upload Drawings", "Process Drawings"], label_visibility="hidden")

    if page == "Upload Drawings":
        st.header("Upload Engineering Drawings")
        st.write("Drag and drop or select multiple engineering drawing files.")
        
        # File uploader with multiple files support
        uploaded_files = st.file_uploader(
            "Select Files", 
            type=['png', 'jpg', 'jpeg'],
            accept_multiple_files=True,
            help="You can select multiple files by holding Ctrl/Cmd while selecting"
        )

        if uploaded_files:
            st.success(f"✅ {len(uploaded_files)} file(s) uploaded successfully!")
            
            # Process each file for identification
            for uploaded_file in uploaded_files:
                # Check if this file is already processed
                if not any(st.session_state.drawings_data['Drawing No.'].str.contains(uploaded_file.name, na=False)):
                    with st.spinner(f'Identifying drawing type for {uploaded_file.name}...'):
                        uploaded_file.seek(0)
                        image_bytes = uploaded_file.read()
                        
                        # First identify the drawing type
                        identification = identify_drawing_type(image_bytes)
                        parsed_id = parse_identification_response(identification)
                        
                        # Add to the table
                        new_row = pd.DataFrame([{
                            'Drawing Type': parsed_id.get('TYPE', 'Unknown'),
                            'Drawing No.': parsed_id.get('DRAWING_NUMBER', uploaded_file.name),
                            'Processing Status': 'Pending',
                            'Extracted Fields Count': '0/0',
                            'Confidence Score': '0%',
                            'View/Edit': 'View'
                        }])
                        
                        st.session_state.drawings_data = pd.concat(
                            [st.session_state.drawings_data, new_row], 
                            ignore_index=True
                        )

            # Display the table
            st.subheader("Uploaded Drawings")
            st.dataframe(
                st.session_state.drawings_data,
                column_config={
                    "View/Edit": st.column_config.ButtonColumn(
                        "View/Edit",
                        help="Click to view or edit the extracted data"
                    )
                },
                hide_index=True
            )

    elif page == "Process Drawings":
        st.header("Process Drawings")
        
        if st.session_state.drawings_data.empty:
            st.warning("Please upload files first on the Upload Drawings page.")
            return

        # Display the table with all drawings
        clicked = st.dataframe(
            st.session_state.drawings_data,
            column_config={
                "View/Edit": st.column_config.ButtonColumn(
                    "View/Edit",
                    help="Click to view or edit the extracted data"
                )
            },
            hide_index=True,
            on_click=lambda row: st.session_state.update({'selected_drawing': row['Drawing No.']})
        )

        # Process selected drawing
        if 'selected_drawing' in st.session_state:
            drawing_idx = st.session_state.drawings_data[
                st.session_state.drawings_data['Drawing No.'] == st.session_state.selected_drawing
            ].index[0]
            
            drawing_data = st.session_state.drawings_data.iloc[drawing_idx]
            
            st.subheader(f"Processing {drawing_data['Drawing No.']}")
            
            col1, col2 = st.columns([3, 2])
            
            with col1:
                if f'results_df_{drawing_idx}' not in st.session_state:
                    st.session_state[f'results_df_{drawing_idx}'] = None

                if st.button("Process Drawing", key=f"process_button_{drawing_idx}"):
                    with st.spinner('Processing drawing...'):
                        # Get the original file
                        uploaded_file = [f for f in uploaded_files if f.name == drawing_data['Drawing No.'] or drawing_data['Drawing No.'] in f.name][0]
                        uploaded_file.seek(0)
                        image_bytes = uploaded_file.read()
                        
                        # Process based on drawing type
                        result = process_drawing(image_bytes, drawing_data['Drawing Type'])
                        
                        if "❌" in result:
                            st.error(result)
                        else:
                            parsed_results = parse_ai_response(result)
                            parameters = get_parameters_for_type(drawing_data['Drawing Type'])
                            
                            # Create a DataFrame with additional columns for confidence and action
                            results_data = []
                            for param in parameters:
                                value = parsed_results.get(param, "")
                                confidence = 100 if value else 0
                                
                                # Determine action based on confidence
                                if confidence == 100:
                                    action = "✅ Auto-filled"
                                elif confidence > 90:
                                    action = "⚠️ Review Required"
                                else:
                                    action = "🔴 Manual Input Required"
                                
                                results_data.append({
                                    "Field Name": param,
                                    "Value": value,
                                    "Action": action,
                                    "Confidence Score": f"{confidence}%",
                                    "Original Value": value  # Keep original value for comparison
                                })
                            
                            st.session_state[f'results_df_{drawing_idx}'] = pd.DataFrame(results_data)
                            
                            # Update the main table
                            filled_count = sum(1 for v in parsed_results.values() if v)
                            total_count = len(parameters)
                            confidence = (filled_count / total_count) * 100
                            
                            st.session_state.drawings_data.at[drawing_idx, 'Processing Status'] = 'Completed' if confidence == 100 else 'Needs Review!'
                            st.session_state.drawings_data.at[drawing_idx, 'Extracted Fields Count'] = f"{filled_count}/{total_count}"
                            st.session_state.drawings_data.at[drawing_idx, 'Confidence Score'] = f"{confidence:.0f}%"
                            
                            st.success("✅ Drawing processed successfully!")

                if st.session_state[f'results_df_{drawing_idx}'] is not None:
                    st.write("### Extracted Parameters")
                    
                    # Create editable dataframe
                    edited_df = st.data_editor(
                        st.session_state[f'results_df_{drawing_idx}'],
                        column_config={
                            "Field Name": st.column_config.Column(
                                "Field Name",
                                width="medium",
                                help="Parameter name"
                            ),
                            "Value": st.column_config.TextColumn(
                                "Value",
                                width="medium",
                                help="Extracted or manually entered value"
                            ),
                            "Action": st.column_config.Column(
                                "Action",
                                width="medium"
                            ),
                            "Confidence Score": st.column_config.Column(
                                "Confidence Score",
                                width="small"
                            ),
                            "Original Value": st.column_config.Column(
                                "Original Value",
                                disabled=True,
                                hidden=True
                            )
                        },
                        hide_index=True,
                        num_rows="fixed",
                    )
                    
                    # Check if any values were manually edited
                    if not edited_df.equals(st.session_state[f'results_df_{drawing_idx}']):
                        for idx, row in edited_df.iterrows():
                            if row['Value'] != row['Original Value']:
                                edited_df.at[idx, 'Action'] = "✏️ Manually Edited"
                                edited_df.at[idx, 'Confidence Score'] = "100%"
                        
                        st.session_state[f'results_df_{drawing_idx}'] = edited_df
                    
                    # Add download button
                    csv = edited_df[['Field Name', 'Value', 'Action', 'Confidence Score']].to_csv(index=False)
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name=f"parameters_{drawing_data['Drawing No.']}.csv",
                        mime="text/csv"
                    )

            with col2:
                # Display the image
                uploaded_file = [f for f in uploaded_files if f.name == drawing_data['Drawing No.'] or drawing_data['Drawing No.'] in f.name][0]
                image = Image.open(uploaded_file)
                st.image(image, caption=f"Drawing: {drawing_data['Drawing No.']}")

if __name__ == "__main__":
    main()
