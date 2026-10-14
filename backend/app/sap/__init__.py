from typing import Optional
from app.config import settings
from app.sap.base import SAPJobService, JobPlatform
from app.sap.mock_sap import MockSAPJobService

# Singleton instance across requests so in-memory jobs & restarts are preserved
_mock_sap_instance: Optional[MockSAPJobService] = None

def get_mock_sap_service() -> MockSAPJobService:
    global _mock_sap_instance
    if _mock_sap_instance is None:
        _mock_sap_instance = MockSAPJobService()
    return _mock_sap_instance

def get_sap_job_service(platform: Optional[str] = None) -> SAPJobService:
    # Explicit platform check takes top priority
    if platform:
        p = platform.upper()
        if p in ("SAP_BTP", "BTP"):
            from app.sap.btp_sap import BTPJobSchedulingService
            return BTPJobSchedulingService()
        elif p in ("MOCK_SAP", "MOCK", "MOCK-SAP", "MOCK_S4HANA"):
            return get_mock_sap_service()

    # If platform not specified, check settings.JOB_PLATFORM
    configured_platform = (settings.JOB_PLATFORM or "mock").upper()
    if configured_platform in ("SAP_BTP", "BTP"):
        from app.sap.btp_sap import BTPJobSchedulingService
        return BTPJobSchedulingService()

    return get_mock_sap_service()
