# Joystick Library for MicroPython

This repository contains a simple and efficient MicroPython library for interfacing with a joystick module. The library provides calibration, scaling, and real-time value retrieval for both axes (X and Y) and an optional button.

## Features

- **X and Y Axis Support**: Reads analog joystick values and scales them to a range of -100 to 100.
- **Button Support**: Handles an optional button for input.
- **Calibration**: Automatically calibrates the joystick's center position.
- **High Performance**: Optimized for speed with native decorators and efficient sampling.

## Main differences from the Original Repository

1. The simple button true/false attribute was replaced with my own irq-based `Button` class, providing software debounce, pressed/released events, hold duration and multi-click detection, here's a [link to it's repository](https://github.com/Sasson100/Button-Micropython/).
2. Removed the esp32-specific modifications that used deprecated functions.
3. Fixed the native wrapper, it wasn't even functional previously since he called it using `@micropython.native` without importing the `micropython` module.
4. Added a bunch of new properties.

## Usage

### Initialization

```python
from joystick import Joystick

# Initialize the joystick on pin 1 for X-axes, pin 2 for Y-axes and pin 3 for the button (optional).
joystick = Joystick(1, 2, 3)
```

### Accessing Joystick Values

```python
# Get the scaled X and Y values
x_value = joystick.x
y_value = joystick.y
# or just
x_value, y_value = joystick.position

# Get the coordinates mapped to a circle
x_circle, y_circle = joystick.circle_position

# Get magnitude and angle
mag = joystick.magnitude
angle = joystick.angle
angle_radians = joystick.angle_radians

# See if it's in the deadzone
joystick.in_deadzone()

# Get the cardinal direction, as a point and as a string
direction = joystick.direction
direction_point = joystick.direction_point

# Get button state
button_state = joystick.button.is_pressed()
# There's a lot more to the button, go to my other repository linked above to read about it.
```

### Example

```python
import time
from joystick import Joystick

joystick = Joystick(1, 2, 3, cal_values=20)

while True:
    print(f"X: {joystick.x}, Y: {joystick.y}, Button: {joystick.button.is_pressed()}")
    time.sleep(0.25)
```

### Performance Benchmark

On a ESP32 the library can get all values together at aprox 0.15 kHz, which while yes is far worse than the original, in my defense there are a lot more methods which chain back into each other.

## Notes

- Adjust the `cal_values` parameter for better calibration accuracy. Higher values result in more samples being averaged.
- Ensure the joystick is in the center position during calibration.
- If the button is not used, set `pin_button<0` or don't pass the argument at all.
