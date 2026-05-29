import multiprocessing as mp
import time
import signal
from typing import Callable, Any, Optional, List
from concurrent.futures import ProcessPoolExecutor, TimeoutError, as_completed


class TimeoutProcessPool:
    def __init__(self, max_workers: int | None = None):
        """Initialize process pool with specified number of workers."""
        self.max_workers = max_workers or mp.cpu_count()
        self.executor = ProcessPoolExecutor(max_workers=self.max_workers)
        self.active_futures = []
    
    def submit(self, func: Callable, *args, timeout: Optional[float] = None, **kwargs) -> Any:
        """
        Submit a function to the process pool with optional timeout.
        
        Args:
            func: Function to execute
            *args: Positional arguments for the function
            timeout: Maximum execution time in seconds (None for no timeout)
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result of the function execution
            
        Raises:
            TimeoutError: If execution exceeds timeout period
            Exception: Any exception raised by the target function
        """
        future = self.executor.submit(func, *args, **kwargs)
        self.active_futures.append(future)
        
        try:
            # Wait for result with timeout
            result = future.result(timeout=timeout)
            self.active_futures.remove(future)
            return result
        except TimeoutError:
            # Cancel the future and clean up
            future.cancel()
            if future in self.active_futures:
                self.active_futures.remove(future)
            raise TimeoutError(f"Process execution exceeded {timeout} seconds")
        except Exception as e:
            # Clean up on any other exception
            if future in self.active_futures:
                self.active_futures.remove(future)
            raise e
    
    def submit_async(self, func: Callable, *args, timeout: Optional[float] = None, **kwargs):
        """
        Submit a function asynchronously and return future object.
        
        Args:
            func: Function to execute
            *args: Positional arguments for the function
            timeout: Maximum execution time in seconds (stored with future)
            **kwargs: Keyword arguments for the function
            
        Returns:
            Future object with timeout attribute
        """
        future = self.executor.submit(func, *args, **kwargs)
        future.timeout = timeout
        self.active_futures.append(future)
        return future
    
    def get_result(self, future, timeout: Optional[float] = None) -> Any:
        """
        Get result from a future with optional timeout override.
        
        Args:
            future: Future object returned by submit_async
            timeout: Timeout override (uses future.timeout if None)
            
        Returns:
            Result of the function execution
        """
        effective_timeout = timeout or getattr(future, 'timeout', None)
        
        try:
            result = future.result(timeout=effective_timeout)
            if future in self.active_futures:
                self.active_futures.remove(future)
            return result
        except TimeoutError:
            future.cancel()
            if future in self.active_futures:
                self.active_futures.remove(future)
            raise TimeoutError(f"Process execution exceeded {effective_timeout} seconds")
        except Exception as e:
            if future in self.active_futures:
                self.active_futures.remove(future)
            raise e
    
    def shutdown(self, wait: bool = True):
        """
        Shutdown the process pool and clean up resources.
        
        Args:
            wait: Whether to wait for pending tasks to complete
        """
        # Cancel all active futures if not waiting
        if not wait:
            for future in self.active_futures:
                future.cancel()
        
        self.executor.shutdown(wait=wait)
        self.active_futures.clear()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()


# Example usage and test functions
def sample_task(n: int, delay: float = 1.0) -> int:
    """Sample function that simulates work."""
    time.sleep(delay)
    return n * n

def long_running_task(duration: float) -> str:
    """Task that runs for specified duration."""
    time.sleep(duration)
    return f"Completed after {duration} seconds"


if __name__ == "__main__":
    # Example usage
    with TimeoutProcessPool(max_workers=4) as pool:
        print("Testing synchronous execution with timeout...")
        
        try:
            # This should complete successfully
            result = pool.submit(sample_task, 5, delay=0.5, timeout=2.0)
            print(f"Result: {result}")
            
            # This should timeout
            result = pool.submit(long_running_task, 3.0, timeout=1.0)
            print(f"Result: {result}")
        except TimeoutError as e:
            print(f"Timeout occurred: {e}")
        
        print("\nTesting asynchronous execution...")
        
        # Submit multiple tasks asynchronously
        futures = []
        for i in range(3):
            future = pool.submit_async(sample_task, i, delay=0.5, timeout=2.0)
            futures.append(future)
        
        # Collect results
        for i, future in enumerate(futures):
            try:
                result = pool.get_result(future)
                print(f"Task {i} result: {result}")
            except TimeoutError as e:
                print(f"Task {i} timed out: {e}")