from seed.check_bundle import check_bundle

from app.publish.bundler import encode_bundle, public_question


def _bundle(difficulties=(1, 2, 2, 3)) -> dict:
    return {
        "level": {"id": "L", "place_ids": ["P"]},
        "places": [{"id": "P", "citations": ["c1"]}],
        "persons": [],
        "events": [
            {
                "id": "E",
                "place_id": "P",
                "person_ids": [],
                "citations": ["c1"],
                "fragment_ids": ["F"],
                "question_ids": [f"Q{i}" for i in range(len(difficulties))],
            }
        ],
        "causal_links": [],
        "fragments": [{"id": "F", "event_id": "E", "media_id": "M", "citations": []}],
        "dialogues": [],
        "questions": [
            {"id": f"Q{i}", "event_id": "E", "difficulty": d, "citations": []}
            for i, d in enumerate(difficulties)
        ],
        "quests": [
            {
                "id": "QU",
                "citations": [],
                "objectives": [{"id": "O", "kind": "collect", "target_id": "F"}],
            }
        ],
        "map_layers": [],
        "citations": {"c1": {"source_id": "S"}},
        "sources": {"S": {"tier": 1}},
        "media": {
            "M": {
                "license": "cc_by",
                "owner": "x",
                "source_url": "u",
                "attribution": "x, CC-BY",
                "attribution_required": True,
            }
        },
    }


def test_valid_bundle_passes():
    assert check_bundle(_bundle()) == []


def test_detects_missing_ref_tier3_license_and_leak():
    b = _bundle(difficulties=(1, 1, 1, 3))
    b["sources"]["S"]["tier"] = 3
    b["fragments"][0]["media_id"] = "MISSING"
    b["media"]["M"]["license"] = "all_rights_reserved"
    b["questions"][0]["correct_answer"] = "a"
    errors = "\n".join(check_bundle(b))
    assert "media 'MISSING'" in errors
    assert "Cấp 1 hoặc Cấp 2" in errors
    assert "all_rights_reserved" in errors
    assert "correct_answer" in errors
    assert "Độ khó 2" in errors


def test_public_question_strips_secrets_and_is_stable():
    q = {
        "id": "q",
        "kind": "order",
        "difficulty": 2,
        "prompt": "p",
        "is_fiction": False,
        "event_id": "e",
        "options": [{"id": "a"}, {"id": "b"}, {"id": "c"}],
        "correct_answer": ["a", "b", "c"],
        "explanation": "x",
        "answer_basis": [],
    }
    out = public_question(q)
    assert not {"correct_answer", "explanation", "answer_basis"} & set(out)
    assert out == public_question(q)
    assert encode_bundle({"b": 1, "a": "Đ"})[1] == encode_bundle({"a": "Đ", "b": 1})[1]
