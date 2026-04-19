from adapters.jira import JiraAdapter
from adapters.slack import SlackAdapter
from adapters.github import GithubAdapter
from adapters.confluence import ConfluenceAdapter
from adapters.notion import NotionAdapter
from adapters.gmail import GmailAdapter
from adapters.skeleton import SkeletonAdapter

class AdapterFactory:
    def __init__(self):
        self._adapters = {
            "jira": JiraAdapter(),
            "confluence": ConfluenceAdapter(),
            "slack": SlackAdapter(),
            "github": GithubAdapter(),
            "notion": NotionAdapter(),
            "gmail": GmailAdapter(),
            # Retain skeleton for firestore/bigquery if any future plans:
            "firestore": SkeletonAdapter("firestore", "Firestore", "Database", "https://www.gstatic.com/mobilesdk/160503_mobilesdk/logo/2x/firebase_28dp.png"),
            "bigquery": SkeletonAdapter("bigquery", "BigQuery", "Data Warehouse", "https://www.gstatic.com/images/branding/product/2x/bigquery_64dp.png"),
        }

    def get_adapter(self, provider: str):
        adapter = self._adapters.get(provider)
        if not adapter:
            raise ValueError(f"No adapter found for provider: {provider}")
        return adapter

    def get_all_adapters_info(self) -> list[dict]:
        return [adapter.info() for adapter in self._adapters.values()]

adapter_factory = AdapterFactory()
