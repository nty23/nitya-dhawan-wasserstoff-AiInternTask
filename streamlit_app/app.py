# ✅ Updated streamlit_app/app.py with document selection UI

import streamlit as st
import requests
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder

st.set_page_config(page_title="📄 Document Theme Chatbot", layout="wide")

st.title("🧠 Document Research & Theme Chatbot")
st.markdown("Upload PDFs or scanned images and ask natural language questions. Get answers with citations and theme insights.")

# Upload Section
st.header("📤 Upload Documents")
uploaded_files = st.file_uploader("Upload one or more PDF or image files", type=["pdf", "png", "jpg", "jpeg"], accept_multiple_files=True)

if uploaded_files:
    with st.spinner("Uploading and processing..."):
        files = [("files", (file.name, file, file.type)) for file in uploaded_files]
        response = requests.post("http://127.0.0.1:5000/upload", files=files)

        if response.status_code == 200:
            st.success("✅ Upload successful!")
            uploaded_data = response.json().get("documents", [])
            st.session_state.uploaded_data = uploaded_data  # persist state
            st.markdown("**Uploaded Documents:**")
            st.write([doc["filename"] for doc in uploaded_data])
        else:
            st.error("❌ Upload failed. Check backend logs.")

# Filter Section
st.header("🧾 Filter Uploaded Documents")

uploaded_data = st.session_state.get("uploaded_data", [])

if uploaded_data:
    years = sorted(list(set([doc.get("year", "Unknown") for doc in uploaded_data])))
    authors = sorted(list(set([doc.get("author", "Unknown") for doc in uploaded_data])))
    types = sorted(list(set([doc.get("type", "Unknown") for doc in uploaded_data])))

    selected_years = st.multiselect("📅 Filter by Year", options=years, default=years)
    selected_authors = st.multiselect("👤 Filter by Author", options=authors, default=authors)
    selected_types = st.multiselect("📁 Filter by Type", options=types, default=types)

    # Filter documents client-side before querying
    filtered_docs = [doc for doc in uploaded_data if doc.get("year") in selected_years and doc.get("author") in selected_authors and doc.get("type") in selected_types]
    filtered_doc_ids = [doc["id"] for doc in filtered_docs]
else:
    st.info("Upload documents to enable filters.")
    filtered_doc_ids = []

# ✅ New: Let user choose specific documents to include in query
st.header("📑 Document Selection")
if filtered_doc_ids:
    doc_id_to_name = {doc["id"]: doc["filename"] for doc in filtered_docs}
    selected_doc_ids = st.multiselect(
        "Select documents to include in the query",
        options=filtered_doc_ids,
        format_func=lambda doc_id: doc_id_to_name.get(doc_id, doc_id),
        default=filtered_doc_ids
    )
else:
    selected_doc_ids = []

# Question Section
st.header("💬 Ask a Question")
user_question = st.text_input("Type your question here and hit Enter")

if user_question and selected_doc_ids:
    with st.spinner("Thinking..."):
        try:
            response = requests.post("http://127.0.0.1:5000/ask", json={
                "question": user_question,
                "doc_ids": selected_doc_ids
            })

            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])

                if not results:
                    st.warning("🤔 No relevant answers found.")
                else:
                    st.success("✅ Answers and Citations Found")

                    for res in results:
                        with st.container(border=True):
                            st.markdown(f"### 📄 {res['filename']} ({res['doc_id']})")
                            st.markdown(f"**💬 Answer:** {res['answer']}")

                            if res.get("citations"):
                                st.markdown("#### 📌 Citations Map")
                                citation_data = [
                                    {
                                        "Document": res["filename"],
                                        "Doc ID": res["doc_id"],
                                        "Sentence": citation
                                    }
                                    for citation in res["citations"]
                                ]

                                df = pd.DataFrame(citation_data)
                                gb = GridOptionsBuilder.from_dataframe(df)
                                gb.configure_pagination()
                                gb.configure_default_column(wrapText=True, autoHeight=True)
                                grid_options = gb.build()

                                AgGrid(df, gridOptions=grid_options, fit_columns_on_grid_load=True)
            else:
                st.error("❌ Error from backend.")
        except Exception as e:
            st.error(f"❌ Exception: {e}")
elif user_question:
    st.warning("No documents match the selected filters. Please adjust your filter criteria.")
