from nemesis_simulator import make_rng


def test_same_seed_gives_same_sequence() -> None:
    first = [make_rng(42).random() for _ in range(3)]
    second = [make_rng(42).random() for _ in range(3)]
    assert first == second


def test_different_seeds_differ() -> None:
    assert make_rng(1).random() != make_rng(2).random()
