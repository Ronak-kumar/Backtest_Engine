import logging
import os
from datetime import datetime as dt
import sys

class Logger():

    date = str(dt.now().date())
    LOGGING_LEVEL = logging.DEBUG
    LOG_IN_STDOUT = True
    LOG_IN_FILE = False
    LOG_PATH = f"{os.getcwd()[:-4]}log/{date}/"
    LOG_FILENAME = "..."
    
    def __init__(self, log_path=LOG_PATH):
        self.logger = None
        self.log_path = log_path
        sys.excepthook = self.handle_exception


    def handle_exception(self, exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        self.logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))



    def setup_logger(self,name, log_file):
        
        """
        write root http calls into log file
        """

        date = dt.now().strftime("%Y_%m_%d")
        log_file = self.log_path / date / log_file
        os.makedirs(self.log_path / date, exist_ok=True)

        formatter = logging.Formatter('%(asctime)s [%(name)s - %(levelname)s - %(lineno)d] : %(message)s')
        handler = logging.FileHandler(log_file, mode='a')
        handler.setFormatter(formatter)

        logger = logging.getLogger(name)
        logger.addHandler(handler)
        logger.setLevel(self.LOGGING_LEVEL)

        self.logger = logger

        return logger
    
    def basic_logger(self, name, log_file):
        """
        write root http calls into log file
        """
        date = dt.now().strftime("%Y_%m_%d")
        log_file = self.log_path / date / log_file
        os.makedirs(self.log_path / date, exist_ok=True)

        # Create and configure logger
        logging.basicConfig(filename=log_file,
                            format='%(asctime)s [%(name)s - %(levelname)s - %(lineno)d] : %(message)s',
                            filemode='a')

        # Creating an object
        logger = logging.getLogger()

        # Setting the threshold of logger to DEBUG
        logger.setLevel(self.LOGGING_LEVEL)
        
        return logger