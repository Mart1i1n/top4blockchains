"""Title-only classification rules. Each test names the keyword path it exercises."""

from __future__ import annotations

from scripts.classify import Keywords, classify_title, keyword_matches

SAMPLE_KEYWORDS = Keywords(
    strong=("blockchain", "ethereum", "smart contract", "mev", "ton", "dao"),
    in_context=("bft", "mpc", "dag", "consensus"),
    negative=("homomorphic encryption", "federated learning"),
)


def test_strong_keyword_includes() -> None:
    status, matched, _ = classify_title("On the Foo of Blockchain Bar", SAMPLE_KEYWORDS)
    assert status == "include"
    assert "blockchain" in matched


def test_strong_keyword_plural_includes() -> None:
    # "blockchain" should also match "Blockchains" — DBLP titles often use the plural form.
    status, _, _ = classify_title("Sharded Blockchains and Their Friends", SAMPLE_KEYWORDS)
    assert status == "include"


def test_in_context_only_needs_review() -> None:
    # AD-MPC: only matches the in-context keyword "mpc"; should land in needs_review.
    status, matched, _ = classify_title(
        "AD-MPC: Asynchronous Dynamic MPC with Guaranteed Output Delivery",
        SAMPLE_KEYWORDS,
    )
    assert status == "needs_review"
    assert matched == ["mpc"]


def test_negative_override_demotes() -> None:
    # Federated learning + BFT/Byzantine context should NOT auto-include.
    status, _, reason = classify_title(
        "Robust BFT for Federated Learning in the Wild", SAMPLE_KEYWORDS
    )
    assert status == "needs_review"
    assert reason and "negative" in reason.lower()


def test_no_match_excludes() -> None:
    status, matched, _ = classify_title("A Practical Side-Channel Attack on AES", SAMPLE_KEYWORDS)
    assert status == "exclude"
    assert matched == []


def test_word_boundary_no_false_match() -> None:
    # Three-letter keywords are the highest-risk for false matches; verify they don't
    # bleed into longer words. "ton" must not match "Bottom"; "dao" must not match
    # "Shadow"; "mev" must not match "improvement".
    assert not keyword_matches("ton", "Bottom-up Analysis")
    assert not keyword_matches("dao", "A Shadow Stack Defence")
    assert not keyword_matches("mev", "Improvement of Stuff")
    # And the actual ones must match.
    assert keyword_matches("ton", "An Attack on TON's ADNL")
    assert keyword_matches("dao", "DAO Decentralization")


def test_hyphen_space_normalisation() -> None:
    # 'smart contract' should match both "smart contract" and "smart-contract"
    assert keyword_matches("smart contract", "Verifying Smart Contract Patterns")
    assert keyword_matches("smart contract", "smart-contract reentrancy")
    assert keyword_matches("smart-contract", "Smart Contract Auditing")
