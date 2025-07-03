#!/usr/bin/env python3

import json
import logging
import deployer_cas
import pika

from CAS.CasClientApi import CasClientApi
from Perun.PerunClientApi import PerunClientApi

# Setup logger
log = logging.getLogger(__name__)


def init_rabbit_connection(rabbitmq_config: dict) -> tuple:
    """
    Initialize RabbitMQ connection and channel.

    :param rabbitmq_config: Dictionary containing RabbitMQ configuration.
    :return: Tuple of connection and channel.
    """
    credentials = pika.PlainCredentials(
        rabbitmq_config["username"], rabbitmq_config["password"]
    )
    parameters = pika.ConnectionParameters(
        host=rabbitmq_config["host"],
        virtual_host=rabbitmq_config["vhost"],
        credentials=credentials,
    )

    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()

    channel.queue_declare(queue=rabbitmq_config["sub_queue"], durable=True)
    channel.queue_declare(queue=rabbitmq_config["pub_queue"], durable=True)
    # Fetch(only) 30 messages ahead if possible.
    channel.basic_qos(prefetch_count=30)

    return connection, channel


def main():
    path = deployer_cas.get_config_path_from_arguments()

    with open(path) as json_data_file:
        config = json.load(json_data_file)

    deployer_cas.set_log_config(config)

    perun_client_api = None
    if "perun" in config["cas"]:
        perun_client_api = PerunClientApi(config["cas"]["perun"])

    username = config["cas"]["username"]
    password = config["cas"]["password"]
    cas_url = config["cas"]["cas_url"]
    cas_agent = CasClientApi(cas_url, username, password)

    rabbitmq_config = config["cas"]["rabbitmq"]

    log.info("Init RabbitMQ agent")
    
    def callback(ch, method, properties, body):
        try:
            msg = body.decode()
            json_msgs = json.loads(msg)
            responses = deployer_cas.process_data(
                json_msgs, cas_agent, perun_client_api
            )
            if not responses:
                log.error("No responses received from deployer_cas.process_data")
                return
            status_update = responses[0].get("data", {})
            log.info("Pusblishing status update to RABBITMQ:\n %s", status_update)
            if status_update == {}:
                log.error("No status update in response, skipping message")
                return

            ch.basic_publish(
                exchange="",
                routing_key=rabbitmq_config["pub_queue"],
                body=json.dumps(status_update),
            )
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except (ValueError, TypeError) as e:
            # these are parent classes for JSON exceptions
            log.error("Failed to process message with exception: %s", e)
            log.error("Message body: %s", body)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        except Exception as e:
            log.error("Critical error %s", e)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    connection, channel = init_rabbit_connection(rabbitmq_config)
    channel.basic_consume(
        queue=rabbitmq_config["sub_queue"], on_message_callback=callback, auto_ack=False
    )
    log.info("Waiting for messages from %s...", rabbitmq_config["sub_queue"])

    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        log.info("Interrupted, closing connection.")
        channel.stop_consuming()
    connection.close()


if __name__ == "__main__":
    main()
