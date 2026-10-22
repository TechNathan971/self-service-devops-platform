import urllib3
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from kubernetes.config.config_exception import ConfigException

MANAGED_LABEL = "app.kubernetes.io/managed-by"
MANAGED_VALUE = "self-service-devops-platform"


class ClusterError(Exception):
    """Something went wrong while talking to the cluster."""


def _describe(exc: Exception) -> str:
    if isinstance(exc, ApiException):
        if exc.status == 409:
            return "a namespace with this name already exists in the cluster"
        return f"Kubernetes API error {exc.status}: {exc.reason}"
    return "cannot reach the cluster (is Docker Desktop running?)"


class KubernetesCluster:
    def __init__(self):
        try:
            config.load_kube_config()
            _, active = config.list_kube_config_contexts()
        except ConfigException as exc:
            raise ClusterError(f"cannot load kubeconfig: {exc}") from exc
        if not active:
            raise ClusterError("no active kubeconfig context")
        context_name = active["name"]
        if not context_name.startswith("kind-"):
            raise ClusterError(
                f"refusing to use context '{context_name}': only local kind clusters are allowed"
            )
        self.core = client.CoreV1Api()

    def create_namespace(self, name: str, env_kind: str, owner: str) -> None:
        body = client.V1Namespace(
            metadata=client.V1ObjectMeta(
                name=name,
                labels={
                    MANAGED_LABEL: MANAGED_VALUE,
                    "devops-platform/kind": env_kind,
                    "devops-platform/owner": owner,
                },
            )
        )
        try:
            self.core.create_namespace(body)
        except (ApiException, urllib3.exceptions.HTTPError) as exc:
            raise ClusterError(_describe(exc)) from exc

    def delete_namespace(self, name: str) -> bool:
        """Returns True if a namespace was deleted, False if it was already gone."""
        try:
            namespace = self.core.read_namespace(name)
        except ApiException as exc:
            if exc.status == 404:
                return False
            raise ClusterError(_describe(exc)) from exc
        except urllib3.exceptions.HTTPError as exc:
            raise ClusterError(_describe(exc)) from exc

        labels = namespace.metadata.labels or {}
        if labels.get(MANAGED_LABEL) != MANAGED_VALUE:
            raise ClusterError("refusing to delete a namespace this platform did not create")

        try:
            self.core.delete_namespace(name)
        except (ApiException, urllib3.exceptions.HTTPError) as exc:
            raise ClusterError(_describe(exc)) from exc
        return True