from teasmart_ml.datasets.dedup import group_duplicates, hamming, phash_hex
from tests.fixtures import write_leaf_photo


def test_the_same_photo_recompressed_is_detected_as_a_duplicate(tmp_path):
    # This is the real case: several sources derive from one Roboflow upload, so
    # the duplicates differ in bytes while being the same image. Hashing bytes
    # or MD5 would miss every one of them.
    original = write_leaf_photo(tmp_path / "a.jpg", quality=95)
    recompressed = write_leaf_photo(tmp_path / "b.jpg", quality=40)
    assert original.read_bytes() != recompressed.read_bytes()
    assert hamming(phash_hex(original), phash_hex(recompressed)) <= 5


def test_a_resized_copy_is_detected_as_a_duplicate(tmp_path):
    big = write_leaf_photo(tmp_path / "big.jpg", size=(512, 512))
    small = write_leaf_photo(tmp_path / "small.jpg", size=(256, 256))
    assert hamming(phash_hex(big), phash_hex(small)) <= 5


def test_two_different_leaves_are_not_grouped(tmp_path):
    a = write_leaf_photo(tmp_path / "a.jpg", seed=1)
    b = write_leaf_photo(tmp_path / "b.jpg", seed=2)
    assert len(group_duplicates([a, b])) == 2


def test_a_group_keeps_the_highest_resolution_copy_first(tmp_path):
    small = write_leaf_photo(tmp_path / "small.jpg", size=(256, 256))
    big = write_leaf_photo(tmp_path / "big.jpg", size=(512, 512))
    (group,) = group_duplicates([small, big])
    assert group[0] == big


def test_single_linkage_puts_a_chain_of_near_duplicates_in_one_group(tmp_path):
    # a~b and b~c must put all three together, or one copy of the same photo
    # still reaches a different split.
    a = write_leaf_photo(tmp_path / "a.jpg", quality=95)
    b = write_leaf_photo(tmp_path / "b.jpg", quality=60)
    c = write_leaf_photo(tmp_path / "c.jpg", quality=30)
    assert len(group_duplicates([a, b, c])) == 1


def test_every_input_appears_in_exactly_one_group(tmp_path):
    paths = [write_leaf_photo(tmp_path / f"{i}.jpg", seed=i) for i in range(5)]
    groups = group_duplicates(paths)
    assert sorted(p for g in groups for p in g) == sorted(paths)
