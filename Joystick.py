from machine import ADC, Pin
from time import sleep_ms
import micropython
from button import Button

class Joystick:
    MaxRaw = micropython.const(65535)
    def __init__(self, pin_x: int, pin_y: int, pin_button: int=-1, *, cal_values: int=10, **kwargs):
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
        **kwargs
            Arguments for the `Button` class

        Raises
        ------
        ValueError
            If `cal_values` isn't bigger than 0
        """
        self._jx = ADC(Pin(pin_x))
        self._jy = ADC(Pin(pin_y))
        
        pull = kwargs.pop("pull","down")

        self._jb = Button(pin_button, pull = pull,**kwargs)

        # Initial calibration
        if cal_values > 0:
            self._x_center, self._y_center = self.calibrate_center(cal_values)
        else:
            raise ValueError("Number of samples for calibration can't be less than 1")
        
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
        """Scales the raw ADC value to a range of -100 to 100."""
        delta = reading - center
        if center == 0:
            return 0  # Prevent division by zero
        if delta >= 0:
            return (delta * 100) // (self.MaxRaw - center)
        else:
            return (delta * 100) // center
        
    @property
    @micropython.native
    def x(self):
        """Return x-axis value from -100 to 100."""
        return self._scale_value(self._jx.read_u16(), self._x_center)

    @property
    @micropython.native
    def y(self):
        """Return y-axis value from -100 to 100."""
        return self._scale_value(self._jy.read_u16(), self._y_center)
    
    @property
    def position(self):
        """Returns the position as a tuple, equivalent to `(self.x,self.y)`"""
        return (self.x,self.y)

    @property
    def button(self):
        """Return the `Button` object, if there is one."""
        return self._jb
    
if __name__ == "__main__":
    J = Joystick(27, 14, 12, cal_values=100)
    import time
    n = 1000
    t0 = time.ticks_us()
    for _ in range(n):
        J.x
        J.y
        J.button.is_pressed()
        J.button.was_pressed()
        J.button.was_released()
        J.button.hold_time
        J.button.multi_click_count
        J.button.multi_click_final
    t1 = time.ticks_us()
    dt = time.ticks_diff(t1, t0)
    print(f'Getting Samples at {n/dt*1e3:2.2f} kHz')

    while True:
        print("X: {}, Y: {}, Button: {}".format(J.x, J.y, J.button.is_pressed()))
        time.sleep_ms(250)  # Sleep for 250 milliseconds
