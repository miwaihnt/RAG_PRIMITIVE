import itertools
from typing import Generator, Iterable, List


def batch_iterator(iterable: Iterable, batch_size: int) -> Generator[List, None, None]:
    """
    イテレータから指定されたバッチサイズごとにデータを束ねて yield する。
    itertools.islice を使うことで、余計なメモリコピーを最小限に抑える。
    """
    it = iter(iterable)
    while True:
        batch = list(itertools.islice(it, batch_size))
        if not batch:
            break
        yield batch
