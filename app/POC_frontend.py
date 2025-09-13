# frontend.py
import json
import os
from datetime import date, datetime

import pandas as pd
import requests
import streamlit as st

# --- Configuration ---
st.set_page_config(page_title="Mediclaim Processor", layout="wide")

API_BASE_URL = "http://127.0.0.1:8000/api/v1"
CONFIDENCE_THRESHOLD = 0.8
CACHE_DIR = ".streamlit_cache"  # Directory to store cached JSON responses


# --- Helper Functions ---
def to_datetime(date_str):
    """Converts string date to datetime object for date_input."""
    if date_str:
        return datetime.strptime(str(date_str), "%Y-%m-%d").date()
    return None


def transform_data_for_adjudication(data_with_confidence):
    """
    CRITICAL: Converts data from the 'WithConfidence' structure to the simple
    structure required by the /adjudicate endpoint.
    """
    simple_data = {}
    for key, field in data_with_confidence.items():
        if key != "line_items" and isinstance(field, dict) and "value" in field:
            simple_data[key] = field["value"]

    simple_line_items = []
    if "line_items" in data_with_confidence:
        for item in data_with_confidence["line_items"]:
            simple_item = {key: field["value"] for key, field in item.items()}
            simple_line_items.append(simple_item)

    simple_data["line_items"] = simple_line_items
    return simple_data


# --- Main App ---
st.title("📄 Mediclaim Processing Workflow")

# --- Authentication Flow ---
if "access_token" not in st.session_state:
    st.session_state.access_token = None

if st.session_state.access_token is None:
    st.header("Login")
    with st.form("login_form"):
        username = st.text_input("Username", value="harsh-user")
        password = st.text_input("Password", type="password", value="harsh-user")
        submitted = st.form_submit_button("Login")
        if submitted:
            response = requests.post(
                f"{API_BASE_URL}/token",
                data={"username": username, "password": password},
            )
            if response.status_code == 200:
                st.session_state.access_token = response.json()["access_token"]
                st.rerun()
            else:
                st.error("Incorrect username or password.")
