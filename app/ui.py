import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
import base64

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Axiom Insight", page_icon="📊",layout="wide")
# -------------------------
# BACKGROUND STYLING
# -------------------------
def set_background():
    css = """
    <style>
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        background-attachment: fixed;
    }
    
    /* Ensure text is readable */
    .stApp, .stApp label, .stApp p, .stApp span, .stApp div {{
        color: #1a1a1a !important;
    }}
    
    /* Input fields */
    .stTextInput input, .stSelectbox select, .stTextArea textarea {{
        background-color: white !important;
        color: #1a1a1a !important;
    }}
    
    /* Placeholder text */
    .stTextInput input::placeholder, .stTextArea textarea::placeholder {{
        color: #666666 !important;
        opacity: 1 !important;
    }}
    
    .stTextInput input::-webkit-input-placeholder, .stTextArea textarea::-webkit-input-placeholder {{
        color: #666666 !important;
        opacity: 1 !important;
    }}
    
    .stTextInput input::-moz-placeholder, .stTextArea textarea::-moz-placeholder {{
        color: #666666 !important;
        opacity: 1 !important;
    }}
    
    /* Selectbox specific fixes */
    .stSelectbox label, .stSelectbox > div > div {{
        color: #1a1a1a !important;
    }}
    
    .stSelectbox [data-baseweb="select"] {{
        background-color: white !important;
    }}
    
    .stSelectbox [data-baseweb="select"] > div {{
        background-color: white !important;
        color: #1a1a1a !important;
    }}
    
    /* Selectbox dropdown menu */
    .stSelectbox [role="listbox"], .stSelectbox [data-baseweb="popover"] {{
        background-color: white !important;
    }}
    
    .stSelectbox [role="option"] {{
        background-color: white !important;
        color: #1a1a1a !important;
    }}
    
    .stSelectbox [role="option"]:hover {{
        background-color: #e6f2ff !important;
        color: #1a1a1a !important;
    }}
    
    /* File uploader */
    .stFileUploader label, .stFileUploader section, .stFileUploader small {{
        color: #1a1a1a !important;
    }}
    
    .stFileUploader [data-testid="stFileUploaderDropzone"] {{
        background-color: rgba(255, 255, 255, 0.9) !important;
    }}
    
    .stFileUploader button {{
        background-color: white !important;
        color: #1a1a1a !important;
        border: 2px solid #0066cc !important;
    }}
    
    .stFileUploader button:hover {{
        background-color: #e6f2ff !important;
    }}
    
    /* Buttons */
    .stButton button {{
        background-color: #0066cc !important;
        color: white !important;
    }}
    
    /* Headings */
    h1, h2, h3, h4, h5, h6 {{
        color: #1a1a1a !important;
    }}
    
    /* Markdown content */
    .stMarkdown {{
        color: #1a1a1a !important;
    }}
    
    /* Info boxes */
    .stAlert {{
        color: #1a1a1a !important;
    }}
    
    /* Expander */
    .streamlit-expanderHeader, .streamlit-expanderContent {{
        color: #1a1a1a !important;
    }}
    
    /* Code blocks */
    .stCode, pre, code {{
        background-color: #f5f5f5 !important;
        color: #1a1a1a !important;
    }}
    
    /* Expander background */
    [data-testid="stExpander"] {{
        background-color: rgba(255, 255, 255, 0.9) !important;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

set_background()

# Welcome banner - centered
st.markdown("""
<div style="background-color: rgba(255, 255, 255, 0.95); 
    padding: 30px; border-radius: 15px; box-shadow: 0px 4px 20px rgba(0,0,0,0.2);
    text-align: center; max-width: 700px; margin: 20px auto;">
    <h2 style="color: #667eea; margin-bottom: 10px;">Welcome to Axiom Insight</h2>
    <p style="color: #555; font-size: 1.1em;">Your AI Document Assistant for Enterprise Intelligence</p>
