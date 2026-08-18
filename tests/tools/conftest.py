from pathlib import Path

import pytest

from data.build_store import build_facts_db
from data.generate_compliance_db import build_policy_db
from surveillance.store.fact_store import FactStore
from surveillance.store.policy_store import PolicyStore

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "edgar_sample"


@pytest.fixture
def fact_store(tmp_path: Path) -> FactStore:
    db_path = tmp_path / "facts.db"
    build_facts_db(FIXTURE_DIR, db_path)
    return FactStore(db_path)


@pytest.fixture
def policy_store(tmp_path: Path) -> PolicyStore:
    db_path = tmp_path / "policy.db"
    build_policy_db(db_path, issuer_ciks=["0000320193", "0000789019", "0001045810"], seed=11)
    return PolicyStore(db_path)
