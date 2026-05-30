import logging
import requests
import time
from math import ceil, sqrt, pi
from typing import List, Literal, Tuple, Optional, Dict, Any, cast
from dacite import from_dict
from .objects import (
    CurrentVersionResponse,
    PoseResponse,
    SpeedResponse,
    LaserResponse,
    EmptyResponse,
    NavStatusResponse,
    ChassisHttpResponseType,
    ChassisHttpResponse,
)


class Chassis:

    def __init__(self, base_url: str = "http://192.168.6.8"):
        # Create a requests session
        self.session = requests.Session()
        self.base_url = base_url
        self._check_version_info()

        self._last_nav_request_time: float = 0
        self._last_nav_position: Tuple[float, float, float] | None = None

    def __del__(self):
        # Close the session when the object is deleted
        self.session.close()

    def _abstract_http_get_or_post_and_parse(
        self,
        url: str,
        method: Literal["GET", "POST"],
        payload: Optional[dict],
        response_class: ChassisHttpResponseType,
    ) -> ChassisHttpResponse:
        """
        Abstract method to send HTTP GET or POST request and parse the response.

        Args:
            url (str): The URL to send the request to.
            method (Literal["GET", "POST"]): The HTTP method to use.
            payload (Optional[dict]): The payload for POST requests.
            response_class (ChassisHttpResponse): The expected response class.

        Returns:
            An instance of the response_class.
        """
        try:
            if method == "GET":
                response = self.session.get(f"{self.base_url}{url}")
            elif method == "POST":
                if payload is None:
                    raise ValueError("Payload must be provided for POST requests")
                response = self.session.post(f"{self.base_url}{url}", json=payload)
            else:
                raise ValueError("Unsupported HTTP method")
        except requests.RequestException as e:
            raise ConnectionError(f"Failed to connect to chassis API: {e}")

        # Raise an error for bad responses
        response.raise_for_status()

        # Parse the response to JSON, and then to the expected response class
        try:
            data = response.json()
            return from_dict(data_class=response_class, data=data)
        except ValueError as e:
            raise ValueError(f"Invalid response format: {e}")
        except TypeError as e:
            raise TypeError(f"Response data does not match expected format: {e}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error while parsing response: {e}")

    def _check_version_info(self) -> None:
        """
        Check if the base_url is valid and the chassis API is reachable.
        An exception is raised if the check fails.
        """
        version_info = cast(
            CurrentVersionResponse,
            self._abstract_http_get_or_post_and_parse(
                url="/reeman/current_version",
                method="GET",
                payload=None,
                response_class=CurrentVersionResponse,
            ),
        )

        logging.info(f"Connected to chassis API, version: {version_info.version}")

    def speed_ctrl(self, vx: float, vth: float) -> bool:
        """
        Control the speed of the chassis.

        Args:
            vx (float): Linear velocity in the x direction (m/s).
                        Positive for forward, negative for backward.
            vth (float): Angular velocity around the z axis (rad/s).
                         Positive for left, negative for right.

        Returns:
            bool: True if the command was successful, False otherwise.
        """
        _ = cast(
            EmptyResponse,
            self._abstract_http_get_or_post_and_parse(
                url="/cmd/speed",
                method="POST",
                payload={"vx": vx, "vth": vth},
                response_class=EmptyResponse,
            ),
        )

        return True

    def move_theta(self, theta: float, vth: float) -> bool:
        """
        Rotate the chassis by a specified angle.

        Args:
            theta (float): The angle to rotate (degrees).
                           Positive for left, negative for right.
            vth (float): Angular velocity around the z axis (rad/s).

        Returns:
            bool: True if the command was successful, False otherwise.
        """
        # Check for zero rotation
        if theta == 0.0:
            logging.warning("Theta is 0, no rotation needed.")
            return True

        # Post the http request
        payload = {
            "direction": 1 if theta >= 0 else 0,
            "angle": ceil(abs(theta)),
            "speed": max(0.1, abs(vth)),
        }
        _ = cast(
            EmptyResponse,
            self._abstract_http_get_or_post_and_parse(
                url="/cmd/turn",
                method="POST",
                payload=payload,
                response_class=EmptyResponse,
            ),
        )

        return True

    def move_x(self, x: float, vx: float) -> bool:
        """
        Move the chassis forward or backward by a specified distance.

        Args:
            x (float): The distance to move (cm).
                       Positive for forward, negative for backward.
            vx (float): Linear velocity in the x direction (m/s).

        Returns:
            bool: True if the command was successful, False otherwise.
        """
        # Check for zero movement
        if x == 0.0:
            logging.warning("Distance is 0, no movement needed.")
            return True

        # Post the http request
        payload = {
            "direction": 1 if x >= 0 else 0,
            "distance": ceil(abs(x)),
            "speed": max(0.1, abs(vx)),
        }
        _ = cast(
            EmptyResponse,
            self._abstract_http_get_or_post_and_parse(
                url="/cmd/move",
                method="POST",
                payload=payload,
                response_class=EmptyResponse,
            ),
        )

        return True

    def get_pos(self) -> Tuple[float, float, float]:
        """
        Get the position of the chassis.
        Returns:
            A tuple (x, y, theta) representing the position.
        """
        pos_info = cast(
            PoseResponse,
            self._abstract_http_get_or_post_and_parse(
                url="/reeman/pose",
                method="GET",
                payload=None,
                response_class=PoseResponse,
            ),
        )
        return (pos_info.x, pos_info.y, pos_info.theta)

    def get_speed(self) -> Tuple[float, float]:
        """
        Get the speed of the chassis.
        Returns:
            A tuple (vx, vth) representing the linear and angular speed.
        """
        speed_info = cast(
            SpeedResponse,
            self._abstract_http_get_or_post_and_parse(
                url="/reeman/speed",
                method="GET",
                payload=None,
                response_class=SpeedResponse,
            ),
        )
        return (speed_info.vx, speed_info.vth)

    def get_laser(self) -> List[List[float]]:
        """
        Get the laser scan data of the chassis.
        Returns:
            A list of tuples representing the coordinates of the laser points.
        """
        laser_info = cast(
            LaserResponse,
            self._abstract_http_get_or_post_and_parse(
                url="/reeman/laser",
                method="GET",
                payload=None,
                response_class=LaserResponse,
            ),
        )
        return laser_info.coordinates
    
    def _should_send_navigation_request(self, x: float, y: float, theta: float) -> bool:
        """
        Determine if a navigation request should be sent based on rate limiting and position change.
        
        Args:
            x (float): X coordinate of the new target
            y (float): Y coordinate of the new target
            theta (float): Orientation of the new target
            
        Returns:
            bool: True if the request should be sent, False otherwise
        """
        current_time = time.time()
        time_since_last_request = current_time - self._last_nav_request_time
        
        if time_since_last_request >= self._get_min_request_interval():
            return True
        
        if self._last_nav_position is None:
            return True
        
        last_x, last_y, last_theta = self._last_nav_position
        position_distance = sqrt((x - last_x) ** 2 + (y - last_y) ** 2)
        angle_difference = abs(self._normalize_angle(theta - last_theta))
        
        return (position_distance > self._get_position_change_threshold())
    
    def _normalize_angle(self, angle: float) -> float:
        """
        Normalize an angle to the range [-pi, pi].
        
        Args:
            angle (float): The angle to normalize in radians
            
        Returns:
            float: The normalized angle
        """
        while angle > pi:
            angle -= 2.0 * pi
        while angle < -pi:
            angle += 2.0 * pi
        return angle
    
    def _update_last_navigation_request(self, x: float, y: float, theta: float) -> None:
        """
        Update the timestamp and position of the last navigation request.
        
        Args:
            x (float): X coordinate of the target
            y (float): Y coordinate of the target
            theta (float): Orientation of the target
        """
        self._last_nav_request_time = time.time()
        self._last_nav_position = (x, y, theta)
    
    def _get_min_request_interval(self) -> float:
        """
        Get the minimum interval between navigation requests in seconds.
        
        Returns:
            float: Minimum interval in seconds
        """
        return 5.0

    def _get_position_change_threshold(self) -> float:
        """
        Get the threshold for position change to bypass rate limiting.
        
        Returns:
            float: Position change threshold in meters
        """
        return 1.0

    def _get_angle_change_threshold(self) -> float:
        """
        Get the threshold for angle change to bypass rate limiting.
        
        Returns:
            float: Angle change threshold in radians
        """
        return 0.3  # About 17 degrees
    
    def navigate_to_pose(self, x: float, y: float, theta: float) -> bool:
        """
        Navigate to a specific pose.
        
        Args:
            x (float): X coordinate in meters
            y (float): Y coordinate in meters
            theta (float): Orientation in radians
            
        Returns:
            bool: True if command was accepted
        """
        if not self._should_send_navigation_request(x, y, theta):
            logging.info("\n\n\n\nNavigation request skipped due to rate limiting or insignificant change\n\n\n")
            return True
        
        payload = {
            "x": x,
            "y": y,
            "theta": theta
        }
        _ = cast(
            EmptyResponse,
            self._abstract_http_get_or_post_and_parse(
                url="/cmd/nav",
                method="POST",
                payload=payload,
                response_class=EmptyResponse,
            ),
        )
        self._update_last_navigation_request(x, y, theta)
        return True
        
    def navigate_to_named_point(self, point_name: str) -> bool:
        """
        Navigate to a named point (waypoint).
        
        Args:
            point_name (str): Name of the waypoint
            
        Returns:
            bool: True if command was accepted
        """
        payload = {"point": point_name}
        _ = cast(
            EmptyResponse,
            self._abstract_http_get_or_post_and_parse(
                url="/cmd/nav_name",
                method="POST",
                payload=payload,
                response_class=EmptyResponse,
            ),
        )
        return True
        
    def navigate_along_path(self, path_name: str) -> bool:
        """
        Navigate along a predefined path.
        
        Args:
            path_name (str): Name of the path
            
        Returns:
            bool: True if command was accepted
        """
        payload = {"name": path_name}
        _ = cast(
            EmptyResponse,
            self._abstract_http_get_or_post_and_parse(
                url="/cmd/points_path",
                method="POST",
                payload=payload,
                response_class=EmptyResponse,
            ),
        )
        return True
        
    def get_navigation_status(self) -> Dict[str, Any]:
        """
        Get current navigation status.
        
        Returns:
            Dictionary containing navigation status with keys:
            - res: Navigation phase
            - reason: Result of the phase
            - goal: Goal name or coordinates
            - dist: Distance to goal
            - mileage: Distance traveled during this navigation
        """
        return cast(
            Dict[str, Any],
            self._abstract_http_get_or_post_and_parse(
                url="/reeman/nav_status",
                method="GET",
                payload=None,
                response_class=NavStatusResponse,  # Return raw JSON
            ),
        )
        
    def cancel_navigation(self) -> bool:
        """
        Cancel current navigation.
        
        Returns:
            bool: True if command was accepted
        """
        _ = cast(
            EmptyResponse,
            self._abstract_http_get_or_post_and_parse(
                url="/cmd/cancel_goal",
                method="POST",
                payload={},
                response_class=EmptyResponse,
            ),
        )
        return True
        
    def relocate(self, x: float, y: float, theta: float) -> bool:
        """
        Relocate the robot at a specific pose (algorithm-assisted).
        
        Args:
            x (float): X coordinate in meters
            y (float): Y coordinate in meters
            theta (float): Orientation in radians
            
        Returns:
            bool: True if command was accepted
        """
        payload = {
            "x": x,
            "y": y,
            "theta": theta
        }
        _ = cast(
            EmptyResponse,
            self._abstract_http_get_or_post_and_parse(
                url="/cmd/reloc_pose",
                method="POST",
                payload=payload,
                response_class=EmptyResponse,
            ),
        )
        return True
        
    def absolute_relocate(self, x: float, y: float, theta: float) -> bool:
        """
        Absolutely relocate the robot at a specific pose (no algorithm).
        
        Args:
            x (float): X coordinate in meters
            y (float): Y coordinate in meters
            theta (float): Orientation in radians
            
        Returns:
            bool: True if command was accepted
        """
        payload = {
            "x": x,
            "y": y,
            "theta": theta
        }
        _ = cast(
            EmptyResponse,
            self._abstract_http_get_or_post_and_parse(
                url="/cmd/reloc_absolute",
                method="POST",
                payload=payload,
                response_class=EmptyResponse,
            ),
        )
        return True
        
    def navigate_to_charge(self, point_name: str = "充电桩") -> bool:
        """
        Navigate to charging station.
        
        Args:
            point_name (str): Name of the charging station point (default: "充电桩")
            
        Returns:
            bool: True if command was accepted
        """
        payload = {
            "type": 2,  # 2 means navigate to charging point and start docking
            "point": point_name
        }
        _ = cast(
            EmptyResponse,
            self._abstract_http_get_or_post_and_parse(
                url="/cmd/charge",
                method="POST",
                payload=payload,
                response_class=EmptyResponse,
            ),
        )
        return True
