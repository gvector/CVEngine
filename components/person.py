from datetime import date
import json


class Person:
    def __init__(self, resource_name: str, id_db: int, email: str, resume_date, cv_docx_name: str, status: str, y_in_pqe,
                 company: str, role: str, country_residenza: str, city_residenza: str, indirizzo_residenza: str, business_line: str, stato: str):
        self.resource_name = resource_name
        self.id_db = id_db
        self.email = email
        self.resume_date = self.reformat_date(resume_date)
        self.cv_docx_name = cv_docx_name
        self.status = status
        self.y_in_pqe = float(y_in_pqe)
        self.company = company
        self.role = role
        self.country_residenza = country_residenza
        self.city_residenza = city_residenza
        self.indirizzo_residenza = indirizzo_residenza
        self.business_line = business_line
        self.stato = stato

    def __str__(self):
        return f"Person: {self.resource_name}"

    def get_coe(self) -> str:
        return self.business_line

    def get_name(self) -> str:
        return self.resource_name

    def present_person(self) -> dict:
        return self.format_presentation(self.__dict__)

    def get_resume_date(self) -> str:
        return self.resume_date

    def to_dict(self) -> dict:
        return self.__dict__

    @staticmethod
    def format_presentation(data: dict) -> 'json':
        return json.dumps(data, indent=4)

    @staticmethod
    def reformat_date(resume_date: 'date') -> str:
        return resume_date.strftime("%Y-%m-%d")

    @classmethod
    def load_from_dict(cls, info_dict: dict):
        return cls(resource_name=info_dict['resource_name'],
                   id_db=info_dict['id'],
                   email=info_dict['email'],
                   resume_date=info_dict['resume_date'],
                   cv_docx_name=info_dict['cv_docx_name'],
                   status=info_dict['status'],
                   y_in_pqe=info_dict['y_in_pqe'],
                   company=info_dict['company'],
                   role=info_dict['role'],
                   country_residenza=info_dict['country_residenza'],
                   city_residenza=info_dict['city_residenza'],
                   indirizzo_residenza=info_dict['indirizzo_residenza'],
                   business_line=info_dict['business_line'],
                   stato=info_dict['type'])
