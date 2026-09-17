from typing import Optional
from sqlalchemy.orm import Session
from app.models.integration import ExternalIdentifierMapping

class IdentifierMapper:
    @staticmethod
    def get_or_create_mapping(
        db: Session,
        hospital_id: str,
        entity_type: str,
        internal_id: str,
        external_id: str,
    ) -> ExternalIdentifierMapping:
        from sqlalchemy.exc import IntegrityError

        mapping = (
            db.query(ExternalIdentifierMapping)
            .filter(
                ExternalIdentifierMapping.hospital_id == hospital_id,
                ExternalIdentifierMapping.entity_type == entity_type,
                ExternalIdentifierMapping.internal_id == internal_id,
            )
            .first()
        )
        if mapping:
            return mapping

        try:
            mapping = ExternalIdentifierMapping(
                hospital_id=hospital_id,
                entity_type=entity_type,
                internal_id=internal_id,
                external_id=external_id,
            )
            db.add(mapping)
            db.flush()
            return mapping
        except IntegrityError:
            db.rollback()
            return (
                db.query(ExternalIdentifierMapping)
                .filter(
                    ExternalIdentifierMapping.hospital_id == hospital_id,
                    ExternalIdentifierMapping.entity_type == entity_type,
                    ExternalIdentifierMapping.internal_id == internal_id,
                )
                .first()
            )

    @staticmethod
    def resolve_external_id(
        db: Session,
        hospital_id: str,
        entity_type: str,
        internal_id: str,
        fallback_prefix: str = "EXT",
    ) -> str:
        mapping = (
            db.query(ExternalIdentifierMapping)
            .filter(
                ExternalIdentifierMapping.hospital_id == hospital_id,
                ExternalIdentifierMapping.entity_type == entity_type,
                ExternalIdentifierMapping.internal_id == internal_id,
            )
            .first()
        )
        if mapping:
            return mapping.external_id

        # Generate a deterministic external ID and record mapping
        generated_ext_id = f"{fallback_prefix}-{internal_id[:8].upper()}"
        IdentifierMapper.get_or_create_mapping(
            db, hospital_id, entity_type, internal_id, generated_ext_id
        )
        return generated_ext_id

    @staticmethod
    def resolve_internal_id(
        db: Session,
        hospital_id: str,
        entity_type: str,
        external_id: str,
    ) -> Optional[str]:
        mapping = (
            db.query(ExternalIdentifierMapping)
            .filter(
                ExternalIdentifierMapping.hospital_id == hospital_id,
                ExternalIdentifierMapping.entity_type == entity_type,
                ExternalIdentifierMapping.external_id == external_id,
            )
            .first()
        )
        return mapping.internal_id if mapping else None
