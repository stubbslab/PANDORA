# states/operation_timer.py
import time

class OperationTimer:
    """OperationTimer class to ensure operations are not performed faster than a specified frequency.

    Args:
        min_interval (float): Minimum time interval (in seconds) between operations.
        name (str): Name identifier for logging purposes.

    Example:
        timer = OperationTimer(min_interval=0.1, name="Shutter")
        if timer.can_operate():
            # Perform operation
            timer.update_last_operation_time()
    """

    def __init__(self, min_interval, name="Operation"):
        self.min_interval = min_interval  # Minimum interval in seconds
        self.last_operation_time = time.time()   # Timestamp of the last operation
        self.remaining_time = 0            # Remaining time until next operation
        # A dictionary to store labeled timestamps
        self.timestamps = {}
    
    def now(self):
        # Returns the current time, for example in seconds since the Epoch
        # Replace with your preferred time source if needed (e.g. time.monotonic())
        return time.time()
    def sleep(self, seconds):
        # Sleep for a given number of seconds
        time.sleep(seconds)

    def mark(self, label: str):
        """
        Record a timestamp with a given label.
        
        Args:
            label (str): A descriptive name for the event being marked.
        
        Example:
            self.mark("exposure_start")
            self.mark("shutter_open")
        """
        current_time = self.now()
        self.timestamps[label] = current_time
        # You could also print or log the event
        # print(f"Marked '{label}' at time {current_time}")

    def get_mark(self, label: str):
        """
        Retrieve a previously recorded timestamp by label.
        
        Args:
            label (str): The name of the event whose time you want to get.
        
        Returns:
            float or None: The recorded time for that label, or None if not found.
        """
        return self.timestamps.get(label, None)

    def elapsed_since(self, label: str):
        """
        Return how much time has passed since a given labeled event.
        
        Args:
            label (str): The label of the event to measure from.
        
        Returns:
            float: The number of seconds elapsed since the event. 
                   Returns None if label not found.

        Example:
            self.mark("start")
            time.sleep(2)
            elapsed = self.elapsed_since("start")  # Should return approximately 2.0
        """
        event_time = self.get_mark(label)
        if event_time is not None:
            return self.now() - event_time
        return None
    
    def can_operate(self, min_interval=None):
        """Check if enough time has passed since the last operation.

        Returns:
            bool: True if operation can proceed, False otherwise.
        """
        self.remaining_time = 0
        if min_interval is None:
            min_interval = self.min_interval
            
        if self.last_operation_time is None:
            return True
        
        current_time = time.time()
        elapsed_time = current_time - self.last_operation_time
        
        if elapsed_time >= min_interval:
            return True
        else:
            self.remaining_time = min_interval - elapsed_time
            return False

    def update_last_operation_time(self):
        """Update the timestamp of the last operation."""
        self.last_operation_time = time.time()

    def sleep_through_remaining_interval(self):
        """Sleep through the remaining time interval until the next operation."""
        # logger.info(f"Sleeping for {remaining_time:.2f} seconds before next operation.")
        time.sleep(self.remaining_time)

    def sleep(self, period):
        time.sleep(period)