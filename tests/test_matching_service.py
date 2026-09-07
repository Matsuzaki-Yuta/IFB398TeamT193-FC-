import json
import sqlite3

import pytest

from backend.services.matching_service import (
    fetch_matching_packages
)


@pytest.fixture
def test_database(tmp_path, monkeypatch):
    db_path = tmp_path / "test_packages.db"

    connection = sqlite3.connect(db_path)

    connection.execute(
        """
        CREATE TABLE packages (
            id TEXT PRIMARY KEY,
            destination TEXT,
            inclusions TEXT,
            highlights TEXT,
            vibe_tags TEXT
        )
        """
    )

    packages = [
        (
            "package-001",
            "Bali, Indonesia",
            json.dumps(["Hotel", "Breakfast"]),
            json.dumps(["Beach", "Temple"]),
            json.dumps(["Adventure", "Wellness"]),
        ),
        (
            "package-002",
            "Bali, Indonesia",
            json.dumps(["Hostel"]),
            json.dumps(["Surfing"]),
            json.dumps(["Adventure"]),
        ),
        (
            "package-003",
            "Tokyo, Japan",
            json.dumps(["Hotel"]),
            json.dumps(["Food Tour"]),
            json.dumps(["Cultural", "Foodie"]),
        ),
    ]

    connection.executemany(
        """
        INSERT INTO packages (
            id,
            destination,
            inclusions,
            highlights,
            vibe_tags
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        packages,
    )

    connection.commit()
    connection.close()

    def test_get_connection():
        connection = sqlite3.connect(db_path)
        connection.row_factory = sqlite3.Row
        return connection

    monkeypatch.setattr(
        "backend.services.matching_service.get_connection",
        test_get_connection
    )

    return db_path


def test_matching_returns_correct_destination(
    test_database
):
    results = fetch_matching_packages(
        ["Bali"],
        ["Adventure"]
    )

    assert len(results) == 2

    assert all(
        "bali" in package["destination"].lower()
        for package in results
    )


def test_matching_is_case_insensitive(
    test_database
):
    results = fetch_matching_packages(
        ["bali"],
        ["adventure"]
    )

    assert len(results) == 2


def test_matching_returns_empty_for_unknown_destination(
    test_database
):
    results = fetch_matching_packages(
        ["London"],
        ["Adventure"]
    )

    assert results == []


def test_matching_returns_empty_without_destination(
    test_database
):
    results = fetch_matching_packages(
        [],
        ["Adventure"]
    )

    assert results == []


def test_matching_returns_empty_without_vibes(
    test_database
):
    results = fetch_matching_packages(
        ["Bali"],
        []
    )

    assert results == []


def test_match_score_counts_matching_vibes(
    test_database
):
    results = fetch_matching_packages(
        ["Bali"],
        ["Adventure", "Wellness"]
    )

    first_result = results[0]

    assert first_result["id"] == "package-001"
    assert first_result["match_score"] == 2


def test_results_sorted_by_match_score(
    test_database
):
    results = fetch_matching_packages(
        ["Bali"],
        ["Adventure", "Wellness"]
    )

    scores = [
        package["match_score"]
        for package in results
    ]

    assert scores == sorted(
        scores,
        reverse=True
    )


def test_match_reasons_are_created(
    test_database
):
    results = fetch_matching_packages(
        ["Bali"],
        ["Adventure"]
    )

    package = results[0]

    assert "match_reasons" in package
    assert len(package["match_reasons"]) == 2


def test_matched_vibes_are_returned(
    test_database
):
    results = fetch_matching_packages(
        ["Bali"],
        ["Adventure", "Wellness"]
    )

    first_result = results[0]

    assert "adventure" in first_result["matched_vibes"]
    assert "wellness" in first_result["matched_vibes"]