from components.logger import logger

from typing import Union
import streamlit as st
import requests


API_URL = "http://10.1.2.97:8001"


def submit(research_type: str, feedback: str, note: str, search_info: Union[str, list]) -> bool:
    if st.session_state.feedback is not None:
        sentiment_mapping = {":large_green_square:":    1,
                             ":large_yellow_square:":   0,
                             ":large_red_square:":      -1}
        if isinstance(search_info, list):
            search_info = "-".join(search_info)
        requests.post(url = f"{API_URL}/send_feedback/",
                      params={'research_type': research_type,
                              'feedback': sentiment_mapping[feedback],
                              'note': note,
                              'search_info': search_info})
        return True
