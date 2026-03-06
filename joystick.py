from machine import ADC, Pin
from time import sleep_ms
import micropython
from button import Button
from math import sqrt, atan2, pi

class Joystick:
    MaxRaw = micropython.const(65535)
    def __init__(self, pin_x: int, pin_y: int, pin_button: int=-1, *, cal_values: int=10, radius:int|float = 1, deadzone:int|float = 0.1, **kwargs):
        """
        Initializes the joystick

        Parameters
        ----------
        pin_x : int
            The pin id for the x coordinate's pin (usually labeled X or HORZ)
        pin_y : int
            The pin id for the y coordinate's pin (usually labeled Y or VERT)
        pin_button : int, optional
            The pin id for the button's pin (Usually labeled B, SW or SEL), by default -1 (inactive)
        cal_values : int, optional
            The number of samples on the initial calibration of the joystick, by default 10
        radius : int | float, optional
            The radius of values for x and y, by default 1
        deadzone : int | float, optional
            The decimal value used for the deadzone calculation, must be between 0 (inclusive) and 1 (exclusive), by default 0.05
        **kwargs
            Arguments for the `Button` class

        Raises
        ------
        ValueError
            If `cal_values` isn't bigger than 0
        ValueError
            if `radius` isn't bigger than 0
        ValueError
            if `deadzone` isn't between 0<=x<1
        """
        if cal_values<=0:
            raise ValueError("Number of samples for calibration can't be less than 1")
        if radius<=0:
            raise ValueError("Range of numbers has to be above 0")
        if not 0<=deadzone<1:
            raise ValueError("Deadzone must be 0<=x<1")

        self._jx = ADC(Pin(pin_x))
        self._jy = ADC(Pin(pin_y))
        
        pull = kwargs.pop("pull","down")

        self._jb = Button(pin_button, pull = pull,**kwargs)

        self.deadzone = deadzone
        self.radius = radius
        # Initial calibration
        self._x_center, self._y_center = self.calibrate_center(cal_values)
        self._direction_list = ["right","up","left","down"]
        self._direction_point_list = [(1,0),(0,1),(-1,0),(0,-1)]
        
        micropython.alloc_emergency_exception_buf(100)

    def calibrate_center(self, num_samples=10, delay_ms=1):
        """
        Calibrates the center value for both ADC pins.
        
        Args:
            num_samples (int): The number of samples to average for calibration.
        
        Returns
            tuple: The calibrated center values for x and y axes.
        """
        total_x = 0
        total_y = 0
        for _ in range(num_samples):
            total_x += self._jx.read_u16()
            total_y += self._jy.read_u16()
            if delay_ms > 0:
                sleep_ms(delay_ms)
        center_x = total_x // num_samples
        center_y = total_y // num_samples
        return center_x, center_y
    
    @micropython.native
    def _scale_value(self, reading, center):
        """Scales the raw ADC value to the set radius."""
        value = self.radius
        delta = reading - center
        if center == 0:
            return 0  # Prevent division by zero
        if delta >= 0:
            return (delta*value) / (self.MaxRaw - center)
        else:
            return (delta*value) / center
    
    @property
    @micropython.native
    def _deadzone_radius_sq(self):
        return self.deadzone*self.radius**2
    
    @property
    def _direction_index(self):
        return round(self.angle_radians*2/pi)

    # Public API

    @property
    @micropython.native
    def raw_x(self)->float:
        """Returns the raw x value, before applying the deadzone."""
        return self._scale_value(self._jx.read_u16(), self._x_center)
    
    @property
    @micropython.native
    def raw_y(self)->float:
        """Returns the raw y value, before applying the deadzone."""
        return self._scale_value(self._jy.read_u16(), self._y_center)

    @property
    @micropython.native
    def position(self) -> tuple[float,float]:
        """Returns a tuple of the joystick's position"""
        x = self.raw_x
        y = self.raw_y
        if x**2+y**2 <= self._deadzone_radius_sq:
            x = y = 0
        return (x,y)
    
    @property
    def x(self):
        return self.position[0]
    
    @property
    def y(self):
        return self.position[1]
    
    def in_deadzone(self):
        """Returns if the joystick is inside the deadzone or not (shortcut for if `position` is (0,0))"""
        return self.position==(0,0)

    @property
    def button(self)->Button:
        """Return the `Button` object, if there is one."""
        return self._jb
    
    @property
    @micropython.native
    def circle_position(self)->tuple[float,float]:
        """Returns the joystick's coordinates mapped to a circle."""
        radius = self.radius
        x = self.x/radius
        y = self.y/radius
        x_p = radius*x*sqrt(1-(y**2)/2)
        y_p = radius*y*sqrt(1-(x**2)/2)
        return (x_p,y_p)
    
    @property
    @micropython.native
    def magnitude(self)->float:
        """Returns the joystick's magnitude"""
        x_sq = self.x**2
        y_sq = self.y**2
        # equation derived from plugging the equations in circle_position into sqrt(x^2+y^2)
        return sqrt(x_sq+y_sq-x_sq*y_sq)
    
    @property
    @micropython.native
    def angle_radians(self)->float:
        """Returns the joystick's angle in radians"""
        x,y = self.position
        return atan2(y,x)
    
    @property
    def angle(self)->float:
        """Returns the joystick's angle in degrees"""
        return self.angle_radians*180/pi
    
    @property
    def direction(self)->str:
        """Returns the cardinal direction of the joystick, returns "neutral" if within the deadzone"""
        if self.in_deadzone():
            return "neutral"
        return self._direction_list[self._direction_index]
    
    @property
    def direction_point(self)->tuple[int,int]:
        if self.in_deadzone():
            return (0,0)
        return self._direction_point_list[self._direction_index]
    
if __name__ == "__main__":
    J = Joystick(27, 14, 12, cal_values=1000)
    import time
    n = 1000
    t0 = time.ticks_us()
    for _ in range(n):
        J.raw_x
        J.raw_y
        J.position
        J.circle_position
        J.magnitude
        J.angle
        J.angle_radians
        J.direction
        J.direction_point
        J.in_deadzone()
        J.button.is_pressed()
        J.button.was_pressed()
        J.button.was_released()
        J.button.hold_time
        J.button.multi_click_count
        J.button.multi_click_final
    t1 = time.ticks_us()
    dt = time.ticks_diff(t1, t0)
    print(f'Getting Samples at {n/dt*1e3:2.2f} kHz')
    time.sleep(2)
    while True:
        print(f"X: {J.x} Y: {J.y} Magnitude: {J.magnitude} Button: {J.button.is_pressed()}")
        time.sleep_ms(250)  # Sleep for 250 milliseconds
