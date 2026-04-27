from app.routers.bench import _build_batch_summary, _choose_document_groups


def _doc(doc_id: str) -> dict:
    return {"id": doc_id, "filename": f"{doc_id}.md", "content": doc_id}


def test_choose_document_groups_all_pairs_for_k_two():
    docs = [_doc("a"), _doc("b"), _doc("c")]

    groups = _choose_document_groups(docs, pair_size=2, sampling_mode="all_pairs", sample_count=None, seed=0)

    assert [[item["id"] for item in group] for group in groups] == [
        ["a", "b"],
        ["a", "c"],
        ["b", "c"],
    ]


def test_choose_document_groups_random_sample_is_unique():
    docs = [_doc("a"), _doc("b"), _doc("c"), _doc("d")]

    groups = _choose_document_groups(docs, pair_size=3, sampling_mode="random", sample_count=2, seed=7)

    normalized = {tuple(item["id"] for item in group) for group in groups}
    assert len(groups) == 2
    assert len(normalized) == 2


def test_build_batch_summary_counts_wins_and_averages():
    class Score:
        def __init__(self, coverage, hierarchy, balance, conciseness, accuracy):
            self.coverage = coverage
            self.hierarchy = hierarchy
            self.balance = balance
            self.conciseness = conciseness
            self.accuracy = accuracy

    class Result:
        def __init__(self, score_a, score_b, elapsed_s):
            self.score_a = score_a
            self.score_b = score_b
            self.elapsed_s = elapsed_s

    results = [
        Result(Score(5, 5, 4, 4, 4), Score(4, 4, 4, 4, 4), 10.0),
        Result(Score(3, 3, 3, 3, 3), Score(4, 4, 4, 4, 4), 20.0),
        Result(Score(4, 4, 4, 4, 4), Score(4, 4, 4, 4, 4), 30.0),
    ]

    summary = _build_batch_summary(results, pair_size=2)

    assert summary.task_count == 3
    assert summary.pair_size == 2
    assert summary.wins_a == 1
    assert summary.wins_b == 1
    assert summary.ties == 1
    assert summary.avg_elapsed_s == 20.0
