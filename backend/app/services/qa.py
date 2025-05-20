from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import Runnable
import os
import re

from dotenv import load_dotenv

load_dotenv()

embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# Initialize the Groq LLM
llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model_name="llama3-8b-8192"
)

def split_into_sentences(text):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if len(s.strip()) > 15]

def build_vector_db_from_text(text, doc_id="UNKNOWN"):
    sentences = split_into_sentences(text)
    documents = [
        Document(page_content=sentence, metadata={"sentence_index": i, "doc_id": doc_id})
        for i, sentence in enumerate(sentences)
    ]
    vectordb = Chroma.from_documents(documents, embedding_model)
    return vectordb

def answer_question(vector_db, question, k=5):
    # Step 1: Retrieve top-k sentences
    relevant_docs = vector_db.similarity_search(question, k=k)

    if not relevant_docs:
        return {
            "answer": "No relevant sentences found.",
            "citations": []
        }

    # Step 2: Format citations
    citations = []
    context = ""
    for doc in relevant_docs:
        sentence = doc.page_content
        sentence_index = doc.metadata.get("sentence_index", "?")
        doc_id = doc.metadata.get("doc_id", "UNKNOWN")
        citation_tag = f"[{doc_id}:S{sentence_index}]"
        citations.append(f"{citation_tag} {sentence}")
        context += f"{citation_tag} {sentence}\n"

    # Step 3: Prompt the LLM to synthesize an answer
    prompt = PromptTemplate(
        input_variables=["context", "question"],
        template=(
            "You are an AI assistant. Use the context below to answer the question. "
            "Be clear and concise, and refer only to the given context.\n\n"
            "Context:\n{context}\n\n"
            "Question: {question}\n\n"
            "Answer:"
        )
    )

    chain: Runnable = prompt | llm
    response = chain.invoke({"context": context, "question": question})

    return {
        "answer": response.content.strip(),
        "citations": citations
    }
