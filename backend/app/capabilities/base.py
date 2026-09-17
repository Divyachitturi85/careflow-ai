import time
import json
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.ai import CapabilityExecution

class CapabilityResult(BaseModel):
    success: bool
    capability_name: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_ms: int = 0

class BaseCapability(ABC):
    name: str = ""
    description: str = ""
    parameters_schema: Optional[Type[BaseModel]] = None

    def run(
        self,
        db: Session,
        current_user: User,
        context: Dict[str, Any],
        correlation_id: str,
        arguments: Dict[str, Any],
        conversation_id: Optional[str] = None,
    ) -> CapabilityResult:
        """Executes capability with validation, timing, and structured database audit."""
        start_time = time.time()
        exec_id = f"CAP-{uuid.uuid4().hex[:10].upper()}"

        try:
            # 1. Validate arguments against Pydantic schema if defined
            validated_args = arguments
            if self.parameters_schema:
                parsed = self.parameters_schema(**arguments)
                validated_args = parsed.model_dump()

            # 2. Execute capability logic
            data = self.execute(
                db=db,
                current_user=current_user,
                context=context,
                correlation_id=correlation_id,
                **validated_args,
            )

            execution_ms = int((time.time() - start_time) * 1000)

            # 3. Record CapabilityExecution in DB
            db_exec = CapabilityExecution(
                conversation_id=conversation_id,
                correlation_id=correlation_id,
                capability_name=self.name,
                input_payload_json=json.dumps(arguments, default=str),
                output_payload_json=json.dumps(data, default=str),
                status="SUCCESS",
                execution_ms=execution_ms,
            )
            db.add(db_exec)
            db.commit()

            return CapabilityResult(
                success=True,
                capability_name=self.name,
                data=data,
                execution_ms=execution_ms,
            )

        except Exception as e:
            execution_ms = int((time.time() - start_time) * 1000)
            err_msg = str(e)

            db_exec = CapabilityExecution(
                conversation_id=conversation_id,
                correlation_id=correlation_id,
                capability_name=self.name,
                input_payload_json=json.dumps(arguments, default=str),
                output_payload_json=json.dumps({"error": err_msg}),
                status="FAILED",
                execution_ms=execution_ms,
                error_message=err_msg,
            )
            db.add(db_exec)
            db.commit()

            return CapabilityResult(
                success=False,
                capability_name=self.name,
                error=err_msg,
                execution_ms=execution_ms,
            )

    @abstractmethod
    def execute(
        self,
        db: Session,
        current_user: User,
        context: Dict[str, Any],
        correlation_id: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Subclasses must implement actual service invocation."""
        pass
