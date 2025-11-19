from components.logger import logger
from components.validator import Validator

import json


class Skill:
    """
    A class used to manage skills to be added to the CV class.

    ...

    Attributes
    ----------
    areas : dict
        A dictionary mapping main skills to their sub-skills.
    main : str
        The main skill.
    sub_skills : dict
        A dictionary mapping sub-skills to their scores.

    Methods
    -------
    __str__() -> str:
        Returns a string representation of the Skill object.
    get_main() -> str:
        Returns the main skill.
    get_secondaries() -> dict:
        Returns the sub-skills.
    update_score(sub_skill: str, score: int) -> None:
        Updates the score of a sub-skill.
    check_skill(bl: str) -> bool:
        Checks if a skill is in the areas.
    """

    areas = {
        "PV": {"Requirements of PV Quality Management System according to Module I of European Good Pharmacovigilance Practice (EU GVP) Guidelines": 1,
                "Plan, conduction, reporting of PV audits according to EU GVP Module IV": 1,
                "EU GVP Module IV": 1,
                "EU GVP Module II": 1,
                "EU GVP Module VII": 1,
                "EU GVP Module VI": 1,
                "EU GVP Module IX": 1,
                "Adverse Event case processing according to EU GVP Module VI": 1,
                "Use of safety database for adverse event managament (like Argus, ArisG)": 1,
                "Argus": 1,
                "ArisG": 1,
                "Pharmacovigilance System Master File (PSMF)": 1,
                "PSMF": 1,
                "Knowledge of Periodic Safety Report (PSUR/PBRER) according to EU GVP Module VII": 1,
                "PSUR": 1,
                "PBRER": 1,
                "Knowledge of Signal detection according to EU GVP Module IX": 1,
                "Knowledge of Risk Management Plan (RMP) according to EU GVP Module V ": 1,
                "RMP": 1,
                "ISO 19011:2018 Guidelines for auditing management systems": 1,
                "ISO 19011": 1,
                "Local pharmacovigilance regulation in their territory/region": 1},
        'COMMISSIONING & QUALIFICATION': {'sub_skill1': 1, 'sub_skill2': 1, 'sub_skill3': 1},
        'COMPLIANCE': {'sub_skill1': 1, 'sub_skill2': 1, 'sub_skill3': 1},
        'DIGITAL GOVERNANCE': {'sub_skill1': 1, 'sub_skill2': 1, 'sub_skill3': 1},
        "THIRD PARTY AUDIT": {"Good Manufacturing Practices (GMP)": 1, "Good Laboratory Practices (GLP)": 1,
                              "GCP Inspections": 1, "Compliance Audit": 1, "Quality Management System": 1},
        "ENGINEERING": {"sub_skill1": 1, "sub_skill2": 1, "sub_skill3": 1},
        "GCP": {"sub_skill1": 1, "sub_skill2": 1, "sub_skill3": 1},
        "LABORATORY": {"sub_skill1": 1, "sub_skill2": 1, "sub_skill3": 1},
        "MARKETING": {"sub_skill1": 1, "sub_skill2": 1, "sub_skill3": 1},
        "REGULATORY AFFAIRS": {"sub_skill1": 1, "sub_skill2": 1, "sub_skill3": 1},
        "TO BE DEFINED": {"sub_skill1": 1, "sub_skill2": 1, "sub_skill3": 1},
        "VALIDATION": {"sub_skill1": 1, "sub_skill2": 1, "sub_skill3": 1},
        "N/A": {"N/A": 1}
    }

    def __init__(self, main_skill: str):
        self.validator = Validator()
        try:
            self.validator.validate_string(main_skill)
            self.validator.validate_in_dictionary(main_skill, self.areas)
            self.main = main_skill
            self.sub_skills = self.areas[main_skill]
        except ValueError as e:
            logger.error(f"Invalid skill [{main_skill}] raise error {e}.")
            self.main = None
            self.sub_skills = None

    def __str__(self):
        return json.dumps(self.__dict__, indent=4)

    def validate_skill(self, skill: str) -> bool:
        if not isinstance(skill, str):
            logger.error(f"Invalid skill [{skill}].")
            raise ValueError(f"{skill} is not a valid skill.")
        if skill not in self.areas:
            logger.error(f"Invalid skill [{skill}].")
            raise ValueError(f"{skill} is not a valid skill.")
        return True

    def get_main(self) -> str:
        return self.main

    def get_secondaries(self) -> dict:
        return self.sub_skills

    def update_score(self, sub_skill: str, score: int) -> None:
        """
        Update the score of a sub-skill.
        
        :param sub_skill: the sub_skill to be updated
        :param score: the new score to associate to the sub_skill
        
        :return: nothing 
        """
        if (sub_skill in self.sub_skills) and (0 <= score <= 10):
            self.sub_skills[sub_skill] = score
            logger.debug(f"Updated {sub_skill} score to {score}.")
        else:
            logger.error(f"Invalid sub-skill [{sub_skill}] or score value [{score}].")
            raise ValueError(f"{sub_skill} is not a valid sub-skill for {self.main}.")

    def check_skill(self, bl: str) -> bool:
        """
        Check if a skill is in the dataset areas.

        :param bl: the business_line to check

        :return: boolean value representing the presence of the skill in the areas
        """
        return bl in self.areas

    def dump_skill(self):
        """
        Returns a dictionary representation of the Skill object.

        :return: dictionary representation of the Skill object
        """
        return {'main': self.main, 'sub_skills': self.sub_skills}
