from components.keywords import Keywords
from components.logger import logger
from components.cvs import CVS

from typing import Union
from tqdm import tqdm
import pandas as pd
import itertools
import json


class Engine:
    """
    A class to manage the processing of the system using the CVs and keywords.

    ...

    Attributes
    ----------
    cvs : CVS
        The CVS object containing all the CVs.
    keywords : Keywords
        The Keywords object containing all the keywords.
    results : dict
        A dictionary mapping CV identifiers to their scores.

    Methods
    -------
    run(bl: str) -> None:
        Processes all the CVs for a given skill, computes their scores, and stores them in the results.
    get_best_n(n: int = 20) -> dict[str, float]:
        Returns the top n CVs based on their scores.
    sort_results() -> dict:
        Returns the results sorted by scores.
    weighted_average(scores: list[float]) -> float:
        Computes the weighted average of the scores.
    """
    def __init__(self, cvs: 'CVS', keywords: 'Keywords') -> None:
        self.cvs = cvs
        self.keywords = keywords
        self.results = {}

    def __str__(self):
        return json.dumps(self.results, indent=4)

    def run_semantic(self, bl: str = None) -> None:
        """
        Processes all the CVs, filter them by a specific business_line, computes their scores referred wo a specific
        skill, and stores them in the results dictionary.

        :param bl: the business_line to filter the CVS [optional]

        :return: nothing, it stores the results in the results dictionary attribute of the class
        """
        if bl is None:
            pbar = tqdm(total=len(self.cvs), desc='Processing CVs', ascii=True)
            for cv in self.cvs.get_cvs():
                scores = cv.match_words(self.keywords.get_embedding())
                self.results[cv.get_idx()] = self.weighted_average(scores, self.keywords.get_weights())
                pbar.update(1)
            pbar.close()
            logger.info("Scoring and of CVs completed")
        else:
            pbar = tqdm(total=len(self.cvs), desc='Processing CVs', ascii=True)
            for cv in self.cvs.filter(bl):
                scores = cv.match_words(self.keywords.get_embedding())
                self.results[cv.get_idx()] = self.weighted_average(scores, self.keywords.get_weights())
                pbar.update(1)
            pbar.close()
        logger.info("Scoring and of CVs completed")

    def run_alike(self, bl: str = None) -> None:
        """
        Processes all the CVs, computes their scores with for the Alike system and stores them in the results dictionary

        :param bl: the business_line to filter the CVS [optional]

        :return: nothing
        """
        if bl is None:
            pbar = tqdm(total=len(self.cvs), desc='Processing CVs', ascii=True)
            for cv in self.cvs.get_cvs():
                scores = cv.match_text(self.keywords.get_words())
                self.results[cv.get_idx()] = round(sum(scores) / len(scores), 2)
                pbar.update(1)
            pbar.close()
        else:
            pbar = tqdm(total=len(self.cvs), desc='Processing CVs', ascii=True)
            for cv in self.cvs.filter(bl):
                scores = cv.match_text(self.keywords.get_words())
                self.results[cv.get_idx()] = sum(scores)
                pbar.update(1)
            pbar.close()
        logger.info("Scoring and of CVs with alike completed")

    def get_best_n(self, n: Union[int, str] = 20) -> dict[str, dict]:
        """
        Returns the top n CVs based on their scores with the basic information.

        :param n: the range of interest to return the top n CVs, default value is 20

        :return: dictionary of the top n CVs with the index, their scores and the information of the CVs;
                    if an error occurs, it returns None
        """
        try:
            sorted_results = self.sort_results(self.results)
            if n == 'ALL':
                return self.compile(self.normalize_scores(sorted_results))
            elif 1 <= n <= len(sorted_results):
                return self.compile(dict(itertools.islice(self.normalize_scores(sorted_results).items(), n)))
            else:
                raise Exception(f"Invalid value for n: {n}")
        except Exception as e:
            logger.error(f"Error in getting the top {n} CVs: {e}")

    def compile(self, results: dict) -> dict[str, dict]:
        """
        Function to compile the results of the CVs into a dictionary with all the
        potential useful information added.

        :param: results: dictionary of the CVs indices (str) and their scores (float) after
                the processing get_bet_n method

        :return: dictionary of the CVs with their scores + the main skill + the plain text of the CV;
                return an empty dictionary if a CV is missing.
        """
        enriched = {}
        for cv_idx, score in results.items():
            cv = self.cvs.get_cv(cv_idx)
            enriched[cv_idx] = {
                "score": score,
                "main_skill": cv.get_skill(),
                "cv_plain_text": cv.get_body()
            }
        return enriched

    @staticmethod
    def normalize_scores(scores: dict) -> dict:
        """
        Function to normalize the scores of the CVs.

        :param scores: values of the scores of the CVs

        :return: dictionary of the CVs with the normalized scores
        """
        lb = min(scores.values())
        ub = max(scores.values())

        range_scores = ub - lb

        norm_scores = {}
        for user, score in scores.items():
            norm_scores[user] = (score - lb) / range_scores if range_scores else 0
        return norm_scores

    @staticmethod
    def sort_results(results: dict) -> dict[str, float]:
        """
        Function to return the results sorted by scores.

        :param: results: dictionary of the CVs and their scores

        :return: dictionary of the CVs sorted by their scores
        """
        return {k: float(v) for k, v in sorted(results.items(), key=lambda item: item[1], reverse=True)}

    @staticmethod
    def weighted_average(scores: list[float], weights: list[float]) -> float:
        """
        Function to compute the weighted average of the scores with their weights.

        :param scores: list with the score for each keyword
        :param weights: list of weights for each keyword

        :return: the weighted average of the scores given the weights
        """
        avg = 0
        for score, weight in zip(scores, weights):
            avg += score * weight
        return avg / sum(weights)

    def export_results(self, filename: str, n: Union[int, str], to_xlsx: bool = True) -> None:
        """
        Saves the results of the CVs processing into a JSON file and optionally into a xlsx file.

        :param n: the value to pass to the get_best_n method
        :param filename: the name of the file (without extension) where to save the results
        :param to_xlsx: a flag to decide whether to save the results also in a xlsx file, default is False

        :return: nothing, it saves the results into a file
        """
        results = self.get_best_n(n=n)
        with open(f"results/json/{filename}.json", 'w') as f:
            json.dump(results, f, indent=4)

        if to_xlsx:
            df = pd.DataFrame(results).transpose()
            df.index.name = 'resource_code'  # Rename index column
            df['main_skill'] = df['main_skill'].apply(
                lambda x: x['main']
            )  # Extract 'main' value from 'main_skill' column
            df_skills = pd.DataFrame([(keyword, weight)
                                      for keyword, weight in zip(self.keywords.get_words(),
                                                                 self.keywords.get_weights())],
                                     columns=['Skill', 'Weight'])

            with pd.ExcelWriter(f"results/excel/{filename}.xlsx") as writer:
                df.to_excel(writer, sheet_name='Results')
                df_skills.to_excel(writer, sheet_name='Skills')
