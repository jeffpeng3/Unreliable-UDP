from client import send_data, loadFile
from server import start_server
from argparse import ArgumentParser, Namespace
from threading import Thread
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import time, sleep
from tqdm import tqdm
from os import cpu_count


def Parse() -> Namespace:
    parser = ArgumentParser(description="Send via UDP")
    parser.add_argument("count", type=int, default=100)
    parser.add_argument("file", type=str)
    return parser.parse_args()


def stress(total_runs: int, file: str, num_threads: int):
    data = loadFile(file)
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = {
            executor.submit(send_data, file, data, "localhost", 6516, 10240): i
            for i in range(total_runs)
        }
        for future in tqdm(
            as_completed(futures),
            total=len(futures),
            desc="Stress Test Progress",
            unit="task",
        ):
            pass
            try:
                future.result()
            except Exception as e:
                print(e)
            # print("Thread Completed.")


if __name__ == "__main__":
    args = Parse()
    Thread(target=start_server, args=(6516,), daemon=True).start()
    sleep(0.5)
    start = time()
    stress(args.count, args.file, min(10, cpu_count() // 2))
    print(f"Total time taken: {time() - start:.2f} seconds")
    sleep(1)
