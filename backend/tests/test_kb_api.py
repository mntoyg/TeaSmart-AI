def test_kb_endpoint_returns_all_records_ordered_by_class_id(client):
    response = client.get("/api/v1/kb")
    assert response.status_code == 200
    body = response.json()
    assert [r["class_id"] for r in body] == [0, 1, 2, 3, 4, 5]
