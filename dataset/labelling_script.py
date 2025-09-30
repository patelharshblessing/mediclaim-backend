import os
import fitz  # PyMuPDF
import streamlit as st
from PyPDF2 import PdfReader, PdfWriter

# --- Page Configuration ---
st.set_page_config(page_title="PDF Labeling Tool", layout="wide")

st.title("📄 PDF Page Labeling Tool")
st.write(
    "Select a source folder with your PDFs and a destination folder. "
    "The tool will display each page, and you can classify it as 'Relevant' or 'Irrelevant'. "
    "The labeled page will be saved as a new single-page PDF in the appropriate subfolder."
)

# --- Helper Functions ---
def get_pdf_files(folder_path):
    """Scans a folder and returns a list of PDF files."""
    if not os.path.isdir(folder_path):
        return []
    return [f for f in os.listdir(folder_path) if f.lower().endswith(".pdf")]

def render_page_as_image(pdf_path, page_num):
    """Renders a specific PDF page as a PNG image for display."""
    try:
        doc = fitz.open(pdf_path)
        page = doc.load_page(page_num)
        pix = page.get_pixmap()
        doc.close()
        return pix.tobytes()
    except Exception as e:
        st.error(f"Error rendering page: {e}")
        return None

def save_single_page_pdf(source_path, dest_folder, original_filename, page_num, label):
    """Extracts a single page from a source PDF and saves it to the destination."""
    try:
        reader = PdfReader(source_path)
        writer = PdfWriter()
        
        # Add the specific page to the new PDF
        writer.add_page(reader.pages[page_num])

        # Create a clean filename
        base_name = os.path.splitext(original_filename)[0]
        new_filename = f"{base_name}_page_{page_num + 1}.pdf"
        
        # Define the full path including the label subfolder
        output_path = os.path.join(dest_folder, label, new_filename)

        # Save the new single-page PDF
        with open(output_path, "wb") as f:
            writer.write(f)
        return new_filename
    except Exception as e:
        st.error(f"Failed to save page {page_num + 1} from {original_filename}: {e}")
        return None

def next_page():
    """Callback function to advance to the next page or file."""
    total_pages = st.session_state.pdf_docs[st.session_state.current_file_index]["total_pages"]
    
    if st.session_state.current_page_index < total_pages - 1:
        st.session_state.current_page_index += 1
    else:
        # Move to the next file if there is one
        if st.session_state.current_file_index < len(st.session_state.pdf_docs) - 1:
            st.session_state.current_file_index += 1
            st.session_state.current_page_index = 0
        else:
            # All files are done
            st.session_state.labeling_complete = True

# --- UI Setup ---
st.header("1. Setup Folders")
source_folder = st.text_input("Source Folder (with original PDFs)", "./source_pdfs")
dest_folder = st.text_input("Destination Folder (for labeled pages)", "./labeled_dataset")

if st.button("Start Labeling Session"):
    if not os.path.isdir(source_folder):
        st.error("Source folder does not exist. Please create it and add PDFs.")
    elif not os.path.isdir(dest_folder):
        st.info(f"Destination folder '{dest_folder}' not found. Creating it.")
        os.makedirs(dest_folder)
    else:
        # Initialize session state
        st.session_state.pdf_files = get_pdf_files(source_folder)
        if not st.session_state.pdf_files:
            st.warning("No PDF files found in the source folder.")
        else:
            # Create subdirectories
            os.makedirs(os.path.join(dest_folder, "relevant"), exist_ok=True)
            os.makedirs(os.path.join(dest_folder, "irrelevant"), exist_ok=True)
            
            # Load PDF info into session state
            st.session_state.pdf_docs = []
            for pdf_file in st.session_state.pdf_files:
                try:
                    reader = PdfReader(os.path.join(source_folder, pdf_file))
                    st.session_state.pdf_docs.append({"name": pdf_file, "total_pages": len(reader.pages)})
                except Exception as e:
                    st.error(f"Could not read {pdf_file}: {e}")
            
            st.session_state.current_file_index = 0
            st.session_state.current_page_index = 0
            st.session_state.labeling_started = True
            st.session_state.labeling_complete = False
            st.success(f"Found {len(st.session_state.pdf_docs)} PDFs. Ready to start labeling!")


# --- Main Labeling Interface ---
if "labeling_started" in st.session_state and st.session_state.labeling_started:

    if st.session_state.labeling_complete:
        st.balloons()
        st.success("🎉 All files have been labeled! You can now close this tool.")
    else:
        st.header("2. Label the Page")

        # Get current file and page details
        current_file_info = st.session_state.pdf_docs[st.session_state.current_file_index]
        current_file_name = current_file_info["name"]
        current_page_num = st.session_state.current_page_index
        total_pages = current_file_info["total_pages"]
        
        st.info(f"**File {st.session_state.current_file_index + 1} of {len(st.session_state.pdf_docs)}:** `{current_file_name}`")
        st.progress((current_page_num + 1) / total_pages, text=f"Page {current_page_num + 1} of {total_pages}")
        
        # Display the current page image
        full_pdf_path = os.path.join(source_folder, current_file_name)
        image_bytes = render_page_as_image(full_pdf_path, current_page_num)
        
        if image_bytes:
            # Use columns to create a narrower, centered view for the image
            view_cols = st.columns([1, 1, 1])
            with view_cols[1]:
                st.image(image_bytes, caption=f"Page {current_page_num + 1}", use_column_width=True)

        # Labeling buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Relevant", use_container_width=True, type="primary"):
                saved_file = save_single_page_pdf(full_pdf_path, dest_folder, current_file_name, current_page_num, "relevant")
                if saved_file:
                    st.toast(f"Saved '{saved_file}' as Relevant!")
                next_page()
                st.rerun()

        with col2:
            if st.button("❌ Irrelevant", use_container_width=True):
                saved_file = save_single_page_pdf(full_pdf_path, dest_folder, current_file_name, current_page_num, "irrelevant")
                if saved_file:
                    st.toast(f"Saved '{saved_file}' as Irrelevant!")
                next_page()
                st.rerun()
