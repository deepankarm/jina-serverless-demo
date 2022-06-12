import sys
import timeit
from concurrent.futures import ProcessPoolExecutor

from jina import Client, DocumentArray


def client_request(idx, host):
    print(f'Client {idx}, sending request!')
    da = Client(host=host).post('/', inputs=DocumentArray.empty(2))
    print(f'Client {idx}, received response {da}')


def load_client(gateway: str = 'grpc://gateway.jina-sls.127.0.0.1.sslip.io', N=10):
    with ProcessPoolExecutor() as executor:
        [executor.submit(client_request, i, gateway) for i in range(N)]


if __name__ == '__main__':
    load_client(N=int(sys.argv[1]) if len(sys.argv) == 2 else 10)
