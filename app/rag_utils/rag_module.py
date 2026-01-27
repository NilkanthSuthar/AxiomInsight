# ========== CONFIG ==========
from pathlib import Path
import os
import pandas as pd
from collections import defaultdict
from langchain_core.documents import Document
import sqlite3


from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_core.output_parsers import StrOutputParser

from .secret_key import openapi_key,langchain_key,cohere_api_key



os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGCHAIN_PROJECT"] = "RAG"
os.environ["LANGCHAIN_API_KEY"] = langchain_key
os.environ["OPENAI_API_KEY"] = openapi_key
os.environ["COHERE_API_KEY"] = cohere_api_key


# ==============================
# ====Split,load,embed==========
# ==============================

openai_embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
vectorstore = Chroma(
    collection_name="my_collection",
    persist_directory="chroma_db",
    embedding_function=openai_embeddings
)


def embed_documents_to_vectorstore(docs):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(docs)
    vectorstore.add_documents(splits)
    
    print("Documents embedded and saved to vectorstore.")
    print("Total documents:", len(vectorstore.get()["documents"]))
    #print("Chunks being added:")
    #for chunk in splits:
    #    print(f"---\n{chunk.page_content[:150]}...\nMetadata: {chunk.metadata}")




def load_file(filepath, role):
    ext = Path(filepath).suffix.lower()
    try:
        if ext == ".csv":
            df1 = pd.read_csv(filepath)
            documents = []
            for row in df1.to_dict(orient="records"):
                content = "\n".join(f"{k}: {v}" for k, v in row.items())
                documents.append(
                    Document(
                        page_content=content,
                        metadata={"role": role.lower(), "source": Path(filepath).name}
                    )
                )
            return documents  # Return a list of documents

        elif ext == ".md":
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            return [
                Document(
                    page_content=content,
                    metadata={"role": role.lower(), "source": Path(filepath).name}
                )
            ]
        else:
            return None

    except Exception as e:
        print(f"Failed to process {filepath}: {e}")
        return None


def run_indexer():
    conn = sqlite3.connect("roles_docs.db")
    c = conn.cursor()
    c.execute("SELECT id, filepath, role FROM documents WHERE embedded = 0")
    
    all_docs = []

    for doc_id, path, role in c.fetchall():
        docs = load_file(path, role)
        if docs:
            if isinstance(docs, list):
                all_docs.extend(docs)
            else:
                all_docs.append(docs)

            # Mark this file as embedded
            c.execute("UPDATE documents SET embedded = 1 WHERE id = ?", (doc_id,))

    if all_docs:
        embed_documents_to_vectorstore(all_docs)
        conn.commit()

    conn.close()
    print(f"Indexed {len(all_docs)} document chunks.")


# ==============================
# ========== PROMPT TEMPLATE ==========
# ==============================
system_prompt = (
    "You are an assistant for summarizing and answering queries from internal company documents.\n"
    "Always use the retrieved context to answer the query, even if partial.\n"
    "Do not guess. If data is not found, explain what you searched for.\n"
    "When responding:\n"
    "- Add **Source** from document metadata if possible.\n"
    "- Use headers\n"
    "- Use bullet points\n"
    "- For CSV-style data, format in table with two columns\n"
    "\n{context}"
)

chat_prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "{input}"),
])

# ==============================
# ========== MODEL ==========
# ==============================
model = ChatOpenAI(
    model="gpt-4o",  
    temperature=0.2,
    streaming=True  # Enable streaming for faster perceived response
)

# Helper function to format documents
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

# ==============================
# Add a Reranker
# ==============================
def wrap_with_reranker(retriever, cohere_api_key, top_n=4):
    #print("[INFO] Using Cohere reranker.")
    reranker = CohereRerank(cohere_api_key=cohere_api_key, top_n=top_n)
    return ContextualCompressionRetriever(
        base_compressor=reranker,
        base_retriever=retriever
    )

def get_rag_chain(user_role: str,cohere_api_key: str = None):
    user_role = user_role.lower()

    if user_role == "admin":
        # Admin sees everything
        retriever = vectorstore.as_retriever(
            search_kwargs={"k": 3},
            search_type="similarity"  # Faster than MMR
        )

    elif user_role == "general":
        # General role sees only general documents
        retriever = vectorstore.as_retriever(
            search_kwargs={
                "k": 3,
                "filter": {"role": "general"}
            },
            search_type="similarity"
        )

    else:
        # All other roles see their docs + general
        retriever = vectorstore.as_retriever(
            search_kwargs={
                "k": 3,
                "filter": {
                    "role": {"$in": [user_role, "general"]}
                }
            },
            search_type="similarity"
        )

    # wrap with reranker
    if cohere_api_key:
        print("Using cohere reranker")
        retriever = wrap_with_reranker(retriever, cohere_api_key)

    # Use LCEL to create the chain
    rag_chain = (
        RunnableParallel(
            context=retriever | format_docs,
            input=RunnablePassthrough()
        )
        | chat_prompt
        | model
        | StrOutputParser()
    )
    
    # Wrap to match expected output format {"answer": "..."}
    def format_output(text):
        return {"answer": text}
    
    return rag_chain | format_output


"""
# ========== MAIN EXECUTION ==========
if __name__ == "__main__":
    run_indexer() 
"""
    # ========== EXAMPLE USAGE ==========
"""
    user_role = "hr" 
    rag_chain = get_rag_chain(user_role)

    
    query = "give me Campaign Highlights from marketing summary."
    response = rag_chain.invoke({"input": query})

    print((response["answer"]))
    for doc in response.get("context", []):
        print(f"Source: {doc.metadata['source']}, Role: {doc.metadata.get('role')}")

"""

