import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# --- Configuration ---
st.set_page_config(page_title="Admin Dashboard", layout="wide")
API_BASE_URL = "http://127.0.0.1:8000/api/v1"

# --- Helper Functions ---

@st.cache_data(ttl=600)  # Cache data for 10 minutes
def get_performance_data(token: str, k: int):
    """Fetches performance data from the API and returns a DataFrame."""
    headers = {"Authorization": f"Bearer {token}"}
    params = {"k": k}
    try:
        response = requests.get(
            f"{API_BASE_URL}/admin/performance/latest", headers=headers, params=params
        )
        response.raise_for_status()
        data = response.json()
        if not data:
            return pd.DataFrame() # Return empty dataframe if no data
        df = pd.DataFrame(data)
        # Convert created_at to datetime for proper sorting and charting
        df["created_at"] = pd.to_datetime(df["created_at"])
        return df
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch data from API: {e}")
        return pd.DataFrame()


# --- Main App ---
st.title("📊 Admin Performance Dashboard")

# --- Authentication Flow ---
if "access_token" not in st.session_state:
    st.session_state.access_token = None

if st.session_state.access_token is None:
    st.header("Admin Login")
    with st.form("login_form"):
        username = st.text_input("Username", value="harsh-admin") # Default to admin user
        password = st.text_input("Password", type="password", value="harsh-admin") # Default password for ease of testing
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
                st.error("Incorrect admin username or password.")
else:
    # --- Main Dashboard UI (if logged in) ---
    st.sidebar.success("Logged in as Admin.")
    if st.sidebar.button("Logout"):
        st.session_state.access_token = None
        st.rerun()

    # --- Sidebar Controls ---
    k_claims = st.sidebar.selectbox(
        "Select Number of Recent Claims:",
        options=[10, 25, 50, 100],
        index=0,
    )
    st.sidebar.info(f"Displaying metrics for the last **{k_claims}** claims processed.")

    # --- Data Fetching and Processing ---
    df = get_performance_data(st.session_state.access_token, k_claims)
    if df.empty:
        st.warning("No performance data found for the selected range.")
    else:
        # --- KPI Cards Section ---
        st.subheader("Average Performance Metrics")
        
        # Calculate metrics, handling potential nulls and division by zero
        avg_extraction_time = df["extract_processing_time_sec"].mean()
        avg_adjudication_time = df["adjudicate_processing_time_sec"].mean()
        # Ensure page_count is not zero to avoid division errors
        df['page_count_safe'] = df['num_pages'].replace(0, 1)
        avg_extraction_per_page = (df['extract_processing_time_sec'] / df['page_count_safe']).mean()

        total_processing_time = df['extract_processing_time_sec'].fillna(0) + df['adjudicate_processing_time_sec'].fillna(0)
        avg_total_time = avg_extraction_per_page+avg_adjudication_time

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Avg Total Time", f"{avg_total_time:.2f} s")
        col2.metric("Avg Extraction Time", f"{avg_extraction_time:.2f} s")
        col3.metric("Avg Adjudication Time", f"{avg_adjudication_time:.2f} s")
        col4.metric("Avg Extraction per Page", f"{avg_extraction_per_page:.2f} s")
        
        st.markdown("---")

        # --- Visualizations Section ---
        st.subheader("Visual Analysis")
        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            # --- Pie Chart for Adjudication Steps ---
            st.write("**Average Time per Adjudication Step**")
            step_times = {
                "IRDA Filter": df["time_irda_filter_sec"].mean(),
                "Rule Matching": df["time_rule_matching_sec"].mean(),
                "Rule Application": df["time_rule_application_sec"].mean(),
                "Sanity Check": df["time_sanity_check_sec"].mean(),
                "Value Extraction": df["extract_processing_time_sec"].mean(),
            }
            # Filter out steps with no data
            step_times = {k: v for k, v in step_times.items() if pd.notna(v) and v > 0}

            if step_times:
                pie_df = pd.DataFrame(step_times.items(), columns=["Step", "Average Time (s)"])
                fig_pie = px.pie(
                    pie_df, values="Average Time (s)", names="Step", hole=0.3
                )
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("No adjudication data available for pie chart.")

        with chart_col2:
            # --- Line Chart for Total Processing Time ---
            st.write("**Total Processing Time (Last K Claims)**")
            df_sorted = df.sort_values(by="created_at", ascending=True).reset_index()
            df_sorted['total_processing_time'] = df_sorted['extract_processing_time_sec'].fillna(0) + df_sorted['adjudicate_processing_time_sec'].fillna(0)
            
            fig_line = px.line(
                df_sorted,
                x=df_sorted.index,
                y="total_processing_time",
                markers=True,
                labels={"x": "Claim (Newest to Oldest →)", "y": "Processing Time (s)"}
            )
            st.plotly_chart(fig_line, use_container_width=True)

        # --- Raw Data Section ---
        with st.expander("Show Raw Data"):
            st.dataframe(df)