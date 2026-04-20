#!/usr/bin/env python3

"""
@AUTHOR Jan Pavlíček (xpavli95@stud.fit.vutbr.cz)
"""

import argparse
import json
import logging
import time
import uuid

from CAS.CasClientApi import CasClientApi
from Perun.PerunClientApi import PerunClientApi
from ServiceRegistryAms.PullPublish import PullPublish
from Utils.common import get_log_conf, publish_ams, process_data_generic

# Setup logger
log = logging.getLogger(__name__)


def build_response_types_from_grant_types(grant_types):
    """
    Function for building OIDC response types
    @grant_types is a list of OIDC grant types
    """
    response_types = []
    if "authorization_code" in grant_types:
        response_types.append("code")
    if "implicit" in grant_types:
        response_types.append("token")
        response_types.append("id_token")
        response_types.append("id_token token")
    if "urn:ietf:params:oauth:grant-type:device_code" in grant_types:
        response_types.append("device_code")
    if "hybrid" in grant_types:
        response_types.append("id_token token")
    return ["java.util.HashSet", response_types]


def build_service_id_from_redirect_uris(redirect_uris):
    """
    Function for building CAS service id from redirect uris
    """
    pattern = "^(" + "|".join(redirect_uris) + ")$"
    return pattern


def generate_client_id():
    """
    Function for generation OIDC client id
    """
    return str(uuid.uuid4())


def build_cas_msg_oidc(msg, new_msg):
    """
    Function that builds messages in format expected by Apereo CAS for OIDC services
    """
    # No configurations for:
    #   token_endpoint_auth_signing_alg
    # Code challenge methods are always enabled for every CAS service
    new_msg["@class"] = "org.apereo.cas.services.OidcRegisteredService"
    if "client_id" in msg and msg["client_id"]:
        new_msg["clientId"] = msg.pop("client_id")
    elif msg["deployment_type"] == "create":
        if not new_msg.get("clientId"):
            new_msg["clientId"] = generate_client_id()

    if "redirect_uris" in msg:
        redirect_uris = msg.pop("redirect_uris")
        new_msg["serviceId"] = build_service_id_from_redirect_uris(redirect_uris)
    issue_refresh_tokens = False
    if "scope" in msg:
        if "offline_access" in msg.get("scope"):
            issue_refresh_tokens = True
        new_msg["scopes"] = ["java.util.HashSet", msg.pop("scope")]
    if "grant_types" in msg:
        grant_types = set(msg.pop("grant_types"))
        if issue_refresh_tokens:
            grant_types.add("refresh_token")
        list_grant_types = list(grant_types)
        new_msg["supportedGrantTypes"] = ["java.util.HashSet", list_grant_types]

        new_msg["supportedResponseTypes"] = build_response_types_from_grant_types(
            list_grant_types
        )

    if issue_refresh_tokens:
        new_msg["generateRefreshToken"] = True

    if "token_endpoint_auth_method" in msg:
        token_endpoint_auth_method = msg.pop("token_endpoint_auth_method")
        if token_endpoint_auth_method == "none":
            new_msg["tokenEndpointAuthenticationMethod"] = "client_secret_basic"
        else:
            new_msg["tokenEndpointAuthenticationMethod"] = token_endpoint_auth_method
    if "client_secret" in msg:
        new_msg["clientSecret"] = msg.pop("client_secret")
    if "jwks" in msg:
        new_msg["jwks"] = json.dumps(msg.pop("jwks"))
    if "jwks_uri" in msg:
        new_msg["jwks"] = msg.pop("jwks")
    if "refresh_token_validity_seconds" in msg:
        new_msg["refreshTokenExpirationPolicy"] = {
            "@class": "org.apereo.cas.support.oauth.services.DefaultRegisteredServiceOAuthRefreshTokenExpirationPolicy",
            "timeToKill": f"PT{str(msg['refresh_token_validity_seconds'])}S"
        }
        if "reuse_refresh_token" in msg:
            new_msg["renewRefreshToken"] = not msg.pop("reuse_refresh_token")
    if "access_token_validity_seconds" in msg:
        access_token_validity = str(msg["access_token_validity_seconds"])
        if msg.pop("access_token_validity_seconds") < 60:
            access_token_validity = "60"
        new_msg["accessTokenExpirationPolicy"] = {
            "@class": "org.apereo.cas.support.oauth.services.DefaultRegisteredServiceOAuthAccessTokenExpirationPolicy",
            "maxTimeToLive": f"PT{access_token_validity}S",
            "timeToKill": f"PT{access_token_validity}S"
        }
    if "id_token_timeout_seconds" in msg:
        new_msg["idTokenExpirationPolicy"] = {
            "@class": "org.apereo.cas.oidc.services.DefaultRegisteredServiceOidcIdTokenExpirationPolicy",
            "timeToLive": f"PT{str(msg['id_token_timeout_seconds'])}S"
        }
    if "device_code_validity_seconds" in msg:
        new_msg["deviceTokenExpirationPolicy"] = {
            "@class": "org.apereo.cas.support.oauth.services.DefaultRegisteredServiceOAuthDeviceTokenExpirationPolicy",
            "timeToKill": f"PT{str(msg['device_code_validity_seconds'])}S"
        }


