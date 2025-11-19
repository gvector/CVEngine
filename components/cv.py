from components.constants import BertModel
from components.logger import logger
from components.person import Person
# from components.skill import Skill

from sklearn.metrics.pairwise import cosine_similarity
from langchain_text_splitters import TokenTextSplitter
from sentence_transformers import SentenceTransformer
# from fuzzysearch import find_near_matches
from transformers import AutoTokenizer
from typing import Union


class CVperson:
    def __init__(self, idx: str, body: str, person: 'Person', fragments: list[list[float]] = None):
        self.idx = idx
        self.body = body
        self.person = person
        self.bert_model = BertModel.GTE_LARGE
        embedding_model = SentenceTransformer(self.bert_model.value)
        if fragments is None:
            self.fragments = self.embed(embedding_model, self.split(text=body, model=self.bert_model.value))
        else:
            self.fragments = fragments

    def __str__(self):
        return f''' Resource_Code: {self.idx}
                    CV: {self.body[:25]}... 
                    CV body Fragments: {len(self.fragments)} 
                    Person Information: {self.person.present_person()} 
                    '''

    def __get__(self, idx: str) -> str:
        return self.body

    @staticmethod
    def split(text: str, model: str) -> list[str]:
        """
        Split the text into fragments based on the maximum token length of the model (512 token for GTE Large model)

        :param text: the text of the CV needed to be split
        :param model: the model used for Tokenization and Embedding

        :return: the list of string fragments
        """
        tokenizer = AutoTokenizer.from_pretrained(model)
        text_splitter = TokenTextSplitter.from_huggingface_tokenizer(
            tokenizer, chunk_size=128, chunk_overlap=50
        )
        logger.debug(f"Text split into {len(text_splitter.split_text(text))} fragments")
        return text_splitter.split_text(text)

    @staticmethod
    def embed(model, docs: list[str]) -> list[list[float]]:
        """
        Embed the list of fragments using the Sentence Transformer model

        :param model: the Model to use for the embedding
        :param docs: the list of fragments to embedded

        :return: the list of embedded fragments represented in float list values
        """
        embedded_docs = []
        for doc in docs:
            embedded_docs.append(model.encode(doc))
        logger.debug("CV embedding completed")
        return [arr.tolist() for arr in embedded_docs]

    def match_words(self, words: list[list[float]]) -> list[float]:
        """
        Compute the similarity of each words with all the fragments of the CV and return a list of similarity values

        :param words: list of float list values representing the list of word embeddings

        :return: list of float values representing the similarity values
        """

        similarities = cosine_similarity(words, self.fragments)
        return similarities.max(axis=1)

    def match_business_line(self, bl: str) -> bool:
        """
        Check if the CV contains the required skill

        :param bl: str representing the required skill

        :return: bool value representing the presence of the skill in the CV
        """
        try:
            if self.person.get_coe():
                return bl == self.person.get_coe()
        except ValueError:
            logger.error(f"Skill {bl} is not a valid skill.")

    def find_in_text(self, un_embedded_word: str) -> int:
        """
        Check if the CV contains the required text with the .find() method and returns the index
        of the first occurrence

        :param un_embedded_word: string of the word to search for in the CV

        :return: integer from [-1; len(CV)] for the index of the first occurrence of the word
        """
        return 1 if un_embedded_word.lower() in self.body.lower() else 0

    def match_text(self, un_embedded_words: list[str] | str) -> dict[str, int]:
        """
        Check if the CV contains the required list of words

        :param un_embedded_words: list of words to look-up in the CV object

        :return: List of 1s representing the presence of the words in the CV
        """
        res = {}
        if isinstance(un_embedded_words, str):
            un_embedded_words = [un_embedded_words]
        for word in un_embedded_words:
            res[word] = self.find_in_text(word)
        return res

    def set_score(self, score: float) -> None:
        self.score = score

    def get_score(self) -> float:
        return self.score

    def get_idx(self) -> str:
        return self.idx

    def get_fragment(self):
        return self.fragments

    def get_body(self) -> str:
        return self.body

    def get_information(self) -> dict:
        return self.person.present_person()

    def get_resource_name(self) -> str:
        return self.person.get_name()

    def get_resume_date(self) -> str:
        return self.person.get_resume_date()

    def to_dict(self):
        return self.__dict__

    @classmethod
    def read_from_dict(cls, idx: str, cv_dict: dict):
        info = {}

        for key, value in cv_dict.items():
            match key:
                case "cv_plain_text":
                    body = value
                case _:
                    info[key] = value

        return cls(idx=idx, body=body, person=Person.load_from_dict(info))
