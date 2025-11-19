from components.sql_connector import SQLManager
# from components.logger import logger
from components.cv import CVperson
from components.cvs import CVS

from datetime import datetime
from tqdm import tqdm


today = datetime.now()

def create_obj(sql_manager: 'SQLManager', cvs_collector: 'CVS') -> None:
    cv_dicts = sql_manager.execute()
    pbar = tqdm(total=len(cv_dicts), desc='Processing CVs', ascii=True)
    for key, value in cv_dicts.items():
        try:
            cv = CVperson.read_from_dict(idx=key, cv_dict=value)
            cvs_collector.add_cv(cv)
            cvs_collector.save(name=f'archive_{today.strftime("%d_%m_%Y")}',
                               pkl_file=True, json_file=False)
        except TypeError as e:
            print(f"TypeError for key {key}: {e}")
        pbar.update(1)
    pbar.close()


# if __name__ == '__main__':
    # logger.info("Starting the process")
    # db = SQLManager(host='10.1.1.90', user='ai_reader', password='ai-r3ad3r_2o24!')
    # db.connect()
    # cvs = CVS()
    #
    # create_obj(sql_manager=db, cvs_collector=cvs)
    #
    # cvs.load_pkl(filename='try_with_personclass')
    # logger.info('CVS Sample Loaded Correctly')

    # conn = mysql.connector.connect(host=os.getenv('HOST'), user=os.getenv('USER'), password=os.getenv('PWD'))
    # logger.info("connection established")
    #
    # query = """SELECT resource_code, cv_plain_text, resource_name, id, email, resume_date, cv_docx_name, status, y_in_pqe, company, role, country_residenza, city_residenza, indirizzo_residenza, business_line, type
    #    FROM hrtm.openai_cvs a
    #    JOIN suitecrm.v_ai_cv_res_information b
    #    USING (resource_code)
    #    WHERE a.resume_date = (
    #        SELECT MAX(b.resume_date)
    #        FROM hrtm.openai_cvs b
    #        WHERE b.resource_code = a.resource_code
    #        AND LENGTH(b.cv_plain_text) > 500
    #    );"""
    #
    # cursor = conn.cursor(buffered=True)
    #
    # ress, columns = run_execution(query=query, n=20)
    #
    # logger.info("extraction completed")
    #
    # cv_dicts = create_cv_dicts(ress, columns)
    # logger.info('Dictionary created')
    #
    # cvs = CVS()
    #
    # pbar = tqdm(total=len(cv_dicts), desc='Processing CVs', ascii=True)
    # for key, value in cv_dicts.items():
    #     cv = CVperson.read_from_dict(idx=key, cv_dict=value)
    #     cvs.add_cv(cv)
    #     cvs.save(name='try_with_personclass_2', pkl_file=True, json_file=False)
    #     pbar.update(1)
    #
    # pbar.close()


    # for cv in cvs.get_cvs():
    #     print(str(cv))
    #     print('*********************************************************************************************')
    #
    # jaeger = Jaeger(cvs=cvs)
    #
    # keyws = ['python', 'java', 'c++', 'c#', 'javascript', 'html', 'css', 'sql']
    # keywords = Keywords(words=keyws, weights=[1*len(keyws)])
    # logger.info(f"Keywords created")
    #
    # logger.info("Executing search...")
    # results = search(jaeger_obj=jaeger, keywords_obj=keywords, filename='NOT_Result', show_results=True)
    # logger.info("Searching extracted!")
    #
    # df = pd.DataFrame.from_dict(results, orient='index')
    # print(df)

    # cursor.close()
    # conn.disconnect()

    # import os
    # from datetime import datetime, timedelta
    # import random
    #
    # # Directory dove creare i file
    # cartella = "source/test_datetime"
    #
    # # Assicurati che la directory esista
    # os.makedirs(cartella, exist_ok=True)
    #
    #
    # # Funzione per generare una data randomica entro un intervallo
    # def genera_data_randomica(data_inizio, data_fine):
    #     delta = data_fine - data_inizio
    #     giorni_random = random.randint(0, delta.days)
    #     return data_inizio + timedelta(days=giorni_random)
    #
    #
    # # Genera file con date randomiche
    # def genera_file_randomici(cartella, numero_file):
    #     data_inizio = datetime(2020, 1, 1)  # Inizio dell'intervallo
    #     data_fine = datetime(2024, 12, 31)  # Fine dell'intervallo
    #
    #     for _ in range(numero_file):
    #         # Genera una data casuale
    #         data_random = genera_data_randomica(data_inizio, data_fine)
    #
    #         # Formatta la data come stringa
    #         data_str = data_random.strftime("%d_%m_%Y")
    #
    #         # Nome del file
    #         nome_file = f"salvataggio_{data_str}.txt"
    #         percorso_file = os.path.join(cartella, nome_file)
    #
    #         # Scrivi un file di esempio
    #         with open(percorso_file, "w") as file:
    #             file.write(f"Questo è un file generato con data {data_str}.\n")
    #
    #     print(f"Generati {numero_file} file nella cartella '{cartella}'.")
    #
    #
    # # Genera 10 file di test
    # genera_file_randomici(cartella, 10)
    #
    # import os
    # from datetime import datetime
    #
    # # Directory dove si trovano i file
    # cartella = "source/test_datetime"
    #
    #
    # # Funzione per trovare il file con la data più recente
    # def trova_file_recente(cartella):
    #     file_data = []
    #
    #     # Itera sui file nella directory
    #     for nome_file in os.listdir(cartella):
    #         # Verifica se il file rispetta il formato desiderato
    #         if nome_file.startswith("archive_") and nome_file.endswith(".txt"):
    #             try:
    #                 # Estrai la parte della data dal nome del file
    #                 data_str = nome_file[len("archive_"):-4]  # Rimuove prefisso e ".txt"
    #
    #                 # Converte la stringa della data in un oggetto datetime
    #                 data = datetime.strptime(data_str, "%d_%m_%Y")
    #
    #                 # Salva il nome del file e la data in una lista
    #                 file_data.append((nome_file, data))
    #             except ValueError:
    #                 # Ignora i file che non rispettano il formato
    #                 continue
    #
    #     # Trova il file con la data più recente
    #     if file_data:
    #         file_recente = max(file_data, key=lambda x: x[1])  # Ordina per data
    #         return file_recente[0]
    #     else:
    #         return None
    #
    #
    # # Trova e stampa il file più recente
    # file_recente = trova_file_recente(cartella)
    # if file_recente:
    #     print(f"Il file più recente è: {file_recente}")
    # else:
    #     print("Nessun file valido trovato nella cartella.")

