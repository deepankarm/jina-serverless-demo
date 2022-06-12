import sys

from helper import change_to_kn_service, copy_to_temp


def main(dirpath, concurrency: int = 2, min_replicas: int = 0, max_replicas: int = 10):
    new_path = copy_to_temp(dirpath)
    change_to_kn_service(
        new_path,
        concurrency=concurrency,
        min_replicas=min_replicas,
        max_replicas=max_replicas,
    )
    print(new_path)


if __name__ == '__main__':
    main(*sys.argv[1:])
