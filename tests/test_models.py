"""Tests for src/models/common.py – MongoBase, utc_now, StatusResponse."""

from bson import ObjectId

from src.models.common import MongoBase, StatusResponse, utc_now


class TestUtcNow:
    def test_returns_iso_string(self):
        result = utc_now()
        assert isinstance(result, str)
        assert "T" in result


class TestMongoBase:
    def test_dump_mongo_converts_id_to_objectid(self):
        oid_str = "507f1f77bcf86cd799439011"
        obj = MongoBase(id=oid_str)
        dumped = obj.model_dump_mongo()
        assert isinstance(dumped["_id"], ObjectId)
        assert str(dumped["_id"]) == oid_str

    def test_dump_mongo_removes_none_id(self):
        obj = MongoBase()
        dumped = obj.model_dump_mongo()
        assert "_id" not in dumped

    def test_validate_id_converts_objectid_to_str(self):
        oid = ObjectId("507f1f77bcf86cd799439011")
        obj = MongoBase.model_validate({"_id": oid, "created_at": "2025-01-01"})
        assert obj.id == "507f1f77bcf86cd799439011"

    def test_validate_id_none_values(self):
        result = MongoBase.validate_id(None)
        assert result is None

    def test_validate_id_empty_dict(self):
        result = MongoBase.validate_id({})
        assert result == {}

    def test_validate_id_string_id_unchanged(self):
        values = {"_id": "already_string", "created_at": "2025-01-01"}
        result = MongoBase.validate_id(values)
        assert "_id" in result


class TestStatusResponse:
    def test_defaults(self):
        r = StatusResponse()
        assert r.status == "ok"
        assert r.message == ""

    def test_custom_message(self):
        r = StatusResponse(message="done")
        assert r.message == "done"
