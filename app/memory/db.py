"""SQLite schema + loaders. Raw measurements, predictions, retrieved documents and
generated text live in separate tables so every claim on a card is traceable."""
from __future__ import annotations

import sqlite3

import pandas as pd

from app.common.channels import channel_kind, channel_name
from app.common.paths import DATA_PROCESSED, DATA_RAW, DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS segments(
  segment_id INTEGER PRIMARY KEY, channel TEXT, channel_name TEXT, channel_kind TEXT,
  split TEXT, sampling INTEGER, n_points INTEGER, start TEXT, end TEXT, label INTEGER);
CREATE TABLE IF NOT EXISTS telemetry_points(
  segment_id INTEGER, idx INTEGER, timestamp TEXT, value REAL, channel TEXT,
  PRIMARY KEY(segment_id, idx));
CREATE INDEX IF NOT EXISTS tp_channel_ts ON telemetry_points(channel, timestamp);
CREATE TABLE IF NOT EXISTS features(segment_id INTEGER PRIMARY KEY, json TEXT);
CREATE TABLE IF NOT EXISTS documents(
  doc_id TEXT PRIMARY KEY, title TEXT, url TEXT, license TEXT, category TEXT,
  stored_mode TEXT, publication_date TEXT, retrieved_at TEXT, sha256 TEXT, n_chunks INTEGER);
CREATE TABLE IF NOT EXISTS chunks(
  chunk_id TEXT PRIMARY KEY, doc_id TEXT, location TEXT, text TEXT, ord INTEGER);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(chunk_id UNINDEXED, text, tokenize='porter');
CREATE TABLE IF NOT EXISTS chunk_vectors(chunk_id TEXT PRIMARY KEY, dim INTEGER, vec BLOB);
CREATE TABLE IF NOT EXISTS records(record_id TEXT PRIMARY KEY, chunk_id TEXT, model TEXT, json TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS predictions(
  segment_id INTEGER PRIMARY KEY, probability REAL, decision TEXT, model TEXT, source TEXT);
CREATE TABLE IF NOT EXISTS investigations(
  card_id TEXT PRIMARY KEY, segment_id INTEGER, created_at TEXT,
  evidence_json TEXT, prediction_json TEXT, documents_json TEXT, similar_json TEXT,
  known_json TEXT, unknown_json TEXT, summary TEXT, summary_model TEXT,
  suggested_action TEXT, review_status TEXT DEFAULT 'unreviewed', revealed INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS feedback(
  id INTEGER PRIMARY KEY AUTOINCREMENT, card_id TEXT, action TEXT, note TEXT, at TEXT);
CREATE TABLE IF NOT EXISTS eval_runs(
  id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, config_hash TEXT, config TEXT, git_sha TEXT, at TEXT);
"""


def connect(path=DB_PATH) -> sqlite3.Connection:
    con = sqlite3.connect(path, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def init_db(path=DB_PATH) -> sqlite3.Connection:
    con = connect(path)
    con.executescript(SCHEMA)
    return con


def load_telemetry(con: sqlite3.Connection) -> None:
    seg = pd.read_csv(DATA_RAW / "segments.csv")
    seg["idx"] = seg.groupby("segment").cumcount()
    con.execute("DELETE FROM telemetry_points")
    con.execute("DELETE FROM segments")
    con.executemany(
        "INSERT INTO telemetry_points VALUES (?,?,?,?,?)",
        seg[["segment", "idx", "timestamp", "value", "channel"]].itertuples(index=False, name=None),
    )
    agg = seg.groupby("segment").agg(channel=("channel", "first"), train=("train", "first"),
                                     sampling=("sampling", "first"), anomaly=("anomaly", "first"),
                                     n=("value", "size"), start=("timestamp", "first"),
                                     end=("timestamp", "last"))
    con.executemany(
        "INSERT INTO segments VALUES (?,?,?,?,?,?,?,?,?,?)",
        [(int(i), r.channel, channel_name(r.channel), channel_kind(r.channel),
          "train" if r.train == 1 else "test", int(r.sampling), int(r.n), r.start, r.end, int(r.anomaly))
         for i, r in agg.iterrows()],
    )
    feats = pd.read_csv(DATA_PROCESSED / "features.csv")
    con.execute("DELETE FROM features")
    con.executemany(
        "INSERT INTO features VALUES (?,?)",
        [(int(r["segment"]), r.drop(["segment", "anomaly", "train"]).to_json()) for _, r in feats.iterrows()],
    )
    con.commit()


if __name__ == "__main__":
    c = init_db()
    load_telemetry(c)
    print({t: c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
           for t in ("segments", "telemetry_points", "features")})
