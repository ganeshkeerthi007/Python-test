import logging
from datetime import datetime
import os

import psycopg2
import json


# Haal DATABASE_URL op uit de omgevingsvariabelen
database_url = os.getenv('DATABASE_URL')

# Aangepaste logniveaus definiëren
COMMS = 25
logging.addLevelName(COMMS, 'COMMS')

class DatabaseHandler(logging.Handler):
    def __init__(self, db_url):
        super().__init__()
        self.db_url = db_url

    def emit(self, record):
        conn = None

        try:
            conn = psycopg2.connect(database_url)
            cursor = conn.cursor()
            insert_query = 'INSERT INTO logs (timestamp, level, log_message_text, log_message_json, reporting_system) VALUES (%s, %s, %s, %s, %s);'

            log_msg = json.loads(record.getMessage())  # when dict is passed to logger module if fetched it transforms to string, so need to reload in dict.
            log_mes_json = json.dumps(
                {
                    "message": log_msg,
                    "direction": getattr(record, "direction", 0),
                    "reporting_system": getattr(record, "reporting_system", 0),
                    "partner_system": getattr(record, "partner_system", 0),
                    "comm_channel": getattr(record, "comm_channel", 0)
                })
            log_data = (
                datetime.utcfromtimestamp(record.created).strftime('%Y-%m-%dT%H:%M:%S'),  # Geformatteerde timestamp
                record.levelno,  # level
                record.getMessage(),  # text log
                json.dumps(json.loads(log_mes_json)),  # json log
                getattr(record, "reporting_system", "0") # reporting system
            )
            cursor.execute(insert_query, log_data)
            conn.commit()
        except Exception as e:  # Een algemenere uitzondering vangen
            print(f"Fout bij het verbinden met of schrijven naar de PostgreSQL database: {e}")
        finally:
            if conn:
                conn.close()


class CustomLogger(logging.Logger):
    def __init__(self, level=logging.NOTSET):
        super().__init__(level)

    def comms(self, message, *args, **kws):
        if self.isEnabledFor(COMMS):
            self._log(COMMS, message, args, **kws)

    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False):
        if extra is None:
            extra = {}
        super()._log(level, msg, args, exc_info, extra, stack_info)



# Logging formatter en handler configureren
def setup_logger():
    # Correct gebruik van CustomLogger met de source_system_code
    logger = CustomLogger()
    logger.setLevel(10)  # Laagste aangepaste niveau
    logger.propagate = False

    db_handler = DatabaseHandler(database_url)
    logger.addHandler(db_handler)

    return logger



