from adapters.jira import JiraAdapter

class AdapterFactory:
    def __init__(self):
        self._adapters = {
            "jira": JiraAdapter()
        }

    def get_adapter(self, provider: str):
        adapter = self._adapters.get(provider)
        if not adapter:
            raise ValueError(f"No adapter found for provider: {provider}")
        return adapter

adapter_factory = AdapterFactory()
