import unittest

from ..confidence import Confidence, ConfidenceComparer


class ConfidenceTest(unittest.TestCase):
    conf_cmp: ConfidenceComparer | None = None

    def setUp(self):
        self.conf_cmp = None

    def use_conf_comparer(self, cmp: ConfidenceComparer):
        self.conf_cmp = cmp

    def assertConfidenceLess(self, c1: Confidence, c2: Confidence):
        if self.conf_cmp is None:
            raise Exception("Confidence comparer not set")
        self.assertLess(self.conf_cmp.compare(c1, c2), 0)

    def assertConfidenceEqual(self, c1: Confidence, c2: Confidence):
        if self.conf_cmp is None:
            raise Exception("Confidence comparer not set")
        self.assertEqual(self.conf_cmp.compare(c1, c2), 0)

    def test_add(self):
        # Confidence
        self.assertEqual(
            Confidence(3.0, 5.0),
            Confidence(1.0, 2.0) + Confidence(2.0, 3.0)
        )
        self.assertEqual(
            Confidence(1.0, 2.0),
            Confidence.impartial() + Confidence(1.0, 2.0)
        )
        self.assertEqual(
            Confidence(2.0, float("inf")),
            Confidence(1.0, float("inf")) + Confidence(1.0, 2.0)
        )
        self.assertEqual(
            Confidence(float("inf"), float("inf")),
            Confidence(1.0, float("inf")) + Confidence(float("inf"), 2.0)
        )

    def test_mul(self):
        # Confidence
        self.assertEqual(
            Confidence(2.0, 4.0),
            Confidence(1.0, 2.0) * 2
        )
        self.assertEqual(
            Confidence.impartial(),
            Confidence.impartial() * 2
        )
        self.assertEqual(
            Confidence(2.0, float("inf")),
            Confidence(1.0, float("inf")) * 2
        )
        self.assertEqual(
            Confidence(float("inf"), float("inf")),
            Confidence(float("inf"), float("inf")) * 2
        )

    def test_conformity_comparer(self):
        conf_comparer = ConfidenceComparer(0)
        self.use_conf_comparer(conf_comparer)

        empty = Confidence(0, 10)
        half = Confidence(5, 10)
        full = Confidence(10, 10)

        self.assertConfidenceLess(empty, full)
        self.assertConfidenceLess(empty, half)
        self.assertConfidenceLess(half, full)

        conformity_lower = Confidence(29, 30)
        conformity_higher = Confidence(2, 2)

        self.assertConfidenceLess(conformity_lower, conformity_higher)

        #
        # Edge-case showcase
        #

        # anything with 0% accuracy equals
        self.assertConfidenceEqual(Confidence.impossible(), Confidence.impartial())
        self.assertConfidenceEqual(Confidence.impossible(), Confidence(0.0, 10.0))
        self.assertConfidenceEqual(Confidence(0.0, 10.0), Confidence(0.0, 5.0))

        # anything with 100% accuracy equals
        self.assertConfidenceEqual(Confidence.certain(1.0), Confidence.absolute())
        self.assertConfidenceEqual(Confidence.certain(1.0), Confidence.certain(2.0))

        # anything else compared based on accuracy (nom/denom)
        self.assertConfidenceLess(Confidence.impossible(), Confidence(1.0, 10.0))
        self.assertConfidenceLess(Confidence.impossible(), Confidence.certain(1.0))
        self.assertConfidenceLess(Confidence.impossible(), Confidence.absolute())

        self.assertConfidenceLess(Confidence(0.0, 10.0), Confidence(1.0, 100.0))
        self.assertConfidenceLess(Confidence(0.0, 10.0), Confidence.certain(1.0))

        self.assertConfidenceLess(Confidence.impartial(), Confidence(1.0, 10.0))
        self.assertConfidenceLess(Confidence.impartial(), Confidence.certain(1.0))

        self.assertConfidenceLess(Confidence(1.0, 10.0), Confidence(2.0, 10.0))
        self.assertConfidenceLess(Confidence(1.0, 10.0), Confidence(1.0, 5.0))
        self.assertConfidenceLess(Confidence(1.0, 10.0), Confidence.certain(1.0))

        self.assertConfidenceLess(Confidence(0.0, 10.0), Confidence.absolute())
        self.assertConfidenceLess(Confidence.impartial(), Confidence.absolute())
        self.assertConfidenceLess(Confidence(1.0, 10.0), Confidence.absolute())

    def test_reliability_comparer(self):
        time_comparer = ConfidenceComparer(1)
        self.use_conf_comparer(time_comparer)

        empty = Confidence(0, 10)
        half = Confidence(5, 10)
        full = Confidence(10, 10)
        self.assertConfidenceLess(empty, full)
        self.assertConfidenceLess(empty, half)
        self.assertConfidenceLess(half, full)

        reliability_lower = Confidence(10, 11)
        reliability_higher = Confidence(11, 100)

        self.assertConfidenceLess(reliability_lower, reliability_higher)

        #
        # Edge-case showcase
        #

        # anything with 0 match equals
        self.assertConfidenceEqual(Confidence.impossible(), Confidence.impartial())
        self.assertConfidenceEqual(Confidence.impossible(), Confidence(0.0, 10.0))
        self.assertConfidenceEqual(Confidence(0.0, 10.0), Confidence(0.0, 5.0))

        # anything with the same match "amount" equals
        self.assertConfidenceEqual(Confidence(1.0, 100.0), Confidence(1.0, 10.0))
        self.assertConfidenceEqual(Confidence(1.0, 10.0), Confidence.certain(1.0))

        # anything else compared based on match "amount" (nom)
        self.assertConfidenceLess(Confidence.impossible(), Confidence(1.0, 10.0))
        self.assertConfidenceLess(Confidence.impossible(), Confidence.certain(1.0))
        self.assertConfidenceLess(Confidence.impossible(), Confidence.absolute())

        self.assertConfidenceLess(Confidence(0.0, 10.0), Confidence(1.0, 100.0))
        self.assertConfidenceLess(Confidence(0.0, 10.0), Confidence.certain(1.0))

        self.assertConfidenceLess(Confidence.impartial(), Confidence(1.0, 10.0))
        self.assertConfidenceLess(Confidence.impartial(), Confidence.certain(1.0))

        self.assertConfidenceLess(Confidence(1.0, 10.0), Confidence(2.0, 10.0))

        self.assertConfidenceLess(Confidence.certain(1.0), Confidence.certain(2.0))
        self.assertConfidenceLess(Confidence.certain(1.0), Confidence.absolute())

        self.assertConfidenceLess(Confidence(0.0, 10.0), Confidence.absolute())
        self.assertConfidenceLess(Confidence.impartial(), Confidence.absolute())
        self.assertConfidenceLess(Confidence(1.0, 10.0), Confidence.absolute())

    def test_mixed_comparer(self):
        mixed_comparer = ConfidenceComparer(0.5)
        self.use_conf_comparer(mixed_comparer)

        empty = Confidence(0, 10)
        half = Confidence(5, 10)
        full = Confidence(10, 10)
        self.assertConfidenceLess(empty, full)
        self.assertConfidenceLess(empty, half)
        self.assertConfidenceLess(half, full)

        mixed_lower = Confidence(10, 15)
        mixed_higher = Confidence(11, 15)
        other_mixed_higher = Confidence(10, 14)

        self.assertConfidenceLess(mixed_lower, mixed_higher)
        self.assertConfidenceLess(mixed_lower, other_mixed_higher)

        #
        # Edge-case showcase
        #

        # anything with "non-positive confidence level" equals
        self.assertConfidenceEqual(Confidence.impossible(), Confidence.impartial())
        self.assertConfidenceEqual(Confidence.impossible(), Confidence(0.0, 10.0))
        self.assertConfidenceEqual(Confidence(0.0, 10.0), Confidence(0.0, 5.0))

        # In contrast to conformity - 100% accuracy doesn't mean equality
        self.assertConfidenceLess(Confidence.certain(1.0), Confidence.absolute())
        self.assertConfidenceLess(Confidence.certain(1.0), Confidence.certain(2.0))

        # In contrast to reliability - same match "amount" doesn't mean equality
        self.assertConfidenceLess(Confidence(1.0, 100.0), Confidence(1.0, 10.0))
        self.assertConfidenceLess(Confidence(1.0, 10.0), Confidence.certain(1.0))

        # anything else compared "more intuitively"
        self.assertConfidenceLess(Confidence.impossible(), Confidence(1.0, 10.0))
        self.assertConfidenceLess(Confidence.impossible(), Confidence.certain(1.0))
        self.assertConfidenceLess(Confidence.impossible(), Confidence.absolute())

        self.assertConfidenceLess(Confidence(0.0, 10.0), Confidence(1.0, 100.0))
        self.assertConfidenceLess(Confidence(0.0, 10.0), Confidence.certain(1.0))

        self.assertConfidenceLess(Confidence.impartial(), Confidence(1.0, 10.0))
        self.assertConfidenceLess(Confidence.impartial(), Confidence.certain(1.0))

        self.assertConfidenceLess(Confidence(1.0, 10.0), Confidence(2.0, 10.0))
        self.assertConfidenceLess(Confidence(1.0, 10.0), Confidence.absolute())

        self.assertConfidenceLess(Confidence(0.0, 10.0), Confidence.absolute())
        self.assertConfidenceLess(Confidence.impartial(), Confidence.absolute())


if __name__ == "__main__":
    unittest.main()
