from components.logger import logger
from components.constants import BertModel

from sentence_transformers import SentenceTransformer
import pickle
import json


class Keywords:
    """
    A class to represent a collection of keywords and their weights for text matching.

    ...                     

    Attributes
    ----------
    bert_model : instruction of the model used for the embedding by the
        SentenceTransformer constant
    embedded_words : dict
        a dictionary of keywords and their corresponding embeddings and weights
    weights : list[float]
        a list of weights corresponding to the keywords

    Methods
    -------
    __str__():
        Returns a string representation of the Keywords object.
    get_embedded_word(word: str = None, weight: float = None):
        Returns the embeddings of the keywords. If a word is provided, it is added to the embedded_words.
    get_weights():
        Returns the weights of the keywords.
    get_words():
        Returns the keywords.
    update_weights(word: str, weight: float):
        Updates the weight of a keyword.
    update_words(old_word: str, new_word: str):
        Updates a keyword.
    """
    def __init__(self, words: list[str], weights: list[float]) -> None:
        self.bert_model = BertModel.GTE_LARGE
        embedding_model = SentenceTransformer(self.bert_model.value)
        self.embedded_words = {word: {'embedding': embedding_model.encode(word).tolist(),
                                      'weight': weight} for word, weight in zip(words, weights)}
        self.weights = weights

    def __len__(self) -> int:
        return len(self.embedded_words)

    def __str__(self):
        # return json.dumps(self.__dict__, indent=4)
        return '\n'.join(f"Keyword: {keyword} --- Weight: {weight['weight']}"
                         for keyword, weight in self.embedded_words.items())

    def get_embedding(self) -> list[list[float]]:
        return list(word['embedding'] for word in self.embedded_words.values())

    def get_embedded_word(self, word: str = None, weight: float = None) -> list[list[float]]:
        """
        Embed the new word given with the corresponding weight and add to the dictionary of embedded words.

        :param word: the skill to match
        :param weight: the weight of the skill

        :return: nothing
        """
        if word:
            if word not in self.embedded_words:
                embedding_model = SentenceTransformer(self.bert_model.value)
                self.embedded_words.update({word: {'embedding': embedding_model.encode(word), 'weight': weight}})
                return self.embedded_words[word]['embedding']
            else:
                logger.error(f"Word {word} already present in the collection")
        else:
            logger.warning("No word provided")

    def get_weights(self) -> list[float]:
        return list(d['weight'] for d in self.embedded_words.values())

    def get_words(self) -> list[str]:
        return list(self.embedded_words.keys())

    def update_weights(self, word: str, weight: float) -> None:
        """
        Update the weight of a keyword.

        :param word: the keyword to which update the weight
        :param weight: new weight to be assigned to the keyword

        :return: nothing
        """
        if word in self.embedded_words and 0.0 < weight <= 1.0:
            logger.debug(f"Updating weight of {word} from {self.embedded_words[word]['weight']} to {weight}")
            self.embedded_words[word]['weight'] = weight

    def update_words(self, old_word: str, new_word: str) -> None:
        """
        Update a keyword.

        :param old_word: the keyword already present to be updated
        :param new_word: the new keyword with which update the old one and to be embedded

        :return: nothing
        """
        if old_word in self.embedded_words:
            _ = self.get_embedded_word(new_word, self.embedded_words[old_word]['weight'])
            logger.debug(f"Updating word from {old_word} to {new_word}")
            del self.embedded_words[old_word]

    @classmethod
    def load(cls, filename: str) -> 'Keywords':
        """
        Load a Keywords object from a Json file.

        :param filename: the name of the file to load

        :return: a Keywords object
        """
        with open(f"source/keywords/{filename}", 'r') as f:
            data = json.load(f)

        words = [word for word in data.keys()]
        weights = [data[word]['weights'] for word in data.keys()]

        return cls(words=words, weights=weights)

    def save_pickle(self, filename: str) -> None:
        """
        Save the Keywords object to a pickle file.

        :param filename: the name of the file to save
        """
        with open(filename, 'wb') as f:
            pickle.dump(self, f)

    @classmethod
    def load_pickle(cls, filename: str) -> 'Keywords':
        """
        Load a Keywords object from a pickle file.

        :param filename: the name of the file to load

        :return: a Keywords object
        """
        with open("source/keywords/"+filename, 'rb') as f:
            return pickle.load(f)

    @classmethod
    def load_from_dashboard(cls, keywords: list[str]) -> 'Keywords':
        """
        Load a Keywords object from a list of keywords.

        :param keywords: a list of keywords obtained from the dashboard

        :return: a Keywords object
        """
        return cls(words=keywords, weights=[1.0 for _ in keywords])
