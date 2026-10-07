from typing import Optional
from app.config import settings
from app.sap.base import SAPJobService, JobPlatform
from app.sap.mock_sap import MockSAPJobService

def get_sap_job_service(platform: Optional[str] = None) -> SAPJobService:
    p = (platform or settings.JOB_PLATFORM or "").lower()
    mode = (settings.SAP_MODE or "").upper()
    if p in ("sap_btp", "btp") or mode == "S4HANA":
        from app.sap.btp_sap import BTPJobSchedulingService
        return BTPJobSchedulingService()
    return MockSAPJobService()


