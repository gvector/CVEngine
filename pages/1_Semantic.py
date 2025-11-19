from components.excel_downloader import convert_df_to_excel, format_results
from components.processor import Reader
from components.feedback import submit
import components.config as config

import requests.exceptions
import streamlit as st
import requests
import arrow
import time


st.set_page_config(page_title="Semantic", page_icon="📈")


col1, col2 = st.columns([.6, .4])
with col1:
    st.write("# Talent Semantic Search")
with col2:
    st.image('pages/LOGO PQE 2023 BLUE.png')

utc = arrow.utcnow()
local = utc.to('Europe/Rome')

if 'time' not in st.session_state:
    st.session_state['time'] = local

if 'results_semantic' not in st.session_state:
    st.session_state['results_semantic'] = None

if 'multiselect_search' not in st.session_state:
    st.session_state['multiselect_search'] = []

if 'data_skill' not in st.session_state:
    st.session_state['data_skill'] = {}

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
    del st.session_state.data_skill
    del st.session_state.uploaded_file
    del st.session_state.results_semantic
    del st.session_state.input_text
    return st.toast(":green[**Cache Successfully Deleted**]")


def clear_feed():
    st.success("Thank you for your feedback!")
    del st.session_state['feedback']
    del st.session_state['feedback_note']
    time.sleep(2)
    st.session_state.feedback_cont = False


def extract_skills(text: str) -> list[str]:
    skills = text.split('\n')
    return [skill.strip() for skill in skills]


def read_input(input_file) -> str:
    reader = Reader(file_path=input_file)
    reader.convert_doc_to_txt()
    return reader.get_raw_data()


def parse_doc(type_input: str) -> None:
    match type_input:
        case 'UPLOAD':
            if st.session_state['uploaded_file'] is not None:
                answer = requests.get(f"{config.API_URL}/extract/",
                                      json={'text': read_input(st.session_state['uploaded_file'])}).json()
                try:
                    st.session_state['data_skill'] = {skill: 0.5 for skill in answer['skills']}
                except requests.exceptions.ConnectionError:
                    st.error(f"Connection Error")
                    st.error("try again to connect")
                    st.button("Check Connection", on_click=parse_doc)
                except KeyError:
                    doc_container.error(f"****Error** loading file: **{st.session_state.uploaded_file.name}**")
                    doc_container.button(':color[**Retry**]', on_click=parse_doc)

        case 'INPUT':
            if st.session_state['input_text']:
                answer = requests.get(f"{config.API_URL}/extract/",
                                      json={'text': st.session_state['input_text']}).json()
                try:
                    st.session_state['data_skill'] = {skill: 0.5 for skill in answer['skills']}
                except requests.exceptions.ConnectionError:
                    st.error(f"Connection Error")
                    st.error("try again to connect")
                    st.button("Check Connection", on_click=parse_doc)
                except KeyError:
                    doc_container.error(f"****Error** loading file: **{st.session_state.uploaded_file.name}**")
                    doc_container.button(':color[**Retry**]', on_click=parse_doc)


def add_skills(input_type: str) -> None:
    match input_type:
        case 'multi':
            st.session_state['data_skill'][st.session_state['multiselect_search'][0]] = 0.5
            time.sleep(0.9)
            st.session_state['multiselect_search'] = []
        case 'input':
            st.session_state['data_skill'][st.session_state['input_search']] = 0.5
            time.sleep(0.9)
            st.session_state['input_search'] = ''


def execute_ranking():
    try:
        ranking = requests.get(url=f"{config.API_URL}/keywords/",
                               json={'list_skills': st.session_state['data_skill']}).json()
        # st.session_state['results_semantic'] = pd.DataFrame(ranking).transpose()
        st.session_state['results_semantic'] = ranking
        st.session_state.feedback_cont = True
    except requests.exceptions.ConnectionError:
        st.error(f"Connection Error")
        st.error("try again to connect")
        st.button("Check Connection", on_click=execute_ranking)


