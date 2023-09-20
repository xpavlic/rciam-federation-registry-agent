import requests

if __name__ == '__main__':
    print(requests.get("https://msg-devel.argo.grnet.gr/v1/projects/rciam-service-registry/subscriptions/muni-deployment-results-topic_muni_service_ssp_demo_deployer:offsets?key=").text)

    print(requests.post("https://msg-devel.argo.grnet.gr/v1/projects/rciam-service-registry/subscriptions/muni-deployment-results-topic_muni_service_ssp_demo_deployer:modifyOffset?key=", json={"offset": 0}).text)
