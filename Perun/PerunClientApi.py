from Perun.PerunRpcAdapter import PerunRpcAdapter, PerunUnknownException, PerunConnectionException


class PerunProcessingException(Exception):
    pass


class PerunClientApi(object):
    ATTRIBUTE_BEAN_NAME = "Attribute"

    def __init__(self, config):
        # required
        api_url = config["api_url"]
        self.sp_managers_vo_id = config["sp_managers_vo_id"]
        self.ext_source_name = config["ext_source_name"]
        self.id_perun_attribute = config["id_attribute"]
        self.managers_group_perun_attribute = config["managers_group_attribute"]

        # optional
        username = config.get("username")
        password = config.get("password")
        self.sp_managers_parent_group_id = config.get("sp_managers_parent_group_id")
        self.properties_mapping = config.get("properties_mapping")
        self.static_attributes = config.get("static_attributes")

        self.perun_rpc_adapter = PerunRpcAdapter(api_url, username, password)

    def set_user_as_service_manager(self, facility_id, admins_group_id, user_id):
        if not self.perun_rpc_adapter.add_group_as_admins(facility_id, admins_group_id):
            print(
                f"Could not set group {admins_group_id} as managers for facility {facility_id}"
            )
            return False
        member_id = self.perun_rpc_adapter.get_member_id_by_user(self.sp_managers_vo_id, user_id)
        if member_id is None:
            print(
                f"Could not set user {user_id} as manager in group {admins_group_id}, user does not have member"
            )
            return False
        return self.perun_rpc_adapter.add_member_to_group(admins_group_id, member_id)

    def get_perun_attr_name_namespace(self, perun_attr):
        name_parts = perun_attr.split(":")
        namespace = ":".join(name_parts[:5])
        friendly_name = ":".join(name_parts[5:])
        return friendly_name, namespace

    def build_perun_attribute(self, perun_attr_config, value):
        attr_name, attr_namespace = self.get_perun_attr_name_namespace(perun_attr_config["attribute"])

        value_mapping = perun_attr_config.get("value_mapping")
        if value_mapping:
            value = value_mapping.get(value)

        attribute = {
            "id": perun_attr_config["id"],
            "beanName": self.ATTRIBUTE_BEAN_NAME,
            "namespace": attr_namespace,
            "friendlyName": attr_name,
            "type": perun_attr_config["type"],
            "value": value,
        }

        if "unique" in perun_attr_config:
            attribute["unique"] = perun_attr_config["unique"]
        return attribute

    def build_perun_static_attributes(self):
        perun_static_attributes = []
        for static_attribute in self.static_attributes:
            perun_static_attributes.append(self.build_perun_attribute(static_attribute, static_attribute["value"]))
        return perun_static_attributes

    def build_perun_attributes(self, perun_message):
        perun_attributes = [self.build_perun_attribute(self.id_perun_attribute, perun_message["id"])]
        for serv_property, attr_mapping in self.properties_mapping.items():
            if serv_property not in perun_message:
                continue
            attr_value = perun_message.get(serv_property)

            if isinstance(attr_mapping, list):
                # Mapping property to multiple attributes
                for item in attr_mapping:
                    perun_attributes.append(self.build_perun_attribute(item, attr_value))
            else:
                perun_attributes.append(self.build_perun_attribute(attr_mapping, attr_value))

        if self.static_attributes:
            perun_attributes.extend(self.build_perun_static_attributes())

        return perun_attributes

    def delete_admins_group(self, facility_id):
        try:
            admins_group_id = self.perun_rpc_adapter.get_facility_attribute_value(
                facility_id, self.managers_group_perun_attribute["attribute"]
            )
            if admins_group_id:
                result = self.perun_rpc_adapter.delete_group(admins_group_id)
                if not result:
                    print(f"Could not delete group {admins_group_id}")
            else:
                print("No admins group ID found for facility: " + facility_id)
        except Exception as e:
            raise PerunProcessingException("Perun exception caught when deleting admins group", e)

    def delete_facility(self, facility_id):
        try:
            self.perun_rpc_adapter.delete_facility(facility_id)
        except Exception as e:
            raise PerunProcessingException("Perun exception caught when deleting facility", e)

    def register_new_service_in_perun(self, perun_message):
        service_name = perun_message["service_name"]
        service_identifier = ""
        if perun_message["protocol"] == "saml":
            service_identifier = perun_message["entity_id"]
        elif perun_message["protocol"] == "oidc":
            service_identifier = perun_message["client_id"]
        admin_sub = perun_message["requester"]
        perun_attributes = self.build_perun_attributes(perun_message)

        try:
            facility = self.perun_rpc_adapter.create_facility_in_perun(service_name, service_identifier)
            if not facility or not facility.get("id") or not facility.get(
                    "name"
            ).strip():
                print("Creating facility in Perun has failed")
                return False
            facility_id = facility.get("id")
        except (PerunUnknownException, PerunConnectionException):
            print("Creating facility in Perun has failed")
            return False

        admins_group_id = None
        try:
            admins_group = self.perun_rpc_adapter.create_admins_group(service_name, self.sp_managers_vo_id,
                                                                      self.sp_managers_parent_group_id)
            if not admins_group:
                raise PerunProcessingException("Could not create admins group")
            admins_group_id = admins_group.get("id")

            user_id = self.perun_rpc_adapter.get_user_id(admin_sub, self.ext_source_name)
            if not user_id:
                raise PerunProcessingException("Could not find requester in perun.")

            if not self.set_user_as_service_manager(
                    facility_id,
                    admins_group_id,
                    user_id,
            ):
                raise PerunProcessingException("Could not set managers group")
            perun_attributes.append(self.build_perun_attribute(self.managers_group_perun_attribute, admins_group_id))
            if not self.perun_rpc_adapter.set_facility_attributes(
                    facility_id,
                    perun_attributes
            ):
                raise PerunProcessingException("Setting new attributes has failed")
        except Exception as e:
            print("Caught an exception when registering service to Perun", e)
            if admins_group_id is not None:
                try:
                    self.perun_rpc_adapter.delete_group(admins_group_id)
                except Exception as e_group:
                    print("Caught an exception when removing admin group", e_group)
            try:
                self.perun_rpc_adapter.delete_facility(facility_id)
            except Exception as e_facility:
                print("Caught an exception when removing facility", e_facility)
            return False
        return True

    def update_service_in_perun(self, perun_message):
        try:
            facilities = self.perun_rpc_adapter.get_facilities_by_attributes(
                self.id_perun_attribute["attribute"], perun_message["id"]
            )
            if not facilities:
                print("No facility found in Perun for service id: " + perun_message["id"])
                return False
            facility = facilities[0]
            service_identifier = ""
            facility_id = facility.get("id")
            if perun_message["protocol"] == "saml":
                service_identifier = perun_message["entity_id"]
            elif perun_message["protocol"] == "oidc":
                service_identifier = perun_message["client_id"]
            if facility["name"] != perun_message["service_name"] or (
                    service_identifier and facility["description"] != service_identifier):
                facility["name"] = perun_message["service_name"]
                facility["description"] = service_identifier
                if not self.perun_rpc_adapter.update_facility(facility):
                    print("Updating facility name or description failed for facility with id: " + facility_id)
                    return False
            perun_attributes = self.build_perun_attributes(perun_message)
            if not self.perun_rpc_adapter.set_facility_attributes(
                    facility_id,
                    perun_attributes
            ):
                print("Updating facility attributes failed for facility with id: " + facility_id)
                return False
        except Exception as e:
            print("Caught an exception when updating service in Perun", e)
            return False
        return True

    def delete_service_in_perun(self, perun_message):
        try:
            facilities = self.perun_rpc_adapter.get_facilities_by_attributes(
                self.id_perun_attribute["attribute"], perun_message["id"]
            )
            facility_ids = [facility.get("id") for facility in facilities]

            if not facility_ids:
                print("No facility found in Perun for service id: " + perun_message["id"])
                return False
            facility_id = facility_ids[0]
            self.delete_admins_group(facility_id)

            self.perun_rpc_adapter.delete_facility(facility_id)
        except Exception as e:
            print("Caught an exception when deleting service", e)
            return False
        return True
