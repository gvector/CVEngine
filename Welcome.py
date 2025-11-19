#export SERVER_NAME=airesfinder.pqe.eu
import components.config as config
import streamlit as st
import arrow
import time


st.set_page_config(
    page_title="Talent Search Dashboard Demo",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)


col1, col2 = st.columns([.6, .4])

with col1:
    st.write("# Talent Search Web Application")

with col2:
    st.image('pages/LOGO PQE 2023 BLUE.png')


utc = arrow.utcnow()
local = utc.to('Europe/Rome')

if 'time' not in st.session_state:
    st.session_state['time'] = local

if 'pwd' not in st.session_state:
    st.session_state['pwd'] = None


def extract_pwd():
    st.session_state['pwd'] = st.session_state['key_pwd']
    time.sleep(0.5)
    st.session_state['key_pwd'] = ''


col1, _ = st.columns([.5, .5])

col1.info("Choose one page from the sidebar on the left to test the different Searching Methods.")

col_pwd, _ = st.columns(2)
col_pwd.text_input(label="Insert PWD", key='key_pwd', value='', on_change=extract_pwd)
if st.session_state['pwd'] == config.DOWNLOAD_PWD:
    st.success("Download Password Correct")
