def test_health_reports_app_and_model_version(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "app": "TeaSmart AI",
        "model_version": "teasmart-v1",
    }
