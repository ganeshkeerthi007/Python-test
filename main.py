import json
import threading
from socket_am import SocketClient
import redis
import datetime
import logger as lg


# setup logger for this module
logger = lg.setup_logger()


HOST = "63.35.161.212"
PORT = 50530

client = SocketClient(HOST, PORT)


def start_socket_client():
    client.run()


if __name__ == "__main__":
    socket_thread = threading.Thread(target=start_socket_client)
    socket_thread.start()

    r = redis.Redis(
        host="www.redis-17636.c269.eu-west-1-3.ec2.cloud.redislabs.com",
        port=17636,
        password="zrIqi3URmVrY3cwoH816JkBcUm5rksrv",
        decode_responses=True)

    q = r.pubsub()
    q.subscribe("FASTAPI_TO_AM")

    for m in q.listen():
        now = datetime.datetime.now()
        timestamp = datetime.datetime.timestamp(now)

        if m.get('type') == "message":

            # Fetch message from Redis FastAPI
            message = m.get('data')
            message_am = str(message.replace("'", '"'))  # set double quotes for JSON

            # log incoming message Redis FASTAPI
            logger.comms(message, extra={"reporting_system": "20", "direction": "10", "partner_system": "30", "comm_channel": "10"})

            try:
                client.send_data(message_am)
                # log message out to Prolog
                logger.comms(message, extra={"reporting_system": "20", "direction": "20", "partner_system": "10", "comm_channel": "20"})
            except Exception as e:
                logger.error({"error": str(e)}, extra={"reporting_system": "20", "direction": "20", "partner_system": "10", "comm_channel": "20"})

        else:
            pass


