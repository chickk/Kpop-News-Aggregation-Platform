import pytest

pytest.importorskip("eventregistry")

from app.news_aggregators.news_api import NewsAPIAggregator


class FakeEventRegistry:
    def __init__(self):
        self.lookups = []

    def getConceptUri(self, concept):
        self.lookups.append(concept)
        return f"lookup:{concept}"


def test_get_concept_uris_keeps_direct_wikipedia_uri():
    aggregator = NewsAPIAggregator.__new__(NewsAPIAggregator)
    aggregator.api = FakeEventRegistry()

    uri = "http://en.wikipedia.org/wiki/Twice_(group)"

    assert aggregator.get_concept_uris([uri, "NMIXX"]) == [uri, "lookup:NMIXX"]
    assert aggregator.api.lookups == ["NMIXX"]
