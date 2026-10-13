import imagehash
import numpy
from PIL import Image

from teasmart_ml.datasets.dedup import (
    DUPLICATE_MAE,
    block_means,
    group_duplicates,
    group_thumbnail_indices,
    hamming,
    phash_hex,
    pixel_mae,
    thumbnail,
)
from tests.fixtures import flat_noise_photo, write_leaf_photo


def test_the_same_photo_recompressed_is_detected_as_a_duplicate(tmp_path):
    # This is the real case: several sources derive from one upload, so the
    # duplicates differ in bytes while being the same image. Hashing bytes or
    # MD5 would miss every one of them.
    original = write_leaf_photo(tmp_path / "a.jpg", quality=95)
    recompressed = write_leaf_photo(tmp_path / "b.jpg", quality=40)
    assert original.read_bytes() != recompressed.read_bytes()
    assert pixel_mae(thumbnail(original), thumbnail(recompressed)) <= DUPLICATE_MAE
    assert len(group_duplicates([original, recompressed])) == 1


def test_a_resized_copy_is_detected_as_a_duplicate(tmp_path):
    big = write_leaf_photo(tmp_path / "big.jpg", size=(512, 512))
    small = write_leaf_photo(tmp_path / "small.jpg", size=(256, 256))
    assert len(group_duplicates([big, small])) == 1


def test_a_near_identical_pair_with_distant_hashes_is_still_a_duplicate(tmp_path):
    # The finding that forced pixels to be the definition rather than a
    # confirmation. pHash thresholds DCT coefficients at their median, so a
    # low-contrast image has many coefficients sitting on that median and a
    # near-identical copy flips them. Using the hash to generate candidates
    # capped recall and left 3.24% of the evaluation set with a twin in training.
    first = flat_noise_photo(tmp_path / "a.png", seed=1)
    second = flat_noise_photo(tmp_path / "b.png", seed=2)
    assert hamming(phash_hex(first), phash_hex(second)) > 20
    assert pixel_mae(thumbnail(first), thumbnail(second)) < 1.0
    assert len(group_duplicates([first, second])) == 1


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
    a = write_leaf_photo(tmp_path / "a.jpg", quality=95)
    b = write_leaf_photo(tmp_path / "b.jpg", quality=60)
    c = write_leaf_photo(tmp_path / "c.jpg", quality=30)
    assert len(group_duplicates([a, b, c])) == 1


def test_every_input_appears_in_exactly_one_group(tmp_path):
    paths = [write_leaf_photo(tmp_path / f"{i}.jpg", seed=i) for i in range(5)]
    groups = group_duplicates(paths)
    assert sorted(p for g in groups for p in g) == sorted(paths)


def test_every_member_is_within_the_threshold_of_its_own_leader():
    rng = numpy.random.default_rng(3)
    thumbnails = rng.uniform(0, 255, size=(40, 32, 32)).astype(numpy.float32)
    for group in group_thumbnail_indices(thumbnails, max_pixel_mae=40.0):
        for member in group:
            assert (
                pixel_mae(thumbnails[group[0]], thumbnails[member]) <= 40.0
            )


def test_a_chain_of_near_misses_does_not_snowball_into_one_group():
    # Membership is judged against the leader, never transitively: transitive
    # grouping chained near misses into a group of 866 real images.
    thumbnails = numpy.stack(
        [
            numpy.full((32, 32), 100.0, dtype=numpy.float32),
            numpy.full((32, 32), 104.0, dtype=numpy.float32),
            numpy.full((32, 32), 108.0, dtype=numpy.float32),
        ]
    )
    assert group_thumbnail_indices(thumbnails, max_pixel_mae=5.0) == ((0, 1), (2,))


def test_block_means_never_exceed_the_pixel_difference_they_bound():
    # Exactness rests on this: the prefilter may only ever skip pairs that the
    # full comparison would also have rejected. If the bound can exceed the true
    # difference, duplicates go missing without anything reporting it.
    rng = numpy.random.default_rng(5)
    for _ in range(200):
        pair = rng.uniform(0, 255, size=(2, 32, 32)).astype(numpy.float32)
        bounds = block_means(pair)
        lower = float(numpy.abs(bounds[0] - bounds[1]).mean())
        assert lower <= pixel_mae(pair[0], pair[1]) + 1e-5


def test_block_means_averages_each_block(tmp_path):
    thumbnails = numpy.arange(32 * 32, dtype=numpy.float32).reshape(1, 32, 32)
    bounds = block_means(thumbnails)
    assert bounds.shape == (1, 16)
    assert bounds[0, 0] == thumbnails[0, :8, :8].mean()


def test_the_hash_column_is_still_available_for_auditing(tmp_path):
    photo = write_leaf_photo(tmp_path / "a.jpg")
    with Image.open(photo) as image:
        assert phash_hex(photo) == str(imagehash.phash(image))
