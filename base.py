from dataclasses import dataclass
from enum import Enum


@dataclass
class Header:
    fileName: str
    fileSize: int
    slices: int
    uuid: int


@dataclass
class Package:
    uuid: int
    serialNo: int
    data: bytes
    checksum: bytes

    def __bool__(self):
        return True


@dataclass
class ReSendRequest:
    uuid: int
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
