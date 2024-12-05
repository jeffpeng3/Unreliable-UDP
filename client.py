from socket import socket, AF_INET, SOCK_DGRAM, setdefaulttimeout
from argparse import ArgumentParser, Namespace
from pickle import loads, dumps
from base import Header, Package, Status, ReSendRequest, Message
from random import random, sample
from uuid import uuid4
from hashlib import sha1
from concurrent.futures import ProcessPoolExecutor, as_completed
from time import time
from tqdm import tqdm

def sendUDP(sock:socket, data:object, addr:tuple[str,int], drop_rate=0.05):
    if random() < drop_rate:
        # print("Oops drop package")
        return
    sock.sendto(dumps(data), addr)


def Parse() -> Namespace:
    parser = ArgumentParser(description="Send via UDP")

    parser.add_argument("-H", "--host", dest="host", default="localhost")
    parser.add_argument("-P", "--port", dest="port", default=7777, type=int)
    parser.add_argument("-b", dest="batch_size", type=int, default=1024)
    parser.add_argument("-d", dest="drop_rate", type=float, default=0.05)
    parser.add_argument("file")

    args = parser.parse_args()
    # print(args.host, args.port, args.file, args.batch_size, args.drop_rate)
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

def main():
    setdefaulttimeout(10)
    args = Parse()
    data = loadFile(args.file)

    fileSize = len(data)
    uuid = uuid4().int
    header = Header(args.file, fileSize, fileSize // args.batch_size + 1, uuid)

    packages:list[Package] = PreparePackages(data, args.batch_size, uuid)

    # print(f"Sending {header} packages")

    sock = socket(AF_INET, SOCK_DGRAM)
    sendUDP(sock, header, (args.host, args.port), 0)

    data, addr = sock.recvfrom(1024)
    requestStatus = loads(data)
    if isinstance(requestStatus, Message) and requestStatus.status != Status.READY:
        # print("Request rejected")
        exit(1)

    # print(f"Sending {len(packages)} packages")
    for package in sample(packages,len(packages)):
        if random() < args.drop_rate:
            # print(f"Oops drop package {package.serialNo}")
            continue
        # print(f"Sending package {package.serialNo}")
        sendUDP(sock, package, (args.host, args.port), args.drop_rate)
        # sleep(0.01)

    while True:
        data, addr = sock.recvfrom(1024)
        message = loads(data)
        if isinstance(message, ReSendRequest):
            # print(f"Resending package {message.serialNo}")
            sock.sendto(dumps(packages[message.serialNo]), (args.host, args.port))
        elif isinstance(message, Message):
            if message.status == Status.SUCESS:
                # print("Success")
                break
            elif message.status == Status.FAIL:
                # print("Fail")
                break


def stress(total_runs: int, num_threads: int):

    with ProcessPoolExecutor(max_workers=num_threads) as executor:
        futures = {executor.submit(main): i for i in range(total_runs)}
        with tqdm(total=total_runs, desc="Stress Test Progress", unit="task") as pbar:

            for future in as_completed(futures):
                pbar.update(1)
                try:
                    result = future.result()
                    # print(f"Thread {result}: Completed.")
                except Exception as e:
                    # print(f"Thread {futures[future]}: Failed with exception {e}.")
                    print(e)
                    return

    print("Stress test completed.")


if __name__ == "__main__":
    start_time = time()
    stress(1000,12)
    print(f"Total time taken: {time() - start_time:.2f} seconds")
