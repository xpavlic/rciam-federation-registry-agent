# rciam-federation-registry-agent

**RCIAM Federation Registry Agent** main objective is to sync data between RCIAM Federation Registry and
different identity and access management solutions, such as Keycloak, SATOSA, SimpleSAMLphp, MITREid Connect and Apereo
CAS. In addition to syncing data with the mentioned software, this synchronization can also be extended to include the
Perun identity management system.

This python library includes a module named `ServiceRegistryAms/` to pull and publish messages from ARGO Messaging
Service using the argo-ams-library, an API module named `MitreidConnect/` to communicate with the API of the MITREid, an
API module named `Keycloak/` to communicate with the API of the Keycloak, an API module named `CAS/` to communicate
with api of the Apereo CAS and an API module named `Perun/` to communicate with the API of the Perun.
The main standalone scripts that are used to deploy updates to the third party services are under `bin/`:

- `deployer_keycloak.py` for Keycloak
- `deployer_mitreid.py` for MITREid
- `deployer_ssp.py` for SimpleSAMLphp
- `deployer_cas.py` for Apereo CAS
- `deployer_cas_rabbitmq.py` just as above but uses `RabbitMQ` instead of `AMS`. `pika` library is used for communication with RabbitMQ server.

## Installation

First install the packages from the requirements.txt file

```bash
pip install -r requirements.txt
```

Install rciam-federation-registry-agent

```bash
pip install rciam-federation-registry-agent
```

## Usage

### deployer_keycloak

deployer_keycloak requires the path of the config file as an argument

```bash
deployer_keycloak -c example_deployers.config.json
```

### deployer_mitreid

deployer_mitreid requires the path of the config file as an argument

```bash
deployer_mitreid.py -c example_deployers.config.json
```

### deployer_ssp

deployer_ssp requires the path of the config file as an argument

```bash
deployer_ssp.py -c example_deployers.config.json
```

### deployer_cas

deployer_cas requires the path of the config file as an argument

```bash
deployer_cas.py -c example_deployers.config.json
```

### deployer_cas_rabbitmq

deployer_cas_rabbitmq requires the path of the config file as an argument

```bash
deployer_cas_rabbitmq.py -c example_deployers.config.json
```

## Configuration

An example of the required configuration file can be found in conf/example_deployers.config.json. The different
configuration options are described below.

```json
{
  "keycloak": {
    "ams": {
      "host": "example.host.com",
      "project": "ams-project-name-keycloak",
      "pull_topic": "ams-topic-keycloak",
      "pull_sub": "ams-sub-keycloak",
      "token": "ams-token-keycloak",
      "pub_topic": "ams-publish-topic-keycloak",
      "poll_interval": 1
    },
    "auth_server": "https://example.com/auth",
    "realm": "example",
    "client_id": "client ID",
    "client_secret": "client secret"
  },
  "mitreid": {
    "ams": {
      "host": "example.host.com",
      "project": "ams-project-name-mitreid",
      "pull_topic": "ams-topic-mitreid",
      "pull_sub": "ams-sub-mitreid",
      "token": "ams-token-mitreid",
      "pub_topic": "ams-publish-topic-mitreid",
      "poll_interval": 1
    },
    "issuer": "https://example.com/oidc",
    "refresh_token": "refresh token",
    "client_id": "client ID",
    "client_secret": "client secret"
  },
  "ssp": {
    "ams": {
      "host": "example.host.com",
      "project": "ams-project-name-ssp",
      "pull_topic": "ams-topic-ssp",
      "pull_sub": "ams-sub-ssp",
      "token": "ams-token-ssp",
      "pub_topic": "ams-publish-topic-ssp",
      "poll_interval": 1,
      "deployer_name": "1"
    },
    "metadata_conf_file": "/path/to/ssp/metadata/file.php",
    "cron_secret": "SSP cron secret",
    "cron_url": "http://localhost/proxy/module.php/cron/cron.php",
    "cron_tag": "hourly",
    "request_timeout": 100
  },
  "cas": {
    "cas_url": "https://example.host.com/cas",
    "username": "admin",
    "password": "password",
    "ams": {
      "host": "example.host.com",
      "project": "ams-project-name-cas",
      "pull_topic": "ams-topic-cas",
      "pull_sub": "ams-sub-cas",
      "token": "ams-token-cas",
      "pub_topic": "ams-publish-topic-cas",
      "poll_interval": 1
    },
    "rabbitmq": {
      "host": "example.host.com",
      "vhost": "rabbitmq-vhost",
      "pub_queue": "results_queue",
      "sub_queue": "deploying_cas_tasks_q",
      "username": "theName-isThe",
      "password": "superSecretPwd"
    }
  },
  "log_conf": "conf/logger.conf"
}
```

As shown above there are three main groups, namely Keycloak, MITREid, SSP and CAS and each group can have its own AMS
settings and service specific configuration values. The only global value is the `log_conf` path if you want to use the
same logging configuration for both of the deployers. In case you need a different configuration for a deployer you can
add log_conf in the scope of "MITREid" or "SSP" or "CAS".

When using the `RabbitMQ` version of the CAS deployer, you can omit the `ams` scope entirely as it's not used. Just like that you can also omit the `rabbitmq` scope when `ams` is used.

