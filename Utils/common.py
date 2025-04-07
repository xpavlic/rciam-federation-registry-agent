import logging
import logging.config
from copy import deepcopy

import requests


def get_log_conf(log_config_file=None):
    """
    Method that searches and gets the default location of configuration and logging configuration
    """
    if log_config_file is not None:
        logging.config.fileConfig(log_config_file, disable_existing_loggers=False)
    else:
        logging.basicConfig(level=logging.INFO, format=logging.BASIC_FORMAT)


# create_ams_response creates a json object with the result of the mitreId api call
# that is readable from the rciam-federation-registry
def create_ams_response(response, service_id, deployer_name, external_id, client_id, proxy_deploy_success):
    new_msg = {}
    new_msg["id"] = service_id
    new_msg["status_code"] = response["status"]
    if len(deployer_name) > 0:
        new_msg["deployer_name"] = deployer_name

    if len(external_id) > 0:
        new_msg["external_id"] = external_id

    if len(client_id) > 0:
        new_msg["client_id"] = client_id

    if response["status"] != 200 and response["status"] != 201 and response[
        "status"] != 204:
        new_msg["error_description"] = response["error"]
        new_msg["proxy_deploy_success"] = proxy_deploy_success
        new_msg["state"] = "error"
    else:
        new_msg["state"] = "deployed"

    return new_msg


"""
Method that creates the Keycloak issuer based on `auth_server` + `realm`

Parameters:
    config (dict): Keycloak's config options

Returns:
    return (string): Keycloak's issuer URL
"""


def get_keycloak_issuer(config):
    return config["auth_server"] + "/realms/" + config["realm"]


"""
Wrapper function for Python requests

Parameters:
    method (str): The request method
    url (str): The URL of the Client Registration API
    header (str): The Headers of the HTTP Request
    data (str): The data of the HTTP Request, else `None`

Returns:
    response (JSON Object): The status of the HTTP Response
"""


def http_request(method, url, header, data=None, auth=None, timeout=5):
    try:
        response = requests.request(
            method, url, headers=header, json=data, auth=auth, timeout=timeout
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as errh:
        print(
            "HTTP Error: %s with error: HTTP %s and response: %s" % (
                url, response.status_code, response.json())
        )
        return {
            "status": response.status_code,
            "error": repr(errh),
            "response": response.json(),
        }
    except requests.exceptions.ConnectionError as errc:
        print(
            "Connection Error: %s with error: HTTP  %s and response: %s"
            % (url, response.status_code, response.text)
        )
        return {
            "status": response.status_code,
            "error": repr(errc),
            "response": response.json(),
        }
    except requests.exceptions.Timeout as errt:
        print(
            "Timeout Error: %s with error: HTTP %s and response: %s" % (
                url, response.status_code, response.text)
        )
        return {
            "status": response.status_code,
            "error": repr(errt),
            "response": response.json(),
        }
    except requests.exceptions.RequestException as err:
        print(
            "Failed to make request to %s with error: HTTP  %s and response: %s"
            % (url, response.status_code, response.text)
        )
        return {
            "status": response.status_code,
            "error": repr(err),
            "response": response.json(),
        }

    if method == "DELETE" or response.status_code == 204 or not response.text:
        return {"status": response.status_code, "response": "OK"}
    else:
        return {"status": response.status_code, "response": response.json()}


# Publish message to ams upstream topic. Get as arguments
# - the messages to be published
# - the ams agent to handle the operation
def publish_ams(pub_messages, ams_agent, log):
    if len(pub_messages) > 0:
        log.info("Publish messaged to ams")
        log.debug("Messages published to ams: " + str(pub_messages))
        ams_agent.publish(pub_messages)


def deploy_to_perun(perun_message, perun_client_api):
    deployment_type = perun_message["deployment_type"]
    success = False
    if deployment_type == "create":
        success = perun_client_api.register_new_service_in_perun(perun_message)
    elif deployment_type == "delete":
        success = perun_client_api.delete_service_in_perun(perun_message)
    elif deployment_type == "edit":
        success = perun_client_api.update_service_in_perun(perun_message)
    return success


def process_data_generic(messages, deploy_to_proxy_func, proxy_type, log, perun_client_api=None):
    # messages to be published
    pub_messages = []
    deployer_name = ""

    for msg in messages:
        log.debug(f"Message from AMS: {msg}")

        # Copy message for deployment to perun.
        perun_msg = deepcopy(msg) if perun_client_api else None
        proxy_deploy_success = msg.get("proxy_deploy_success", False)

        # Remove rciam service id to make request to Cas
        service_id = msg.pop("id")
        external_id = ""
        client_id = ""
        response = {"status": 200}

        if not proxy_deploy_success:
            # Service not deployed to proxy yet proceed with deployment
            try:
                response, external_id, client_id = deploy_to_proxy_func(msg)
                log.info(f"Message received from {proxy_type}: {response}")
                if response["status"] in [200, 201, 204]:
                    proxy_deploy_success = True
            except Exception as e:
                log.critical(
                    f"Exception catch when calling {proxy_type} deployment, return error to ams. Exception {e}")
                ams_message = create_ams_response(
                    {"status": 0, "error": f"An error occurred while calling {proxy_type}"},
                    service_id,
                    deployer_name,
                    external_id,
                    client_id,
                    proxy_deploy_success
                )
                pub_messages.append({"attributes": {}, "data": ams_message})
                return pub_messages
        try:
            if perun_client_api and response["status"] in [200, 201, 204]:
                # Service deployed to proxy successfully proceed with deployment to perun.
                if client_id:
                    perun_msg["client_id"] = client_id
                if not deploy_to_perun(perun_msg, perun_client_api):
                    response["status"] = 0
                    response["error"] = "Deployment to Perun failed"

            # Deployment completed without exceptions, create response message
            ams_message = create_ams_response(
                response,
                service_id,
                deployer_name,
                external_id,
                client_id,
                proxy_deploy_success
            )
        except Exception as e:
            log.critical(f"Exception catch when calling Perun deployment, return error to ams. Exception {e}")
            ams_message = create_ams_response(
                {"status": 0, "error": "An error occurred while calling Perun"},
                service_id,
                deployer_name,
                external_id,
                client_id,
                proxy_deploy_success
            )

        pub_messages.append({"attributes": {}, "data": ams_message})
    return pub_messages
