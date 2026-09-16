import math

TICK_SIZE = 0.01  # Minimum price increment (discrete tick)

# Number of decimal places implied by TICK_SIZE (e.g. 0.01 → 2).
# Used by round_to_tick to avoid floating-point drift from float * float arithmetic.
_TICK_DECIMALS: int = round(-math.log10(TICK_SIZE))


def round_to_tick(price: float) -> float:
    """Round price to the nearest tick.

    Uses round(price, _TICK_DECIMALS) instead of round(price / TICK_SIZE) * TICK_SIZE
    to avoid binary floating-point accumulation errors (e.g. 102.03000000000001).
    """
    return round(price, _TICK_DECIMALS)
