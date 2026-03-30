# Cluster Lifecycle Data Flow

How cluster operations flow from the UI through the backend to Hive and spoke clusters.

---

## Cluster Creation Flow

```
User fills in cluster creation wizard
  -> frontend constructs ClusterDeployment YAML
  -> frontend/src/resources/resource.ts builds API path:
     /apis/hive.openshift.io/v1/namespaces/<ns>/clusterdeployments
  -> POST to console backend proxy
    -> backend/src/routes/proxy.ts doProxy()
      -> proxies to kube-apiserver
      -> kube-apiserver validates via Hive webhook
        -> clusterdeploymentvalidators webhook checks the resource
      -> ClusterDeployment CR created
  -> Hive controllers start provisioning
    -> creates Infrastructure on cloud provider (AWS, Azure, GCP, etc.)
    -> monitors provisioning progress
  -> ManagedCluster CR auto-created
  -> Klusterlet deployed to new cluster
  -> Addons deployed via ManagedClusterAddon CRs
```

## Cluster Import Flow

```
User provides kubeconfig or API token in import wizard
  -> ManagedCluster CR created on hub
  -> managedcluster-import-controller generates import manifests
  -> manifests applied to spoke cluster
    -> klusterlet agent starts on spoke
    -> klusterlet registers with hub
  -> ManagedCluster status transitions: Pending -> Joined -> Available
  -> Addons deployed based on ManagedClusterAddon CRs
```

## ClusterSet Transfer Flow

```
User selects clusters to transfer to a new ClusterSet
  -> UI updates ManagedCluster labels: cluster.open-cluster-management.io/clusterset=<set-name>
  -> ManagedClusterSet membership updated
  -> UI table should show "Transferred" status
```

If managed clusters are NotReady, the transfer API call may succeed but
the expected "Transferred" text never appears in the table cell.

## Failure Points

| Point | What breaks | Symptom |
|-------|------------|---------|
| Hive webhook misconfigured | All ClusterDeployment operations fail | 500 "failed calling webhook" |
| Wrong API version (v1beta1) | ClusterDeployment creation fails | 404 "resource not found" |
| Console proxy intercepts | Fake 500 returned without reaching Hive | "admission webhook timed out" (realistic error message) |
| Managed clusters NotReady | Transfer operations fail silently | "Transferred" text never appears |
| ClusterCurator events dropped | Automation status doesn't update | Stale curator status in UI |
| Import controller down | New imports fail | ManagedCluster stays Pending |
