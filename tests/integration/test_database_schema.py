from sqlalchemy import inspect

from src.campaigns import models as campaign_models  # noqa: F401
from src.database import Base, create_engine
from src.dictionaries import models as dictionary_models  # noqa: F401


def test_metadata_creates_expected_tables_and_constraints():
    engine = create_engine("sqlite:///:memory:")

    with engine.begin() as connection:
        Base.metadata.create_all(connection)
        inspector = inspect(connection)

        assert set(inspector.get_table_names()) == {
            "campaign",
            "campaign_stream",
            "stream_offer",
            "dictionary_item",
        }

        campaign_columns = {column["name"] for column in inspector.get_columns("campaign")}
        assert campaign_columns == {
            "id",
            "keitaro_campaign_id",
            "name",
            "domain_id",
            "group_id",
            "source_id",
            "created_at",
            "updated_at",
        }

        stream_columns = {
            column["name"] for column in inspector.get_columns("campaign_stream")
        }
        assert stream_columns == {
            "id",
            "campaign_id",
            "keitaro_stream_id",
            "name",
            "kind",
            "created_at",
            "updated_at",
        }

        offer_columns = {column["name"] for column in inspector.get_columns("stream_offer")}
        assert offer_columns == {
            "id",
            "stream_id",
            "keitaro_offer_id",
            "weight",
            "active",
            "pinned_weight",
            "created_at",
            "updated_at",
        }
        offer_active_column = next(
            column
            for column in inspector.get_columns("stream_offer")
            if column["name"] == "active"
        )
        assert offer_active_column["default"] is not None

        dictionary_columns = {
            column["name"] for column in inspector.get_columns("dictionary_item")
        }
        assert dictionary_columns == {
            "id",
            "type",
            "keitaro_id",
            "name",
            "created_at",
            "updated_at",
        }

        campaign_unique_constraints = {
            tuple(constraint["column_names"])
            for constraint in inspector.get_unique_constraints("campaign")
        }
        assert campaign_unique_constraints == {("keitaro_campaign_id",)}

        campaign_indexes = {
            tuple(index["column_names"]) for index in inspector.get_indexes("campaign")
        }
        assert campaign_indexes == {("keitaro_campaign_id",)}

        stream_unique_constraints = {
            tuple(constraint["column_names"])
            for constraint in inspector.get_unique_constraints("campaign_stream")
        }
        assert stream_unique_constraints == {("campaign_id", "keitaro_stream_id")}

        offer_unique_constraints = {
            tuple(constraint["column_names"])
            for constraint in inspector.get_unique_constraints("stream_offer")
        }
        assert offer_unique_constraints == {("stream_id", "keitaro_offer_id")}

        dictionary_unique_constraints = {
            tuple(constraint["column_names"])
            for constraint in inspector.get_unique_constraints("dictionary_item")
        }
        assert dictionary_unique_constraints == {("type", "keitaro_id")}

        stream_foreign_keys = {
            (fk["constrained_columns"][0], fk["referred_table"], fk["referred_columns"][0])
            for fk in inspector.get_foreign_keys("campaign_stream")
        }
        assert stream_foreign_keys == {("campaign_id", "campaign", "id")}

        offer_foreign_keys = {
            (fk["constrained_columns"][0], fk["referred_table"], fk["referred_columns"][0])
            for fk in inspector.get_foreign_keys("stream_offer")
        }
        assert offer_foreign_keys == {("stream_id", "campaign_stream", "id")}

    engine.dispose()
