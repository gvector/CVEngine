import docx2txt
import warnings
import json


warnings.filterwarnings("ignore")


class Reader:
    def __init__(self, file_path):
        self.file_path = file_path
        self.raw_data = None
        self.data = None

    def convert_doc_to_txt(self):
        self.raw_data = docx2txt.process(self.file_path)

    def read_file(self):
        self.data = self.raw_data.read()
        raise Exception("File Path not Valid")

    def get_data(self):
        return self.data

    def get_raw_data(self):
        return self.raw_data

    def run_extraction(self, destination: str, chain):
        answer = chain.run(self.raw_data)["data"]
        json.dump(answer, open(destination, 'w'), indent=2)
