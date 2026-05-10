import mysql.connector
from mysql.connector import Error
import ctypes
import os
import time
from datetime import timedelta

BATCH_SIZE = 5000   # rows per read chunk and per write commit

dir_path = os.path.dirname(os.path.realpath(__file__))

chart_gen = ctypes.WinDLL(f'{dir_path}/Ft8ChartGen.dll')
chart_gen.SquareToItuZone.argtypes = [ctypes.c_wchar_p]
chart_gen.SquareToItuZone.restype = ctypes.c_int


# ---------------------------------------------------------------------------
# Progress / statistics
# ---------------------------------------------------------------------------

class Stats:
    def __init__(self, total: int):
        self.total = total
        self.processed = 0
        self.success = 0
        self.failed = 0
        self.fallback_used = 0
        self._start = time.monotonic()
        self._last_print = 0.0

    def record(self, zone: int, used_fallback: bool = False):
        self.processed += 1
        if zone > 0:
            self.success += 1
            if used_fallback:
                self.fallback_used += 1
        else:
            self.failed += 1

    @property
    def elapsed(self) -> float:
        return time.monotonic() - self._start

    @property
    def rate(self) -> float:
        return self.processed / self.elapsed if self.elapsed > 0 else 0.0

    @property
    def eta_sec(self) -> float:
        remaining = self.total - self.processed
        return remaining / self.rate if self.rate > 0 else 0.0

    def print_progress(self, force: bool = False):
        now = time.monotonic()
        if not force and (now - self._last_print) < 0.5:
            return
        self._last_print = now

        if self.total == 0:
            return
        pct = self.processed / self.total
        bar_w = 35
        filled = int(bar_w * pct)
        bar = '█' * filled + '░' * (bar_w - filled)
        eta = str(timedelta(seconds=int(self.eta_sec)))
        print(
            f"\r[{bar}] {pct*100:5.1f}%  "
            f"{self.processed:,}/{self.total:,}  "
            f"{self.rate:,.0f} rec/s  "
            f"ETA {eta}  "
            f"OK:{self.success:,} Fail:{self.failed:,}",
            end='', flush=True
        )

    def print_summary(self):
        elapsed = str(timedelta(seconds=int(self.elapsed)))
        pct_ok   = self.success  / self.total * 100 if self.total else 0
        pct_fail = self.failed   / self.total * 100 if self.total else 0
        print(f"\n\n{'='*60}")
        print(f"  Completed in       {elapsed}")
        print(f"  Total processed:   {self.total:,}")
        print(f"  Success:           {self.success:,}  ({pct_ok:.1f}%)")
        if self.fallback_used:
            print(f"    incl. 4-char fallback: {self.fallback_used:,}")
        print(f"  Failed (→ -1):     {self.failed:,}  ({pct_fail:.1f}%)")
        print(f"  Avg throughput:    {self.rate:,.0f} records/sec")
        print(f"{'='*60}")


# ---------------------------------------------------------------------------
# Zone resolution
# ---------------------------------------------------------------------------

def resolve_zone(grid: str) -> tuple[int, bool]:
    """
    Resolve a Maidenhead grid square to an ITU zone number.

    Tries the full grid first, then falls back to the 4-character prefix
    (some older locators stored in the DB are already 4-char, others may
    have a corrupt 5th/6th character).

    Returns:
        (zone, used_fallback)
        zone > 0  — valid ITU zone
        zone == -1 — could not resolve; mark as invalid in DB
    """
    zone = chart_gen.SquareToItuZone(grid)
    if zone > 0:
        return zone, False

    if len(grid) > 4:
        zone = chart_gen.SquareToItuZone(grid[:4])
        if zone > 0:
            return zone, True

    return -1, False


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def get_pending_count(connection) -> int:
    cursor = connection.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM main.ft8_stationinfo WHERE ituZone = 0 AND grid != ''"
    )
    count = cursor.fetchone()[0]
    cursor.close()
    return count


def ensure_temp_table(write_cursor):
    write_cursor.execute("""
        CREATE TEMPORARY TABLE IF NOT EXISTS _zone_updates (
            id      INT PRIMARY KEY,
            ituZone INT NOT NULL
        )
    """)


def flush_batch(write_cursor, write_conn, updates: list, failures: list):
    """
    Persist one batch of resolved zones to the database and commit.

    updates  — list of (id, zone) for successfully resolved stations
    failures — list of station ids that could not be resolved (zone → -1)
    """
    if not updates and not failures:
        return

    if updates:
        write_cursor.execute("DELETE FROM _zone_updates")
        write_cursor.executemany(
            "INSERT INTO _zone_updates (id, ituZone) VALUES (%s, %s)",
            updates
        )
        write_cursor.execute("""
            UPDATE main.ft8_stationinfo AS s
            JOIN _zone_updates AS u ON s.id = u.id
            SET s.ituZone = u.ituZone
        """)

    if failures:
        # Mark as -1 so they are skipped on future runs
        write_cursor.executemany(
            "UPDATE main.ft8_stationinfo SET ituZone = -1 WHERE id = %s",
            [(fid,) for fid in failures]
        )

    write_conn.commit()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    read_conn  = None
    write_conn = None
    try:
        db_cfg = dict(host='localhost', database='main', user='root', password='1q2w3e$R')

        read_conn  = mysql.connector.connect(**db_cfg)
        write_conn = mysql.connector.connect(**db_cfg)
        print(f"Connected to MySQL {read_conn.get_server_info()}")

        total = get_pending_count(read_conn)
        if total == 0:
            print("Nothing to do — all stations already have ITU zones assigned.")
            return

        print(f"Pending stations: {total:,}  (batch size: {BATCH_SIZE:,})\n")
        stats = Stats(total)

        # Unbuffered cursor streams rows from server without loading all into RAM
        read_cursor = read_conn.cursor(buffered=False)
        read_cursor.execute(
            "SELECT id, callsign, grid FROM main.ft8_stationinfo WHERE ituZone = 0 AND grid != ''"
        )

        write_cursor = write_conn.cursor()
        ensure_temp_table(write_cursor)

        updates:  list[tuple[int, int]] = []
        failures: list[int]             = []

        while True:
            rows = read_cursor.fetchmany(BATCH_SIZE)
            if not rows:
                break

            for station_id, callsign, grid in rows:
                zone, used_fallback = resolve_zone(grid)
                stats.record(zone, used_fallback)

                if zone > 0:
                    updates.append((station_id, zone))
                else:
                    failures.append(station_id)

            flush_batch(write_cursor, write_conn, updates, failures)
            updates.clear()
            failures.clear()
            stats.print_progress(force=True)

        stats.print_summary()

    except Error as e:
        print(f"\nMySQL error: {e}")
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Progress up to last commit is saved.")
    finally:
        for conn in (read_conn, write_conn):
            if conn and conn.is_connected():
                conn.close()
        print("Connections closed.")


if __name__ == '__main__':
    main()
