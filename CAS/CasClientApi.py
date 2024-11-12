import requests

from Utils.common import http_request


class CasClientApi:
    registered_services_endpoint = '/actuator/registeredServices'
    oidc_type = "OidcRegisteredService"
    saml_type = "SAMLRegisteredService"

    def __init__(self, cas_url, username, password):
        self.username = username
        self.password = password
        self.url = cas_url + self.registered_services_endpoint

    def get_clients(self):
        return http_request(
            "GET", self.url, {}, auth=(self.username, self.password)
        )

    def get_client_by_client_id(self, client_id):
        url = f"{self.url}/type/{self.oidc_type}"
        response = http_request(
            "GET", url, {}, auth=(self.username, self.password)
        )
        client = None
        if response.get("error"):
            return response
        elif len(response.get("response")) != 0:
            client = next(
                (item for item in response.get("response")[1] if
                 item.get('clientId') == client_id),
                None
            )
        response["response"] = client
        return response

    def get_client_by_entity_id(self, entity_id):
        url = f"{self.url}/type/{self.saml_type}"
        response = http_request(
            "GET", url, {}, auth=(self.username, self.password)
        )
        client = None
        if response.get("error"):
            return response
        elif len(response.get("response")) != 0:
            client = next(
                (item for item in response.json()[1] if
                 item.get('serviceId') == entity_id),
                None
            )
        response["response"] = client
        return response

    def create_client(self, client_object):
        return http_request(
            "POST",
            self.url,
            {},
            data=client_object,
            auth=(self.username, self.password)
        )

    def update_client(self, client_object):
        return http_request(
            "PUT",
            self.url,
            {},
            data=client_object,
            auth=(self.username, self.password)
        )

    def delete_client_by_external_id(self, external_id):
        url = self.url + "/" + str(external_id)
        return http_request(
            "DELETE",
            url,
            {},
            auth=(self.username, self.password)
        )
