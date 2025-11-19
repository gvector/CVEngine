from components.constants import BertModel
from components.keywords import Keywords
from components.logger import logger
from components.cvs import CVS

from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import pandas as pd
import numpy as np
import pickle
import json


class Matrix:
    def __init__(self, file_Excel: str, exe_scale: bool):
        data = pd.read_excel(file_Excel, header=3)
        self.data = self._clean_table(data, exe_scale=exe_scale)
        self.bert_model = BertModel.GTE_LARGE
        embedding_model = SentenceTransformer(self.bert_model.value)
        self.embedding_map = self._create_embedding_map(model=embedding_model)

    def __str__(self):
        return f''' Matrix Object: {self.data.shape} \n
        Columns: {self.data.columns} \n
        embedding_map: {self.get_embedding_map()} \n
        Data Sample: {self.data.head(10)} \n'''

    @staticmethod
    def _clean_table(data: 'pd.DataFrame', exe_scale: bool) -> 'pd.DataFrame':
        data = data.iloc[:223]
        unnamed_cols = data.filter(like='Unnamed:').columns
        data = data.drop(columns=unnamed_cols)
        data = data.drop(columns=["Nome Risorsa"])
        data = data.set_index("Codice Risorsa")

        data.replace(['SI', 'si'], 5, inplace=True)
        data.replace(['NO', 'no'], 1, inplace=True)
        data.replace(['NA', 'X', 'N/A', 'nan', 'NaN', '\xa0', 'n/A', 'na'], 0, inplace=True)
        data.fillna(0, inplace=True)

        if exe_scale:
            def normalize(x):
                if x == 0:
                    return x
                else:
                    return round(1 + 4 * (x - 1) / (10 - 1))
            data = data.applymap(normalize)

        return data

    def _create_embedding_map(self, model: 'SentenceTransformer') -> dict[str, list[float]]:
        embedding_map = {}

        pbar = tqdm(total=len(self.data.columns), desc='Embedding Skills', ascii=True)
        for col in self.data.columns:
            embedding_map[col] = self._embed(model=model, skill=col)
            pbar.update(1)
        pbar.close()
        return embedding_map

    @staticmethod
    def _embed(model: 'SentenceTransformer', skill: str) -> list[float]:
        return model.encode(skill).tolist()

    def get_data(self) -> 'pd.DataFrame':
        return self.data

    def get_col(self) -> list[str]:
        return list(self.data.columns)

    def get_embed(self) -> dict[str, list[float]]:
        return self.embedding_map

    def get_embedding_map(self) -> str:
        return json.dumps(self.embedding_map, indent=4)

    def filter_data(self, key_extract: list[str]) -> 'pd.DataFrame':
        return self.data[key_extract]

    def sort_data(self, key_extract: list[str]) -> dict:
        print(key_extract)
        sorted_data = self.filter_data(key_extract).sort_values(by=key_extract, ascending=False)
        # return self.filter_data(key_extract).sort_values(by=key_extract, ascending=False)
        return sorted_data.to_dict(orient='index')

    @staticmethod
    def add_info(cvs: 'CVS', results: 'dict') -> dict:
        final_dict = {}
        for key, _ in results.items():
            cv = cvs.get_cv(idx=key)
            if cv is not None:
                final_dict[key] = {**results[key],
                                   **cv.person.to_dict()}
        return final_dict

    def save(self, filename: str) -> None:
        try:
            with open("source/" + filename + '.pkl', "wb") as f:
                pickle.dump(self, f)
        except pickle.PickleError:
            logger.error(f"Error to serialize the data {self} to the file {filename}")
        except Exception as e:
            logger.error(f"An error occurred: {e}")

    @classmethod
    def load(cls, filename: str) -> 'Matrix':
        try:
            with open("source/" + filename + '.pkl', "rb") as f:
                return pickle.load(f)
        except pickle.UnpicklingError:
            logger.error(f"Error to deserialize the data from the file {filename}")
        except Exception as e:
            logger.error(f"An error occurred: {e}")


if __name__ == '__main__':
    matrix = Matrix(file_Excel='source/matrix_ontology/CSV_Matrix.xlsx')
    print(matrix)
