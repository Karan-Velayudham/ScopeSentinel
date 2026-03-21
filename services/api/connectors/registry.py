from connectors.apps.github import GithubConnector
from connectors.apps.slack import SlackConnector
from connectors.apps.jira import JiraConnector
from connectors.apps.datadog import DatadogConnector

AVAILABLE_CONNECTORS = [
    GithubConnector,
    SlackConnector,
    JiraConnector,
    DatadogConnector
]

def get_connector_catalog() -> list[dict]:
    return [c.info().model_dump() for c in AVAILABLE_CONNECTORS]

def get_connector_class(connector_id: str):
    for c in AVAILABLE_CONNECTORS:
        if c.info().id == connector_id:
            return c
    return None
