import requests
from requests import request

from Utils.common import http_request

"""
Manages all clients on MITREid Connect

"""


class mitreidClientApi:

    """
    Class constructor

    Parameters:
        issuer (str): The URI of the Authorization Server
        token  (str): An access token with admin privileges

    """

    def __init__(self, issuer, token):
        self.issuer = issuer
        self.token = token

    """
    Get all registered clients

    Returns:
        response (JSON Object): All registered clients in JSON format
    """

    def getClients(self):
        url = self.issuer + "/api/clients"
        header = {"Authorization": "Bearer " + self.token}

        return http_request("GET", url, header)

    """
    Get a registered client by ID

    Parameters:
        id (str): The id of the client
    
    Returns:
        response (JSON Object): A registered client in JSON format
    """

    def getClientById(self, id):
        url = self.issuer + "/api/clients/" + str(id)
        header = {"Authorization": "Bearer " + self.token}

        return http_request("GET", url, header)

    """
    Register new client

    Parameters:
        clientObject (str): A string with the client data in JSON format
    
    Returns:
        response (JSON Object): The registered client in JSON format
    """

    def createClient(self, clientObject):
        url = self.issuer + "/api/clients"
        header = {
            "Authorization": "Bearer " + self.token,
            "Content-Type": "application/json",
        }

        return http_request("POST", url, header, clientObject)

    """
    Update an existing client by ID

    Parameters:
        id (str): The id of the client
        clientObject (str): A string with the client data in JSON format
    
    Returns:
        response (JSON Object): The registered client in JSON format
    """

    def updateClientById(self, id, clientObject):
        url = self.issuer + "/api/clients/" + str(id)
        header = {
            "Authorization": "Bearer " + self.token,
            "Content-Type": "application/json",
        }

        return http_request("PUT", url, header, clientObject)

    """
    Delete a registered client by ID

    Parameters:
        id (str): The id of the client
    
    Returns:
        response (boolean): True if the client was deleted successfully
    """

    def deleteClientById(self, id):
        url = self.issuer + "/api/clients/" + str(id)
        header = {"Authorization": "Bearer " + self.token}

        return http_request("DELETE", url, header)
