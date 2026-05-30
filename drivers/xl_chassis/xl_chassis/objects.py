from dataclasses import dataclass
from typing import Type, Union, Tuple, List


@dataclass
class CurrentVersionResponse:
    version: str


@dataclass
class PoseResponse:
    x: float
    y: float
    theta: float


@dataclass
class SpeedResponse:
    vx: float
    vth: float


@dataclass
class LaserResponse:
    coordinates: List[List[float]]


@dataclass
class NavStatusResponse:
    res: int
    reason: int
    goal: str
    dist: float
    mileage: float


@dataclass
class EmptyResponse:
    pass


ChassisHttpResponseType = Union[
    Type[CurrentVersionResponse],
    Type[PoseResponse],
    Type[SpeedResponse],
    Type[LaserResponse],
    Type[EmptyResponse],
    Type[NavStatusResponse],
]

ChassisHttpResponse = Union[
    CurrentVersionResponse,
    PoseResponse,
    SpeedResponse,
    LaserResponse,
    EmptyResponse,
    NavStatusResponse,
]
