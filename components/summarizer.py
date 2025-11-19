from components.cv import CVperson

from datetime import datetime
import json
import os


class SummaryManager:
    def __init__(self, file_name: str):
        self.file_path = 'source/summaries/' + file_name
        self.summary = self.load_summary_file()

    def load_summary_file(self) -> dict:
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as file:
                return json.load(file)
        return {}

    def save_summary_file(self):
        with open(self.file_path, 'w') as file:
            json.dump(self.summary, file, indent=4)

    def get_summary(self, resource_key: str) -> str:
        return self.summary[resource_key]['summary']

    def get_date(self, resource_key: str) -> str:
        return self.summary[resource_key]['resume_date']

    def check_keys(self, resource_name: str, resume_date: str) -> bool:
        return True if (resource_name in self.summary and
                        datetime.strptime(resume_date, "%Y-%m-%d").date() == datetime.strptime(self.summary[resource_name]['resume_date'], "%Y-%m-%d").date()) else False

    def check_infos(self, cv: 'CVperson'):

        if cv.get_resource_name() in self.summary:
            if datetime.strptime(cv.get_resume_date(), "%Y-%m-%d").date() == datetime.strptime(self.summary[cv.get_resource_name()]['resume_date'], "%Y-%m-%d").date():
                return True
            else:
                return False
        return False

    def save_summary(self, cv: 'CVperson', summary: str):
        self.summary[cv.get_resource_name()] = {'resume_date': cv.get_resume_date(),
                                                'summary': summary}
        self.save_summary_file()
