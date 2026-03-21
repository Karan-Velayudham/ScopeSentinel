"""
Connector registry — maps connector_id → connector class.
FIX M-5: Expanded to include 10 connectors.
"""
from connectors.apps.github import GithubConnector
from connectors.apps.slack import SlackConnector
from connectors.apps.jira import JiraConnector
from connectors.apps.datadog import DatadogConnector
from connectors.apps.gitlab import GitLabConnector
from connectors.apps.linear import LinearConnector
from connectors.apps.pagerduty import PagerDutyConnector
from connectors.apps.jenkins import JenkinsConnector
from connectors.apps.discord import DiscordConnector
from connectors.apps.prometheus import PrometheusConnector

AVAILABLE_CONNECTORS = [
    GithubConnector,
    SlackConnector,
    JiraConnector,
    DatadogConnector,
    GitLabConnector,
    LinearConnector,
    PagerDutyConnector,
    JenkinsConnector,
    DiscordConnector,
    PrometheusConnector,
]

_CONNECTOR_MAP = {c.info()["id"]: c for c in AVAILABLE_CONNECTORS}


def get_connector_catalog() -> list[dict]:
    """Returns the full list of available connectors as dicts."""
    return [c.info() for c in AVAILABLE_CONNECTORS]


def get_connector_class(connector_id: str):
    """Returns the connector class for the given ID, or None."""
    return _CONNECTOR_MAP.get(connector_id)
