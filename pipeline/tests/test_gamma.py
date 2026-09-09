import math
import unittest
from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd

from src.calculations.gamma import (
    bs_gamma,
    gamma_profile_by_strike,
    gamma_profile_near_term,
)


def _chain_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "strike": [590.0, 600.0, 610.0],
            "openInterest": [100.0, 200.0, 100.0],
            "impliedVolatility": [0.2, 0.2, 0.2],
        }
    )


@dataclass
class _Chain:
    expiration: str
    calls: pd.DataFrame
    puts: pd.DataFrame


class GammaFeedValidationTests(unittest.TestCase):
    def test_near_term_profile_skips_nan_spot(self) -> None:
        frame = _chain_frame()
        chain = _Chain(
            expiration=str(date.today() + timedelta(days=7)),
            calls=frame,
            puts=frame,
        )

        self.assertIsNone(gamma_profile_near_term([chain], math.nan))

    def test_single_expiration_profile_skips_nan_spot(self) -> None:
        frame = _chain_frame()

        self.assertIsNone(
            gamma_profile_by_strike(
                frame,
                frame,
                math.nan,
                str(date.today() + timedelta(days=7)),
            )
        )

    def test_black_scholes_skips_non_finite_inputs(self) -> None:
        self.assertIsNone(bs_gamma(math.nan, 600.0, 7 / 365, 0.2))
        self.assertIsNone(bs_gamma(600.0, math.inf, 7 / 365, 0.2))
        self.assertIsNone(bs_gamma(600.0, 600.0, 7 / 365, math.nan))

    def test_valid_profile_is_unchanged(self) -> None:
        frame = _chain_frame()
        result = gamma_profile_by_strike(
            frame,
            frame,
            600.0,
            str(date.today() + timedelta(days=7)),
        )

        self.assertIsNotNone(result)
        self.assertEqual(result["spot"], 600.0)
        self.assertEqual(len(result["buckets"]), 11)


if __name__ == "__main__":
    unittest.main()
