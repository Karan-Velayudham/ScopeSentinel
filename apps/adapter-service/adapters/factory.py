from adapters.jira import JiraAdapter
from adapters.skeleton import SkeletonAdapter

class AdapterFactory:
    def __init__(self):
        self._adapters = {
            "jira": JiraAdapter(),
            "slack": SkeletonAdapter("slack", "Slack", "Communication", "https://cdn.brandfolder.io/5H0G5K1W/at/pl6487hbm9mhmjk8sk69bj3/slack-mark-rgb.png"),
            "firestore": SkeletonAdapter("firestore", "Firestore", "Database", "https://www.gstatic.com/mobilesdk/160503_mobilesdk/logo/2x/firebase_28dp.png"),
            "bigquery": SkeletonAdapter("bigquery", "BigQuery", "Data Warehouse", "https://www.gstatic.com/images/branding/product/2x/bigquery_64dp.png"),
            "notion": SkeletonAdapter("notion", "Notion", "Productivity", "https://upload.wikimedia.org/wikipedia/commons/4/45/Notion_app_logo.png"),
            "github": SkeletonAdapter("github", "GitHub", "VCS", "https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png"),
        }

    def get_adapter(self, provider: str):
        adapter = self._adapters.get(provider)
        if not adapter:
            raise ValueError(f"No adapter found for provider: {provider}")
        return adapter

    def get_all_adapters_info(self) -> list[dict]:
        return [adapter.info() for adapter in self._adapters.values()]

adapter_factory = AdapterFactory()
