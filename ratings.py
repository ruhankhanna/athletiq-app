import math


def rating_100m(time):
    return max(0, 8.15 - 7.82 * math.log10(time - 9.0))

def rating_200m(time):
    return max(0, 8.51 - 5.90 * math.log10(time - 18.61))

def rating_400m(time):
    return max(0, 8.72 - 5.02 * math.log10(time - 42.45))

def rating_800m(time):
    return max(0, 8.87 - 4.41 * math.log10(time - 101.33))

def rating_1500m(time):
    return max(0, 9.07 - 3.49 * math.log10(time - 205.42))


def rating_1600m(time):
    return max(0, 9.17 - 3.51 * math.log10(time - 220.42))

def rating_3000m(time):
    return max(0, 9.23 - 3.05 * math.log10(time - 419.42))

def rating_3200m(time):
    return max(0, 9.26 - 3.12 * math.log10(time - 509.42))

def rating_5k_xc(time):
    return max(0, 9.40 - 2.62 * math.log10(time - 756.42))


def get_event_rating(event_name, time):
    name = event_name.upper()
    if name == "100M": return rating_100m(time)
    elif name == "200M": return rating_200m(time)
    elif name == "400M": return rating_400m(time)
    elif name == "800M": return rating_800m(time)
    elif name == "1500M": return rating_1500m(time)
    elif name == "3000M": return rating_3000m(time)
    elif name == "3200M": return rating_3200m(time)
    elif name == "1600M": return rating_1600m(time)
    elif name in ["5000M", "5K"]: return rating_5k_xc(time)
    elif name in ["5K", "5K XC", "XC"]: return rating_5k_xc(time)
    return None


def invert_rating(rating, A, B, offset):
    return 10 ** ((A - rating) / B) + offset

# Per-event inversions
expected_time_funcs = {
    "100M": lambda r: invert_rating(r, 8.15, 7.82, 9.0),
    "200M": lambda r: invert_rating(r, 8.51, 5.90, 18.61),
    "400M": lambda r: invert_rating(r, 8.72, 5.02, 42.45),
    "800M": lambda r: invert_rating(r, 8.87, 4.41, 101.33),
    "1500M": lambda r: invert_rating(r, 9.07, 3.49, 205.42),
    "1600M": lambda r: invert_rating(r, 9.17, 3.51, 220.42),
    "3000M": lambda r: invert_rating(r, 9.23, 3.05, 419.42),
    "3200M": lambda r: invert_rating(r, 9.26, 3.12, 509.42),
    "5K": lambda r: invert_rating(r, 9.40, 2.62, 756.42)
}

def get_expected_time(event_name, rating):
    fn = expected_time_funcs.get(event_name.upper())
    return fn(rating) if fn else None

def adjust_rating_based_on_field(event_name, athlete_time, base_rating, field_ratings):
    """
    Adjust the athlete's rating based on how the rest of the field performed.

    - `event_name`: e.g. "1600M"
    - `athlete_time`: float (in seconds)
    - `base_rating`: float (0–10 scale)
    - `field_ratings`: list of float ratings for other athletes
    """
    expected_times = [
        get_expected_time(event_name, r)
        for r in field_ratings if get_expected_time(event_name, r)
    ]

    if not expected_times:
        return base_rating  # fallback: no adjustment

    actual_deltas = [actual - expected for actual, expected in zip([athlete_time]*len(expected_times), expected_times)]
    avg_field_delta = sum(actual_deltas) / len(actual_deltas)

    # Subtract if field did well (you underperformed)
    # Add if field underperformed (you outperformed conditions)
    adjustment = -0.8 * avg_field_delta

    # Convert delta in seconds to rating-space estimate
    adjusted = base_rating + adjustment

    # Clamp result
    return max(0, min(10, adjusted))
