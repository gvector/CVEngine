from components.logger import logger

import time


def time_execution(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        logger.debug(f"Tempo di esecuzione di {func.__name__}: {end_time - start_time} secondi", '\n')
        return result
    return wrapper
