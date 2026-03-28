"""
Gallery management for face recognition
Handles database loading and face matching
"""
import sqlite3
import numpy as np


class Gallery:
    """Face gallery manager"""

    def __init__(self, db_path: str):
        """
        Initialize gallery from database

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.templates = None
        self.unique_pids = None
        self.names = None
        self.template_owner_index = None
        self.P = 0  # Number of persons
        self.M = 0  # Number of templates
        self.D = 0  # Embedding dimension
        self.id_server_map = {}  # person_id -> id_server

        self._load_from_db()

    def _load_from_db(self):
        """Load gallery data from database"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Load person names and id_server mapping
        cur.execute("SELECT person_id, COALESCE(display_name,''), id_server FROM persons")
        person_rows = cur.fetchall()
        id_to_name = {int(pid): name for pid, name, _ in person_rows}
        self.id_server_map = {
            int(pid): int(id_srv) for pid, _, id_srv in person_rows
            if id_srv is not None
        }

        # Load face templates
        cur.execute("SELECT person_id, emb_dim, embedding FROM face_templates")
        rows = cur.fetchall()
        conn.close()

        if not rows:
            raise ValueError("No templates found in database")

        person_ids = np.array([int(r[0]) for r in rows], dtype=np.int32)
        emb_dim = int(rows[0][1])

        # Build normalized embeddings
        embs = []
        for pid, dim, blob in rows:
            if int(dim) != emb_dim:
                raise ValueError("Inconsistent embedding dimensions in DB")
            e = np.frombuffer(blob, dtype=np.float32)
            e = e / (np.linalg.norm(e) + 1e-12)
            embs.append(e)

        self.templates = np.stack(embs, axis=0).astype(np.float32)  # (M, D)
        self.unique_pids = np.unique(person_ids)  # (P,)

        # Map template to person index
        pid_to_index = {pid: i for i, pid in enumerate(self.unique_pids)}
        self.template_owner_index = np.array(
            [pid_to_index[pid] for pid in person_ids], dtype=np.int32
        )

        # Person names
        self.names = [id_to_name.get(int(pid), "") for pid in self.unique_pids]

        self.P = self.unique_pids.shape[0]
        self.M, self.D = self.templates.shape

    def match(self, embedding: np.ndarray, threshold: float, margin: float = 0.03):
        """
        Match embedding against gallery

        Args:
            embedding: Face embedding (D,)
            threshold: Similarity threshold
            margin: Margin between best and 2nd best

        Returns:
            dict: {
                'match': bool,
                'person_id': int or -1,
                'person_name': str,
                'score': float,
                'best_score': float,
                'second_score': float
            }
        """
        # Compute similarities
        sims = self.templates @ embedding  # (M,)

        # Get best score per person
        best_per_person = np.full((self.P,), -1e9, dtype=np.float32)
        np.maximum.at(best_per_person, self.template_owner_index, sims)

        # Find top 2
        if self.P == 1:
            b_idx = 0
            b_score = float(best_per_person[0])
            s_score = -1e9
        else:
            top2_idx = np.argpartition(best_per_person, -2)[-2:]
            top2_idx = top2_idx[np.argsort(best_per_person[top2_idx])[::-1]]
            b_idx = int(top2_idx[0])
            s_idx = int(top2_idx[1])
            b_score = float(best_per_person[b_idx])
            s_score = float(best_per_person[s_idx])

        # Check thresholds
        ok_thr = b_score >= threshold
        ok_margin = True if self.P == 1 else ((b_score - s_score) >= margin)

        if ok_thr and ok_margin:
            pid = int(self.unique_pids[b_idx])
            name = self.names[b_idx]
            match = True
        else:
            pid = -1
            name = ""
            match = False

        return {
            'match': match,
            'person_id': pid,
            'person_name': name,
            'score': b_score,
            'best_score': b_score,
            'second_score': s_score
        }

    def __repr__(self):
        return f"Gallery(persons={self.P}, templates={self.M}, dim={self.D})"
