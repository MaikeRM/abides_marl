TICK_SIZE = 0.01  # Minimum price increment (discrete tick)

def round_to_tick(price: float) -> float:
    """Round price to the nearest tick."""
    return round(price / TICK_SIZE) * TICK_SIZE
