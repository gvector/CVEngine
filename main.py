from components.cv import CV
from components.cvs import CVS
from components.skill import Skill
from components.logger import logger
from components.jaeger import Jaeger
from components.processor import Reader
from components.keywords import Keywords
from components.llm import GptLLM
from components.sql_connector import SQLManager

from tqdm import tqdm
import json
import os


def load_database(db_obj: 'SQLManager', file_db: str) -> dict:
    if os.path.exists(f'source/{file_db}'):
        db_dict = db_obj.load(filename=file_db)
        logger.info("Database loading completed")
    else:
        db_dict = db_obj.execute(limited=False)
        logger.info("Database extraction completed")
        db_obj.save(results=db_dict, filename=file_db)
        logger.info(f"Query results saved to {file_db}")

    return db_dict


def create_archive(db_dictionary: dict, filename: str) -> None:
    pbar = tqdm(total=len(db_dictionary), desc='Processing CVs', ascii=True)
    count = 0
    for idx, item in db_dictionary.items():
        cvs.add_cv(CV(idx=idx,
                      body=item['cv'],
                      skill=Skill(item['skill'])))
        if count % 10 == 0:
            cvs.save(name=filename)
        count += 1
        pbar.update(1)
    pbar.close()
    logger.info("CVs Archive created")
    logger.debug(f"CVs collection: {str(cvs.get_cvs())}")
    cvs.save(name=filename)
    logger.info(f"CVs collection saved")


def search(jaeger_obj: 'Jaeger', keywords_obj: 'Keywords', filename: str, bl: str = None, show_results: bool = False) -> None:
    logger.info(f"Engine created")
    results = jaeger_obj.export_results(filename=filename, keywords=keywords_obj, bl=bl, to_xlsx=False, show=show_results)
    logger.info(f"Top CVs extracted and saved to {filename}")

    if show_results:
        logger.info(json.dumps(results, indent=4))


if __name__ == '__main__':

    # db = SQLManager(host='localhost', user='root', password='', database='test')
    # db.connect()
    #
    # # filename_db = 'db_complete.json'
    # #
    # # if os.path.exists(f'source/{filename_db}'):
    # #     db_dict = db.load(filename=filename_db)
    # #     logger.info("Database loading completed")
    # # else:
    # #     db_dict = db.execute(query=query, limited=False)
    # #     logger.info("Database extraction completed")
    # #     db.save(results=db_dict, filename=filename_db)
    # #     logger.info(f"Query results saved to {filename_db}")
    #
    # db_dict = load_database(db_obj=db, file_db='db_complete.json')
    # logger.info('Loading the database')
    #
    # cvs = CVS()
    # filename_cvs = 'cvs_complete_128'
    #
    # if os.path.exists('source/'+filename_cvs+'.json') or os.path.exists('source/'+filename_cvs+'.pkl'):
    #     cvs.load_pkl(filename=filename_cvs)
    #     logger.info(f"CVs collection loaded. Length: {len(cvs)}")
    # else:
    #     create_archive(db_dictionary=db_dict, filename=filename_cvs)
    # # else:
    # #     pbar = tqdm(total=len(db_dict), desc='Processing CVs', ascii=True)
    # #     count = 0
    # #     for idx, item in db_dict.items():
    # #         body = item['cv']
    # #         skill = Skill(item['skill'])
    # #         cv = CV(idx=idx, body=body, skill=skill)
    # #         logger.debug(f"CV collection: {str(cv)}")
    # #         cvs.add_cv(cv)
    # #         if count % 10 == 0:
    # #             cvs.save_json(filename=filename_cvs)
    # #             cvs.save_pkl(filename=filename_cvs)
    # #         count += 1
    # #         pbar.update(1)
    # #     pbar.close()
    # #     logger.info("CVs collection completed")
    # #     logger.debug(f"CVs collection: {str(cvs.get_cvs())}")
    # #
    # #     cvs.save_json(filename=filename_cvs)
    # #     cvs.save_pkl(filename=filename_cvs)
    # #     logger.info(f"CVs collection saved")
    #
    # jaeger = Jaeger(cvs=cvs)
    #
    # keywords = Keywords.load(filename='keywords_pv.json')
    # logger.info(f"Keywords created")
    #
    # logger.info("Executing search...")
    # search(jaeger_obj=jaeger, keywords_obj=keywords, filename='results_pv_test', show_results=True)
    # logger.info("Searching extracted!")
    #
    # logger.info(f"Summarizing the CV of ROD: \n")
    # api_key = os.getenv('API_KEY')
    # llm_gpt = GptLLM(api_key=api_key)
    # llm_answer, *_ = llm_gpt.get_answer(cvs.get_cv('ROD'))
    # print(f"Summary Extracted: \n{llm_answer}\n")

    reader = Reader(file_path='C.docx')
    reader.convert_doc_to_txt()

    llm = GptLLM(api_key=os.getenv('API_KEY'))
    answer, *_ = llm.get_skill(jobpost=reader.get_raw_data())
    print(json.dumps(answer, indent=4))
