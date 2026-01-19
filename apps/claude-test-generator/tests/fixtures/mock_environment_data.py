"""
Mock Environment Data Fixtures
===============================

Centralized mock environment and cluster data for testing Agent D
and environment assessment components.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class MockNode:
    """Mock Kubernetes node structure."""
    name: str
    status: str
    roles: List[str]
    version: str


@dataclass
class MockClusterEnvironment:
    """Mock cluster environment structure."""
    console_url: str
    api_url: str
    nodes: List[MockNode]
    acm_version: str
    health: str
    namespaces: List[str]
    crds_present: List[str]
    errors: List[str]


# Standard mock environments for testing
MOCK_ENVIRONMENTS: Dict[str, MockClusterEnvironment] = {
    "healthy_cluster": MockClusterEnvironment(
        console_url="https://console.example.com",
        api_url="https://api.example.com:6443",
        nodes=[
            MockNode(name="master-0", status="Ready", roles=["master", "worker"], version="v1.28.0"),
            MockNode(name="master-1", status="Ready", roles=["master", "worker"], version="v1.28.0"),
            MockNode(name="master-2", status="Ready", roles=["master", "worker"], version="v1.28.0")
        ],
        acm_version="2.15.0",
        health="Healthy",
        namespaces=["open-cluster-management", "open-cluster-management-hub", "open-cluster-management-agent"],
        crds_present=["clustercurators.cluster.open-cluster-management.io",
                      "managedclusters.cluster.open-cluster-management.io",
                      "policies.policy.open-cluster-management.io"],
        errors=[]
    ),

    "unhealthy_cluster": MockClusterEnvironment(
        console_url="https://console.unhealthy.example.com",
        api_url="https://api.unhealthy.example.com:6443",
        nodes=[
            MockNode(name="master-0", status="Ready", roles=["master"], version="v1.27.0"),
            MockNode(name="master-1", status="NotReady", roles=["master"], version="v1.27.0"),
            MockNode(name="worker-0", status="Ready", roles=["worker"], version="v1.27.0")
        ],
        acm_version="2.14.0",
        health="Unhealthy",
        namespaces=["open-cluster-management"],
        crds_present=["clustercurators.cluster.open-cluster-management.io"],
        errors=["Node master-1 is not responding", "Etcd cluster degraded"]
    ),

    "feature_deployed": MockClusterEnvironment(
        console_url="https://console.deployed.example.com",
        api_url="https://api.deployed.example.com:6443",
        nodes=[
            MockNode(name="master-0", status="Ready", roles=["master", "worker"], version="v1.28.0")
        ],
        acm_version="2.15.0",
        health="Healthy",
        namespaces=["open-cluster-management", "open-cluster-management-hub"],
        crds_present=[
            "clustercurators.cluster.open-cluster-management.io",
            "managedclusters.cluster.open-cluster-management.io",
            "policies.policy.open-cluster-management.io",
            "multiclusterobservabilities.observability.open-cluster-management.io"
        ],
        errors=[]
    ),

    "feature_not_deployed": MockClusterEnvironment(
        console_url="https://console.bare.example.com",
        api_url="https://api.bare.example.com:6443",
        nodes=[
            MockNode(name="master-0", status="Ready", roles=["master"], version="v1.28.0")
        ],
        acm_version="2.15.0",
        health="Healthy",
        namespaces=["open-cluster-management"],
        crds_present=[],  # No CRDs deployed
        errors=[]
    ),

    "unreachable_cluster": MockClusterEnvironment(
        console_url="https://console.unreachable.example.com",
        api_url="https://api.unreachable.example.com:6443",
        nodes=[],
        acm_version="unknown",
        health="Unreachable",
        namespaces=[],
        crds_present=[],
        errors=["Connection refused", "Unable to connect to cluster"]
    )
}


def get_mock_environment(env_name: str) -> Optional[MockClusterEnvironment]:
    """Get a mock environment by name."""
    return MOCK_ENVIRONMENTS.get(env_name)


def create_custom_environment(
    console_url: str = "https://console.custom.example.com",
    health: str = "Healthy",
    acm_version: str = "2.15.0",
    **kwargs
) -> MockClusterEnvironment:
    """Create a custom mock environment with specified parameters."""
    return MockClusterEnvironment(
        console_url=console_url,
        api_url=kwargs.get("api_url", console_url.replace("console", "api") + ":6443"),
        nodes=kwargs.get("nodes", [MockNode("master-0", "Ready", ["master"], "v1.28.0")]),
        acm_version=acm_version,
        health=health,
        namespaces=kwargs.get("namespaces", ["open-cluster-management"]),
        crds_present=kwargs.get("crds_present", []),
        errors=kwargs.get("errors", [])
    )


# Mock oc/kubectl command outputs
MOCK_OC_COMMAND_OUTPUTS: Dict[str, Dict[str, str]] = {
    "healthy_cluster": {
        "oc get nodes": """NAME       STATUS   ROLES                  AGE   VERSION
