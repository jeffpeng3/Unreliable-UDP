from socket import socket, AF_INET, SOCK_DGRAM
from argparse import ArgumentParser, Namespace
from pickle import loads, dumps
from itertools import batched
from base import Header, Package, Status, ReSendRequest, Message
from random import random
from uuid import uuid4
from hashlib import sha1


def sendUDP(sock:socket, data:object, addr:tuple[str,int], drop_rate=0.05):
    if random() < drop_rate:
        print("Oops drop package")
        return
    sock.sendto(dumps(data), addr)


def Parse() -> Namespace:
    parser = ArgumentParser(description="Send via UDP")

    parser.add_argument("-H", "--host", dest="host", required=True)
    parser.add_argument("-P", "--port", dest="port", required=True, type=int)
    parser.add_argument("-F", "--file", dest="file", required=True)
    parser.add_argument("-b", dest="batch_size", type=int, default=1024)
    parser.add_argument("-d", dest="drop_rate", type=float, default=0.05)

    args = parser.parse_args()
    print(args.host, args.port, args.file, args.batch_size, args.drop_rate)
    return args


def loadFile(file: str) -> bytes:
    with open(file, "rb") as f:
        return f.read()

def PreparePackages(data: bytes, batch_size: int, uuid: int) -> list[Package]:
    packages: list[Package] = []
    for idx, ptr in enumerate(range(0, len(data), batch_size)):
        data = data[ptr : ptr + batch_size]
        sha1sum = sha1(data).digest()
        packages.append(Package(uuid, idx, data, sha1sum))
    return packages

if __name__ == "__main__":
    args = Parse()
    data = loadFile(args.file)

    fileSize = len(data)
    uuid = uuid4().int
    header = Header(args.file, fileSize, fileSize // args.batch_size + 1, uuid)

    packages:list[Package] = PreparePackages(data, args.batch_size, uuid)

    print(f"Sending {len(packages)} packages")
    print(f"Sending {header} packages")

    sock = socket(AF_INET, SOCK_DGRAM)
    sock.sendto(dumps(header), (args.host, args.port))
    data, addr = sock.recvfrom()
    requestStatus = loads(data)
    if requestStatus.status != Status.READY:
        print("Request rejected")
        exit(1)
    for package in packages:
        if random() < args.drop_rate:
            print(f"Oops drop package {package.serialNo}")
            continue
        sock.sendto(dumps(package), (args.host, args.port))

    while True:
        data, addr = sock.recvfrom()
        message = loads(data)
        if isinstance(message, ReSendRequest):
            print(f"Resending package {message.serialNo}")
            sock.sendto(dumps(packages[message.serialNo]), (args.host, args.port))
        if message.status == Status.SUCESS:
            print("Success")
            break
