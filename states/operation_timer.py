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
        self.last_operation_time = None   # Timestamp of the last operation
        self.remaining_time = 0            # Remaining time until next operation

    def can_operate(self):
        """Check if enough time has passed since the last operation.

        Returns:
            bool: True if operation can proceed, False otherwise.
        """
        if self.last_operation_time is None:
            return True
        
        current_time = time.time()
        elapsed_time = current_time - self.last_operation_time
        
        if elapsed_time >= self.min_interval:
            return True
        else:
            self.remaining_time = self.min_interval - elapsed_time
            return False

    def update_last_operation_time(self):
        """Update the timestamp of the last operation."""
        self.last_operation_time = time.time()

    def sleep_through_remaining_interval(self):
        """Sleep through the remaining time interval until the next operation."""
        # logger.info(f"Sleeping for {remaining_time:.2f} seconds before next operation.")
        time.sleep(self.remaining_time)