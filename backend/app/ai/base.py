from abc import ABC, abstractmethod
from typing import List
from app.schemas.job import FailureAnalysisSchema, JobRunDetailSchema, JobLogSchema, JobParameterSchema

class AIService(ABC):
    @abstractmethod
    async def analyze_job_failure(
        self,
        job_details: JobRunDetailSchema,
        logs: List[JobLogSchema],
        parameters: List[JobParameterSchema]
    ) -> FailureAnalysisSchema:
        """Analyzes a failed SAP job and returns a validated structured FailureAnalysisSchema."""
        pass
