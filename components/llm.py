from components.cv import CVperson

from abc import ABC, abstractmethod
from openai import OpenAI
from typing import Union
import json

class LLM(ABC):
    def __init__(self, api_key: str, model: str, temperature: float = 0.0):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature

    def get_model_name(self) -> str:
        return self.model

    @abstractmethod
    def get_response(self, message: str) -> (str, int, int):
        pass

    @abstractmethod
    def update_api_key(self, api_key: str) -> None:
        pass

    def get_answer(self, cv_selected: 'CVperson') -> (str, int, int):
        input_message = self.get_message(cv=cv_selected)
        output_message, input_token, output_token = self.get_response(input_message)
        return output_message, input_token, output_token

    def get_answer_india(self, cv_text: str) -> (str, int, int):
        input_message = self.get_message_india(cv=cv_text)
        output_message, input_token, output_token = self.get_response(input_message)
        return output_message, input_token, output_token

    def get_skill(self, jobpost_txt: str) -> (str, int, int):
        input_message = self.get_skill_requested(jobpost=jobpost_txt)
        output_message, input_token, output_token = self.get_response(input_message)
        return output_message, input_token, output_token

    @staticmethod
    def get_message(cv: 'CVperson') -> str:
        # message = f"Extract the areas of competence from this person\'s CV. The areas of competence must be for which the person is an expert. There must be a maximum of 6 areas, order them from most important to least important based on the information in the CV: {cv.get_body()}\n"
        message = f"Extract the areas of competence from the CV of the person. The areas of competence must be those for which the person has expertise. The areas must be ordered and numbered from most important to least important according to the information in the CV. Do not include personal comments, but list the areas together with a brief summary of the CV. CV= {cv.get_body()}\n"
        return message

    @staticmethod
    def get_message_india(cv: str) -> str:
        message = f"Extract the areas of competence from this person\'s CV. The areas of competence must be for which the person is an expert. There must be a maximum of 6 areas, order them from most important to least important based on the information in the CV: {cv}\n"
        return message

    @staticmethod
    def get_skill_requested(jobpost: str) -> str:
        message = f"Extract the skills strictly required for the following job post. Return the result in JSON format under the unique key 'skills'. Ingore the languages requirements and the year of experiences. Job post: {jobpost}\n"
        return message


class GptLLM(LLM):

    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo-0125", temperature: float = 0.0):
        super().__init__(api_key=api_key, model=model, temperature=temperature)
        self.client = OpenAI(api_key=api_key)

    def get_response(self, message: str) -> (str, int, int):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": message
                },
            ],
            temperature=self.temperature,
        )
        return response.choices[0].message.content, response.usage.prompt_tokens, response.usage.completion_tokens

    def update_api_key(self, api_key: str) -> None:
        if len(api_key) == 51 and api_key.startswith("sk-"):
            self.api_key = api_key
            self.client = OpenAI(api_key=api_key)
        else:
            raise ValueError(f"API key not valid for {self.model}")
