"""
Interpolation utilities for performance report generation.
Contains functions for data interpolation and smoothing.
"""

import math


def improved_interpolate(x, xs, ys, max_extrapolate=None, use_smooth=False):
    """
    Improved interpolation function for estimating y-values at a given x.
    
    For x values:
      - Less than or equal to xs[0]: returns max(ys[0], 0)
      - Greater than or equal to xs[-1]: performs linear extrapolation based on the last two data points.
      - In between: interpolates between measured points either linearly or using a smooth (cubic Hermite) approach.
    
    Optionally, if max_extrapolate is provided, any x value greater than max_extrapolate will be clamped.
    
    Args:
        x (float): The query x-value.
        xs (list[float]): Sorted list of x-coordinates of measured data points.
        ys (list[float]): Corresponding y-coordinates.
        max_extrapolate (float, optional): Maximum x value to extrapolate. If x > max_extrapolate, x is clamped.
        use_smooth (bool, optional): If True, use smooth (cubic Hermite/smoothstep) interpolation between points.
    
    Returns:
        float: The interpolated or extrapolated y-value (guaranteed to be non-negative).
    """
    # Clamp x to max_extrapolate if provided.
    if max_extrapolate is not None and x > max_extrapolate:
        x = max_extrapolate

    # If x is before the first measured point, return the first value.
    if x <= xs[0]:
        return max(ys[0], 0)

    # If x is after the last measured point, use linear extrapolation.
    if x >= xs[-1]:
        if len(xs) >= 2:
            slope = (ys[-1] - ys[-2]) / (xs[-1] - xs[-2])
            extrapolated = ys[-1] + slope * (x - xs[-1])
            return max(extrapolated, 0)
        else:
            return max(ys[-1], 0)

    # For x between measured points, find the correct interval.
    for i in range(1, len(xs)):
        if xs[i-1] <= x <= xs[i]:
            t = (x - xs[i-1]) / (xs[i] - xs[i-1])
            if use_smooth:
                # Smoothstep interpolation for a smoother, optimistic transition.
                t_smooth = t * t * (3 - 2 * t)
                interpolated = ys[i-1] * (1 - t_smooth) + ys[i] * t_smooth
            else:
                # Standard linear interpolation.
                interpolated = ys[i-1] + t * (ys[i] - ys[i-1])
            return max(interpolated, 0)
