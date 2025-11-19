from components.logger import logger

from typing import Union
import mysql.connector


query_person = """
    SELECT resource_code, cv_plain_text, resource_name, id, email, resume_date, cv_docx_name, status, y_in_pqe, company, role, country_residenza, city_residenza, indirizzo_residenza, business_line, type
    FROM hrtm.openai_cvs a
    JOIN suitecrm.v_ai_cv_res_information b
        USING (resource_code)
    WHERE a.resume_date = (
            SELECT MAX(b.resume_date)
            FROM hrtm.openai_cvs b
            WHERE b.resource_code = a.resource_code
                AND LENGTH(b.cv_plain_text) > 500
        );"""


class SQLManager:
    """
    A class used to manage SQL database connections and operations with mysql package.

    ...

    Attributes
    ----------
    host : str
        The host of the SQL database.
    user : str
        The username to connect to the SQL database.
    password : str
        The password to connect to the SQL database.
    database : str
        The name of the SQL database.
    connection : mysql.connector.connection
        The connection object to the SQL database.
    cursor : mysql.connector.cursor
        The cursor object to execute SQL queries.

    Methods
    -------
    connect():
        Establishes a connection to the SQL database and initializes the cursor.
    parse(data: list[tuple]) -> dict[str: str]:
        Parses the fetched data from the SQL query into a dictionary.
    enhance(data: list[tuple], info: pd.DataFrame) -> dict[str, dict]:
        Enhances the fetched data with additional information from a DataFrame.
    execute(query: str, limited: bool = False) -> dict[str, dict]:
        Executes a SQL query and returns the result.
    save(results: dict[str, str], filename: str) -> None:
        Saves the results of a SQL query into a JSON file.
    disconnect() -> None:
        Closes the connection to the SQL database.
    """
    def __init__(self, host: str, user: str, password: str, database: str = None) -> None:
        self.host = host
        self.user = user
        self.password = password
        self.database = None
        self.connection = None
        self.cursor = None

    def connect(self) -> None:
        """
        Establishes a connection to the SQL database and initializes the cursor object.

        :return: nothing
        """
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database
            )
            self.cursor = self.connection.cursor()
            logger.info(f"Successfully connected to the database to the HOST: {self.host}")
        except Exception as e:
            logger.error(f"An error occurred while connecting to the database: {e}")

    @staticmethod
    def parse(data: list[tuple], columns_names: list[str]) -> dict[str, dict]:
        cv_dicts = {}
        for res in data:
            for key, value in zip(columns_names, res):
                if key == "resource_code":
                    rc = value
                    cv_dicts[rc] = {}
                else:
                    cv_dicts[rc][key] = value
        return cv_dicts

    def execute(self, query: str = query_person) -> Union[dict[str, dict], None]:
        """
        Executes a SQL query and returns the result.

        :param query: string in SQL language representing the query to execute

        :return: dictionary of the results of the query in the form of
            {resource_code: {cv: cv_plain_text, skill: business_line}} after the modification
        """
        try:
            self.cursor.execute(query)
            ress = self.cursor.fetchall()
            columns = [column[0] for column in self.cursor.description]
            return self.parse(data=ress, columns_names=columns)
        except Exception as e:
            logger.error(f"An error occurred: {e}")
            return None

    def disconnect(self) -> None:
        self.cursor.close()
        self.connection.close()
