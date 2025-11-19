from components.excel_downloader import convert_df_to_excel
from components.feedback import submit
import components.config as config

import requests.exceptions
import streamlit as st
import pandas as pd
import requests
import arrow
import time


st.set_page_config(page_title="Matrix", page_icon="📈")


col1, col2 = st.columns([.6, .4])
with col1:
    st.write("# Talent Matrix Search")
with col2:
    st.image('pages/LOGO PQE 2023 BLUE.png')

utc = arrow.utcnow()
local = utc.to('Europe/Rome')

if 'time' not in st.session_state:
    st.session_state['time'] = local

if 'skills_matrix' not in st.session_state:
    st.session_state['skills_matrix'] = {}

if 'results_matrix' not in st.session_state:
    st.session_state['results_matrix'] = None

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
    del st.session_state.skills_matrix
    del st.session_state.results_matrix
    del st.session_state.coe_matrix
    st.session_state['coe_matrix'] = None

    return st.toast(":green[**Cache Successfully Deleted**]")


def clear_feed():
    st.success("Thank you for your feedback!")
    del st.session_state['feedback']
    del st.session_state['feedback_note']
    time.sleep(2)
    st.session_state.feedback_cont = False


def extract_skills(insertion: str):
    match insertion:
        case 'input':
            st.session_state['skills_matrix'][st.session_state['input_matrix']] = 1.0
            time.sleep(1)
            st.session_state['input_matrix'] = ''
        case 'select':
            st.session_state['skills_matrix'][st.session_state['select_matrix']] = 1.0
            time.sleep(1)
            st.session_state['select_matrix'] = None


def load_onto():
    match st.session_state['coe_matrix']:
        case 'C&Q':
            st.session_state['onto_matrix'] = requests.get(f"{config.API_URL}/get_ontology/",
                                                           json={'coe_name': st.session_state['coe_matrix']}).json()
        case 'CSV':
            st.session_state['onto_matrix'] = requests.get(f"{config.API_URL}/get_ontology/",
                                                           json={'coe_name': st.session_state['coe_matrix']}).json()
        case 'GCP':
            st.session_state['onto_matrix'] = requests.get(f"{config.API_URL}/get_ontology/",
                                                           json={'coe_name': st.session_state['coe_matrix']}).json()
        case 'RA':
            st.session_state['onto_matrix'] = requests.get(f"{config.API_URL}/get_ontology/",
                                                           json={'coe_name': st.session_state['coe_matrix']}).json()
        case 'DG':
            st.session_state['onto_matrix'] = requests.get(f"{config.API_URL}/get_ontology/",
                                                           json={'coe_name': st.session_state['coe_matrix']}).json()
        case 'COMP':
            st.session_state['onto_matrix'] = requests.get(f"{config.API_URL}/get_ontology/",
                                                           json={'coe_name': st.session_state['coe_matrix']}).json()
        case 'PV':
            st.session_state['onto_matrix'] = requests.get(f"{config.API_URL}/get_ontology/",
                                                           json={'coe_name': st.session_state['coe_matrix']}).json()
        case 'LES':
            st.session_state['onto_matrix'] = requests.get(f"{config.API_URL}/get_ontology/",
                                                           json={'coe_name': st.session_state['coe_matrix']}).json()
        # case 'MD':
        #     st.session_state['onto_matrix'] = requests.get(f"{config.API_URL}/get_ontology/",
        #                                                    json={'coe_name': st.session_state['coe_matrix']}).json()
        case 'ENG':
            st.session_state['onto_matrix'] = requests.get(f"{config.API_URL}/get_ontology/",
                                                           json={'coe_name': st.session_state['coe_matrix']}).json()


def execute_search(df: dict):
    try:
        st.session_state['skills_matrix'] = df
        ranking = requests.get(f'{config.API_URL}/matrix/',
                               json={'list_skills': (st.session_state['skills_matrix'],
                                                     st.session_state['coe_matrix'])}).json()
        st.session_state['results_matrix'] = pd.DataFrame(ranking).transpose()
        st.session_state.feedback_cont = True
    except requests.exceptions.ConnectionError:
        st.error(f"Connection Error")
        st.error("try again to connect")
        st.button("Check Connection", on_click=execute_search)


def format_results(fixed_columns: list[str]) -> pd.DataFrame:
    columns_order = ['resource_name', 'company', 'role', 'business_line', 'country_residenza', 'email', 'cv_docx_name',
                     'resume_date', 'y_in_pqe']

    df = st.session_state['results_matrix']

    fixed_present = [col for col in df.columns if col in fixed_columns]
    ordered_columns = fixed_present + columns_order
    df = df[ordered_columns]
    df.fillna(0, inplace=True)
    return df[:int(config.N_ROWS)]


########################################################################################################################
########################################################################################################################


with st.container(border=True):
    st.markdown("#### Select the *CoE* where to search in the Matrix")
    st.selectbox(label=" ", options=["RA", "C&Q", "LES", "GCP", "CSV", "COMP", "DG", "PV", "ENG"], index=None,
                 placeholder="Select the CoE", key='coe_matrix', label_visibility='collapsed', on_change=load_onto)

    if st.session_state['coe_matrix'] is None:
        st.warning("**WARNING**: Select the CoE before inserting the keywords to be searched in the Matrix")
    else:
        st.markdown(f'#### Select the keywords from the Matrix of **{st.session_state.coe_matrix}**:')
        st.selectbox(label=" ", options=st.session_state['onto_matrix']['ontology'], index=None,
                     placeholder="Select the keywords", key='select_matrix', label_visibility='collapsed',
                     on_change=extract_skills, args=('select',))

        st.write('***')

        st.markdown(f'#### Insert the keywords to be searched in the Matrix of **{st.session_state.coe_matrix}**:')
        st.text_input(label=" ", label_visibility='collapsed', key='input_matrix',
                      value='', placeholder="EX. ERP, CSV, ARGUS", on_change=extract_skills, args=('input',))


if len(st.session_state['skills_matrix']) != 0:
    matrix_df = st.data_editor(st.session_state['skills_matrix'], use_container_width=True,
                               hide_index=True,
                               num_rows='dynamic',
                               column_config={
                                   '': 'Skill',
                                   'value': st.column_config.NumberColumn(
                                       label="Minimum [1: 5]",
                                       min_value=1,
                                       max_value=5,
                                       step=1
                                   )
                               })

    st.button("Run **Ranking**", on_click=execute_search, args=(matrix_df,))


if st.session_state['results_matrix'] is not None:
    st.dataframe(format_results(st.session_state['onto_matrix']['ontology']))
    if st.session_state['pwd'] == config.DOWNLOAD_PWD:
        st.download_button(label="Download Results", data=convert_df_to_excel(format_results(st.session_state['onto_matrix']['ontology'])),
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
                              on_click=submit, kwargs={'research_type': 'MATRIX',
                                                       'feedback': st.session_state['feedback'],
                                                       'note': st.session_state['feedback_note'],
                                                       'search_info': st.session_state['skills_matrix']})
        if sent:
            clear_feed()
            st.rerun()


with st.sidebar:
    st.button(label="CLEAR", on_click=btn_del)
