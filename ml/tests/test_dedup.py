from teasmart_ml.datasets.dedup import (
    group_duplicates,
    group_hash_indices,
    hamming,
    phash_hex,
)
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


def test_every_recompression_of_one_photo_lands_in_one_group(tmp_path):
    # Three encodings of one photograph belong together, or a copy of it
    # still reaches a different split.
    a = write_leaf_photo(tmp_path / "a.jpg", quality=95)
    b = write_leaf_photo(tmp_path / "b.jpg", quality=60)
    c = write_leaf_photo(tmp_path / "c.jpg", quality=30)
    assert len(group_duplicates([a, b, c])) == 1


def test_every_input_appears_in_exactly_one_group(tmp_path):
    paths = [write_leaf_photo(tmp_path / f"{i}.jpg", seed=i) for i in range(5)]
    groups = group_duplicates(paths)
    assert sorted(p for g in groups for p in g) == sorted(paths)


def test_a_chain_of_near_misses_does_not_snowball_into_one_group():
    # Measured on the real corpus: transitive grouping walked 866 images into a
    # single "duplicate" group, discarding hundreds of distinct photographs.
    # Membership is therefore judged against the group leader, not against any
    # member: a is 4 from b, b is 4 from c, but a is 8 from c, so c starts its
    # own group.
    a = "0000000000000000"
    b = "000000000000000f"
    c = "00000000000000ff"
    assert hamming(a, b) == 4
    assert hamming(b, c) == 4
    assert hamming(a, c) == 8
    assert group_hash_indices([a, b, c], max_distance=5) == ((0, 1), (2,))


def test_hash_grouping_keeps_the_input_order_as_the_leader_preference():
    # group_duplicates sorts by pixel area before hashing, so the leader is the
    # highest-resolution copy and index 0 of each group is the one to keep.
    identical = "abcdef0123456789"
    assert group_hash_indices([identical, identical, identical], max_distance=5) == (
        (0, 1, 2),
    )


def test_a_hash_match_the_pixel_check_rejects_is_not_grouped():
    # Measured on the real corpus: at a Hamming distance of 5, 24% of collapsed
    # pairs were not the same photograph - two different leaves centred on the
    # same background share a coarse layout, and a 64-bit perceptual hash sees
    # only coarse layout. The hash finds candidates; pixels decide.
    identical = "abcdef0123456789"
    hashes = [identical, identical]
    assert group_hash_indices(hashes, max_distance=5) == ((0, 1),)
    assert group_hash_indices(
        hashes, max_distance=5, confirm=lambda _leader, _candidate: False
    ) == ((0,), (1,))


def test_group_duplicates_applies_the_pixel_check(tmp_path):
    original = write_leaf_photo(tmp_path / "a.jpg", quality=95)
    recompressed = write_leaf_photo(tmp_path / "b.jpg", quality=40)
    pair = [original, recompressed]
    assert len(group_duplicates(pair)) == 1
    assert len(group_duplicates(pair, max_pixel_mae=0.0)) == 2