master-0   Ready    control-plane,master   10d   v1.28.0
master-1   Ready    control-plane,master   10d   v1.28.0
master-2   Ready    control-plane,master   10d   v1.28.0""",

        "oc get mch -n open-cluster-management": """NAME                 STATUS    AGE
multiclusterhub      Running   10d""",

        "oc get clustercurators -A": """NAMESPACE   NAME              AGE   STATUS
default     sample-curator   5d    Completed""",

        "oc version": """Client Version: 4.14.0
Server Version: 4.14.0
Kubernetes Version: v1.28.0"""
    },

    "unhealthy_cluster": {
        "oc get nodes": """NAME       STATUS     ROLES                  AGE   VERSION
master-0   Ready      control-plane,master   10d   v1.27.0
master-1   NotReady   control-plane,master   10d   v1.27.0
worker-0   Ready      worker                 10d   v1.27.0""",

        "oc get mch -n open-cluster-management": """NAME                 STATUS    AGE
multiclusterhub      Degraded  10d""",

        "oc version": """Client Version: 4.13.0
Server Version: 4.13.0
Kubernetes Version: v1.27.0"""
    },

    "unreachable_cluster": {
        "oc get nodes": "error: Unable to connect to the server: connection refused",
        "oc get mch -n open-cluster-management": "error: Unable to connect to the server: connection refused",
        "oc version": """Client Version: 4.14.0
error: Unable to connect to the server: connection refused"""
    }
}


class MockEnvironmentAssessmentClient:
    """Mock environment assessment client for testing."""

    def __init__(self, environments: Dict[str, MockClusterEnvironment] = None):
        self.environments = environments or MOCK_ENVIRONMENTS
        self.current_environment = "healthy_cluster"
        self.call_count = 0
        self.should_fail = False
        self.failure_message = "Mock environment failure"
        self.connection_timeout = False

    def set_current_environment(self, env_name: str):
        """Set the current environment for testing."""
        self.current_environment = env_name

    def set_failure_mode(self, should_fail: bool, message: str = "Mock environment failure"):
        """Configure the mock to simulate failures."""
        self.should_fail = should_fail
        self.failure_message = message

    def set_connection_timeout(self, timeout: bool):
        """Set whether to simulate connection timeout."""
        self.connection_timeout = timeout

    def assess_environment(self, cluster_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """Mock implementation of environment assessment."""
        self.call_count += 1

        if self.connection_timeout:
            raise TimeoutError("Connection timed out")

        if self.should_fail:
            raise Exception(self.failure_message)

        env = self.environments.get(self.current_environment)
        if not env:
            raise Exception(f"Environment {self.current_environment} not found")

        return {
            "console_url": env.console_url,
            "api_url": env.api_url,
            "health": env.health,
            "acm_version": env.acm_version,
            "nodes": [{"name": n.name, "status": n.status} for n in env.nodes],
            "deployment_status": "deployed" if env.crds_present else "not_deployed",
            "namespaces": env.namespaces,
            "crds_present": env.crds_present,
            "errors": env.errors
        }

    def run_oc_command(self, command: str) -> str:
        """Mock oc command execution."""
        self.call_count += 1

        outputs = MOCK_OC_COMMAND_OUTPUTS.get(self.current_environment, {})
        return outputs.get(command, f"Mock output for: {command}")

    def reset(self):
        """Reset the mock state."""
        self.call_count = 0
        self.should_fail = False
        self.connection_timeout = False
        self.current_environment = "healthy_cluster"


# Expected outputs for environment assessment scenarios
EXPECTED_ENVIRONMENT_OUTPUTS = {
    "healthy_cluster": {
        "health": "Healthy",
        "deployment_status": "deployed",
        "node_count": 3,
        "all_nodes_ready": True,
        "has_errors": False
    },
    "unhealthy_cluster": {
        "health": "Unhealthy",
        "deployment_status": "deployed",
        "node_count": 3,
        "all_nodes_ready": False,
        "has_errors": True
    },
    "feature_deployed": {
        "health": "Healthy",
        "deployment_status": "deployed",
        "node_count": 1,
        "all_nodes_ready": True,
        "has_errors": False
    },
    "feature_not_deployed": {
        "health": "Healthy",
        "deployment_status": "not_deployed",
        "node_count": 1,
        "all_nodes_ready": True,
        "has_errors": False
    },
    "unreachable_cluster": {
        "health": "Unreachable",
        "deployment_status": "unknown",
        "node_count": 0,
        "all_nodes_ready": False,
        "has_errors": True
    }
}
