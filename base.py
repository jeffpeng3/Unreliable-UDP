from dataclasses import dataclass
from enum import Enum


@dataclass
class Header:
    fileName: str
    fileSize: int
    slices: int
    uid: int


@dataclass
class Package:
    uid: int
    serialNo: int
    data: bytes
    checksum: bytes


@dataclass
class ReSendRequest:
    uid: int
    serialNo: int


class Status(Enum):
    READY = 0
    SUCESS = 1
    FAIL = 2
    CANCELED = 3


@dataclass
class Message:
    uid: int
    status: Status
