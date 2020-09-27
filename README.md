# Description
[zabbix-kubernetes-monitoring](https://github.com/sleepka/zabbix-kubernetes-monitoring) is zabbix-agent script and template for zabbix server. It is used for Kubernetes monitoring by Zabbix. Easy to deploy and configure. Auto discovery of pods, deployments, services, etc.

# Installation
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

## Multi-Cluster support
Simply add more dicts to `k8s_stats.json`. Sample config file provided in repo has two clusters added.

## How to create zabbix user in Kubernetes
```bash
$ kubectl apply -n kube-system -f zabbix-user-example.yml 
serviceaccount/zabbix-user created
clusterrole.rbac.authorization.k8s.io/zabbix-user created
clusterrolebinding.rbac.authorization.k8s.io/zabbix-user created
```

## How to retrieve TOKEN and API SERVER
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
