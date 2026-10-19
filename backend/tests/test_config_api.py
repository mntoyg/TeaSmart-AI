def test_config_endpoint_serves_the_client_contract(client):
    # Every number here exists on both sides of the wire. Serving them is what
    # stops the browser and the server drifting apart silently when one changes.
    response = client.get("/api/v1/config")
    assert response.status_code == 200
    body = response.json()
    assert body["model_version"] == "teasmart-v1"
    assert body["min_confidence"] == 0.60
    assert body["class_order"] == [
        "grey_blight",
        "brown_blight",
        "algal_spot",
        "healthy",
        "other_disease",
    ]


def test_config_serves_the_preprocessing_the_onnx_contract_fixes(client):
    pre = client.get("/api/v1/config").json()["preprocessing"]
    assert pre["size"] == [224, 224]
    assert pre["preserve_aspect_ratio"] is False
    assert pre["scale"] == 255.0
    assert pre["mean"] == [0.485, 0.456, 0.406]
    assert pre["std"] == [0.229, 0.224, 0.225]
    assert pre["layout"] == "NCHW"


def test_config_serves_the_quality_thresholds_the_browser_duplicates(client):
    # Stage 1 is the one thing implemented twice, because it is cheap. Both
    # copies have to judge a frame the same way or a worker gets contradictory
    # advice depending on whether the network is up.
    quality = client.get("/api/v1/config").json()["quality"]
    assert quality["blur_threshold"] == 80.0
    assert quality["exposure_min_mean"] == 40.0
    assert quality["exposure_max_mean"] == 215.0
    assert quality["clip_max_pct"] == 0.10


def test_the_class_order_comes_from_the_knowledge_base_not_a_second_list(client):
    # Derived from class_id, with physical_burn excluded because the model never
    # emits it. A hard-coded copy here could disagree with the records.
    kb = {record["canonical"]: record["class_id"] for record in client.get("/api/v1/kb").json()}
    order = client.get("/api/v1/config").json()["class_order"]
    assert [kb[name] for name in order] == [0, 1, 2, 3, 4]
    assert "physical_burn" not in order


def test_config_names_the_fp32_graph_and_promises_logits(client):
    # Pinned because int8 failed the parity bound in spec 8.4 by moving a
    # probability 0.248 against a limit of 0.05. Reverting this name would send
    # the browser a graph that disagrees with the server around min_confidence,
    # where the product makes its decisions.
    onnx = client.get("/api/v1/config").json()["onnx"]
    assert onnx["file"] == "teasmart-v1.onnx"
    assert onnx["output_is_logits"] is True
    assert onnx["output"] == "logits"


def test_config_serves_the_measured_confidence_floor(client):
    # Measured 2026-10-19: docs/eval/2026-10-19-d3-model.md section 4. The
    # browser reads this rather than carrying its own copy.
    assert client.get("/api/v1/config").json()["min_confidence"] == 0.60