else:
    # --- Main Application UI (if logged in) ---
    st.sidebar.success("Logged in successfully!")
    if st.sidebar.button("Logout"):
        st.session_state.access_token = None
        st.rerun()

    # Initialize session state for workflow data
    if "extracted_data" not in st.session_state:
        st.session_state.extracted_data = None
    if "adjudicated_data" not in st.session_state:
        st.session_state.adjudicated_data = None

    # --- Step 1: Extraction ---
    st.header("Step 1: Extract Data from Bill")
    uploaded_file = st.file_uploader("Upload a medical bill (PDF)", type=["pdf"])
    # --- NEW: Caching Logic ---
    force_reprocess = st.checkbox("Force re-process and ignore cache")

    if uploaded_file:
        # Create cache directory if it doesn't exist
        if not os.path.exists(CACHE_DIR):
            os.makedirs(CACHE_DIR)

        # Define the path for the cached JSON file
        cache_filename = f"{os.path.splitext(uploaded_file.name)[0]}.json"
        cache_path = os.path.join(CACHE_DIR, cache_filename)

        if st.button("Process Bill"):
            # Check if a cached file exists and we are not forcing a re-process
            if os.path.exists(cache_path) and not force_reprocess:
                st.info(f"Loading extracted data from cache: {cache_path}")
                with open(cache_path, "r") as f:
                    st.session_state.extracted_data = json.load(f)
                st.session_state.adjudicated_data = None
                st.success("Data loaded from cache! Please review below.")
            else:
                # If no cache, call the API
                headers = {"Authorization": f"Bearer {st.session_state.access_token}"}
                files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
                with st.spinner(
                    "Calling AI to extract data... This may take a moment."
                ):
                    response = requests.post(
                        f"{API_BASE_URL}/claims/extract", files=files, headers=headers
                    )
                    if response.status_code == 200:
                        extracted_data = response.json()
                        st.session_state.extracted_data = extracted_data
                        st.session_state.adjudicated_data = None

                        # Save the successful response to the cache file
                        with open(cache_path, "w") as f:
                            json.dump(extracted_data, f, indent=4)
                        st.success(
                            f"Data extracted and saved to cache! Please review below."
                        )
                    else:
                        st.error(f"Error: {response.status_code} - {response.text}")

    # --- Step 2: Verification & Adjudication ---
    if st.session_state.extracted_data:
        st.header("Step 2: Verify Data & Enter Policy Details")
        st.info(
            f"Fields with low confidence (< {CONFIDENCE_THRESHOLD:.0%}) are highlighted in red. Please verify and edit them as needed."
        )

        data = st.session_state.extracted_data

        # --- Editable Header Fields ---
        st.subheader("Header & Policy Information")
        cols = st.columns(3)
        edited_header = {}
        header_keys = [
            "hospital_name",
            "patient_name",
            "bill_no",
            "bill_date",
            "admission_date",
            "discharge_date",
            "net_payable_amount",
        ]

        for i, key in enumerate(header_keys):
            with cols[i % 3]:
                field = data.get(key, {})
                confidence = field.get("confidence", 1.0)
                label = f"{key.replace('_', ' ').title()}"

                # Apply red color if confidence is low
                if confidence < CONFIDENCE_THRESHOLD:
                    st.markdown(
                        f'<p style="color:red;">{label}</p>', unsafe_allow_html=True
                    )
                else:
                    st.write(label)

                if "date" in key:
                    edited_header[key] = st.date_input(
                        "", value=to_datetime(field.get("value")), key=key
                    )
                else:
                    edited_header[key] = st.text_input(
                        "", value=field.get("value"), key=key
                    )

        # --- Policy Details Inputs ---
        with cols[0]:
            policy_number = st.text_input(
                "Policy Number", placeholder="Enter Policy Number"
            )
        with cols[1]:
            insurance_provider = st.text_input(
                "Insurance Provider", placeholder="Enter Provider Name"
            )

        # --- Editable Line Items ---
        st.subheader("Itemized Charges")

        edited_line_items_data = []

        if "line_items" in data and data["line_items"]:
            for i, item in enumerate(data["line_items"]):
                col1, col2, col3, col4 = st.columns(4)
                edited_item = {}

                # Use each column individually
                with col1:
                    field_data = item.get("description", {})
                    label_text = "Description"
                    if field_data.get("confidence", 1.0) < CONFIDENCE_THRESHOLD:
                        st.markdown(
                            f'<p style="color:red;">{label_text}</p>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.write(f"**{label_text}**")

                    # --- FIX: Provide a unique, non-empty label ---
                    edited_item["description"] = st.text_input(
                        label=f"desc_label_{i}",  # Unique label
                        value=field_data.get("value", ""),
                        key=f"desc_{i}",
                        label_visibility="collapsed",
                    )

                with col2:
                    field_data = item.get("quantity", {})
                    label_text = "Quantity"
                    if field_data.get("confidence", 1.0) < CONFIDENCE_THRESHOLD:
                        st.markdown(
                            f'<p style="color:red;">{label_text}</p>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.write(f"**{label_text}**")

                    quantity_value = field_data.get("value")
                    default_qty = (
                        1.0 if quantity_value is None else float(quantity_value)
                    )
                    edited_item["quantity"] = st.number_input(
                        label=f"qty_label_{i}",  # Unique label
                        value=default_qty,
                        key=f"qty_{i}",
                        label_visibility="collapsed",
                    )

                with col3:
                    field_data = item.get("unit_price", {})
                    label_text = "Unit Price"
                    if field_data.get("confidence", 1.0) < CONFIDENCE_THRESHOLD:
                        st.markdown(
                            f'<p style="color:red;">{label_text}</p>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.write(f"**{label_text}**")

                    price_value = field_data.get("value")

                    # --- FIX: Access the nested 'value' from the 'total_amount' object ---
                    total_amount_value = item.get("total_amount", {}).get("value", 0.0)

                    default_price = (
                        total_amount_value
                        if price_value is None
                        else float(price_value)
                    )

                    edited_item["unit_price"] = st.number_input(
                        label=f"price_label_{i}",
                        value=default_price,
                        key=f"price_{i}",
                        format="%.2f",
                        label_visibility="collapsed",
                    )

                with col4:
                    field_data = item.get("total_amount", {})
                    label_text = "Total Amount"
                    if field_data.get("confidence", 1.0) < CONFIDENCE_THRESHOLD:
                        st.markdown(
                            f'<p style="color:red;">{label_text}</p>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.write(f"**{label_text}**")

                    total_value = field_data.get("value")
                    default_total = 0.0 if total_value is None else float(total_value)
                    edited_item["total_amount"] = st.number_input(
                        label=f"total_label_{i}",  # Unique label
                        value=default_total,
                        key=f"total_{i}",
                        format="%.2f",
                        label_visibility="collapsed",
                    )

                edited_line_items_data.append(edited_item)
                st.markdown("---")

        # --- Adjudication Button ---
        if st.button("Adjudicate Claim"):
            if not policy_number:
                policy_number = "MVP1"
            if not insurance_provider:
                insurance_provider = "Default Provider"

            # 1. Start building the payload with the edited header info
            final_data_for_adjudication = edited_header

            # --- FIX: Iterate directly over the list and handle nulls ---
            line_items_payload = []
            # The .to_dict() method is removed here
            for record in edited_line_items_data:
                # If quantity is null/None, default to 1
                if pd.isna(record.get("quantity")):
                    record["quantity"] = 1.0

                # If unit_price is null/None, default it to the total_amount
                if pd.isna(record.get("unit_price")):
                    record["unit_price"] = record.get("total_amount", 0.0)

                line_items_payload.append(record)

            final_data_for_adjudication["line_items"] = line_items_payload

            # store the net_payable_amount in the payload
            # final_data_for_adjudication['net_payable_amount'] = net_payable_amount

            # Convert date objects to strings for JSON serialization
            for key in ["bill_date", "admission_date", "discharge_date"]:
                value = final_data_for_adjudication.get(key)
                if isinstance(value, date):
                    final_data_for_adjudication[key] = value.strftime("%Y-%m-%d")

            # 2. Prepare API call
            headers = {"Authorization": f"Bearer {st.session_state.access_token}"}
            params = {
                "policy_number": policy_number,
                "insurance_provider": insurance_provider,
            }

            with st.spinner("Applying rules and adjudicating..."):
                response = requests.post(
                    f"{API_BASE_URL}/claims/adjudicate",
                    json=final_data_for_adjudication,
                    headers=headers,
                    params=params,
                )
                if response.status_code == 200:
                    st.session_state.adjudicated_data = response.json()
                    st.success("Claim adjudicated!")
                else:
                    try:
                        error_detail = response.json().get("detail", "Unknown error")
                    except Exception:
                        error_detail = response.text or "No response body"
                    st.error(f"Error: {response.status_code} - {error_detail}")

    # --- Step 3: Display Adjudication Result ---
    if st.session_state.adjudicated_data:
        st.header("Final Adjudication Result")
        res = st.session_state.adjudicated_data

        cols = st.columns(2)
        cols[0].metric("Total Claimed", f"₹{res.get('total_claimed_amount', 0):.2f}")
        cols[1].metric("Total Allowed", f"₹{res.get('total_allowed_amount', 0):.2f}")

        # Display adjustments log
        if res.get("adjustments_log"):
            st.subheader("Adjustments Log")
            for adjustment in res["adjustments_log"]:
                st.write(f"- {adjustment}")
        # display sanity check result if available
        if res.get("sanity_check_result"):
            st.subheader("Final AI Sanity Check")
            sanity = res["sanity_check_result"]
            st.write(
                f"**Is Reasonable:** {'Yes' if sanity.get('is_reasonable') else 'No'}"
            )
            st.write(f"**Reasoning:** {sanity.get('reasoning', 'N/A')}")
            if sanity.get("flags"):
                st.write("**Flags:**")
                for flag in sanity["flags"]:
                    st.write(f"- {flag}")

        st.dataframe(pd.DataFrame(res["adjudicated_line_items"]))
