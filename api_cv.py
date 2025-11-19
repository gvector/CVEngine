from components.summarizer import SummaryManager
from components.keywords import Keywords
from components.matrix import Matrix
from components.logger import logger
from components.jaeger import Jaeger
from components.llm import GptLLM
from components.cvs import CVS

from fastapi import FastAPI
from typing import Union
import warnings
import uvicorn
import json
import os


app = FastAPI()


warnings.filterwarnings("ignore")


cvs = CVS()
cvs.load_pkl()

jaeger = Jaeger(cvs=cvs)

llm = GptLLM(api_key=os.getenv('API_KEY'))
llm_summary = GptLLM(api_key=os.getenv('API_KEY'), model='gpt-4o-mini')

summary_manager = SummaryManager(file_name='llm_resources_summary.json')


# matrix_cq = Matrix('source/matrix_ontology/C&Q_Matrix.xlsx', exe_scale=False)
# matrix_cq.save('cq_matrix')
# print("Matrix cq saved")
# matrix_csv = Matrix('source/matrix_ontology/CSV_Matrix.xlsx', exe_scale=True)
# matrix_csv.save('csv_matrix')
# print("Matrix csv saved")
# matrix_les = Matrix('C:\\Users\msd\PycharmProjects\CV-GPT\source/matrix_ontology/LES_Matrix.xlsx', exe_scale=True)
# matrix_les.save('les_matrix')
# print("Matrix les saved")
# matrix_gcp = Matrix(file_Excel='C:\\Users\msd\PycharmProjects\CV-GPT\source\matrix_ontology\GCP_Matrix.xlsx', adjust=True)
# matrix_gcp.save('gcp_matrix')
# print("Matrix gcp saved")
# matrix_ra = Matrix(file_Excel='C:\\Users\msd\PycharmProjects\CV-GPT\source\matrix_ontology\RA_Matrix.xlsx')
# matrix_ra.save('ra_matrix')
# print("Matrix RA saved")
# matrix_comp = Matrix(file_Excel='C:\\Users\msd\PycharmProjects\CV-GPT\source\matrix_ontology\COMP_Matrix.xlsx', exe_scale=True)
# matrix_comp.save('comp_matrix')
# print("Matrix COMP saved")
# matrix_dg = Matrix(file_Excel='C:\\Users\msd\PycharmProjects\CV-GPT\source\matrix_ontology\DG_Matrix.xlsx')
# matrix_dg.save('dg_matrix')
# print("Matrix DG saved")
# matrix_md = Matrix(file_Excel='C:\\Users\msd\PycharmProjects\CV-GPT\source\matrix_ontology\MD_Matrix.xlsx')
# matrix_md.save('md_matrix')
# print("Matrix MD saved")
# matrix_pv = Matrix(file_Excel='C:\\Users\msd\PycharmProjects\CV-GPT\source\matrix_ontology\PV_Matrix.xlsx')
# matrix_pv.save('pv_matrix')
# print("Matrix PV saved")
# matrix_eng = Matrix(file_Excel='C:\\Users\msd\PycharmProjects\CV-GPT\source\matrix_ontology\ENG_Matrix.xlsx')
# matrix_eng.save('eng_matrix')
# print("Matrix ENG saved")


matrix_csv = Matrix.load('csv_matrix')
matrix_cq = Matrix.load('cq_matrix')
matrix_les = Matrix.load('les_matrix')
matrix_gcp = Matrix.load('gcp_matrix')
matrix_ra = Matrix.load('ra_matrix')
matrix_comp = Matrix.load('comp_matrix')
matrix_dg = Matrix.load('dg_matrix')
matrix_md = Matrix.load('md_matrix')
matrix_pv = Matrix.load('pv_matrix')
matrix_eng = Matrix.load('eng_matrix')


@app.get("/keywords/")
def keywords_list(skills: dict) -> dict:
    keywords = Keywords(skills['list_skills'], [1]*len(skills['list_skills']))
    logger.info(f"Executed Semantic search")
    return search(keywords=keywords, runtype='semantic')


