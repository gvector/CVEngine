from components.excel_downloader import convert_df_to_excel, format_logic
import components.config as config
from components.feedback import submit

import requests.exceptions
import streamlit as st
import requests
import arrow
import time


st.set_page_config(page_title="Logic", page_icon="📈")


# API_URL = "http://10.1.2.97:8001"


col1, col2 = st.columns([.6, .4])
with col1:
    st.write("# Talent Logic Search")
with col2:
    st.image('pages/LOGO PQE 2023 BLUE.png')

utc = arrow.utcnow()
local = utc.to('Europe/Rome')

if 'skills_logic' not in st.session_state:
    st.session_state['skills_logic'] = ['']

if 'results_logic' not in st.session_state:
    st.session_state['results_logic'] = None

if 'time' not in st.session_state:
    st.session_state['time'] = local

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
    del st.session_state.skills_logic
    del st.session_state.results_logic
    return st.toast(":green[**Cache Successfully Deleted**]")

def clear_feed():
    st.success("Thank you for your feedback!")
    del st.session_state['feedback']
    del st.session_state['feedback_note']
    time.sleep(2)
    st.session_state.feedback_cont = False


def execute_search():
    try:
        # st.session_state['skills_logic'] = df
        ranking = requests.get(f'{config.API_URL}/logic/',
                               json={'list_skills': st.session_state['skills_logic']}).json()
        st.session_state['results_logic'] = format_logic(res=ranking)
        st.session_state.feedback_cont = True
    except requests.exceptions.ConnectionError:
        st.error(f"Connection Error")
        st.error("try again to connect")
        st.button("Check Connection", on_click=execute_search)


def apply_modify() -> None:
    if len(st.session_state['logic_table']['edited_rows']) > 0:
        for row in st.session_state['logic_table']['edited_rows']:
            st.session_state['skills_logic'][row] = st.session_state['logic_table']['edited_rows'][row]['value']

    if len(st.session_state['logic_table']['added_rows']) > 0:
        for row in st.session_state['logic_table']['added_rows']:
            if 'value' in row:
                st.session_state['skills_logic'].append(row['value'])

    if len(st.session_state['logic_table']['deleted_rows']) > 0:
        st.session_state['skills_logic'] = [x for j, x in enumerate(st.session_state['skills_logic']) if j not in st.session_state['logic_table']['deleted_rows']]

    del st.session_state['logic_table']


def extract_skills():
    st.session_state['skills_logic'].append(st.session_state['input_logic'])
    time.sleep(0.9)
    st.session_state['input_logic'] = ''


########################################################################################################################
########################################################################################################################


with st.container(border=True):
    st.markdown('#### Insert the specific *keywords*')
    st.data_editor(st.session_state['skills_logic'],
                   use_container_width=True,
                   hide_index=True,
                   num_rows='dynamic',
                   key='logic_table',
                   column_config={'value': "Skill"},
                   on_change=apply_modify)

    col_run, _ = st.columns([.5, .5])

    with col_run:
        st.button(label="**Run**", on_click=execute_search, use_container_width=True, type='primary')


if st.session_state['results_logic'] is not None:
    st.dataframe(st.session_state['results_logic'])

    if st.session_state['pwd'] == config.DOWNLOAD_PWD:
        st.download_button(label="Download Results",  data=convert_df_to_excel(st.session_state['results_logic']),
                           file_name=f"Results_{st.session_state['time'].format('YYYY-MM-DD HH:mm:ss')}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    container_feed = st.container(border=True)
    # with container_feed:
    if st.session_state.feedback_cont:
        container_feed.markdown("### Feedback on the performance")
        container_feed.radio(label="None", label_visibility='collapsed', index=None, key='feedback',
                             options=[":large_green_square:", ":large_yellow_square:", ":large_red_square:"],
                             captions=["Answer **correct**", "Answer **accurate** but **not complete**",
                                       "Answer **wrong**"])
        container_feed.text_input(label="Additional Note", placeholder="Insert Additional Note",
                                  key="feedback_note")

        sent = container_feed.button(label="**Submit Feedback**", type='primary',
                              on_click=submit, kwargs={'research_type': 'LOGIC',
                                                       'feedback': st.session_state['feedback'],
                                                       'note': st.session_state['feedback_note'],
                                                       'search_info': st.session_state['skills_logic']})
        if sent:
            clear_feed()
            st.rerun()

with st.sidebar:
    st.button(label="CLEAR", on_click=btn_del)