</div>
""", unsafe_allow_html=True)

# Two-column layout
left_col, right_col = st.columns([7,1])

# -------------------------
# SESSION INIT
# -------------------------
if "auth" not in st.session_state:
    st.session_state.auth = None
if "role" not in st.session_state:
    st.session_state.role = None
if "page" not in st.session_state:
    st.session_state.page = "login"
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Load roles into session state if not present
def fetch_roles():
    try:
        role_res = requests.get(f"{API_URL}/roles", auth=HTTPBasicAuth(*st.session_state.auth))
        return role_res.json().get("roles", [])
    except:
        return []


# -------------------------
# LOGIN PAGE
# -------------------------
if st.session_state.page == "login":
    st.markdown("",unsafe_allow_html=True)
    
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown("### Login")
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            
            if st.button("Login", use_container_width=True):
                if not username or not password:
                    st.error("Please enter both username and password")
                else:
                    with st.spinner("Authenticating..."):
                        res = requests.get(f"{API_URL}/login", auth=HTTPBasicAuth(username, password))
                        if res.status_code == 200:
                            st.session_state.auth = (username, password)
                            st.session_state.username = username
                            st.session_state.password = password
                            st.session_state.role = res.json()["role"]
                        
                            # Fetch roles once login is successful
                            st.session_state.roles = fetch_roles()

                            st.session_state.page = "main"  # Navigate to main app
                            st.success("Login successful!")
                            st.rerun()
                        else:
                            try:
                                st.error(f"{res.json().get('detail', 'Login failed.')}")
                            except:
                                st.error("Server error. Please check FastAPI logs.")



# -------------------------
# MAIN APP AFTER LOGIN
# -------------------------
if st.session_state.page == "main":
    username = st.session_state.username
    role = st.session_state.role

    with right_col:
        st.markdown(f"**User:** `{username}`  \n**Role:** `{role}`")
        # --- Logout ---
        if st.button("Logout"):
            st.session_state.auth = None
            st.session_state.role = None
            st.session_state.page = "login"
            st.rerun()
    
        # Role-specific section
        # Dynamic rendering
    with left_col:
        st.markdown("")
        if role == "Admin":
            st.write("You Have Global Access")
            tab1, tab2, tab3 = st.tabs(["Chat", "Upload Documents", "User Management"])
        
        elif role == "General":
            st.write(f"You Have Access to Documents and Features Related to the `{role}` Role.")
            (tab1,) = st.tabs(["Chat"])

        else:
            st.write(f"You Have Access to Documents and Features Related to the `{role}` Role.")
            st.markdown("You Also Have Access to **General Documents** (e.g., Company Policies, Holidays, Announcements)")
            (tab1,) = st.tabs(["Chat"])
    
 
    # --- Chat Tab ---
    with tab1:
        st.subheader("Ask a Question")
        
        # Query suggestions
        with st.expander("Example Questions"):
            if role == "Admin":
                st.markdown("""
                - What is the total marketing spend for 2024?
                - Show me employee count by department
                - Summarize the quarterly financial performance
                """)
            elif role == "Finance":
                st.markdown("""
                - What were the Q4 expenses?
                - Show revenue breakdown
                - What is the gross margin trend?
                """)
            else:
                st.markdown("""
                - What are the company holidays?
                - Explain the leave policy
                - What are the working hours?
                """)
        
        # Chat input
        question = st.text_area("Your Question", placeholder="Type your question here...", height=100)
        
        col1, col2 = st.columns([1, 4])
        with col1:
            submit_btn = st.button("Submit", use_container_width=True)
        with col2:
            clear_history = st.button("Clear History", use_container_width=True)
        
        if clear_history:
            st.session_state.chat_history = []
            st.rerun()
        
        if submit_btn:
            if not question.strip():
                st.warning("Please Enter a Question")
            else:
                with st.spinner("Processing Your Query..."):
                    try:
                        res = requests.post(
                            f"{API_URL}/chat",
                            json={"question": question, "role": st.session_state.role},
                            auth=HTTPBasicAuth(*st.session_state.auth),
                            timeout=30
                        )
                        
                        if res.status_code == 200:
                            answer = res.json()["answer"]
                            mode = res.json().get("mode", "Unknown")
                            
                            # Add to history
                            st.session_state.chat_history.append({
                                "question": question,
                                "answer": answer,
                                "mode": mode
                            })
                            
                            st.success(f"Answer (Mode: {mode})")
                            st.markdown(answer)
                        else:
                            st.error("Something Went Wrong While Processing Your Question.")
                            if res.text:
                                with st.expander("Error Details"):
                                    st.code(res.text)
                    except requests.Timeout:
                        st.error("Request Timed Out. Please Try Again.")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
        
        # Display chat history
        if st.session_state.chat_history:
            st.markdown("---")
            st.subheader("Chat History")
            
            for i, chat in enumerate(reversed(st.session_state.chat_history[-5:])):
                with st.expander(f"Q{len(st.session_state.chat_history) - i}: {chat['question'][:50]}..."):
                    st.markdown(f"**Question:** {chat['question']}")
                    st.markdown(f"**Answer ({chat['mode']}):** {chat['answer']}")
            

    # --- Upload Tab (Admin) ---
    if st.session_state.role == "Admin":
        with tab2:
            st.subheader("Upload Documents")
            st.info("Upload .md or .csv files to make them available for queries")
            
            roles = st.session_state.roles
            selected_role = st.selectbox("Select Document Access Role", roles, help="Choose which role can access this document")
            doc_file = st.file_uploader("Upload Document (.md or .csv)", type=["csv", "md"])

            if doc_file:
                st.write(f"Selected File: **{doc_file.name}** ({doc_file.size / 1024:.1f} KB)")
            
            if st.button("Upload Document", use_container_width=True) and doc_file:
                with st.spinner(f"Uploading and indexing {doc_file.name}..."):
                    try:
                        res = requests.post(
                            f"{API_URL}/upload-docs",
                            files={"file": doc_file},
                            data={"role": selected_role},
                            auth=HTTPBasicAuth(*st.session_state.auth),
                            timeout=60
                        )
                        
                        if res.ok:
                            st.success(f"{res.json()['message']}")
                        else:
                            st.error(f"{res.json().get('detail', 'Something Went Wrong.')}")
                    except requests.Timeout:
                        st.error("Upload Timed Out. Large Files May Take Longer.")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

        # --- Admin Tab (Admin Only) ---
        with tab3:
            st.subheader("User Management")
            
            with st.container():
                st.markdown("#### Add New User")
                new_user = st.text_input("New Username", placeholder="username")
                new_pass = st.text_input("New Password", type="password", placeholder="password")
                new_role = st.selectbox("Assign Role", roles)
                
                if st.button("Create User", use_container_width=True):
                    if not new_user or not new_pass:
                        st.error("Please Fill in All Fields")
                    elif len(new_pass) < 6:
                        st.warning("Password Should Be at Least 6 Characters")
                    else:
                        with st.spinner("Creating user..."):
                            res = requests.post(
                                f"{API_URL}/create-user",
                                data={"username": new_user, "password": new_pass, "role": new_role},
                                auth=HTTPBasicAuth(*st.session_state.auth)
                            )
                            
                            if res.ok:
                                st.success(f"{res.json()['message']}")
                            else:
                                st.error(f"{res.json().get('detail', 'Something Went Wrong.')}")

            st.markdown("---")
            
            with st.container():
                st.markdown("#### Role Management")
                new_role_input = st.text_input("New Role Name", placeholder="e.g., Marketing, HR, Engineering")
                
                if st.button("Add Role", use_container_width=True):
                    if not new_role_input:
                        st.error("Please Enter a Role Name")
                    else:
                        with st.spinner("Creating role..."):
                            res = requests.post(
                                f"{API_URL}/create-role",
                                data={"role_name": new_role_input},
                                auth=HTTPBasicAuth(*st.session_state.auth)
                            )
                            
                            if res.ok:
                                st.success(f"{res.json()['message']}")
                                st.session_state.roles = fetch_roles()  # Refresh role list
                                st.rerun()  # Rerun so dropdowns get updated
                            else:
                                st.error(f"❌ {res.json().get('detail', 'Something went wrong.')}")

   
