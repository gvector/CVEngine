class Validator:
    """
   The Validator class provides methods for data validation. These methods can be used to verify
   that the data is of the correct type, is not empty, is present in a dictionary, or meets certain conditions.

   Methods:
       validate_string(value: Any) -> None:
           Checks that the value is a non-empty string. Raises a ValueError exception if it is not.

       validate_in_dictionary(value: Any, dictionary: dict) -> None:
           Checks that the value is a key in the provided dictionary. Raises a ValueError exception if it is not.

       validate_int(value: Any) -> None:
           Checks that the value is an integer between 1 and 10. Raises a ValueError exception if it is not.

       validate_keywords(words: list[str], weights: list[int]) -> None:
           Checks that the lists of words and weights have the same length and that each word is a non-empty string and each weight is an integer between 1 and 10.

       validate_idx(idx: str) -> None:
           Checks that the index is a non-empty string of at least 3 characters in length.
       """

    # Validator Methods for Skill Class (skill), Keywords Class (words), and SQLManager Class (query)
    @staticmethod
    def validate_string(value) -> None:
        """
        Methods for the Skill Class (main_skill), Keywords Class (words), and SQLManager Class (query) to validate the string type.

        :param value: the string to be validated for the type and the non-emptiness
        """
        if not isinstance(value, str) or len(value) == 0:
            raise ValueError(f"{value} is not a valid type, it must be a non-empty String.")

    @staticmethod
    def validate_in_dictionary(value, dictionary) -> None:
        """
        Methods for the Skill class (main_skill) to verify that a value is in the keys of a dictionary.

        :param value: the value to be searched in
        :param dictionary: the dictionary where to search the value
        """
        if value not in dictionary:
            raise ValueError(f"'{value}' is not a valid key for the dictionary {dictionary}.")

    @staticmethod
    def validate_int(value) -> None:
        """
        Methods for the Skill class (score), Keywords class (weights) to validate the integer type.

        :param value: the integer to be validated for the type and the range
        """
        if (not isinstance(value, int)) or (not 1 <= value <= 10):
            raise ValueError(f"{value} is not a valid weight, it must be an integer between 1 and 10.")

    # Validator Methods for Keywords Class
    def validate_keywords(self, words: list[str], weights: list[int]) -> None:
        """
        Methods for the Keywords class to validate the words and the weights lists before the constructor.

        :param words: list of words to be validated as string type
        :param weights: list of weights to be validated as integer type
        """
        if len(words) != len(weights):
            raise ValueError("The number of words and weights must be the same!")
        else:
            for word, weight in zip(words, weights):
                self.validate_string(word)
                self.validate_int(weight)

    # Validator Methods for CV Class
    def validate_idx(self, idx: str) -> None:
        """
        Methods for the CV class to validate the initial data in the constructor adre valid indices

        :param idx: value to be validated as string with the validate_string method and for the length of at least 3 characters
        """
        if not self.validate_string(idx) or len(idx) < 3:
            raise ValueError(f"Invalid idx [{idx}].")

    @staticmethod
    def validate_saving(path: str, filename: str) -> None:
        """
        Validate the path and the filename for saving the results.

        :param path: the finale path the file should follow
        :param filename: the filename of the saved results

        :return: nothing
        """
        Validator.validate_string(filename)
        if filename != path:
            raise ValueError(f"Filename {filename} is not valid.")
