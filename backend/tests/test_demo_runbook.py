from pathlib import Path


def test_generated_phone_runbook_describes_rear_camera_as_an_ideal_request():
    source = Path(__file__).resolve().parents[2] / "scripts" / "prepare_demo.py"
    contents = source.read_text(encoding="utf-8")
    phone_section = contents.split('_PHONE_SECTION = """', 1)[1].split('"""', 1)[0]

    assert "แอปจะขอกล้องหลังด้วย" in phone_section
    assert "`facingMode: { ideal: 'environment' }`" in phone_section
    assert "หากเครื่องไม่มีกล้องหลังและใช้กล้องหน้าได้" in phone_section
    assert "ถือเป็นพฤติกรรมที่ตั้งใจ" in phone_section
