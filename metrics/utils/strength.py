"""
Strength-related helper functions used across multiple metrics.
"""

def estimate_1rm(weight: float, reps: int) -> float:
    """
    Estimate one-repetition maximum (1RM) using the Epley formula.

    Parameters
    ----------
    weight : float
        Lifted weight.
    reps : int
        Number of repetitions.

    Returns
    -------
    float
        Estimated one-rep max.
    """
    return weight * (1 + reps / 30)