def msg_add_cas_saml_attribute_policy(requested_attributes, new_msg):
    """
    Function for appending Apereo CAS message with attribute release policy
    """
    if not requested_attributes:
        return

    allowed_attributes = []

    for attribute in requested_attributes:
        friendly_name = attribute.get("friendly_name")
        urn_name = attribute.get("name")

        if urn_name:
            allowed_attributes.append(urn_name)
        elif friendly_name:
            allowed_attributes.append(friendly_name)

    allowed_attributes = list(set(allowed_attributes))

    new_msg["attributeReleasePolicy"] = {
        "@class": "org.apereo.cas.services.ChainingAttributeReleasePolicy",
        "policies": [
            "java.util.ArrayList",
            [
                {
                    "@class": "org.apereo.cas.services.ReturnAllowedAttributeReleasePolicy",
                    "allowedAttributes": ["java.util.ArrayList", allowed_attributes]
                }
            ]
        ]
    }


def build_cas_msg_saml(msg, new_msg):
    """
    Function that builds messages in format expected by Apereo CAS for SAML services
    """
    new_msg["@class"] = "org.apereo.cas.support.saml.services.SamlRegisteredService"
    if "entity_id" in msg:
        new_msg["serviceId"] = msg.pop("entity_id")
    if "metadata_url" in msg:
        new_msg["metadataLocation"] = msg.pop("metadata_url")
    if "requested_attributes" in msg:
        msg_add_cas_saml_attribute_policy(msg["requested_attributes"], new_msg)


def format_cas_msg(msg):
    """
    Function for building messages in format expected by Apereo CAS
    """
    new_msg = {}
    if "service_name" in msg:
        new_msg["name"] = msg.pop("service_name")
    if "service_description" in msg:
        new_msg["description"] = msg.pop("service_description")
    if "logo_uri" in msg:
        new_msg["logo"] = msg.pop("logo_uri")
    if "policy_uri" in msg:
        new_msg["privacyUrl"] = msg.pop("policy_uri")
    if "website_url" in msg:
        new_msg["informationUrl"] = msg.pop("website_url")

    if "aup_uri" in msg:
        aup_uri = msg.pop("aup_uri")
        if aup_uri:
            new_msg["acceptableUsagePolicy"] = {
                "@class": "org.apereo.cas.services.DefaultRegisteredServiceAcceptableUsagePolicy",
                "enabled": True,
                "text": aup_uri
            }

    new_msg_contacts = []
    if "contacts" in msg:
        new_msg_contacts.append(
            ["java.util.ArrayList", [
                {
                    "@class": "org.apereo.cas.services.DefaultRegisteredServiceContact",
                    "email": contact["email"],
                    "type": contact["type"]
                } for contact in msg["contacts"]
            ]]
        )

    if "protocol" in msg:
        if msg["protocol"] == "oidc":
            build_cas_msg_oidc(msg, new_msg)

        elif msg["protocol"] == "saml":
            build_cas_msg_saml(msg, new_msg)
        msg.pop("protocol")
    return new_msg


def deploy_to_cas(registry_message, cas_agent):
    """
    Function responsible for calling of message transformation functions and calling Apereo CAS API for service
    management
    """
    deployment_type = registry_message["deployment_type"]
    cas_msg = format_cas_msg(registry_message)
    response = {}
    external_id = ""
    client_id = ""
    if deployment_type == "create":
        log.info("Create new client")
        response = cas_agent.create_client(cas_msg)
        if response["status"] == 200:
            external_id = response["response"].get("id")
            client_id = response["response"].get("clientId", "")
    elif deployment_type == "delete":
        external_id = registry_message["external_id"]
        log.info("Delete client with id: " + str(external_id))
        response = cas_agent.delete_client_by_external_id(external_id)
    elif deployment_type == "edit":
        external_id = registry_message["external_id"]
        log.info("Update client with id: " + str(external_id))
        cas_msg["id"] = int(external_id)
        response = cas_agent.update_client(cas_msg)
        external_id = response["response"].get("id")
        client_id = response["response"].get("clientId", "")
    return response, str(external_id), client_id


def process_data(messages, cas_agent, perun_client_api=None):
    """
    Function calling generic processing function controlling deployment to Apereo CAS and Perun IDM.
    """
    def deploy_func(msg):
        return deploy_to_cas(msg, cas_agent)

    return process_data_generic(
        messages,
        deploy_func,
        "CAS",
        log,
        perun_client_api
    )

def get_config_path_from_arguments()-> str:
    """
    Function for getting config path from arguments
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c",
        required=True,
        type=str,
        help="Configuration file location path"
    )
    args = parser.parse_args()
    return args.c

def set_log_config(configuration: dict):
    """
    Set log_conf from project arguments else use the global setting
    """
    if "log_conf" in configuration["cas"]:
        get_log_conf(configuration["cas"]["log_conf"])
    else:
        get_log_conf(configuration["log_conf"])

if __name__ == "__main__":
    path = get_config_path_from_arguments()
    with open(path) as json_data_file:
        config = json.load(json_data_file)

    set_log_config(config)

    log.info("Init ams agent")
    ams = PullPublish(config["cas"]["ams"])

    perun_client_api = None
    if "perun" in config["cas"]:
        perun_client_api = PerunClientApi(config["cas"]["perun"])

    cas_agent = CasClientApi(config["cas"]["cas_url"], config["cas"]["username"], config["cas"]["password"])

    # Get messages
    while True:
        log.info("Pull messages from ams")
        messages, ids = ams.pull(1)
        log.info("Received " + str(len(messages)) + " messages from ams")
        if len(messages) > 0:
            username = config["cas"]["username"]
            password = config["cas"]["password"]
            cas_url = config["cas"]["cas_url"]

            ams.ack(ids)
            responses = process_data(messages, cas_agent, perun_client_api)
            publish_ams(responses, ams, log)
        time.sleep(config["cas"]["ams"]["poll_interval"])
    log.info("Exit script")
