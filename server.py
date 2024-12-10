from socket import socket, AF_INET, SOCK_DGRAM
from argparse import ArgumentParser, Namespace
from pickle import loads, dumps
from base import Header, Package, Status, ReSendRequest, Message
from hashlib import sha1
from dataclasses import dataclass, field


def info(*args, **kwargs):
    print("[server]", *args, **kwargs)


def dummy_print(*args, **kwargs):
    pass


DEBUG = False
SAVE_FILE = True

if not DEBUG:
    info = print
    print = dummy_print


@dataclass
class ReceiveStatus:
    address: tuple[str, int]
    total: int
    packages: list[Package | None]
    fileName: str
    fileSize: int
    uuid: int
    received: int = field(default=0)
    retry: int = field(default=0)

    def addPackage(self, package: Package) -> bool:
        if not verifyPackages(package):
            print(f"Package {package.serialNo} is corrupted")
            return False

        self.received += 1
        self.packages[package.serialNo] = package
        return True

    def isComplete(self) -> bool:
        return self.received == self.total

    def saveFile(self):
        if SAVE_FILE:
            info(f"Saving file {self.fileName}")
            storeFile(
                f"{str(self.uuid)[:6]}-{self.fileName}",
                b"".join([p.data for p in self.packages if p is not None]),
            )


def sendUDP(sock: socket, data: object, addr: tuple[str, int]):
    sock.sendto(dumps(data), addr)


def Parse() -> Namespace:
    parser = ArgumentParser(description="Send via UDP")
    parser.add_argument("port", type=int)

    args = parser.parse_args()
    print(args.port)
    return args


def storeFile(name: str, content: bytes):
    with open(f"save/{name}", "wb") as f:
        f.write(content)
    pass


def verifyPackages(package: Package) -> bool:
    if sha1(package.data).digest() != package.checksum:
        return False
    return True


def sendReSendRequest(sock: socket, uuid: int, serialNo: int, addr: tuple[str, int]):
    sendUDP(sock, ReSendRequest(uuid, serialNo), addr)


def checkBuffer(buffer: dict[int, ReceiveStatus], sock: socket):
    for i in [*filter(lambda x: x.retry >= 5, buffer.values())]:
        print(f"Failed to receive all packages for {i.uuid}")
        sendUDP(sock, Message(i.uuid, Status.FAIL), i.address)
        buffer.pop(i.uuid)
    for uuid, recv in buffer.items():
        recv.retry += 1
        print(f"Resending request for {recv.uuid} : {recv.retry}")
        for idx, value in enumerate(recv.packages):
            if value is None:
                sendReSendRequest(sock, uuid, idx, recv.address)


def start_server(port: int):
    sock = socket(AF_INET, SOCK_DGRAM)
    sock.bind(("localhost", port))

    buffer: dict[int, ReceiveStatus] = {}

    info(f"Server started at port {port}")

    file_count = 0

    while True:
        try:
            data, addr = sock.recvfrom(1073741824)
        except TimeoutError:
            print("Timeout")
            if buffer:
                checkBuffer(buffer, sock)
            continue
        object = loads(data)
        if isinstance(header := object, Header):
            if header.uuid not in buffer:
                sock.settimeout(0.1)
                buffer[header.uuid] = ReceiveStatus(
                    addr,
                    header.slices,
                    [None for _ in range(header.slices)],
                    header.fileName,
                    header.fileSize,
                    header.uuid,
                )
                sendUDP(sock, Message(header.uuid, Status.READY), addr)
                print(f"Receiving {header}")

        elif isinstance(package := object, Package):
            if package.uuid not in buffer:
                print(f"Received unknown package {package.uuid}")
                continue
            recv = buffer[package.uuid]
            if not recv.addPackage(package):
                sendReSendRequest(sock, package.uuid, package.serialNo, addr)
                continue

            print(f"Received {recv.received}/{recv.total}")
            recv.retry = 0
            if recv.isComplete():
                sendUDP(sock, Message(package.uuid, Status.SUCESS), addr)
                print(f"Received all packages for {recv.fileName}")
                recv.saveFile()
                file_count += 1
                print(f"{package.uuid} File saved")
                buffer.pop(package.uuid)
                print(f"Buffer size {len(buffer)}")
                if len(buffer) == 0:
                    info("All files received")
                    info(f"Total files received: {file_count}")
                    sock.settimeout(None)
        else:
            info(f"Unknown object {object}")
            sendUDP(sock, Message(-1, Status.FAIL), addr)


if __name__ == "__main__":
    args = Parse()
    start_server(args.port)
