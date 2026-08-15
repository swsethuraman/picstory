"""Subject clustering for S03 (DECISIONS.md D-007): a wider, disclosed
perceptual-similarity grouping than F03's near-duplicate runs.

D-007's ruling: implement S03's "batch-mates" as a looser Hamming-distance
grouping over the same dHash primitive F03 uses
(`_imaging.difference_hash`), but deliberately relaxed from F03's
calibration in the two ways the ruling names: (1) a wider distance
threshold, so "same subject, different attempts/angles" - not just
near-identical copies - cluster together, and (2) no focal-length or
timestamp gate, since a photographer changing lens or returning to a
subject later is still the same "batch-mate" relationship S03's Detection
text describes, unlike F03's "no change ... consecutive" copies. Own
constants below, calibrated independently of f03.py's - conflating the two
thresholds would silently make this the too-narrow proxy D-007 rejected.

Unlike F03 (pairwise-*consecutive* only - a burst is, by definition, an
unbroken run), subject clusters need not be adjacent: two attempts at the
same subject taken minutes apart, with other subjects shot in between,
should still cluster. So this compares every pair in the batch, not just
neighbors, and merges transitively (union-find) into connected components.
That carries the same chain-similarity caveat critic-003 named for F03's
pairwise-consecutive runs (frame 1 vs. frame 5 could differ a lot while
every adjacent link stays under threshold) - one layer more exposed here
since any pair, not just neighbors, can extend a chain. Nothing in the
source material's batches (a handful of attempts per subject, not a long
walking pan) obviously triggers pathological chaining across unrelated
subjects; flagging for whoever next tunes this, the same way critic-003
flagged F03's version.
"""

from __future__ import annotations

from picstory.detectors._imaging import hamming_distance
from picstory.frame import Frame

HASH_SIZE = 8
# Deliberately looser than F03's HASH_DISTANCE_THRESHOLD (6/64). Calibrated
# against tests/test_s03_tight_framing.py's fixture (F03's own checkerboard
# + moving-block scene generator, reused so the two thresholds are directly
# comparable): a subject shifted 15% of frame width scores 14 - already
# above F03's threshold (rejected as a "real variation" there), but this is
# exactly the case S03 wants to admit ("a different attempt/angle at the
# same subject"). A subject shifted 50% of frame width scores 20 - clearly a
# different composition, not an attempt at the same shot. 15 sits between
# the two, and (checked directly) also avoids chaining the two together
# through an intermediate frame in that same fixture set.
HASH_DISTANCE_THRESHOLD = 15


def _frame_hash(frame: Frame):
    # QUEUE.md item 15b: same HASH_SIZE (8) as f03.py's own hash, so this
    # reuses the memoized `Frame.dhash` entry F03 already populated for the
    # same frame in the same batch run, rather than recomputing it.
    return frame.dhash(hash_size=HASH_SIZE)


def group_subject_clusters(frames: list[Frame]) -> list[list[str]]:
    """Connected components of frames within HASH_DISTANCE_THRESHOLD of each other.

    Compares every pair in the batch (not just consecutive - see module
    docstring), with no focal-length/timestamp gate. Returns each cluster as
    a list of `frame_id`s in batch order; a frame with no batch-mate within
    threshold is simply absent (a singleton has no "tightest among
    batch-mates" to compute) - the same "absent, not a singleton group"
    convention `f03.group_near_duplicates` already uses.
    """
    n = len(frames)
    hashes = [_frame_hash(f) for f in frames]
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        root_i, root_j = find(i), find(j)
        if root_i != root_j:
            parent[root_i] = root_j

    for i in range(n):
        for j in range(i + 1, n):
            if hamming_distance(hashes[i], hashes[j]) <= HASH_DISTANCE_THRESHOLD:
                union(i, j)

    clusters: dict[int, list[str]] = {}
    for i, frame in enumerate(frames):
        clusters.setdefault(find(i), []).append(frame.frame_id)

    return [ids for ids in clusters.values() if len(ids) >= 2]
