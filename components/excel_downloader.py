import components.config as config

from openpyxl.utils.exceptions import IllegalCharacterError
from io import BytesIO
import pandas as pd
import re


def format_results(d: dict) -> pd.DataFrame:
    # columns_order = ['score', 'resource_name', 'company', 'role', 'business_line', 'country_residenza', 'email',
    #                  'cv_docx_name', 'body', 'resume_date', 'status', 'y_in_pqe', 'city_residenza',
    #                  'indirizzo_residenza', 'id_db']
    df = pd.DataFrame(d).transpose()
    df = df[config.COLUMNS_LIST]
    df.fillna(0, inplace=True)
    return df[:int(config.N_ROWS)]


def convert_df_to_excel(df: pd.DataFrame) -> bytes:
    output = BytesIO()

    # Rimuove caratteri illegali dalle celle
    def clean_illegal_chars(val):
        if isinstance(val, str):
            # Rimuove caratteri di controllo non ammessi da openpyxl
            return re.sub(r"[\x00-\x08\x0B-\x0C\x0E-\x1F]", "", val)
        return val

    df_clean = df.applymap(clean_illegal_chars)

    try:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_clean.to_excel(writer, index=False, sheet_name="Results")
        processed_data = output.getvalue()
        return processed_data
    except IllegalCharacterError as e:
        print("Errore carattere illegale:", e)
        # In caso, ritorna un file vuoto invece di bloccare Streamlit
        return b""

# def convert_df_to_excel(df: 'pd.DataFrame') -> 'bytes':
#     output = BytesIO()
#     with pd.ExcelWriter(output, engine='openpyxl') as writer:
#         df.to_excel(writer, index=False)
#     processed_data = output.getvalue()
#     return processed_data




def format_logic(res: dict) -> pd.DataFrame:
    df = pd.DataFrame.from_dict(res, orient='index')
    # Ordina per aggregate_score in ordine decrescente
    df = df.sort_values(by='score', ascending=False)
    # Elimina le righe con aggregate_score pari a 0
    df = df[df['score'] > 0]
    # Rimuovi la colonna aggregate_score
    df = df.drop(columns=['score', 'body'])
    return df
