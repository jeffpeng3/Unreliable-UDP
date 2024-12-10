from socket import socket, AF_INET, SOCK_DGRAM
from argparse import ArgumentParser, Namespace
from pickle import loads, dumps
from base import Header, Package, Status, ReSendRequest, Message
from random import random, sample
from uuid import uuid4
from hashlib import sha1


def dummy_print(*args, **kwargs):
    pass


def info(*args, **kwargs):
    print("[Sender]", *args, **kwargs)


DEBUG = False

if not DEBUG:
    info = print
    print = dummy_print


def sendUDP(sock: socket, data: object, addr: tuple[str, int], drop_rate=0.005):
    if random() < drop_rate:
        print("Oops drop package")
        return
    sock.sendto(dumps(data), addr)


def parse() -> Namespace:
    parser = ArgumentParser(description="Send via UDP")

    parser.add_argument("-H", "--host", dest="host", default="localhost")
    parser.add_argument("-P", "--port", dest="port", default=7777, type=int)
    parser.add_argument("-b", dest="batch_size", type=int, default=1024)
    parser.add_argument("-d", dest="drop_rate", type=float, default=0.05)
    parser.add_argument("file")

    args = parser.parse_args()
    return args


def loadFile(file: str) -> bytes:
    with open(file, "rb") as f:
        return f.read()


def PreparePackages(data: bytes, batch_size: int, uuid: int) -> list[Package]:
    packages: list[Package] = []
    for idx, ptr in enumerate(range(0, len(data), batch_size)):
        temp = data[ptr : ptr + batch_size]
        sha1sum = sha1(temp).digest()
        packages.append(Package(uuid, idx, temp, sha1sum))
    return packages


def send_data(
    fileName: str,
    data: bytes,
    host: str,
    port: int,
    batch_size: int,
    drop_rate: float = 0.0,
):
    fileSize = len(data)
    uuid = uuid4().int
    header = Header(fileName, fileSize, fileSize // batch_size + 1, uuid)

    packages: list[Package] = PreparePackages(data, batch_size, uuid)

    sock = socket(AF_INET, SOCK_DGRAM)
    sock.settimeout(1)

    for retryCount in range(5):
        try:
            print(f"Sending {header} packages")

            sendUDP(sock, header, (host, port))

            data, addr = sock.recvfrom(1024)
            requestStatus = loads(data)
            if (
                isinstance(requestStatus, Message)
                and requestStatus.status != Status.READY
            ):
                print("Request rejected")
                raise Exception("Request rejected")

            print(f"Sending {len(packages)} packages")
            for package in sample(packages, len(packages)):
                if random() < drop_rate:
                    print(f"Oops drop package {package.serialNo}")
                    continue
                print(f"Sending package {package.serialNo}")
                sendUDP(sock, package, (host, port), drop_rate)

            while True:
                data, addr = sock.recvfrom(1024)
                message = loads(data)
                if isinstance(message, ReSendRequest):
                    print(f"Resending package {message.serialNo}")
                    sock.sendto(dumps(packages[message.serialNo]), (host, port))
                elif isinstance(message, Message):
                    if message.status == Status.SUCESS:
                        info("Success")
                        return
                    elif message.status == Status.FAIL:
                        print("Fail")
                        break
                else:
                    raise Exception("Unknown error")
        except Exception as e:
            if retryCount == 2:
                print(f"Failed to send data: {e}")
                exit(1)
            print(f"failed to send data: {e}, retrying...")


if __name__ == "__main__":
    args = parse()
    data = loadFile(args.file)
    send_data(args.file, data, args.host, args.port, args.batch_size, args.drop_rate)