@app.get("/get_ontology/")
def ontology(CoE_matrix: dict) -> dict:
    """
    Function used in the 1_Semantic poage and 4_Matrix page ot get the skill contained in the matrix as Ontology

    :param CoE_matrix: list of string of the skills

    :return: a dictionary with te list of skills as value
    """
    match CoE_matrix['coe_name']:
        case 'PV':
            return {'ontology': matrix_pv.get_col()}
        case 'LES':
            return {'ontology': matrix_les.get_col()}
        case 'C&Q':
            return {'ontology': matrix_cq.get_col()}
        case 'CSV':
            return {'ontology': matrix_csv.get_col()}
        case 'GCP':
            return {'ontology': matrix_gcp.get_col()}
        case 'RA':
            return {'ontology': matrix_ra.get_col()}
        case 'COMP':
            return {'ontology': matrix_comp.get_col()}
        case 'DG':
            return {'ontology': matrix_dg.get_col()}
        case 'MD':
            return {'ontology': matrix_md.get_col()}
        case 'ENG':
            return {'ontology': matrix_eng.get_col()}
        case 'ALL':
            return {'ontology': list(set(matrix_les.get_col()
                                         + matrix_cq.get_col()
                                         + matrix_csv.get_col()
                                         + matrix_gcp.get_col()
                                         + matrix_ra.get_col()
                                         + matrix_comp.get_col()
                                         + matrix_dg.get_col()
                                         + matrix_md.get_col()
                                         + matrix_pv.get_col()
                                         + matrix_eng.get_col()
                                         )
                                     )
                    }


@app.get("/coe/")
def coe(CoE: dict) -> dict:
    """
    End Point to search in the 3_Ontology page the resources based on the CoE selected

    :param CoE: the name of the CoE selected which refers to the list of skills to use

    :return: dictionary containing the resources and the score
    """
    logger.info(f"Executed Ontologic search for {CoE['coe_name']}")
    match CoE['coe_name']:
        case '**PV**':
            keywords = matrix_pv.get_col()
            return search(keywords=keywords, runtype='semantic')
        case '**C&Q**':
            keywords = matrix_cq.get_col()
            return search(keywords=keywords, runtype='semantic')
        case '**CSV**':
            keywords = matrix_csv.get_col()
            return search(keywords=keywords, runtype='semantic')
        case '**LES**':
            keywords = matrix_les.get_col()
            return search(keywords=keywords, runtype='semantic')
        case '**GCP**':
            keywords = matrix_gcp.get_col()
            return search(keywords=keywords, runtype='semantic')
        case '**RA**':
            keywords = matrix_ra.get_col()
            return search(keywords=keywords, runtype='semantic')
        case '**COMP**':
            keywords = matrix_comp.get_col()
            return search(keywords=keywords, runtype='semantic')
        case '**DG**':
            keywords = matrix_dg.get_col()
            return search(keywords=keywords, runtype='semantic')
        case '**MD**':
            keywords = matrix_md.get_col()
            return search(keywords=keywords, runtype='semantic')
        case '**ENG**':
            keywords = matrix_eng.get_col()
            return search(keywords=keywords, runtype='semantic')


@app.get("/matrix/")
def matrix(skill: dict) -> dict[str, dict]:
    """
    End Point to search in the 4_Matrix page the resources based on the list of skills selected and the
    CoE representing the matrix where to sort the resources

    :param skill: dictionary containing the list of skills and the CoE name

    :return: dictionary with the resources and the score for the specific Skills
    """
    return search(keywords=skill['list_skills'][0], runtype='matrix', matrix_type=skill['list_skills'][1])


@app.get('/logic/')
def logic(keywords: dict) -> dict:
    """
    End Point to search in the 2_Logic page the resources based on the list of skills inserted by the user

    :param keywords: list of skills contained in a dictionary

    :return: dictionary with the resources and the score addressed to the specific skills
    """
    return search(keywords=keywords['list_skills'], runtype='logic')


