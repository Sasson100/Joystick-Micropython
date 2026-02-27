import time, micropython
from machine import Pin, Timer

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Callable

class Button:
    def __init__(
        self,
        pin_id: int,
        debounce_ms = 30,
        pull: str = "up",
        multi_click_timeout: int = 200,
        custom_callback: Callable[[bool],None] | None = None
        ):
        """
        Initialize a debounced GPIO button.

        This class is designed for active-low buttons by default. Adjust `pull` 
        if your button has a different electrical configuration.

        Parameters
        ----------
        pin_id : int
            GPIO pin number connected to the button.
        debounce_ms : int, optional
            Debounce interval in milliseconds. State changes occurring within this 
            window are ignored. Default is 30 ms.
        pull : {"up", "down"}, optional
            Internal pull resistor configuration:
            - "up"   : idle state is HIGH, button press pulls LOW (default)
            - "down" : idle state is LOW, button press pulls HIGH
        multi_click_timeout : int, optional
            Maximum interval in milliseconds between consecutive presses to be 
            considered part of the same multi-click sequence. Default is 200 ms.
        custom_callback : Callable[[bool], None] or None, optional
            Function called after each button state change. Receives a single 
            boolean argument indicating the new button state. Default is None.

        Raises
        ------
        ValueError
            If `pull` is not "up" or "down".
        ValueError
            If `custom_callback` is not a callable or None.

        Notes
        -----
        - The `custom_callback` function is subject to MicroPython interrupt callback 
        restrictions. See: https://docs.micropython.org/en/latest/reference/isr_rules.html
        - All timing parameters (debounce, multi-click) are in milliseconds.
        """
        
        now = time.ticks_ms()

        # Setting up the pin
        pull = pull.lower()
        if pull not in ("up","down"):
            raise ValueError("pull must be either up or down")
        elif pin_id<0 or pull == "down":
            pull_val = Pin.PULL_DOWN
            self._active_on = True
        else:
            pull_val = Pin.PULL_UP
            self._active_on = False
        
        self._pin = Pin(pin_id, Pin.IN, pull_val)
        self._pin.irq(
            trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING,
            handler=self._irq_handler
        )

        if callable(custom_callback) or custom_callback is None:
            self._custom_callback = custom_callback
        else:
            raise ValueError("custom_callback must either be a function with a single argument (state) or be empty")

        # Setting up attributes
        self._debounce_ms = debounce_ms
        self._state = self._read_value()
        self._last_change = self._last_press = self._last_release = now
        self._pressed_event = self._released_event = False

        self._multi_click_timeout = multi_click_timeout
        self._multi_click_final = self._multi_click_count = 0
        self._multi_click_timer = Timer(-1)

        micropython.alloc_emergency_exception_buf(100)
    
    def _read_value(self) -> bool:
        """
        Read the logical button state.

        Returns
        -------
        bool
            True if the button is currently pressed, False otherwise.

        Notes
        -----
        The returned value accounts for the configured pull direction.
        """
        value = self._pin.value()
        return value == self._active_on

    def _irq_handler(self,_: Pin):
        """
        Irq handler for the button.

        Parameters
        ----------
        _ : Pin
            Throwaway parameter required by `Pin.irq`, equal to the button's pin.
        """
        now = time.ticks_ms()
        new_state = self._read_value()
        if time.ticks_diff(now, self._last_change)<self._debounce_ms or new_state==self._state:
            return

        self._state = new_state
        self._last_change = now

        if new_state:
            self._pressed_event = True
            self._last_press = now

            self._multi_click_timer.deinit()
            self._multi_click_count += 1
        else:
            self._released_event = True
            self._last_release = now
            self._multi_click_timer.init(mode = Timer.ONE_SHOT, period=self._multi_click_timeout, callback=self._multi_click_timer_func)

        if self._custom_callback:
            self._custom_callback(new_state)

    def _multi_click_timer_func(self,_: Timer):
        """
        `_multi_click_timer`'s callback function.

        Parameters
        ----------
        _ : Timer
            Throwaway parameter required by `Timer.init`, equal to the timer object.
        """
        self._multi_click_final = self._multi_click_count
        self._multi_click_count = 0

    # Public API
    def is_pressed(self) -> bool:
        """
        Current logical state of the button.

        Returns
        -------
        bool
            True if the button is currently pressed, False otherwise.
        """
        return self._state

    def was_pressed(self) -> bool:
        """
        Check whether a press event occurred.

        Returns
        -------
        bool
            True if the button was pressed since the last call to this method,
            False otherwise.

        Notes
        -----
        This method clears the internal pressed event flag when read.
        """
        if self._pressed_event:
            self._pressed_event = False
            return True
        return False

    def was_released(self) -> bool:
        """
        Check whether a release event occurred.

        Returns
        -------
        bool
            True if the button was released since the last call to this method,
            False otherwise.

        Notes
        -----
        This method clears the internal released event flag when read.
        """
        if self._released_event:
            self._released_event = False
            return True
        return False
    
    def clear_events(self) -> None:
        """
        Resets the pressed and released events and both multi-click counters.
        """
        self._pressed_event = self._released_event = False
        self._multi_click_final = self._multi_click_final = 0

    @property
    def hold_time(self) -> int:
        """
        Duration the button has been held.

        Returns
        -------
        int
            Time in milliseconds that the button has been continuously pressed.
            Returns 0 if the button is not currently pressed.
        """
        if not self.is_pressed():
            return 0
        
        return time.ticks_diff(time.ticks_ms(),self._last_press)
    
    @property
    def multi_click_count(self) -> int:
        """
        Number of times the button's been pressed in a row

        Returns
        -------
        int
            Number of times the button's been pressed with less than
            `multi_click_timeout` milliseconds between presses in a row.
        """
        return self._multi_click_count

    @property
    def multi_click_final(self) -> int:
        """
        Number of times the button was pressed in a row
        after the pressing streak ended.

        Returns
        -------
        int
            Number of times the button was pressed 
        """
        count = self._multi_click_final
        self._multi_click_final = 0
        return count