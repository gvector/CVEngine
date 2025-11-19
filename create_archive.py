from components.sql_connector import SQLManager
from components.logger import logger
from test_person import create_obj
from components.cvs import CVS


from datetime import datetime


today = datetime.now()


if __name__ == '__main__':
    
    logger.info("Starting the process")
    db = SQLManager(host='10.1.1.90',
                    user='ai_reader',
                    password='ai-r3ad3r_2o24!')

    db.connect()

    create_obj(sql_manager=db,
               cvs_collector=CVS())

    logger.info(f"Archive created and saved to 'archive_{today.strftime("%d_%m_%Y")}.pkl'")
