from tracker.scrapers.codechef import CodeChefScraper


class FakeResponse:
    text = """
    <html><head><title>Ana | CodeChef</title></head><body>
      <div class="rating-number">1,670</div>
      <div class="rating-ranks">
        <ul><li><a><strong>846</strong><span>Global Rank</span></a></li>
            <li><a><strong>1,898</strong><span>Country Rank</span></a></li></ul>
      </div>
      <h3>Fully Solved (202)</h3>
    </body></html>
    """


class FakeClient:
    def request(self, *_args, **_kwargs):
        return FakeResponse()


def test_codechef_reads_rank_cards():
    result = CodeChefScraper(FakeClient()).fetch("anafa_sadiq", "https://www.codechef.com/users/anafa_sadiq")
    assert result.rating == 1670
    assert result.global_rank == 846
    assert result.country_rank == 1898
    assert result.rank == 846
    assert result.problems_solved == 202