def search(keywords: Union['Keywords', dict, list[str]], runtype: str, matrix_type: str = None) -> dict:
    if isinstance(keywords, dict):
        key_names, weights = keywords.keys(), keywords.values()
        keywords = Keywords(list(key_names), list(weights))
    if isinstance(keywords, list):
        keywords = Keywords(keywords, [1]*len(keywords))
    match runtype:
        case 'semantic':
            return jaeger.export_results(keywords=keywords, show=True, runtype='semantic')
        case 'logic':
            logger.info(f"Executed Logic search")
            print(keywords)
            return jaeger.export_results(keywords=keywords, show=True, runtype='logic')
        case 'matrix':
            logger.info(f"Executed Matrix search for {matrix_type}")
            match matrix_type:
                case 'C&Q':
                    return jaeger.export_results(keywords=keywords, show=True,
                                                 runtype='matrix', matrix_obj=matrix_cq)
                case 'PV':
                    return jaeger.export_results(keywords=keywords, show=True,
                                                 runtype='matrix', matrix_obj=matrix_pv)
                case 'CSV':
                    return jaeger.export_results(keywords=keywords, show=True,
                                                 runtype='matrix', matrix_obj=matrix_csv)
                case 'GCP':
                    return jaeger.export_results(keywords=keywords, show=True,
                                                 runtype='matrix', matrix_obj=matrix_gcp)
                case 'DG':
                    return jaeger.export_results(keywords=keywords, show=True,
                                                 runtype='matrix', matrix_obj=matrix_dg)
                case 'COMP':
                    return jaeger.export_results(keywords=keywords, show=True,
                                                 runtype='matrix', matrix_obj=matrix_comp)
                case 'LES':
                    return jaeger.export_results(keywords=keywords, show=True,
                                                 runtype='matrix', matrix_obj=matrix_les)
                case 'ENG':
                    return jaeger.export_results(keywords=keywords, show=True,
                                                 runtype='matrix', matrix_obj=matrix_eng)
                case 'RA':
                    return jaeger.export_results(keywords=keywords, show=True,
                                                 runtype='matrix', matrix_obj=matrix_ra)



@app.get('/names/')
def code(resource: dict) -> dict[str, str]:
    """
    End Point to get the Summary of the resource selected by the Name

    :param resource: the name of the resources selected by the user

    :return: dictionary containing the resource name and the summary by the LLM model
    """
    logger.debug(f"'Resource Selected: {cvs.get_cv_byname(resource['name'])}'")
    if summary_manager.check_infos(cv=cvs.get_cv_byname(resource['name'])):
        logger.info(f"Summary found for {resource['name']}")
        return {'answer': summary_manager.get_summary(resource_key=resource['name'])}

    llm_answer, *_ = llm_summary.get_answer(cvs.get_cv_byname(resource['name']))
    summary_manager.save_summary(cv=cvs.get_cv_byname(resource['name']), summary=llm_answer)
    logger.info(f"Summary produced for {resource['name']}")
    return {'answer': llm_answer}


@app.get('/extract/')
def extract(jobpost: dict) -> dict:
    """
    End Point used in the 1_Semantic page to extract the Skills from the text inserted by the user
    via the file_iploader or the text_area

    :param jobpost:  the file in txt format to be passed to the extractor

    :return: dictionary containing the list of skills extracted from the text and a default evaluation of 0.5
    """
    answer, *_ = llm.get_skill(jobpost_txt=jobpost['text'])
    return json.loads(answer)


@app.get('/info/')
def info() -> dict:
    """
    End Point that return all the resources by name-id and cv

    :return: dictionary with the ids and the cvs of the resources
    """
    return {'ids': [cv.get_idx() for cv in cvs.get_cvs()],
            'names': [cv.person.resource_name for cv in cvs.get_cvs()]}


import csv


if "feedback.csv" in os.listdir("resources"):
    feedback_file = open(os.path.join("resources", "feedback.csv"), "a")
else:
    feedback_file = open(os.path.join("resources", "feedback.csv"), "w")
    feedback_file.write("research_type,feedback,note, search_info\n")

writer_feedback = csv.writer(feedback_file)


@app.post("/send_feedback/")
def send_feedback(research_type: str, feedback: int, note: str, search_info: str):
    writer_feedback.writerow([research_type, feedback, note, search_info])
    feedback_file.flush()
    logger.info("feedback sent and saved")



if __name__ == "__main__":
    uvicorn.run(app=app, port=8001, host='10.1.2.97')
