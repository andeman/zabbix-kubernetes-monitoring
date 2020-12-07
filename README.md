#### Table of Contents

1. [Description](#description)
1. [Concept](#concept)
1. [Requirements](#requirements)
1. [Usage](#usage)
    - [Installation](#installation)
    - [Multi-Cluster support](#multi-cluster-support)
    - [How to create a Zabbix user in Kubernetes](#how-to-create-a-zabbix-user-in-kubernetes)
    - [How to retrieve TOKEN and API SERVER](#how-to-retrieve-token-and-api-server)

## Description
A Zabbix template to monitor Kubernetes. It is easy to deploy and configure. The template includes auto discovery of pods, deployments, services, etc.

## Concept

This template was designed around a unique monitoring concept. In order
to understand the design decisions made, a quick summary is outlined below.

Design goals:

* Avoid false-alerts
* Avoid trigger flapping
* Reduce overall monitoring "noise"

To achieve these goals the following principles were applied:

* Trigger severity has a **distinct meaning**
  * `Warning` – Alert is only displayed in Zabbix GUI. No notifications will be send.
  * `High` – All previous, plus the alert is send via e-mail. (Typical 5x8 alert.)
  * `Disaster` – All previous, plus the alert is send via instant messaging or SMS. (Typical 7x24 alert.)
  * Note: Zabbix "Actions" need to be configured accordingly.

* Enforce 3-step escalation and delay alarms
  * After at least two failures a `Warning` trigger may fire.
  * If the problem persists for the time period specified by `{$ESCALATION_1_DELAY}`, then the `High` trigger fires.
  * If the problem persists for the time period specified by `{$ESCALATION_2_DELAY}`, then the `Disaster` trigger fires.
  * These triggers have dependencies defined, i.e. a `Warning` trigger is closed when the `High` trigger fires.

As a result, *every* alarm starts with a `Warning` trigger, which should
not send any notifications. Only if enough time has passed, then a `High`
or `Disaster` trigger will be activated and notifications will be send.

This simple approach ensures that load spikes or small hiccups do not
cause any alarms/notifications. Additionally triggers are not resolved
too soon (which would result in trigger flapping), but instead a certain
amount of time has to pass.

Of course, this delay can be customized by defining `{$ESCALATION_1_DELAY}`
and `{$ESCALATION_2_DELAY}` on a per-host level.

## Requirements

Basic requirements for this template:

* Zabbix Server version 4.4 or later
* Kubernetes version 1.16 or later
* Python 3.x

Besides that the 3-step escalation requires that you define the following
global macros:

* `{$ESCALATION_1_DELAY}`, i.e. with a value of `600`
* `{$ESCALATION_2_DELAY}`, i.e. with a value of `1200`

If you want to completely disable the escalation delay, then you may
set these values to `0` (NOT RECOMMENDED).

## Usage

### Installation

1. Copy `k8s-stats.py` to /usr/lib/zabbix/externalscripts and `k8s-stats.json` to /etc/zabbix/ and fix file permissions
```
cp k8s-stats.py /usr/lib/zabbix/externalscripts/
cp k8s-stats.json /etc/zabbix/
chmod +x /usr/lib/zabbix/externalscripts/k8s-stats.py
chown zabbix. /etc/zabbix/k8s-stats.json
chmod 640 /etc/zabbix/k8s-stats.json
```
2. Import Zabbix template `k8s-zabbix-template.xml` to Zabbix server
3. Create zabbix user in Kubernetes (can use `zabbix-user-example.yml`) and set it's token and API server url in `k8s-stats.json`. The root item key names in JSON config refer to 
4. Apply template to host `{$K8S_CLUSTER_NAME}` macro value in zabbix configuration, see step 5.
5. Update `{$K8S_CLUSTER_NAME}` macro value appropriately in host configuration. Example:
```json
{
    "my-cloud-123": {
        "api_url": "https://my_cloud_address:6443",
        "access_token": "my_cloud_token"
    }
}
```
You then need to use `{$K8S_CLUSTER_NAME} => my-cloud-123` on zabbix host you have attached the template to

### Multi-Cluster support

Simply add more dicts to `k8s_stats.json`. Sample config file provided in repo has two clusters added.

### How to create a Zabbix user in Kubernetes

```bash
$ kubectl apply -n kube-system -f zabbix-user-example.yml 
serviceaccount/zabbix-user created
clusterrole.rbac.authorization.k8s.io/zabbix-user created
clusterrolebinding.rbac.authorization.k8s.io/zabbix-user created
```

### How to retrieve TOKEN and API SERVER

1. **TOKEN**:
```bash
$ TOKENNAME=$(kubectl get sa/zabbix-user -n kube-system -o jsonpath='{.secrets[0].name}')
$ TOKEN=$(kubectl -n kube-system get secret $TOKENNAME -o jsonpath='{.data.token}'| base64 --decode)
$ echo $TOKEN
```

2. **API SERVER**:
```bash
$ APISERVER=https://$(kubectl -n default get endpoints kubernetes --no-headers | awk '{ print $2 }')
$ echo $APISERVER
```
