def test_kb_endpoint_returns_all_records_ordered_by_class_id(client):
    response = client.get("/api/v1/kb")
    assert response.status_code == 200
    body = response.json()
    assert [r["class_id"] for r in body] == [0, 1, 2, 3, 4, 5]


def test_no_record_shows_an_english_placeholder_where_a_reader_expects_words(client):
    """A farmer reads these fields on a Thai card.

    The healthy record carried the literal string "None" in `pathogen`, which
    reached the screen as the word None. Records 4 and 5 already say the same
    thing in Thai, so the leftover was a gap in the data rather than a choice.
    """
    placeholders = {"none", "null", "n/a", "na", "-", "undefined", "nan", ""}
    offenders = [
        (record["class_id"], field, value)
        for record in client.get("/api/v1/kb").json()
        for field, value in record.items()
        if isinstance(value, str) and value.strip().lower() in placeholders
    ]
    assert offenders == []
