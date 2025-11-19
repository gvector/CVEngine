from components.keywords import Keywords
from components.logger import logger
from components.matrix import Matrix
from components.cvs import CVS

from sklearn.metrics.pairwise import cosine_similarity
# from typing import Union
from tqdm import tqdm
# import pandas as pd
import numpy as np
# import json


class Jaeger:
    def __init__(self, cvs: CVS):
        self.cvs = cvs

    def run_semantic(self, keywords: 'Keywords', bl: str = None) -> dict:
        results = {}
        if bl is None:
            pbar = tqdm(total=len(self.cvs), desc='Processing CVs', ascii=True)
            for cv in self.cvs.get_cvs():
                results[cv.get_idx()] = np.average(a=cv.match_words(keywords.get_embedding()),
                                                   weights=keywords.get_weights())
                pbar.update(1)
        else:
            pbar = tqdm(total=len(self.cvs), desc='Processing CVs', ascii=True)
            for cv in self.cvs.filter(bl):
                results[cv.get_idx()] = np.average(a=cv.match_words(keywords.get_embedding()),
                                                   weights=keywords.get_weights())
                pbar.update(1)
            pbar.close()
        logger.debug("Scoring and of CVs completed")
        return results

    def run_alike(self, keywords: list[str], bl: str = None) -> dict:
        results = {}
        if bl is None:
            pbar = tqdm(total=len(self.cvs), desc=f'Processing CVs for {len(keywords)}', ascii=True)
            for cv in self.cvs.get_cvs():
                scores = cv.match_text(keywords)
                results[cv.get_idx()] = {k: v for k, v in scores.items()}
                # print(f"CV {cv.get_idx()} scored {scores}")
                pbar.update(1)
            pbar.close()
        else:
            pbar = tqdm(total=len(self.cvs), desc='Processing CVs', ascii=True)
            for cv in self.cvs.filter(bl):
                scores = cv.match_text(keywords)
                results[cv.get_idx()] = sum(scores)
                pbar.update(1)
            pbar.close()
        logger.debug("Scoring and of CVs with alike completed")
        return results

    @staticmethod
    def run_matrix(keywords: 'Keywords', matrix: 'Matrix') -> dict:
        """
        Function to compute the max similarity between the skill inserted and the ones present in the Matrix object

        :return:
        """
        key_extract = []
        for keyw in keywords.get_embedding():
            max_sim = -1
            max_key = None
            for key, embed in matrix.get_embed().items():
                logger.debug(keyw, key)
                similarity = cosine_similarity(np.array(keyw).reshape(1, -1), np.array(embed).reshape(1, -1))
                if similarity > max_sim:
                    max_sim = similarity
                    max_key = key
            key_extract.append(max_key)
        logger.debug(key_extract)
        return matrix.sort_data(key_extract)

    def sort_results(self, keywords: 'Keywords', bl: str = None) -> dict:
        results = self.run_semantic(keywords, bl)
        return {k: float(v) for k, v in sorted(results.items(), key=lambda item: item[1], reverse=True)}

    @staticmethod
    def sort_scoring(results: dict) -> dict:
        return dict(sorted(results.items(), key=lambda item: item[1], reverse=True))

    def normalize_scores(self, keywords: 'Keywords', bl: str = None, runtype: str = 'semantic') -> dict:
        if runtype == 'logic':
            return self.run_alike(keywords.get_words(), bl)
        else:
            results = self.run_semantic(keywords, bl)

        lb, ub, range_scores = min(results.values()), max(results.values()), max(results.values()) - min(
            results.values())
        for user, score in results.items():
            results[user] = (score - lb) / range_scores if range_scores else 0

        return self.sort_scoring(results)


    def compile_person(self, keywords: 'Keywords', bl: str = None, runtype: str = 'semantic') -> dict[str, dict]:
        enriched = {}
        if runtype == 'logic':
            results = self.normalize_scores(keywords, bl, runtype=runtype)
            for cv_idx, keyword_scores in results.items():
                cv = self.cvs.get_cv(cv_idx)
                aggregate_score = sum(keyword_scores.values())
                cv.set_score(aggregate_score)
                enriched[cv.get_idx()] = {
                    'score': aggregate_score,
                    **{keyword: score for keyword, score in keyword_scores.items()},
                    'body': cv.get_body(),
                    **cv.person.to_dict()
                }
            return enriched
        else:
            results = self.normalize_scores(keywords, bl)
        for cv_idx, score in results.items():
            cv = self.cvs.get_cv(cv_idx)
            cv.set_score(score)
            enriched[cv.get_idx()] = {'score': score,
                                      'body': cv.get_body(),
                                      **cv.person.to_dict()}
        return enriched

    def compile_matrix(self, keywords: 'Keywords', matrix: 'Matrix') -> dict[str, dict]:
        result = self.run_matrix(keywords=keywords, matrix=matrix)
        return matrix.add_info(cvs=self.cvs, results=result)

    def export_results(self, keywords: 'Keywords', matrix_obj: 'Matrix' = None, bl: str = None,
                       show: bool = False, runtype: str = 'semantic') -> dict[str, dict]:
        if show:
            match runtype:
                case 'semantic':
                    return self.compile_person(keywords)
                case 'logic':
                    return self.compile_person(keywords, bl, runtype=runtype)
                case 'matrix':
                    return self.compile_matrix(keywords=keywords, matrix=matrix_obj)
