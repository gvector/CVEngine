from altair import DateTime

from components.cv import CVperson
from components.logger import logger

from typing import Self, Union
from datetime import datetime
from tqdm import tqdm
import pickle
import json
import os


class CVS:
    """
    A class to represent the collection of CV objects.

    ...

    Attributes
    ----------
    cvs : list[CV]
        a list of CV objects

    Methods
    -------
    __len__():
        Returns the number of CV objects in the collection.
    __add__(other: CV | Self):
        Adds a CV object or another CVS object to the collection.
    __getitem__(idx: int):
        Returns the CV object at the specified index.
    __setitem__(idx: int, cv: CV):
        Sets the CV object at the specified index.
        delete(resource: str):
    Deletes the CV object with the specified resource.
    get_cvs():
        Returns the list of CV objects.
    dump():
        Returns a dictionary representation of the CVS object.
    save_json(filename: str):
        Saves the CVS object to a JSON file.
    load_from_json(filename: str):
        Loads a CVS object from a JSON file.
    """
    def __init__(self, cvs = None):
        if cvs is None:
            cvs = []
        self.cvs = cvs

    def __len__(self) -> int:
        return len(self.cvs)

    def __add__(self, other: CVperson | Self) -> 'CVS':
        """
        Add a CV object or another CVS object to the existing CVS collection.

        :param other: the CV or CVS object to add

        :return: the new CVS object
        """
        # if isinstance(other, CV):
        #     logger.debug("CV added to the CVs collection")
        #     return CVS(self.cvs.append(other))
        if isinstance(other, CVperson):
            logger.debug("CV added to the CVs collection")
            return CVS(self.cvs.append(other))
        elif isinstance(other, CVS):
            logger.debug("CVs added to the CVs collection")
            return CVS(self.cvs.extend(other.cvs))
        else:
            raise TypeError("other must be an instance of CV or CVS")

    def add_cv(self, cv: 'CVperson') -> None:
        """
        Add a CV object to the existing CVS collection.

        :param cv: the CV object to add
        """
        # if isinstance(cv, CV):
        #     self.cvs.append(cv)
        #     logger.debug("CV added to the CVs collection")
        if isinstance(cv, CVperson):
            self.cvs.append(cv)
            logger.debug("CV added to the CVs collection")
        else:
            raise TypeError("cv must be an instance of CV")

    def __setitem__(self, idx: int, cv: CVperson) -> None:
        self.cvs[idx] = cv

    def filter(self, skill: str) -> list['CVperson']:
        """
        Filter the collection of CVs by checking if they match with the wanted skill.

        :param skill: the skill to match

        :return: the list of CVs that match the skill
        """
        logger.debug(f"Filtering CVs with skill: {skill}")
        return [cv for cv in self.cvs if cv.match_skill(skill)]

    def alike_filter(self, words: list[str], threshold: int = 5) -> list[CVperson]:
        """
        Filter the collection of CVs by checking if they match with the wanted words.

        :param words: the words to match
        :param threshold: threshold to filter the CV based on alike search

        :return: the list of CVs that match the words
        """
        logger.info(f"Filtering CVs with words: {words} and threshold: {threshold}")
        return [cv for cv in self.cvs if sum(cv.match_text(words)) > threshold]

    def delete(self, resource: str) -> None:
        for cv in self.cvs:
            if cv.get_idx() == resource:
                logger.debug(f"Deleting CV {resource}")
                del cv

    def get_cvs(self) -> list['CVperson']:
        return self.cvs

    def get_cv(self, idx: str) -> Union['CV', 'CVperson', None]:
        try:
            if (not isinstance(idx, str)) or (len(idx) < 3):
                raise ValueError("idx must be a string of at least 3 characters")

            for cv in self.cvs:
                if cv.get_idx() == idx:
                    return cv
        except KeyError:
            logger.error(f"CV with index: {idx} not found")
            return None
        except IndexError:
            logger.error("CVS is empty")
            return None

    def get_cv_byname(self, name: str) -> Union['CVperson', None]:
        try:
            if isinstance(name, str):
                for cv in self.get_cvs():
                    if cv.get_resource_name() == name:
                        return cv
        except KeyError:
            logger.error(f"CV with name: {name} not found")
            return None

    def dump(self) -> dict:
        return {cv.get_idx(): {"fragment": cv.get_fragment(), "skill": cv.get_skill(), "body": cv.get_body()} for cv in self.cvs}

    def save_json(self, filename: str) -> None:
        json.dump(self.dump(), open("source/"+filename+'.json', "w"), indent=4)


    def save_pkl(self, filename: str) -> None:
        """
        Save the CVS object to a pickle file.

        :param filename: name of the fle where to save the object

        :return:nothing
        """
        try:
            with open("source/archive/"+filename+'.pkl', "wb") as f:
                pickle.dump(self.cvs, f)
        except pickle.PickleError:
            logger.error(f"Error to serialize the data {self.cvs} to the file {filename}")
        except Exception as e:
            logger.error(f"An error occurred: {e}")

    def save(self, name: str, pkl_file: bool = True, json_file: bool = True) -> None:
        """
        Save the CVS object to a pickle file and/or json file.

        :param name: name of the file where to save the object
        :param pkl_file: boolean to save the object to a pickle file
        :param json_file: boolean to save the object to a json file

        :return:nothing
        """
        if pkl_file:
            self.save_pkl(filename=name)
        if json_file:
            self.save_json(filename=name)

    @staticmethod
    def _search_most_recent() -> (str, datetime):
        file_data = []
        for file in os.listdir("source/archive"):
            if file.startswith("archive_") and file.endswith(".pkl"):
                try:
                    date_str = file[len("archive_"):-4]
                    date = datetime.strptime(date_str, "%d_%m_%Y")
                    file_data.append((file, date))
                except ValueError:
                    continue
        if file_data:
            recent = max(file_data, key=lambda x: x[1])
            logger.info(recent)
            return recent
        else:
            return None

    def load_pkl(self) -> None:
        """
        Load a CVS object from a pickle file.

        :param filename: name of the file from which to load the object

        :return:nothing
        """
        filename = self._search_most_recent()
        logger.info(filename[0])

        try:
            with open('source/archive/'+filename[0], 'rb') as f:
                data = pickle.load(f)
            self.cvs = data
            logger.info(f"File {filename[0]} loaded correctly")
        except FileNotFoundError:
            logger.error(f"No File found with name {filename[0]} for the path 'source/archive/{filename[0]}'")
        except pickle.UnpicklingError:
            logger.error(f"Error to deserialize the data from the file 'source/archive/{filename[0]}'")
        except Exception as e:
            logger.error(f"An error occurred: {e}")
