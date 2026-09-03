from tracker.scrapers.gfg import GFGScraper


class FakeResponse:
    status_code = 200
    text = """
    <html><head><title>Ana | GeeksforGeeks</title></head><body>
      <div>School (2) Basic (3) Easy (17) Medium (11) Hard (4)</div>
      <div>Coding Score 219</div><div>Problems Solved 37</div>
      <div>Institute Rank 8</div><div>Articles Published 1</div>
    </body></html>
    """


class FakeClient:
    def request(self, *_args, **_kwargs):
        return FakeResponse()


def test_gfg_reads_score_and_difficulty_counts():
    result = GFGScraper(FakeClient()).fetch("ana", "https://www.geeksforgeeks.org/user/ana")
    assert result.coding_score == 219
    assert result.problems_solved == 37
    assert result.easy == 17
    assert result.medium == 11
    assert result.hard == 4