def apply_modify() -> None:
    keys_list = list(st.session_state['data_skill'].keys())
    if len(st.session_state['semantic_table']['edited_rows']) > 0:
        for row in st.session_state['semantic_table']['edited_rows']:
            if '_index' in st.session_state['semantic_table']['edited_rows'][row]:
                st.session_state['data_skill'][st.session_state['semantic_table']['edited_rows'][row]['_index']] = st.session_state['data_skill'].pop(keys_list[row])
            if 'value' in st.session_state['semantic_table']['edited_rows'][row]:
                st.session_state['data_skill'][keys_list[row]] = st.session_state['semantic_table']['edited_rows'][row]['value']

    if len(st.session_state['semantic_table']['added_rows']) > 0:
        for row in st.session_state['semantic_table']['added_rows']:
            if '_index' in row:
                st.session_state['data_skill'][row['_index']] = 0.5

    if len(st.session_state['semantic_table']['deleted_rows']) > 0:
        for row in st.session_state['semantic_table']['deleted_rows']:
            del st.session_state['data_skill'][keys_list[row]]

    del st.session_state['semantic_table']


@st.cache_data
def load_onto() -> list[str]:
    answer = requests.get(f"{config.API_URL}/get_ontology/",
                          json={'coe_name': 'ALL'}).json()
    return answer['ontology']


keywords_full = load_onto()


########################################################################################################################
########################################################################################################################

doc_container = st.container(border=True)
doc_container.write("#### Upload *Job Post*")
doc_container.file_uploader(label=" ", key='uploaded_file', type=["docx", "pdf"], label_visibility='collapsed',
                            on_change=parse_doc, args=('UPLOAD',))

doc_container.write("#### Insert *Job Post* text")
doc_container.text_area(label=" ", key='input_text', placeholder="Insert text", label_visibility='collapsed')
doc_container.button(label="Extract Skills", on_click=parse_doc, args=('INPUT',))

with st.container(border=True):
    st.write("#### Select skills from the *Ontology*")
    st.multiselect(label=" ", options=keywords_full, label_visibility='collapsed', key='multiselect_search',
                   on_change=add_skills, args=('multi',))

    st.write("#### Inserting a skill *Manually*")
    st.text_input(label=" ", key='input_search', placeholder="Enter skill", label_visibility='collapsed',
                  on_change=add_skills, args=('input',))

if len(st.session_state.data_skill) != 0:
    st.data_editor(data=st.session_state['data_skill'],
                   use_container_width=True,
                   num_rows='dynamic',
                   key='semantic_table',
                   column_config={'': "Skill",
                                  'value': st.column_config.NumberColumn(
                                      label="Weight [0, 1]",
                                      min_value=0.0, max_value=1.0, step=0.1)},
                   on_change=apply_modify
                   )

    col_run, _ = st.columns([.5, .5])

    with col_run:
        st.button(label="**Run**", on_click=execute_ranking, use_container_width=True, type='primary')


if st.session_state['results_semantic'] is not None:
    st.dataframe(format_results(st.session_state['results_semantic']))
    if st.session_state['pwd'] == config.DOWNLOAD_PWD:
        try:
            df = st.session_state["results_semantic"]
            formatted = format_results(df)
            excel_data = convert_df_to_excel(formatted)
            st.download_button(
                label="Download Results",
                data=excel_data,
                file_name=f"Results_{st.session_state['time'].format('YYYY-MM-DD HH:mm:ss')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except Exception as e:
            import traceback
            st.error(traceback.format_exc())

    container_feed = st.container(border=True)
    if st.session_state.feedback_cont:
        container_feed.markdown("### Feedback on the performance")
        container_feed.radio(label="None", label_visibility='collapsed', index=None, key='feedback',
                             options=[":large_green_square:", ":large_yellow_square:", ":large_red_square:"],
                             captions=["Answer **correct**", "Answer **accurate** but **not complete**",
                                       "Answer **wrong**"])
        colt, colb = container_feed.columns([.7, .3])
        colt.text_input(label="", label_visibility='collapsed', placeholder="Insert Additional Note",
                                  key="feedback_note")
        colb.button(label="Add Note")

        sent = container_feed.button(label="**Submit Feedback**", type='primary',
                                     on_click=submit, kwargs={'research_type': 'SEMANTIC',
                                                              'feedback': st.session_state['feedback'],
                                                              'note': st.session_state['feedback_note'],
                                                              'search_info': [skill for skill in st.session_state['data_skill']]})
        if sent:
            clear_feed()
            st.rerun()


with st.sidebar:
    st.button(label="CLEAR", on_click=btn_del)
