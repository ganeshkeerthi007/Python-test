import socket
import time
import dictionarry as di
import redis
import json
import threading
import logger as lg

# setup logger for this module
logger = lg.setup_logger()

encoding = 'utf-8'


# Redis channel subscription
r = redis.Redis(
    host="www.redis-17636.c269.eu-west-1-3.ec2.cloud.redislabs.com",
    port=17636,
    password="zrIqi3URmVrY3cwoH816JkBcUm5rksrv",
    decode_responses=True)
w = r.pubsub()
w.subscribe("AM_TO_FASTAPI_API")
w.subscribe("AM_TO_FASTAPI_SOCK")


class SocketClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port

        self.curr_sock = None
        self.lock = threading.Lock()

    def connect(self):
        # Connects to server
        self.close()  # Sluit de huidige socket indien deze bestaat
        self.curr_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.curr_sock.connect((self.host, self.port))
            print("Connected to server.")
        except Exception as e:
            print("Error during connection attempt:", e)
            self.curr_sock = None

    def receive_data(self):

        # Receive data from server
        try:
            while True:
                data = self.curr_sock.recv(4096)
                logger.debug({data})
                if not data:
                    break
                full_msg = data.decode(encoding)
                if len(full_msg) > 0:  # If incoming message > 0 characters, interpret message
                    next_msg_len = int(full_msg[:5])
                    msgs_to_eval = []
                    while len(full_msg) > 0:  # split up messages in case are received as one string and store in list
                        msgs_to_eval.append(full_msg[5:next_msg_len + 5])
                        logger.debug({"Message to evaluate": msgs_to_eval})
                        full_msg = full_msg[5 + next_msg_len:]
                        if len(full_msg) > 0:
                            next_msg_len = int(full_msg[:5])
                        else:
                            pass
                    while len(msgs_to_eval) > 0:
                        print("message to eval:", msgs_to_eval)
                        if msgs_to_eval[0:13] == ["'not processed:1'"]:  # pick up non-interpretable messages from AM
                            print("error")

                            pass
                        else:
                            try:
                                msg = msgs_to_eval[0]
                                msg_dict = json.loads(msg)

                                logger.comms(json.dumps(msg_dict), extra={"reporting_system": "20", "direction": "10", "partner_system": "10", "comm_channel": "20"})  # log msg must be string

                                call_type = msg_dict["type"]  # picks up call type
                                print(call_type)

                                if call_type == "asa_mes":
                                    print(f'Attributes: {msg_dict["attributes"]}')
                                    if msg_dict["attributes"]["parent"] == "grenzen" and msg_dict["attributes"]["status"] == 1:
                                        student_hash = f'Student:{msg_dict["student_id"]}'
                                        value = "true"
                                        r.hset(student_hash, "session_prepare_status", value)
                                        log_msg = json.dumps({"type": "asa_mes", "hash": student_hash, "key": "session_prepare_status", "value": "true"})
                                        logger.comms(log_msg, extra={"reporting_system": "20", "direction": "20", "partner_system": "30", "comm_channel": "10"})
                                    else:
                                        pass

                                elif call_type == "log":

                                    # map log elements
                                    level = str(msg_dict["attributes"]["level"])
                                    reporting_system = str(msg_dict["attributes"]["source"])
                                    log = msg_dict["attributes"]["log_message_json"]["attributes"]["message"]
                                    direction = str(msg_dict["attributes"]["log_message_json"]["attributes"]["direction"])
                                    partner_system = str(msg_dict["attributes"]["log_message_json"]["attributes"]["partner_system"])
                                    comm_channel = str(msg_dict["attributes"]["log_message_json"]["attributes"]["comm_channel"])

                                    # log depends on level
                                    if level == 10:
                                        logger.debug(log_msg, extra={"reporting_system": reporting_system, "direction": direction, "partner_system": partner_system, "comm_channel": comm_channel})
                                    elif level == 20:
                                        logger.info(log_msg, extra={"reporting_system": reporting_system, "direction": direction, "partner_system": partner_system, "comm_channel": comm_channel})
                                    elif level == 25:
                                        try:
                                            logger.comms(log_msg, extra={"reporting_system": reporting_system, "direction": direction, "partner_system": partner_system, "comm_channel": comm_channel})
                                            print('Logged')
                                        except e:
                                            print(e)
                                    elif level == 30:
                                        logger.warning(log_msg, extra={"reporting_system": reporting_system, "direction": direction, "partner_system": partner_system, "comm_channel": comm_channel})
                                    elif level == 40:
                                        logger.error(log_msg, extra={"reporting_system": reporting_system, "direction": direction, "partner_system": partner_system, "comm_channel": comm_channel})
                                    elif level == 50:
                                        logger.critical(log_msg, extra={"reporting_system": reporting_system, "direction": direction, "partner_system": partner_system, "comm_channel": comm_channel})

                                elif call_type == "startup":
                                    print(f'Startup result: {msg_dict["attributes"]["result"]}')
                                    if msg_dict["attributes"]["result"] == "ok":
                                        student_hash = f'Student:{msg_dict["student_id"]}'
                                        r.hset(student_hash, 'startup_status', 'true')
                                        log_msg = json.dumps({"type": "startup", "hash": student_hash, "key": "startup_status", "value": "true"})
                                        logger.comms(log_msg, extra={"reporting_system": "20", "direction": "20", "partner_system": "30", "comm_channel": "10"})
                                    else:
                                        pass

                                elif call_type == "testmode":
                                    student_hash = f'Student:{msg_dict["student_id"]}'
                                    testmode = msg_dict["attributes"]["testmode"]
                                    r.hset(student_hash, "testmode", testmode)
                                    log_msg = json.dumps({"type": "testmode", "hash": student_hash, "key": "testmode", "value": testmode})
                                    logger.comms(log_msg, extra={"reporting_system": "20", "direction": "20", "partner_system": "30", "comm_channel": "10"})

                                elif call_type == "next_exercises":
                                    student_id = msg_dict["student_id"]
                                    testmode = msg_dict["attributes"]["testmode"]
                                    level = msg_dict["attributes"]["level"]
                                    domain = msg_dict["attributes"]["domain"]
                                    worksheets = msg_dict["attributes"]["worksheets"]
                                    exercises = msg_dict["attributes"]["exercises"][0]
                                    if exercises == "empty":
                                        msg_fnl = {"type": "session_finished", "student_id": student_id}
                                    else:
                                        msg_fnl = {"type": "exercises", "student_id": student_id, "attributes": {"mode": testmode, "level": level,  \
                                                   "stype": domain, "worksheet": worksheets, "exercise": exercises}}
                                    log_msg = json.dumps(msg_fnl)
                                    logger.comms(log_msg, extra={"reporting_system": "20", "direction": "20", "partner_system": "30", "comm_channel": "10"})
                                    print(msg_fnl)
                                    print(type(msg_fnl))
                                    r.publish(di.call_types.get(call_type), log_msg)  # looks in dictionary for which redis channel to use

                                elif call_type == "test_result":
                                    step_nr = msg_dict["attributes"]["stepnumber"]
                                    student_id = msg_dict["student_id"]
                                    status = "ok" if len(msg_dict["attributes"]["errpositions"]) == 0 else "niet ok"
                                    comment_message = "none"
                                    ortho_formula = msg_dict["attributes"]["ortho_formula"]
                                    evaluation_value = msg_dict["attributes"]["ortho_formula"]
                                    message = f'{{"type": "test_formula", "student_id": {student_id}, "attributes": {{"step": {step_nr} , "formula": "{ortho_formula}", "result": "{evaluation_value}", "comment":' \
                                        f' {{"status": "{status}", "message": "{comment_message}"}}}}}}'
                                    msg = message.replace("'", '"')
                                    r.publish(di.call_types.get(call_type), msg)  # looks in dictionary for which redis channel to use
                                    log_msg = json.dumps(message)
                                    logger.comms(log_msg, extra={"reporting_system": "20", "direction": "20", "partner_system": "30", "comm_channel": "10"})

                                elif call_type == "wall":
                                    student_id = int(msg_dict["student_id"])
                                    student_hash = f'Student:{student_id}'
                                    wall_date = msg_dict["attributes"]["date_time"]
                                    wall_level = msg_dict["attributes"]["maxlevel"]
                                    scores = msg_dict["attributes"]["flattenedlayers"]
                                    score_list = []
                                    for x in scores:
                                        diploma_id = round(x / 10000)
                                        level = di.level_dict[str(x)[-4]]
                                        component_id = f'{diploma_id}-{level}'
                                        color_code = int(str(x)[-1])
                                        score_list.append([component_id, color_code])
                                    wall_student = {"type": "wall", "student_id": student_id, "date": wall_date, "max_level": wall_level, "scores": score_list}
                                    wall_msg = str(wall_student)
                                    r.hset(student_hash, "wall", wall_msg)
                                    log_msg = json.dumps(wall_student)
                                    logger.comms(log_msg, extra={"reporting_system": "20", "direction": "20", "partner_system": "30", "comm_channel": "10"})
                                    score_list.clear()

                                elif call_type == "student_mes":
                                    student_id = msg_dict["student_id"]
                                    student_message = msg_dict["attributes"]["message"]
                                    message = f'{{"type": "student_message", "student_id": {student_id}, "attributes": {{"message_voice": "{student_message}", "message_text": "{student_message}"}}}}'
                                    msg = message.replace("'", '"')
                                    r.publish(di.call_types.get(call_type), msg)  # looks in dictionary for which redis channel to use
                                    log_msg = json.dumps(message)
                                    logger.comms(msg, extra={"reporting_system": "20", "direction": "20", "partner_system": "30", "comm_channel": "10"})

                                elif call_type == "question_yn":
                                    student_id = msg_dict["student_id"]
                                    question_id = msg_dict["attributes"]["question_id"]
                                    voice_message = msg_dict["attributes"]["message_voice"]
                                    text_message = msg_dict["attributes"]["message_text"]
                                    algorithm = str(msg_dict["attributes"]["algorithm"])
                                    msg = f'{{"type": "question_yn", "student_id": {student_id}, "attributes": {{"question_id": {question_id}, "message_voice": "{voice_message}", "message_text": "{text_message}", ' \
                                          f'"algorithm": {algorithm}}}}}'

                                    try:
                                        r.publish(di.call_types.get(call_type), msg)  # looks in dictionary for which redis channel to use
                                        json.dumps(msg)
                                        logger.comms(msg, extra={"reporting_system": "20", "direction": "20", "partner_system": "30", "comm_channel": "10"})

                                    except redis.RedisError as error:
                                        logger.error(json.dumps({"error": str(error)}), extra={"reporting_system": "20", "direction": "20", "partner_system": "30", "comm_channel": "10"})

                                elif call_type == "componenent_details":
                                    student_id = msg_dict["student_id"]
                                    student_hash = f'Student:{student_id}'
                                    level = msg_dict["attributes"]["level"]
                                    diploma_id = msg_dict["attributes"]["diplomaid"]
                                    teacher_required = msg_dict["attributes"]["teacher_required"]
                                    missing_teacher_required = msg_dict["attributes"]["missing_teacher_required"]
                                    student_used_algorithms = msg_dict["attributes"]["student_used_algorithms"]
                                    student_used_bad_algorithms = msg_dict["attributes"]["student_used_bad_algorithms"]
                                    requested_components_tq_algs = msg_dict["attributes"]["requested_components_tq_algs"]
                                    comp_details = {"level": level, "diploma_id": diploma_id, "teacher_required": teacher_required, "missing_teacher_required": missing_teacher_required,
                                                    "student_used_algorithms": student_used_algorithms, "student_used_bad_algorithms": student_used_bad_algorithms, "requested_components_tq_algs":
                                                    requested_components_tq_algs}
                                    comp_msg = str(comp_details)
                                    r.hset(student_hash, "component_details", comp_msg)
                                    log_msg = json.dumps(comp_details)
                                    logger.comms(comp_details, extra={"reporting_system": "20", "direction": "20", "partner_system": "30", "comm_channel": "10"})

                                elif call_type == "explanation":
                                    student_hash = f'Student:{msg_dict["student_id"]}'
                                    algo = msg_dict["attributes"]["script"]
                                    steps = {"type": "explanation", "script": algo}
                                    send_msg = json.dumps(steps)
                                    r.hset(student_hash, "explanation", send_msg)
                                    log_msg = json.dumps({"type": "explanation", "hash": student_hash, "key": "explanation", "value": steps})
                                    logger.comms(log_msg, extra={"reporting_system": "20", "direction": "20", "partner_system": "30", "comm_channel": "10"})
                                else:
                                    print(msgs_to_eval)
                            except Exception as e:
                                logger.error(json.dumps({"error": str(e)}), extra={"reporting_system": "20", "direction": "20", "partner_system": "30", "comm_channel": "10"})
                            del msgs_to_eval[0]
                else:
                    print("SERVER: Ik heb een lege boodschap ontvangen")

        except Exception as e:
            logger.error(json.dumps({"error": str(e)}), extra={"reporting_system": "20", "direction": "20", "partner_system": "30", "comm_channel": "10"})

        finally:
            print('Socket closed')
            self.close()

    def send_data(self, data):
        # Sends data to the server
        if self.curr_sock:
            try:
                self.curr_sock.sendall(data.encode(encoding))
            except Exception as e:
                logger.error(json.dumps({"error": str(e)}), extra={"reporting_system": "20", "direction": "20", "partner_system": "30", "comm_channel": "10"})
                self.close()
        else:
            print("No active connection to send data over")

    def close(self):
        # Close the socket
        if self.curr_sock:
            try:
                self.curr_sock.close()
                print("Socket closed.")
            except Exception as e:
                logger.error(json.dumps({"error": str(e)}), extra={"reporting_system": "20", "direction": "20", "partner_system": "30", "comm_channel": "10"})
            finally:
                self.curr_sock = None

    def run(self):
        # Keeps trying to connect and receive over the
        while True:
            if not self.curr_sock:
                self.connect()

            if self.curr_sock:
                self.receive_data()
            print("Connection lost, try to reconnect in 2 seconds ...")
            time.sleep(0.5)
