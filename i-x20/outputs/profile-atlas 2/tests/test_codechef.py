from tracker.scrapers.codechef import CodeChefScraper


class FakeResponse:
    text = """
    <html><head><title>Ana | CodeChef</title></head><body>
      <div class="rating-number">1,670</div>
      <div class="rating-ranks">
        <ul><li><a><strong>846</strong><span>Global Rank</span></a></li>
            <li><a><strong>1,898</strong><span>Country Rank</span></a></li></ul>
      </div>
      <ul class="inline-list">
        <li><a href="/ratings/all"><strong>9,297</strong></a> Global Rank</li>
        <li><a href="/ratings/all?filterBy=Country%3DIndia"><strong>8,488</strong></a> Country Rank</li>
      </ul>
      <h3>Fully Solved (202)</h3>
      <div>No. of Contests Participated: 31</div>
      <div>Total Submissions: 1,245</div>
    </body></html>
    """


class FakeClient:
    def request(self, *_args, **_kwargs):
        return FakeResponse()


def test_codechef_reads_rank_cards():
    result = CodeChefScraper(FakeClient()).fetch("anafa_sadiq", "https://www.codechef.com/users/anafa_sadiq")
    assert result.rating == 1670
    assert result.global_rank == 9297
    assert result.country_rank == 8488
    assert result.rank == 9297
    assert result.problems_solved == 202
    assert result.contests_attended == 31
    assert result.total_submissions == 1245
