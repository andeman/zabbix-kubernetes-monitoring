#!/usr/bin/env python

import json
import os
import ssl
import sys
import time

try:
    import urllib.request as urllib2
except ImportError:
    import urllib2

config_file = "/etc/zabbix/k8s-stats.json"
tmp_file_dir = "/tmp/"
cache_ttl = 60
# Script parameters
cluster = sys.argv[1]
method = sys.argv[2]
target = sys.argv[3]
object_namespace = None
object_name = None
object_state = None
container_name = None

if method == "stats":
    object_namespace = sys.argv[4]
    object_name = sys.argv[5]
    if target == "container" or target == "pod" or target == "deployments":
        object_state = sys.argv[6]
    if target == "container":
        container_name = sys.argv[7]

if os.path.isfile(config_file) and os.access(config_file, os.R_OK):
    with open(config_file, "r") as json_file:
        config = json.load(json_file)
else:
    print("Config file is missing or not readable. File [{}]".format(config_file))

api_server = config[cluster]["api_url"]
token = config[cluster]["access_token"]

targets = [
    "pods",
    "nodes",
    "containers",
    "deployments",
    "apiservices",
    "componentstatuses",
]
target = "pods" if "containers" == target else target

if "pods" == target or "nodes" == target or "componentstatuses" == target:
    api_req = "/api/v1/{}".format(target)
elif "deployments" == target:
    api_req = "/apis/apps/v1/{}".format(target)
elif "apiservices" == target:
    api_req = "/apis/apiregistration.k8s.io/v1/{}".format(target)


def rawdata(qtime=cache_ttl):
    if target in targets:
        tmp_file = "{}/kubernetes_stats_{}_{}.tmp".format(tmp_file_dir, cluster, target)
        tmp_file_exists = True if os.path.isfile(tmp_file) else False
        if tmp_file_exists and (time.time() - os.path.getmtime(tmp_file)) <= qtime:
            file = open(tmp_file, "r")
            data = file.read()
            file.close()
        else:
            # Fix for self signed certs
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            req = urllib2.Request(api_server + api_req)
            req.add_header("Authorization", "Bearer {}".format(token))
            # Use context with no ssl check for selfsigned certs
            data = urllib2.urlopen(req, context=ctx).read()

            with open(tmp_file, "wb") as f:
                f.write(data)

            if not tmp_file_exists:
                os.chmod(tmp_file, 0o666)

        return data
    else:
        return False


if target in targets:

    if "discovery" == method:
        # discovery
        result = {"data": []}
        data = json.loads(rawdata())

        for item in data["items"]:
            if (
                "nodes" == target
                or "componentstatuses" == target
                or "apiservices" == target
            ):
                result["data"].append({"{#NAME}": item["metadata"]["name"]})
            elif "containers" == target:
                for cont in item["spec"]["containers"]:
                    result["data"].append(
                        {
                            "{#NAME}": item["metadata"]["name"],
                            "{#NAMESPACE}": item["metadata"]["namespace"],
                            "{#CONTAINER}": cont["name"],
                        }
                    )
            else:
                result["data"].append(
                    {
                        "{#NAME}": item["metadata"]["name"],
                        "{#NAMESPACE}": item["metadata"]["namespace"],
                    }
                )

        print(json.dumps(result))

    elif "stats" == method:
        # stats
        data = json.loads(rawdata(100))

        if "pods" == target or "deployments" == target:
            for item in data["items"]:
                if (
                    item["metadata"]["namespace"] == object_namespace
                    and item["metadata"]["name"] == object_name
                ):
                    if "statusPhase" == object_state:
                        print(item["status"]["phase"])
                    elif "statusReason" == object_state:
                        if "reason" in item["status"]:
                            print(item["status"]["reason"])
                    elif "statusReady" == object_state:
                        for status in item["status"]["conditions"]:
                            if status["type"] == "Ready" or (
                                status["type"] == "Available"
                                and "deployments" == target
                            ):
                                print(status["status"])
                                break
                    elif "containerReady" == object_state:
                        for status in item["status"]["containerStatuses"]:
                            if status["name"] == container_name:
                                if (
                                    status["ready"]
                                    or item["status"]["phase"] == "Succeeded"
                                ):
                                    print(True)
                                else:
                                    print(False)
                                break
                    elif "containerRestarts" == object_state:
                        for status in item["status"]["containerStatuses"]:
                            if status["name"] == container_name:
                                print(status["restartCount"])
                                break
                    elif "Replicas" == object_state:
                        print(item["spec"]["replicas"])
                    elif "updatedReplicas" == object_state:
                        if "updatedReplicas" in item["status"]:
                            print(item["status"]["updatedReplicas"])
                        else:
                            print("0")
                    break
        if "nodes" == target or "apiservices" == target:
            for item in data["items"]:
                if item["metadata"]["name"] == object_namespace:
                    for status in item["status"]["conditions"]:
                        if status["type"] == object_name:
                            print(status["status"])
                            break
        elif "componentstatuses" == target:
            for item in data["items"]:
                if item["metadata"]["name"] == object_namespace:
                    for status in item["conditions"]:
                        if status["type"] == object_name:
                            print(status["status"])
                            break