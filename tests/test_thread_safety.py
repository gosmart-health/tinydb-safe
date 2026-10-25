import threading

import pytest

from tinydb import TinyDB, where
from tinydb.middlewares import CachingMiddleware
from tinydb.operations import increment
from tinydb.storages import JSONStorage, MemoryStorage
from tinydb.table import Document


def _run_threaded(num_threads, worker_fn):
    """
    Run ``worker_fn(thread_idx, barrier)`` across ``num_threads`` threads and
    re-raise any exception that occurred in any worker thread.
    """
    barrier = threading.Barrier(num_threads)
    errors = []
    errors_lock = threading.Lock()

    def wrapper(idx):
        try:
            worker_fn(idx, barrier)
        except BaseException as exc:  # pragma: no cover
            with errors_lock:
                errors.append(exc)

    threads = [
        threading.Thread(target=wrapper, args=(i,))
        for i in range(num_threads)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    if errors:
        raise errors[0]


# ---------------------------------------------------------------------------
# 1. Read-Modify-Write (RMW) Lost Updates (_update_table & drop_table)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('storage_mode', ['memory', 'json'])
def test_concurrent_rmw_updates(tmpdir, storage_mode):
    """
    Verify concurrent Read-Modify-Write updates on the same document and
    table do not lose updates.
    """
    if storage_mode == 'memory':
        db = TinyDB(storage=MemoryStorage)
    else:
        db = TinyDB(str(tmpdir.join('rmw.json')), storage=JSONStorage)

    doc_id = db.insert({'count': 0})
    num_threads = 10
    increments_per_thread = 15

    def worker(idx, barrier):
        barrier.wait()
        for _ in range(increments_per_thread):
            db.update(increment('count'), doc_ids=[doc_id])

    _run_threaded(num_threads, worker)

    result = db.get(doc_id=doc_id)
    assert result is not None
    assert result['count'] == num_threads * increments_per_thread
    db.close()


@pytest.mark.parametrize('storage_mode', ['memory', 'json'])
def test_concurrent_table_writes_and_drop_table(tmpdir, storage_mode):
    """
    Verify concurrent writes to one table do not get clobbered when another
    thread creates and drops a different table.
    """
    if storage_mode == 'memory':
        db = TinyDB(storage=MemoryStorage)
    else:
        db = TinyDB(str(tmpdir.join('drop.json')), storage=JSONStorage)

    table_a = db.table('table_a')
    num_writers = 6
    inserts_per_writer = 20

    def worker(idx, barrier):
        barrier.wait()
        if idx == 0:
            for i in range(inserts_per_writer):
                temp = db.table(f'temp_{i % 3}')
                temp.insert({'temp': i})
                db.drop_table(f'temp_{i % 3}')
        else:
            for i in range(inserts_per_writer):
                table_a.insert({'writer': idx, 'seq': i})

    _run_threaded(num_writers, worker)

    assert len(table_a) == (num_writers - 1) * inserts_per_writer
    db.close()


# ---------------------------------------------------------------------------
# 2. ID Generation Race (_get_next_id & insert / insert_multiple)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('storage_mode', ['memory', 'json'])
def test_concurrent_insert_unique_ids(tmpdir, storage_mode):
    """
    Verify concurrent insert() and insert_multiple() calls allocate unique
    document IDs without raising duplicate ID errors or losing documents.
    """
    if storage_mode == 'memory':
        db = TinyDB(storage=MemoryStorage)
    else:
        db = TinyDB(str(tmpdir.join('ids.json')), storage=JSONStorage)

    num_threads = 8
    inserts_per_thread = 15
    allocated_ids = []
    ids_lock = threading.Lock()

    def worker(idx, barrier):
        local_ids = []
        barrier.wait()
        for i in range(inserts_per_thread):
            doc_id = db.insert({'thread': idx, 'i': i})
            local_ids.append(doc_id)

        batch_ids = db.insert_multiple([
            {'thread': idx, 'batch': 0},
            Document({'thread': idx, 'explicit': True}, doc_id=10000 + idx),
            {'thread': idx, 'batch': 1},
        ])
        local_ids.extend(batch_ids)

        with ids_lock:
            allocated_ids.extend(local_ids)

    _run_threaded(num_threads, worker)

    expected_total = num_threads * (inserts_per_thread + 3)
    assert len(allocated_ids) == expected_total
    assert len(set(allocated_ids)) == expected_total
    assert len(db) == expected_total
    db.close()


# ---------------------------------------------------------------------------
# 3. Shared File Handle Cursor Race (JSONStorage concurrent reads & writes)
# ---------------------------------------------------------------------------

def test_json_storage_concurrent_reads_and_writes(tmpdir):
    """
    Verify concurrent reads and writes on JSONStorage do not corrupt the
    shared file handle seek position or raise JSONDecodeError.
    """
    path = str(tmpdir.join('cursor_race.json'))
    db = TinyDB(path, storage=JSONStorage)
    db.insert({'seed': 'x' * 500})

    num_threads = 8
    iterations = 25

    def worker(idx, barrier):
        barrier.wait()
        if idx % 2 == 0:
            # Reader thread
            for _ in range(iterations):
                docs = db.all()
                assert isinstance(docs, list)
                raw = db.storage.read()
                assert raw is None or isinstance(raw, dict)
        else:
            # Writer thread alternating between large and small payloads
            # to exercise file seek, write, flush, fsync, and truncate
            for i in range(iterations):
                doc_id = db.insert({'writer': idx, 'payload': 'y' * (i * 20)})
                if i % 3 == 0:
                    db.remove(doc_ids=[doc_id])

    _run_threaded(num_threads, worker)
    db.close()


# ---------------------------------------------------------------------------
# 4. Query Cache Mutation & Stale Cache Race (Table.search & LRUCache)
# ---------------------------------------------------------------------------

def test_concurrent_search_lru_cache_contention(tmpdir):
    """
    Verify concurrent Table.search() calls (which mutate LRUCache's
    OrderedDict on cache hits/evictions) and concurrent writes (which clear
    the cache) do not raise RuntimeError/KeyError or leave stale cache entries.
    """
    db = TinyDB(storage=MemoryStorage)
    table = db.table('cached', cache_size=5)

    for i in range(20):
        table.insert({'key': i, 'status': 'initial'})

    num_threads = 10
    iterations = 40

    def worker(idx, barrier):
        barrier.wait()
        if idx < 7:
            # Reader threads hitting and evicting the small LRU cache
            for i in range(iterations):
                key = (idx + i) % 20
                res = table.search(where('key') == key)
                assert len(res) == 1
                assert res[0]['key'] == key
        else:
            # Writer threads updating documents and invalidating query cache
            for i in range(iterations):
                key = (idx + i) % 20
                table.update({'status': f'updated_{i}'}, where('key') == key)

    _run_threaded(num_threads, worker)

    # Final update to a known state and verify cached search is never stale
    for i in range(20):
        table.update({'status': 'final'}, where('key') == i)
        res = table.search(where('key') == i)
        assert len(res) == 1
        assert res[0]['status'] == 'final'

    db.close()


# ---------------------------------------------------------------------------
# 5. Non-Atomic Compound Operations (Table.upsert) & Table Registry (table())
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('storage_mode', ['memory', 'json'])
def test_concurrent_upsert(tmpdir, storage_mode):
    """
    Verify concurrent upsert() calls for the same query are atomic and do not
    insert duplicate documents when the target document does not yet exist.
    """
    if storage_mode == 'memory':
        db = TinyDB(storage=MemoryStorage)
    else:
        db = TinyDB(str(tmpdir.join('upsert.json')), storage=JSONStorage)

    num_threads = 10

    def worker(idx, barrier):
        barrier.wait()
        for step in range(5):
            db.upsert(
                {'singleton': True, 'last_writer': idx, 'step': step},
                where('singleton') == True  # noqa: E712
            )

    _run_threaded(num_threads, worker)

    matches = db.search(where('singleton') == True)  # noqa: E712
    assert len(matches) == 1
    assert len(db) == 1
    db.close()


def test_concurrent_table_creation():
    """
    Verify concurrent db.table(name) calls return the exact same Table
    instance.
    """
    db = TinyDB(storage=MemoryStorage)
    num_threads = 12
    tables = [None] * num_threads

    def worker(idx, barrier):
        barrier.wait()
        tables[idx] = db.table('shared_table')

    _run_threaded(num_threads, worker)

    first = tables[0]
    assert first is not None
    assert all(t is first for t in tables)
    db.close()


# ---------------------------------------------------------------------------
# 6. In-Memory Shared Reference Mutation (MemoryStorage & CachingMiddleware)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('use_caching_middleware', [False, True])
def test_memory_and_caching_middleware_concurrent_iter_and_write(
    tmpdir, use_caching_middleware
):
    """
    Verify concurrent iteration (iter(db), db.all(), db.search()) and writes
    on MemoryStorage and CachingMiddleware(JSONStorage) do not raise
    'RuntimeError: dictionary changed size during iteration' or lose data.
    """
    path = str(tmpdir.join('cached_mw.json'))
    if use_caching_middleware:
        middleware = CachingMiddleware(JSONStorage)
        middleware.WRITE_CACHE_SIZE = 7
        db = TinyDB(path, storage=middleware)
    else:
        db = TinyDB(storage=MemoryStorage)

    for i in range(10):
        db.insert({'idx': i, 'kind': 'seed'})

    num_threads = 8
    iterations = 30

    def worker(idx, barrier):
        barrier.wait()
        if idx % 2 == 0:
            # Iterator / reader thread
            for _ in range(iterations):
                snapshot = [doc for doc in db]
                assert len(snapshot) >= 10
                _ = db.search(where('kind') == 'seed')
        else:
            # Writer thread inserting, updating, and removing its own docs
            for i in range(iterations):
                doc_id = db.insert({'writer': idx, 'iter': i, 'kind': 'temp'})
                db.update({'iter': i + 100}, doc_ids=[doc_id])
                db.remove(doc_ids=[doc_id])

    _run_threaded(num_threads, worker)

    assert len(db.search(where('kind') == 'seed')) == 10
    assert len(db.search(where('kind') == 'temp')) == 0
    db.close()

    if use_caching_middleware:
        with TinyDB(path, storage=JSONStorage) as reopened:
            assert len(reopened.search(where('kind') == 'seed')) == 10
            assert len(reopened.search(where('kind') == 'temp')) == 0

