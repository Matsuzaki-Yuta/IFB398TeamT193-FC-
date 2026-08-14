import json

from database import get_connection


def fetch_matching_packages(destination_terms, vibe_terms):
    if not destination_terms or not vibe_terms:
        return []

    destination_conditions = " OR ".join(
        ["LOWER(destination) LIKE ?"] * len(destination_terms)
    )
    destination_parameters = [f"%{term.lower()}%" for term in destination_terms]

    with get_connection() as connection:
        rows = connection.execute(
            f"SELECT * FROM packages WHERE {destination_conditions}",
            destination_parameters,
        ).fetchall()

    requested_vibes = {vibe.lower() for vibe in vibe_terms}
    results = []
    for row in rows:
        package = dict(row)
        package_vibes = {
            vibe.lower() for vibe in json.loads(package["vibe_tags"] or "[]")
        }
        matched_vibes = requested_vibes & package_vibes
        if not matched_vibes:
            continue

        package["inclusions"] = json.loads(package["inclusions"] or "[]")
        package["highlights"] = json.loads(package["highlights"] or "[]")
        package["vibe_tags"] = sorted(package_vibes)
        package["matched_destination"] = next(
            (
                term for term in destination_terms
                if term.lower() in package["destination"].lower()
            ),
            destination_terms[0],
        )
        package["matched_vibes"] = sorted(matched_vibes)
        package["match_reasons"] = [
            f"Destination matched: {package['matched_destination']}",
            f"Travel style matched: {', '.join(package['matched_vibes'])}",
        ]
        package["match_score"] = len(matched_vibes)
        results.append(package)

    return sorted(results, key=lambda package: package["match_score"], reverse=True)