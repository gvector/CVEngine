import components.config as config

import requests.exceptions
import streamlit as st
import requests
import arrow


st.set_page_config(page_title="Summary", page_icon="📈")


# config.API_URL = "http://10.1.2.97:8001"


col1, col2 = st.columns([.6, .4])

with col1:
    st.write("# Talent Summary Tool")

with col2:
    st.image('pages/LOGO PQE 2023 BLUE.png')


utc = arrow.utcnow()
local = utc.to('Europe/Rome')

if 'time' not in st.session_state:
    st.session_state['time'] = local


########################################################################################################################
########################################################################################################################


def load_cvs() -> list[str]:
    try:
        return requests.get(f"{config.API_URL}/info/").json()
    except requests.exceptions.ConnectionError:
        st.error(f"Connection Error")
        st.warning("try again to connect")
        st.button("Check Connection", on_click=load_cvs)


def btn_del():
    if 'names' in st.session_state:
        del st.session_state['names']
        st.session_state.names = None
    elif 'ids' in st.session_state:
        del st.session_state['ids']
        st.session_state.ids = None
    del st.session_state.summary

    return st.toast(":green[**Cache Successfully Deleted**]")


def btn_search():
    try:
        if st.session_state['names'] is not None:
            st.session_state['summary'] = requests.get(f"{config.API_URL}/names/",
                                                       json={'name': st.session_state['names']}).json()
    except requests.exceptions.ConnectionError:
        st.error(f"Connection Error")
        st.warning("try again to connect")
        st.button("Check Connection", on_click=btn_search)


########################################################################################################################
########################################################################################################################


if 'users_info' not in st.session_state:
    st.session_state.users_infos = load_cvs()

container_code = st.container(border=True)
try:
    container_code.markdown('#### Select the **Resource**')
    container_code.selectbox(label="Select the Resource Name", options=st.session_state['users_infos']['names'], index=None,
                             placeholder="Select the Resource Name", key='names', label_visibility='collapsed',
                             on_change=btn_search)
except TypeError:
    st.error("Loading information Failed")


if 'summary' in st.session_state:
    container_text = st.container(border=True)
    container_text.markdown(f"#### {st.session_state.names if 'names' in st.session_state else st.session_state.ids}'s CV")
    container_text.markdown(st.session_state.summary['answer'])


with st.sidebar:
    st.button(label="CLEAR", on_click=btn_del)
