import unittest
from datetime import timedelta

from ..time_frame import RelativeTimeFrame


class RelativeTimeFrameTest(unittest.TestCase):

    def test_bounds(self):
        bounded = RelativeTimeFrame(timedelta(seconds=30), timedelta(minutes=30))
        self.assertTrue(bounded.has_min)
        self.assertTrue(bounded.has_max)

        left_bounded = RelativeTimeFrame(minimal=timedelta(microseconds=1))
        self.assertTrue(left_bounded.has_min)
        self.assertFalse(left_bounded.has_max)

        right_bounded = RelativeTimeFrame(maximal=timedelta(days=12))
        self.assertFalse(right_bounded.has_min)
        self.assertTrue(right_bounded.has_max)

        unbounded = RelativeTimeFrame()
        self.assertFalse(unbounded.has_min)
        self.assertFalse(unbounded.has_max)

    def test_union(self):
        early = RelativeTimeFrame(timedelta(seconds=10), timedelta(seconds=20))
        late = RelativeTimeFrame(timedelta(seconds=15), timedelta(seconds=25))

        expected_union = RelativeTimeFrame(timedelta(seconds=10), timedelta(seconds=25))
        self.assertEqual(expected_union, early.union(late))

    def test_unbounded_union(self):
        left_bounded = RelativeTimeFrame(minimal=timedelta(microseconds=1))
        right_bounded = RelativeTimeFrame(maximal=timedelta(days=12))

        expected_union = RelativeTimeFrame(timedelta(0), timedelta.max)
        self.assertEqual(expected_union, left_bounded.union(right_bounded))
        self.assertEqual(expected_union, right_bounded.union(left_bounded))

    def test_intersect(self):
        early = RelativeTimeFrame(timedelta(seconds=10), timedelta(seconds=20))
        late = RelativeTimeFrame(timedelta(seconds=15), timedelta(seconds=25))

        expected_intersect = RelativeTimeFrame(timedelta(seconds=15), timedelta(seconds=20))
        self.assertEqual(expected_intersect, early.intersect(late))

    def test_unbounded_intersect(self):
        left_bounded = RelativeTimeFrame(minimal=timedelta(microseconds=1))
        right_bounded = RelativeTimeFrame(maximal=timedelta(days=12))

        expected_intersect = RelativeTimeFrame(timedelta(microseconds=1), timedelta(days=12))
        self.assertEqual(expected_intersect, left_bounded.intersect(right_bounded))
        self.assertEqual(expected_intersect, right_bounded.intersect(left_bounded))

    def test_contains(self):
        # --- RelativeTimeFrames
        # Minimal and maximal in
        self.assertTrue(
            RelativeTimeFrame(timedelta(seconds=5), timedelta(seconds=10))
            in RelativeTimeFrame(timedelta(seconds=1), timedelta(seconds=11))
        )
        # Minimal not in
        self.assertFalse(
            RelativeTimeFrame(timedelta(seconds=5), timedelta(seconds=10))
            in RelativeTimeFrame(timedelta(seconds=6), timedelta(seconds=11))
        )
        # Maximal not in
        self.assertFalse(
            RelativeTimeFrame(timedelta(seconds=5), timedelta(seconds=10))
            in RelativeTimeFrame(timedelta(seconds=1), timedelta(seconds=9))
        )
        # Minimal and maximal not in
        self.assertFalse(
            RelativeTimeFrame(timedelta(seconds=0), timedelta(seconds=12))
            in RelativeTimeFrame(timedelta(seconds=1), timedelta(seconds=11))
        )
        # Minimal on bound
        self.assertTrue(
            RelativeTimeFrame(timedelta(seconds=5), timedelta(seconds=10))
            in RelativeTimeFrame(timedelta(seconds=5), timedelta(seconds=11))
        )
        # Maximal on bound
        self.assertTrue(
            RelativeTimeFrame(timedelta(seconds=5), timedelta(seconds=10))
            in RelativeTimeFrame(timedelta(seconds=1), timedelta(seconds=10))
        )

        # --- timedeltas
        self.assertTrue(
            timedelta(seconds=5) in RelativeTimeFrame(timedelta(seconds=1), timedelta(seconds=10))
        )
        self.assertFalse(
            timedelta(seconds=11) in RelativeTimeFrame(timedelta(seconds=1), timedelta(seconds=10))
        )

    def test_add(self):
        self.assertEqual(
            RelativeTimeFrame(timedelta(seconds=1), timedelta(seconds=10)) +
            RelativeTimeFrame(timedelta(seconds=1), timedelta(seconds=10)),
            RelativeTimeFrame(timedelta(seconds=2), timedelta(seconds=20))
        )
        self.assertEqual(
            RelativeTimeFrame(minimal=timedelta(seconds=1)) +
            RelativeTimeFrame(timedelta(seconds=1), timedelta(seconds=10)),
            RelativeTimeFrame(timedelta(seconds=2), timedelta.max)
        )
        self.assertEqual(
            RelativeTimeFrame(minimal=timedelta(seconds=1)) +
            RelativeTimeFrame(minimal=timedelta(seconds=1)),
            RelativeTimeFrame(timedelta(seconds=2), timedelta.max)
        )

    def test_eq(self):
        self.assertEqual(
            RelativeTimeFrame(timedelta(seconds=1), timedelta(seconds=10)),
            RelativeTimeFrame(timedelta(seconds=1), timedelta(seconds=10))
        )
        self.assertNotEqual(
            RelativeTimeFrame(timedelta(seconds=1), timedelta(seconds=10)),
            RelativeTimeFrame(timedelta(seconds=1), timedelta(seconds=11))
        )
        self.assertNotEqual(
            RelativeTimeFrame(timedelta(seconds=1), timedelta(seconds=10)),
            (timedelta(seconds=1), timedelta(seconds=11))
        )


if __name__ == "__main__":
    unittest.main()
