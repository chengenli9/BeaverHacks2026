from backend.app.media.service import _frame_timestamp_candidates


def test_frame_timestamp_candidates_back_off_from_end_of_file():
    candidates = _frame_timestamp_candidates(166.094, 166.1445)

    assert candidates[0] == 165.894
    assert all(candidate <= 165.894 for candidate in candidates)
    assert candidates[-1] >= 165.094