### Configuration with sync to Perun IDM

An example of the required configuration file can be found in conf/example_deployer_perun.config.json. The different
configuration options are described below.

```json
{
  "cas": {
    "cas_url": "https://example.host.com/cas",
    "username": "admin",
    "password": "password",
    "ams": {
      "host": "example.host.com",
      "project": "ams-project-name-cas",
      "pull_topic": "ams-topic-cas",
      "pull_sub": "ams-sub-cas",
      "token": "ams-token-cas",
      "pub_topic": "ams-publish-topic-cas",
      "poll_interval": 1
    },
    "perun": {
      "api_url": "https://example.host.com/ba/rpc/json",
      "username": "username",
      "password": "password",
      "ext_source_name": "https://example.com/idp/",
      "sp_managers_vo_id": 3898,
      "sp_managers_parent_group_id": 13110,
      "id_attribute": {
        "id": 3560,
        "type": "java.lang.Integer",
        "attribute": "urn:perun:facility:attribute-def:def:serviceIdInMitre"
      },
      "managers_group_attribute": {
        "id": 3613,
        "type": "java.lang.Integer",
        "attribute": "urn:perun:facility:attribute-def:def:rpManagersGroupId"
      },
      "properties_mapping": {
        "client_id": [
          {
            "id": 3624,
            "type": "java.lang.String",
            "attribute": "urn:perun:facility:attribute-def:def:rpIdentifier",
            "unique": true
          },
          {
            "id": 3482,
            "type": "java.lang.String",
            "attribute": "urn:perun:facility:attribute-def:def:OIDCClientID",
            "unique": true
          }
        ],
        "entity_id": [
          {
            "id": 3624,
            "type": "java.lang.String",
            "attribute": "urn:perun:facility:attribute-def:def:rpIdentifier",
            "unique": true
          },
          {
            "id": 3395,
            "type": "java.lang.String",
            "attribute": "urn:perun:facility:attribute-def:def:entityID",
            "unique": true
          }
        ],
        "integration_environment": [
          {
            "id": 3515,
            "type": "java.lang.Boolean",
            "attribute": "urn:perun:facility:attribute-def:def:isTestSp",
            "value_mapping": {
              "demo": true,
              "development": true,
              "production": false
            }
          }
        ]
      },
      "static_attributes": [
        {
          "id": 3578,
          "type": "java.lang.String",
          "attribute": "urn:perun:facility:attribute-def:def:masterProxyIdentifier",
          "value": "https://login.cesnet.cz/idp/"
        }
      ]
    }
  },
  "log_conf": "conf/logger.conf"
}
```

The `perun` part of the configuration can be used same for each type of the deployer. And properties have the following
meanings

- `api_url` url to perun rpc
- `username` (optional) user to be used for the authorization
- `password` (optional) password to be used for the authorization
- `ext_source_name` user identity provider name (for finding user in Perun)
- `sp_managers_vo_id` id of the VO in which the managers groups will be created
- `sp_managers_parent_group_id` (optional) managers group will be created as subgroup of this group
- `id_attribute` attribute to bind service from Federation registry to facility in Perun (store service id in this attr)
- `managers_group_attribute` facility attribute to link facility managers group with facility
- `properties_mapping` mapping of properties to perun facility attributes
- `static_attributes` fill static value to facility attributes (not mapped to any property but fixed values)

The attributes config is equal to Perun attribute definition. Properties can be mapped to multiple attributes if mapped
to list of attribute definitions. With `value_mapping`. Property values can be mapped to different values in perun
attributes (shown with `integration_environment` property mapping example).

### ServiceRegistryAms

Use ServiceRegistryAms as a manager to pull and publish messages from AMS

```python
from ServiceRegistryAms.PullPublish import PullPublish

with open('config.json') as json_data_file:
    config = json.load(json_data_file)
    ams = PullPublish(config)

    message = ams.pull(1)
    ams.publish(args)
```

### Keycloak

Use Keycloak as an API manager to communicate with Keycloak

- First obtain an access token and create the Keycloak API Client (find client_credentials_grant under `Utils`
  directory)

```python
  access_token = client_credentials_grant(issuer_url, client_id, client_secret)
keycloak_agent = KeycloakClientApi(issuer_url, access_token)
```

- Use the following functions to create, delete and update a service on client_credentials_grant

```python
  response = keycloak_agent.create_client(keycloak_msg)
response = keycloak_agent.update_client(external_id, keycloak_msg)
response = keycloak_agent.delete_client(external_id)
```

### MITREid Connect

Use MITREid Connect as an API manager to communicate with MITREid

- First obtain an access token and create the MITREid API Client (find refresh_token_grant under `Utils` directory)

```python
  access_token = refresh_token_grant(issuer_url, refresh_token, client_id, client_secret)
mitreid_agent = mitreidClientApi(issuer_url, access_token)
```

- Use the following functions to create, delete and update a service on MITREid

```python
  response = mitreid_agent.createClient(mitreid_msg)
response = mitreid_agent.updateClientById(external_id, mitreid_msg)
response = mitreid_agent.deleteClientById(external_id)
```

## License

[Apache](http://www.apache.org/licenses/LICENSE-2.0)
