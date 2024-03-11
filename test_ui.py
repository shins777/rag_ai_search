
import time
import streamlit as st

import os
import sys

directory = os.getcwd()
# Append sys path to refer utils.
sys.path.append(directory+"/src")

from controller import Controller
import constant as const

# https://b.corp.google.com/issues/324447032
os.environ["GRPC_DNS_RESOLVER"] = "native"

title ="Knowledge search system"
sub_header = "AI assistant for knowledge search"

# Set Streamlit page configuration
st.set_page_config(page_title=title, layout='wide')

# Initialize session states
if "generated" not in st.session_state:
    st.session_state["generated"] = []
if "past" not in st.session_state:
    st.session_state["past"] = []
if "input" not in st.session_state:
    st.session_state["input"] = ""

st.subheader(sub_header)

# Set up sidebar with various options
with st.sidebar.expander("Configuration", expanded=True):

    project_id = st.text_input(label='Project ID', value =const.project_id)
    region = st.text_input(label='Region', value =const.region)
    search_url = st.text_area(label='Vertex AI Search', value =const.search_url,height=200)
    num_pages = st.number_input('Search pages',min_value=1,max_value=5, value=3)



def get_text():
    input_text = st.text_area("You: ", st.session_state["input"], key="input",
                            placeholder="Your AI assistant here! Ask me anything ...", 
                            label_visibility='hidden')
    return input_text


question_list= None
contexts_list= None
final_contexts= None
final_outcome= None
elapsed_time = None

controller = Controller()

tab1, tab2, tab3, tab4 = st.tabs(["Search", "Searched Results", "Final Contexts & Outcome", "Latency"])

with tab1 : 
    # Get the user input
    question = get_text()
    # col1, col2, col3 = st.columns([1,1,1],gap="small")

    if tab1.button("Search!"):
        detailed = True
        question_list, contexts_list, final_contexts, final_outcome, elapsed_time = controller.process(question, detailed)

        st.session_state.past.append(question) 
        st.session_state.generated.append(final_outcome) 

    # Display the conversation history
    with st.expander("Conversation", expanded=True):
        for i in range(len(st.session_state["past"])-1, -1, -1):
            st.info(st.session_state["past"][i],icon="😊")
            st.success(st.session_state["generated"][i], icon="🤖")

with tab2:
    with st.container(height=100):
        if question_list !=None:
            st.success(f"Questions : {question_list}")        

    with st.container(height=500):
        if question_list !=None:        
            st.success(f"Number of Searched Results: {len(contexts_list)}")              

        if contexts_list !=None:
            for contexts in contexts_list:
                st.info(f"Searched Result  : \n\n{contexts}" )
with tab3:
    if final_contexts !=None:
        with st.container(height=600):
            st.info(f"Final Contexts : \n\n{final_contexts}")
    if final_outcome !=None:
        with st.container(height=600):
            st.info(f"Final Outcome : \n\n {final_outcome}")
with tab4:
    if elapsed_time !=None:    
        with st.container(height=600):
            st.info(f"Latency  : \n\n {elapsed_time}")        

