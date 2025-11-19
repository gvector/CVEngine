from components.excel_downloader import convert_df_to_excel, format_results
from components.feedback import submit
import components.config as config

import requests.exceptions
import streamlit as st
import pandas as pd
import requests
import arrow
import time


st.set_page_config(page_title="Ontologic", page_icon="📈")


col1, col2 = st.columns([.6, .4])
with col1:
    st.write("# Talent Ontological Search")
with col2:
    st.image('pages/LOGO PQE 2023 BLUE.png')

utc = arrow.utcnow()
local = utc.to('Europe/Rome')

if 'time' not in st.session_state:
    st.session_state['time'] = local

if 'results_onto' not in st.session_state:
    st.session_state['results_onto'] = None

if 'feedback_cont' not in st.session_state:
    st.session_state['feedback_cont'] = False


try:
    if st.session_state['pwd']:
        pass
except KeyError:
    st.switch_page('Welcome.py')


########################################################################################################################
########################################################################################################################


def btn_del():
    del st.session_state.coe_onto
    del st.session_state.results_onto
    st.session_state['coe_onto'] = None
    return st.toast(":green[**Cache Successfully Deleted**]")


def clear_feed():
    st.success("Thank you for your feedback!")
    del st.session_state['feedback']
    del st.session_state['feedback_note']
    time.sleep(2)
    st.session_state.feedback_cont = False


def present_skill(data: list[str]) -> pd.DataFrame:
    df = pd.DataFrame(data, columns=['Skill'])
    df['Weight'] = 1.0
    return df


def search_btn():
    if st.session_state['coe_onto']:
        try:
            ranking = requests.get(f"{config.API_URL}/coe/",
                                   json={'coe_name': st.session_state['coe_onto']}).json()
            # st.session_state['results_onto'] = pd.DataFrame(ranking).transpose()
            st.session_state['results_onto'] = ranking
            st.session_state.feedback_cont = True
        except requests.exceptions.ConnectionError:
            st.error(f"Connection Error")
            st.error("try again to connect")
            st.button("Check Connection", on_click=search_btn)
    time.sleep(1.5)


########################################################################################################################
########################################################################################################################


with st.container(border=True):
    st.markdown("#### Select the *CoE* for Ontological Search")
    st.radio(key='coe_onto', label=" ", index=None,
             options=["**PV**", "**C&Q**", "**CSV**", "**LES**", "**GCP**", "**RA**", "**COMP**", "**DG**", "**MD**", "**ENG**"],
             captions=[":blue[PharmacoVigilance]", ":blue[Commissioning & Qualification]", ":blue[Computer System Validation]",
                       ":blue[Laboratory Excellence Service]", ":blue[Good Compliance Practice]",
                       ":blue[Regulatory Affairs]", ":blue[Compliance]", ":blue[Digital Governance]", ":blue[Medical Devices]",
                       ":blue[Engineering]"],
             label_visibility='collapsed', on_change=search_btn, horizontal=True)


if st.session_state['results_onto'] is not None:
    st.markdown(f"### Results for {st.session_state['coe_onto']}")
    st.dataframe(format_results(st.session_state['results_onto']))
    if st.session_state['pwd'] == config.DOWNLOAD_PWD:
        st.download_button(label="Download Results", data=convert_df_to_excel(format_results(st.session_state['results_onto'])),
                           file_name=f"Results_{st.session_state['time'].format('YYYY-MM-DD HH:mm:ss')}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    container_feed = st.container(border=True)
    if st.session_state.feedback_cont:
        container_feed.markdown("### Feedback on the performance")
        container_feed.radio(label="None", label_visibility='collapsed', index=None, key='feedback',
                             options=[":large_green_square:", ":large_yellow_square:", ":large_red_square:"],
                             captions=["Answer **correct**", "Answer **accurate** but **not complete**",
                                       "Answer **wrong**"])
        container_feed.text_input(label="Additional Note", placeholder="Insert Additional Note",
                                  key="feedback_note")

        sent = container_feed.button(label="**Submit Feedback**", type='primary',
                              on_click=submit, kwargs={'research_type': 'ONTOLOGIC',
                                                       'feedback': st.session_state['feedback'],
                                                       'note': st.session_state['feedback_note'],
                                                       'search_info': st.session_state['coe_onto']})
        if sent:
            clear_feed()
            st.rerun()


with st.sidebar:
    st.button(label="CLEAR", on_click=btn_del)
