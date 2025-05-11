"""
@AUTHOR Jan Pavlíček (xpavli95@stud.fit.vutbr.cz)
"""

import json
import logging

import requests

log = logging.getLogger(__name__)


class PerunConnectionException(Exception):
    pass


class PerunUnknownException(Exception):
    pass


class PerunRpcAdapter:
    """
    Class for communication with the Perun Rpc
    """
    FACILITIES_MANAGER = "facilitiesManager"
    GROUPS_MANAGER = "groupsManager"
    MEMBERS_MANAGER = "membersManager"
    USERS_MANAGER = "usersManager"
    ATTRIBUTES_MANAGER = "attributesManager"

    PARAM_FACILITY = "facility"
    PARAM_GROUP = "group"
    PARAM_PARENT_GROUP = "parentGroup"
    PARAM_VO = "vo"
    PARAM_USER = "user"
    PARAM_MEMBER = "member"
    PARAM_AUTHORIZED_GROUP = "authorizedGroup"
    PARAM_EXT_SOURCE_NAME = "extSourceName"
    PARAM_EXT_LOGIN = "extLogin"
    PARAM_ATTRIBUTES = "attributes"
    PARAM_FORCE = "force"
    PARAM_ATTRIBUTE_NAME = "attributeName"
    PARAM_ATTRIBUTE_VALUE = "attributeValue"

    FACILITY_BEAN_NAME = "Facility"
    GROUP_BEAN_NAME = "Group"

    def __init__(self, api_url, username, password):
        self.api_url = api_url
        self.username = username
        self.password = password

    def handle_http_client_error_exception(self, exception, action_url, response):
        """
        Method for handling errors received from Perun IDM. It filters known Perun exceptions and raises unknown ones.
        """
        content_type = response.headers.get("Content-Type", "")

        if "json" in content_type.lower():
            try:
                json_data = response.json()
                if "errorId" in json_data and "name" in json_data:
                    if json_data["name"] in {
                        "ExtSourceNotExistsException",
                        "FacilityNotExistsException",
                        "GroupNotExistsException",
                        "MemberNotExistsException",
                        "ResourceNotExistsException",
                        "VoNotExistsException",
                        "UserNotExistsException",
                    }:
                        return None

            except json.JSONDecodeError:
                log.critical("Cannot parse error message from JSON")
                raise PerunUnknownException(exception)

        log.critical(
            f"HTTP ERROR {response.status_code} URL {action_url} Content-Type: {content_type} response: {response.text}"
        )
        raise PerunUnknownException(exception)

    def call_perun_api(self, manager, method, body):
        """
        Method for calling Perun RPC API
        """
        action_url = f"{self.api_url}/{manager}/{method}"

        try:
            response = requests.post(action_url,
                                     headers={'Content-Type': 'application/json'},
                                     json=body,
                                     auth=(self.username, self.password))
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as ex:
            return self.handle_http_client_error_exception(ex, action_url, response)
        except Exception as e:
            raise PerunConnectionException(e)

    def create_facility_in_perun(self, facility_name, facility_description):
        """
        Method creates facility in Perun with facility name and description
        """
        facility = {
            "id": None,
            "name": facility_name,
            "description": facility_description,
            "beanName": self.FACILITY_BEAN_NAME
        }
        body = {self.PARAM_FACILITY: facility}
        return self.call_perun_api(self.FACILITIES_MANAGER, "createFacility", body)

    def create_admins_group(self, facility_name, sp_managers_vo_id, sp_managers_parent_group_id=None):
        """
        Method creates admin group in Perun within desired VO and optionally as subgroup of other group.
        """
        group = {
            "id": None,
            "shortName": facility_name,
            "name": facility_name,
            "description": f"Administrators of SP - {facility_name}",
            "beanName": self.GROUP_BEAN_NAME,
            "parentGroupId": sp_managers_parent_group_id,
            "voId": sp_managers_vo_id
        }
        body = {self.PARAM_GROUP: group}
        if sp_managers_parent_group_id is None:
            body[self.PARAM_VO] = sp_managers_vo_id
        else:
            body[self.PARAM_PARENT_GROUP] = sp_managers_parent_group_id
        return self.call_perun_api(self.GROUPS_MANAGER, "createGroup", body)

    def get_user_id(self, sub, ext_source_name):
        """
        Method finds a user by its unique ID and Identity providers identifier. It returns the id of the user.
        """
        body = {
            self.PARAM_EXT_SOURCE_NAME: ext_source_name,
            self.PARAM_EXT_LOGIN: sub
        }
        perun_user = self.call_perun_api(
            self.USERS_MANAGER,
            "getUserByExtSourceNameAndExtLogin",
            body
        )
        if not perun_user:
            log.warning(
                f"User with sub: {sub} and ext source {ext_source_name} not found in Perun"
            )
            return None
        return perun_user.get("id")

    def add_group_as_admins(self, facility_id, admins_group_id):
        """
        Method for setting group as managers group of the facility.
        """
        body = {
            self.PARAM_FACILITY: facility_id,
            self.PARAM_AUTHORIZED_GROUP: admins_group_id
        }
        result = self.call_perun_api(self.FACILITIES_MANAGER, "addAdmin", body)
        return result is None

    def get_member_id_by_user(self, vo_id, user_id):
        """
        Method for getting member id of user within the VO
        """
        body = {self.PARAM_VO: vo_id, self.PARAM_USER: user_id}
        result = self.call_perun_api(self.MEMBERS_MANAGER, "getMemberByUser", body)
        if result is None:
            raise PerunUnknownException("User is not member in VO")
        return result.get("id")

    def add_member_to_group(self, group_id, member_id):
        """
        Method for adding VO member to group
        """
        body = {self.PARAM_GROUP: group_id, self.PARAM_MEMBER: member_id}
        result = self.call_perun_api(self.GROUPS_MANAGER, "addMember", body)
        return result is None

    def set_facility_attributes(self, facility_id, perun_attributes):
        """
        Method for setting facility attributes
        """
        body = {
            self.PARAM_FACILITY: facility_id,
            self.PARAM_ATTRIBUTES: perun_attributes
        }
        result = self.call_perun_api(self.ATTRIBUTES_MANAGER, "setAttributes", body)
        return result is None

    def delete_facility(self, facility_id):
        """
        Method for deleting facility
        """
        body = {
            self.PARAM_FACILITY: facility_id,
            self.PARAM_FORCE: True
        }
        result = self.call_perun_api(self.FACILITIES_MANAGER, "deleteFacility", body)
        return result is None

    def delete_group(self, group_id):
        """Method for deleting group"""
        body = {
            self.PARAM_GROUP: group_id,
            self.PARAM_FORCE: True
        }
        result = self.call_perun_api(self.GROUPS_MANAGER, "deleteGroup", body)
        return result is None

    def get_facility_attribute_value(self, facility_id, attribute_urn):
        """
        Method for getting facility attribute value
        """
        body = {
            self.PARAM_FACILITY: facility_id,
            self.PARAM_ATTRIBUTE_NAME: attribute_urn
        }
        result = self.call_perun_api(self.ATTRIBUTES_MANAGER, "getAttribute", body)
        return result.get("value")

    def get_facilities_by_attributes(self, attribute_name, attribute_value):
        """
        Method for getting all facilities with the attribute set to specific value
        """
        body = {
            self.PARAM_ATTRIBUTE_NAME: attribute_name,
            self.PARAM_ATTRIBUTE_VALUE: attribute_value
        }
        result = self.call_perun_api(self.FACILITIES_MANAGER, "getFacilitiesByAttribute", body)
        return result

    def update_facility(self, facility):
        """
        Method for updating facility
        """
        body = {
            self.PARAM_FACILITY: facility,
        }
        result = self.call_perun_api(self.FACILITIES_MANAGER, "updateFacility", body)
        return result is not None
