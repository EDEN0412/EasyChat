import pytest
from app import db

@pytest.fixture(autouse=True)
def setup_test_transaction():
    """各テストの前にトランザクションを開始し、テスト後にロールバックする"""
    # テーブルをクリーンアップ
    for table in reversed(db.metadata.sorted_tables):
        db.session.execute(table.delete())
    db.session.commit()

    try:
        yield
    finally:
        db.session.rollback()
        db.session.remove() 