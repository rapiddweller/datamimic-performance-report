import pytest
from app.report_components.interpolation import improved_interpolate


class TestImprovedInterpolate:
    """Tests for improved_interpolate function"""
    
    def test_basic_interpolation(self):
        """Test basic linear interpolation between two points"""
        xs = [1, 3]
        ys = [10, 20]
        
        # Should be midpoint between 10 and 20
        assert improved_interpolate(2, xs, ys) == 15
        
        # 1/4 of the way from 10 to 20
        assert improved_interpolate(1.5, xs, ys) == 12.5
        
        # 3/4 of the way from 10 to 20
        assert improved_interpolate(2.5, xs, ys) == 17.5
    
    def test_extrapolation_before_first_point(self):
        """Test extrapolation for x < xs[0]"""
        xs = [2, 4]
        ys = [10, 20]
        
        # Should return first y value
        assert improved_interpolate(1, xs, ys) == 10
        assert improved_interpolate(0, xs, ys) == 10
        assert improved_interpolate(-5, xs, ys) == 10
    
    def test_extrapolation_after_last_point(self):
        """Test extrapolation for x > xs[-1]"""
        xs = [2, 4]
        ys = [10, 20]
        
        # Linear extrapolation based on last two points
        # Slope = (20-10)/(4-2) = 5
        # At x=6: 20 + 5*(6-4) = 30
        assert improved_interpolate(6, xs, ys) == 30
        
        # At x=5: 20 + 5*(5-4) = 25
        assert improved_interpolate(5, xs, ys) == 25
    
    def test_max_extrapolate(self):
        """Test clamping of extrapolation"""
        xs = [2, 4]
        ys = [10, 20]
        
        # Should clamp x to 5, resulting in y = 25
        assert improved_interpolate(6, xs, ys, max_extrapolate=5) == 25
        
        # No clamping needed
        assert improved_interpolate(4.5, xs, ys, max_extrapolate=5) == 22.5
    
    def test_smooth_interpolation(self):
        """Test smooth interpolation"""
        xs = [0, 10]
        ys = [0, 100]
        
        # Compare linear vs smooth interpolation
        
        # At exactly halfway (t=0.5)
        # Linear: 50
        # Smooth: t_smooth = 0.5*0.5*(3-2*0.5) = 0.5*0.5*2 = 0.5
        # So result is 0*(1-0.5) + 100*0.5 = 50
        linear_50pct = improved_interpolate(5, xs, ys, use_smooth=False)
        smooth_50pct = improved_interpolate(5, xs, ys, use_smooth=True)
        assert linear_50pct == 50
        assert smooth_50pct == 50
        
        # At 30% (t=0.3)
        # Linear: 30
        # Smooth: t_smooth = 0.3*0.3*(3-2*0.3) = 0.09*2.4 = 0.216
        # So result is 0*(1-0.216) + 100*0.216 = 21.6
        linear_30pct = improved_interpolate(3, xs, ys, use_smooth=False)
        smooth_30pct = improved_interpolate(3, xs, ys, use_smooth=True)
        assert linear_30pct == 30
        assert abs(smooth_30pct - 21.6) < 0.001
        assert smooth_30pct < linear_30pct  # Smooth should be less at 30%
        
        # At 70% (t=0.7)
        # Linear: 70
        # Smooth: t_smooth = 0.7*0.7*(3-2*0.7) = 0.49*1.6 = 0.784
        # So result is 0*(1-0.784) + 100*0.784 = 78.4
        linear_70pct = improved_interpolate(7, xs, ys, use_smooth=False)
        smooth_70pct = improved_interpolate(7, xs, ys, use_smooth=True)
        assert linear_70pct == 70
        assert abs(smooth_70pct - 78.4) < 0.001
        assert smooth_70pct > linear_70pct  # Smooth should be more at 70%
    
    def test_non_negative_output(self):
        """Test that output is always non-negative"""
        xs = [1, 3]
        ys = [-10, -20]
        
        # Should return 0 instead of negative values
        assert improved_interpolate(2, xs, ys) == 0
        assert improved_interpolate(0, xs, ys) == 0
        assert improved_interpolate(4, xs, ys) == 0
    
    def test_all_negative_ys(self):
        """Test when all y values are negative"""
        xs = [1, 3, 5]
        ys = [-10, -20, -30]
        
        # Should return 0 for all queries
        assert improved_interpolate(0, xs, ys) == 0
        assert improved_interpolate(2, xs, ys) == 0
        assert improved_interpolate(4, xs, ys) == 0
        assert improved_interpolate(6, xs, ys) == 0
    
    def test_single_point(self):
        """Test with only one data point"""
        xs = [5]
        ys = [10]
        
        # Before point
        assert improved_interpolate(4, xs, ys) == 10
        
        # At point
        assert improved_interpolate(5, xs, ys) == 10
        
        # After point - should return y value since no extrapolation possible
        assert improved_interpolate(6, xs, ys) == 10
    
    def test_exact_x_match(self):
        """Test when x exactly matches one of the xs values"""
        xs = [1, 3, 5]
        ys = [10, 20, 30]
        
        # x matches exactly
        assert improved_interpolate(1, xs, ys) == 10
        assert improved_interpolate(3, xs, ys) == 20
        assert improved_interpolate(5, xs, ys) == 30
    
    def test_multiple_intervals(self):
        """Test interpolation with multiple intervals"""
        xs = [1, 3, 6, 10]
        ys = [10, 20, 15, 30]
        
        # Between points 1 and 2
        assert improved_interpolate(2, xs, ys) == 15
        
        # Between points 2 and 3
        assert improved_interpolate(4.5, xs, ys) == 17.5
        
        # Between points 3 and 4
        assert improved_interpolate(8, xs, ys) == 22.5
    
    def test_negative_x_values(self):
        """Test with negative x values"""
        xs = [-10, -5]
        ys = [100, 50]
        
        # Between the points
        assert improved_interpolate(-7.5, xs, ys) == 75
        
        # Before first point
        assert improved_interpolate(-15, xs, ys) == 100
        
        # After last point
        assert improved_interpolate(-2.5, xs, ys) == 25  # Extrapolation 