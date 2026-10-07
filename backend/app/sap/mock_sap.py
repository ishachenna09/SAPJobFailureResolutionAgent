from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
import random
from app.sap.base import SAPJobService
from app.schemas.job import JobRunDetailSchema, JobStepSchema, JobLogSchema, JobParameterSchema

class MockSAPJobService(SAPJobService):
    """
    Local Mock SAP Application Job Runtime conforming to SAP_COM_0326 semantics.
    Supports JobStatusGet, JobinfoGet, JobHeaderSet/Logs, JobParamValuesGet, JobRestart.
    """
    def __init__(self):
        self._seed_mock_data()

    def _seed_mock_data(self):
        now = datetime.now(timezone.utc)
        today_str = now.strftime("%Y-%m-%d")

        self.jobs_db: Dict[str, Dict[str, Any]] = {
            # Failed Job 1 (Can be run through agent - DB Lock retryable)
            "Z_CUSTOMER_LOAD:1001": {
                "id": 1,
                "job_name": "Z_CUSTOMER_LOAD",
                "run_count": 1001,
                "status": "FAILED",
                "job_text": "Daily Master Customer Load from S/4HANA",
                "job_user": "SAP_BATCH_USER",
                "environment": "MOCK_SAP_S4HANA",
                "restart_allowed": True,
                "max_retries": 2,
                "retry_count": 0,
                "return_code": 8,
                "failed_step_number": 3,
                "start_time": (now - timedelta(minutes=15)).isoformat(),
                "end_time": (now - timedelta(minutes=14)).isoformat(),
                "steps": [
                    {"step_number": 1, "step_name": "Validate Input Files", "program_name": "R_CUST_VAL_01", "status": "SUCCESS", "return_code": 0, "start_time": "10:25:02", "end_time": "10:25:05"},
                    {"step_number": 2, "step_name": "Transform Staging Records", "program_name": "R_CUST_TRSF_02", "status": "SUCCESS", "return_code": 0, "start_time": "10:25:05", "end_time": "10:25:11"},
                    {"step_number": 3, "step_name": "Update Customer Database (KNA1/KNB1)", "program_name": "R_CUST_DB_UPDATE", "status": "FAILED", "return_code": 8, "start_time": "10:25:11", "end_time": "10:25:19"},
                    {"step_number": 4, "step_name": "Generate Customer Audit Log", "program_name": "R_CUST_AUDIT", "status": "NOT_EXECUTED", "return_code": 0, "start_time": None, "end_time": None}
                ],
                "logs": [
                    {"timestamp": "10:25:02", "severity": "INFO", "step_number": 1, "message": "Step 1 started: Validating customer input files", "is_error_highlight": False},
                    {"timestamp": "10:25:05", "severity": "INFO", "step_number": 1, "message": "Step 1 completed successfully. 4,500 records parsed.", "is_error_highlight": False},
                    {"timestamp": "10:25:05", "severity": "INFO", "step_number": 2, "message": "Step 2 started: Transforming customer staging data", "is_error_highlight": False},
                    {"timestamp": "10:25:11", "severity": "INFO", "step_number": 2, "message": "Step 2 completed successfully. Return Code: 0.", "is_error_highlight": False},
                    {"timestamp": "10:25:11", "severity": "INFO", "step_number": 3, "message": "Step 3 started: Updating database tables KNA1/KNB1", "is_error_highlight": False},
                    {"timestamp": "10:25:17", "severity": "INFO", "step_number": 3, "message": "Attempting to acquire exclusive DB lock on table KNA1...", "is_error_highlight": False},
                    {"timestamp": "10:25:19", "severity": "ERROR", "step_number": 3, "message": "ERROR: DATABASE_LOCK_TIMEOUT - Could not lock record range KNA1: 1000-2000 after 120s wait time", "is_error_highlight": True},
                    {"timestamp": "10:25:19", "severity": "ERROR", "step_number": 3, "message": "Transaction rolled back automatically. Job execution terminated with return code 8.", "is_error_highlight": True}
                ],
                "parameters": [
                    {"param_name": "COMPANY_CODE", "param_value": "1000"},
                    {"param_name": "POSTING_DATE", "param_value": today_str},
                    {"param_name": "CUSTOMER_GROUP", "param_value": "ALL"}
                ]
            },

            # Failed Job 2 (Can be run through agent - RFC Network Timeout)
            "Z_VENDOR_SYNC:3001": {
                "id": 2,
                "job_name": "Z_VENDOR_SYNC",
                "run_count": 3001,
                "status": "FAILED",
                "job_text": "Vendor Master Synchronization via RFC",
                "job_user": "SAP_RFC_USER",
                "environment": "MOCK_SAP_S4HANA",
                "restart_allowed": True,
                "max_retries": 2,
                "retry_count": 0,
                "return_code": 6,
                "failed_step_number": 2,
                "start_time": (now - timedelta(minutes=8)).isoformat(),
                "end_time": (now - timedelta(minutes=7)).isoformat(),
                "steps": [
                    {"step_number": 1, "step_name": "Extract Vendor Delta", "program_name": "R_VEND_EXT", "status": "SUCCESS", "return_code": 0, "start_time": "11:30:00", "end_time": "11:30:10"},
                    {"step_number": 2, "step_name": "Transmit via RFC Gateway", "program_name": "R_RFC_SEND", "status": "FAILED", "return_code": 6, "start_time": "11:30:10", "end_time": "11:30:25"}
                ],
                "logs": [
                    {"timestamp": "11:30:00", "severity": "INFO", "step_number": 1, "message": "Step 1 complete. 850 vendor records extracted.", "is_error_highlight": False},
                    {"timestamp": "11:30:10", "severity": "INFO", "step_number": 2, "message": "Opening RFC connection to gateway sap_gw_prod_01...", "is_error_highlight": False},
                    {"timestamp": "11:30:25", "severity": "ERROR", "step_number": 2, "message": "ERROR: RFC_TIMEOUT - Gateway connection lost after 15000ms", "is_error_highlight": True}
                ],
                "parameters": [
                    {"param_name": "RFC_DESTINATION", "param_value": "SAP_GW_PROD"}
                ]
            },

            # Failed Job 3 (Escalates to Human - Authorization Failure)
            "Z_FIN_POSTING:2001": {
                "id": 3,
                "job_name": "Z_FIN_POSTING",
                "run_count": 2001,
                "status": "FAILED",
                "job_text": "Financial Document Posting & Reconciliation",
                "job_user": "FIN_SYSTEM_SVC",
                "environment": "MOCK_SAP_S4HANA",
                "restart_allowed": False,
                "max_retries": 0,
                "retry_count": 0,
                "return_code": 12,
                "failed_step_number": 1,
                "start_time": (now - timedelta(minutes=10)).isoformat(),
                "end_time": (now - timedelta(minutes=9)).isoformat(),
                "steps": [
                    {"step_number": 1, "step_name": "Verify Financial Authorizations", "program_name": "R_FIN_AUTH_CHK", "status": "FAILED", "return_code": 12, "start_time": "11:10:00", "end_time": "11:10:04"}
                ],
                "logs": [
                    {"timestamp": "11:10:00", "severity": "INFO", "step_number": 1, "message": "Step 1 started: Verifying user authorizations for financial posting", "is_error_highlight": False},
                    {"timestamp": "11:10:04", "severity": "ERROR", "step_number": 1, "message": "ERROR: AUTHORIZATION_FAILURE - User FIN_SYSTEM_SVC lacks authorization object F_BKPF_BUK for Company Code 2000", "is_error_highlight": True},
                    {"timestamp": "11:10:04", "severity": "ERROR", "step_number": 1, "message": "Authorization check failed (Activity 01 - Create). Job terminated with RC 12.", "is_error_highlight": True}
                ],
                "parameters": [
                    {"param_name": "COMPANY_CODE", "param_value": "2000"},
                    {"param_name": "LEDGER", "param_value": "0L"}
                ]
            },

            # Failed Job 4 (Escalates to Human - Authorization Failure)
            "Z_PAYROLL_RUN:2002": {
                "id": 4,
                "job_name": "Z_PAYROLL_RUN",
                "run_count": 2002,
                "status": "FAILED",
                "job_text": "Executive Payroll Reconciliation & Posting",
                "job_user": "HR_PAYROLL_SVC",
                "environment": "MOCK_SAP_S4HANA",
                "restart_allowed": False,
                "max_retries": 0,
                "retry_count": 0,
                "return_code": 12,
                "failed_step_number": 1,
                "start_time": (now - timedelta(minutes=12)).isoformat(),
                "end_time": (now - timedelta(minutes=11)).isoformat(),
                "steps": [
                    {"step_number": 1, "step_name": "Verify Payroll Authorization Object P_ORGIN", "program_name": "R_PAY_AUTH_CHK", "status": "FAILED", "return_code": 12, "start_time": "11:15:00", "end_time": "11:15:04"}
                ],
                "logs": [
                    {"timestamp": "11:15:00", "severity": "INFO", "step_number": 1, "message": "Step 1 started: Checking HR authorization object P_ORGIN for Payroll Area US", "is_error_highlight": False},
                    {"timestamp": "11:15:04", "severity": "ERROR", "step_number": 1, "message": "ERROR: AUTHORIZATION_FAILURE - User HR_PAYROLL_SVC missing object P_ORGIN (INFTY 0008, AUTHC R/W)", "is_error_highlight": True},
                    {"timestamp": "11:15:04", "severity": "ERROR", "step_number": 1, "message": "Security policy restriction: Automated restart forbidden for HR payroll authorization failures.", "is_error_highlight": True}
                ],
                "parameters": [
                    {"param_name": "PAYROLL_AREA", "param_value": "US"},
                    {"param_name": "PERIOD", "param_value": "08/2026"}
                ]
            },

            # Successful Job 1
            "Z_INVOICE_BATCH:4001": {
                "id": 5,
                "job_name": "Z_INVOICE_BATCH",
                "run_count": 4001,
                "status": "SUCCESS",
                "job_text": "Batch Billing & Invoice Generation",
                "job_user": "SAP_BILLING_USER",
                "environment": "MOCK_SAP_S4HANA",
                "restart_allowed": True,
                "max_retries": 2,
                "retry_count": 0,
                "return_code": 0,
                "failed_step_number": None,
                "start_time": (now - timedelta(minutes=5)).isoformat(),
                "end_time": (now - timedelta(minutes=4)).isoformat(),
                "steps": [
                    {"step_number": 1, "step_name": "Fetch Billing Queue", "program_name": "RV60SBAT", "status": "SUCCESS", "return_code": 0, "start_time": "12:00:00", "end_time": "12:00:15"},
                    {"step_number": 2, "step_name": "Generate Invoices", "program_name": "SDBILLDL", "status": "SUCCESS", "return_code": 0, "start_time": "12:00:15", "end_time": "12:01:00"}
                ],
                "logs": [
                    {"timestamp": "12:00:00", "severity": "INFO", "step_number": 1, "message": "Step 1 complete. 128 documents retrieved.", "is_error_highlight": False},
                    {"timestamp": "12:01:00", "severity": "INFO", "step_number": 2, "message": "Step 2 completed cleanly. Return Code: 0.", "is_error_highlight": False}
                ],
                "parameters": [
                    {"param_name": "SALES_ORG", "param_value": "1010"}
                ]
            },

            # Successful Job 2
            "Z_SALES_REPORT:4002": {
                "id": 6,
                "job_name": "Z_SALES_REPORT",
                "run_count": 4002,
                "status": "SUCCESS",
                "job_text": "Daily Sales & Revenue Aggregation Report",
                "job_user": "SAP_REPORT_USER",
                "environment": "MOCK_SAP_S4HANA",
                "restart_allowed": True,
                "max_retries": 2,
                "retry_count": 0,
                "return_code": 0,
                "failed_step_number": None,
                "start_time": (now - timedelta(minutes=3)).isoformat(),
                "end_time": (now - timedelta(minutes=2)).isoformat(),
                "steps": [
                    {"step_number": 1, "step_name": "Extract Sales Ledger", "program_name": "R_SALES_EXT", "status": "SUCCESS", "return_code": 0, "start_time": "12:10:00", "end_time": "12:10:20"},
                    {"step_number": 2, "step_name": "Compile Executive Dashboard Data", "program_name": "R_SALES_COMP", "status": "SUCCESS", "return_code": 0, "start_time": "12:10:20", "end_time": "12:11:00"}
                ],
                "logs": [
                    {"timestamp": "12:10:00", "severity": "INFO", "step_number": 1, "message": "Step 1 complete. Sales ledger aggregated.", "is_error_highlight": False},
                    {"timestamp": "12:11:00", "severity": "INFO", "step_number": 2, "message": "Step 2 completed cleanly. Return Code: 0.", "is_error_highlight": False}
                ],
                "parameters": [
                    {"param_name": "REGION", "param_value": "GLOBAL"}
                ]
            }
        }

    def _get_key(self, job_name: str, run_count: int) -> str:
        return f"{job_name}:{run_count}"

    def ensure_job_registered(self, job_name: str, run_count: int, scenario: str = "TRANSIENT_DB_LOCK"):
        """Ensures dynamic jobs created in the simulator exist with full steps in Mock SAP database."""
        key = self._get_key(job_name, run_count)
        if key not in self.jobs_db:
            now_str = datetime.now(timezone.utc).strftime("%H:%M:%S")
            if scenario == "AUTHORIZATION_FAILURE":
                self.jobs_db[key] = {
                    "id": random.randint(1000, 9999),
                    "job_name": job_name,
                    "run_count": run_count,
                    "status": "FAILED",
                    "job_text": f"Simulated {job_name} Authorization Failure",
                    "job_user": "SAP_AUTH_USER",
                    "environment": "MOCK_SAP_S4HANA",
                    "restart_allowed": False,
                    "max_retries": 0,
                    "retry_count": 0,
                    "return_code": 12,
                    "failed_step_number": 1,
                    "start_time": datetime.now(timezone.utc).isoformat(),
                    "steps": [
                        {"step_number": 1, "step_name": "Authorization Verification", "program_name": "R_AUTH_CHK", "status": "FAILED", "return_code": 12, "start_time": now_str, "end_time": now_str}
                    ],
                    "logs": [
                        {"timestamp": now_str, "severity": "ERROR", "step_number": 1, "message": f"ERROR: AUTHORIZATION_FAILURE - User lacks permissions for {job_name}", "is_error_highlight": True}
                    ],
                    "parameters": [{"param_name": "JOB_MODE", "param_value": "SIMULATED"}]
                }
            elif scenario == "RESTART_FROM_START" or scenario == "INTERMEDIATE_STATE_INCONSISTENCY":
                self.jobs_db[key] = {
                    "id": random.randint(1000, 9999),
                    "job_name": job_name,
                    "run_count": run_count,
                    "status": "FAILED",
                    "job_text": f"Simulated {job_name} Batch Inconsistency Failure",
                    "job_user": "SAP_CO_BATCH",
                    "environment": "MOCK_SAP_S4HANA",
                    "restart_allowed": True,
                    "max_retries": 2,
                    "retry_count": 0,
                    "return_code": 8,
                    "failed_step_number": 2,
                    "start_time": datetime.now(timezone.utc).isoformat(),
                    "steps": [
                        {"step_number": 1, "step_name": "Initialize Staging Table", "program_name": "R_STAGING_INIT", "status": "SUCCESS", "return_code": 0, "start_time": now_str, "end_time": now_str},
                        {"step_number": 2, "step_name": "Batch Calculation Process", "program_name": "R_CALC_RUN", "status": "FAILED", "return_code": 8, "start_time": now_str, "end_time": now_str},
                        {"step_number": 3, "step_name": "Generate Settlement Journal", "program_name": "R_JOURNAL_POST", "status": "NOT_EXECUTED", "return_code": 0, "start_time": None, "end_time": None}
                    ],
                    "logs": [
                        {"timestamp": now_str, "severity": "INFO", "step_number": 1, "message": "Step 1 completed cleanly.", "is_error_highlight": False},
                        {"timestamp": now_str, "severity": "ERROR", "step_number": 2, "message": "ERROR: INTERMEDIATE_STATE_INCONSISTENCY - Staging corrupt; full batch recalculation required", "is_error_highlight": True}
                    ],
                    "parameters": [{"param_name": "JOB_MODE", "param_value": "SIMULATED"}]
                }
            else:
                self.jobs_db[key] = {
                    "id": random.randint(1000, 9999),
                    "job_name": job_name,
                    "run_count": run_count,
                    "status": "FAILED",
                    "job_text": f"Simulated {job_name} Execution",
                    "job_user": "SAP_BATCH_USER",
                    "environment": "MOCK_SAP_S4HANA",
                    "restart_allowed": True,
                    "max_retries": 2,
                    "retry_count": 0,
                    "return_code": 8,
                    "failed_step_number": 2,
                    "start_time": datetime.now(timezone.utc).isoformat(),
                    "steps": [
                        {"step_number": 1, "step_name": "Initialization & Staging", "program_name": "R_INIT_01", "status": "SUCCESS", "return_code": 0, "start_time": now_str, "end_time": now_str},
                        {"step_number": 2, "step_name": "Process Database Transactions", "program_name": "R_DB_PROC", "status": "FAILED", "return_code": 8, "start_time": now_str, "end_time": now_str},
                        {"step_number": 3, "step_name": "Finalize Execution Summary", "program_name": "R_SUMMARY", "status": "NOT_EXECUTED", "return_code": 0, "start_time": None, "end_time": None}
                    ],
                    "logs": [
                        {"timestamp": now_str, "severity": "INFO", "step_number": 1, "message": "Step 1 completed cleanly.", "is_error_highlight": False},
                        {"timestamp": now_str, "severity": "ERROR", "step_number": 2, "message": "ERROR: DATABASE_LOCK_TIMEOUT - Resource locked by concurrent process", "is_error_highlight": True}
                    ],
                    "parameters": [{"param_name": "JOB_MODE", "param_value": "SIMULATED"}]
                }

    async def get_job_status(self, job_name: str, run_count: int) -> Dict[str, Any]:
        key = self._get_key(job_name, run_count)
        if key not in self.jobs_db:
            self.ensure_job_registered(job_name, run_count)
        job = self.jobs_db[key]
        return {
            "job_name": job["job_name"],
            "run_count": job["run_count"],
            "status": job["status"],
            "return_code": job["return_code"],
            "failed_step_number": job["failed_step_number"],
            "exists": True
        }

    async def get_job_info(self, job_name: str, run_count: int) -> JobRunDetailSchema:
        key = self._get_key(job_name, run_count)
        if key not in self.jobs_db:
            self.ensure_job_registered(job_name, run_count)
        job = self.jobs_db[key]

        steps = [JobStepSchema(**s) for s in job["steps"]]
        logs = [JobLogSchema(**l) for l in job["logs"]]
        params = [JobParameterSchema(**p) for p in job["parameters"]]

        return JobRunDetailSchema(
            id=job["id"],
            job_name=job["job_name"],
            run_count=job["run_count"],
            status=job["status"],
            start_time=job["start_time"],
            end_time=job.get("end_time"),
            return_code=job["return_code"],
            failed_step_number=job["failed_step_number"],
            job_user=job["job_user"],
            job_text=job.get("job_text"),
            retry_count=job["retry_count"],
            environment=job.get("environment", "MOCK_SAP"),
            restart_allowed=job.get("restart_allowed", True),
            max_retries=job.get("max_retries", 2),
            steps=steps,
            logs=logs,
            parameters=params
        )

    async def get_job_logs(self, job_name: str, run_count: int) -> List[JobLogSchema]:
        job_info = await self.get_job_info(job_name, run_count)
        return job_info.logs

    async def get_job_parameters(self, job_name: str, run_count: int) -> List[JobParameterSchema]:
        job_info = await self.get_job_info(job_name, run_count)
        return job_info.parameters

    async def restart_job(self, job_name: str, run_count: int, restart_mode: str = "E") -> Dict[str, Any]:
        """
        Executes SAP JobRestart per SAP_COM_0326.
        Crucial Phase 2 Rule: Does NOT overwrite the failed run; creates a new restarted run.
        """
        orig_key = self._get_key(job_name, run_count)
        if orig_key not in self.jobs_db:
            self.ensure_job_registered(job_name, run_count)
        orig_job = self.jobs_db[orig_key]

        new_run_count = run_count + 1
        new_key = self._get_key(job_name, new_run_count)

        now = datetime.now(timezone.utc)
        now_str = now.strftime("%H:%M:%S")

        failed_step = orig_job.get("failed_step_number", 1) or 1
        new_steps = []
        new_logs = []

        if restart_mode == "A":
            # RESTART_FROM_START: Rerun ALL steps 1..N
            for s in orig_job["steps"]:
                new_steps.append({
                    "step_number": s["step_number"],
                    "step_name": s["step_name"],
                    "program_name": s.get("program_name"),
                    "status": "SUCCESS",
                    "return_code": 0,
                    "start_time": now_str,
                    "end_time": now_str
                })
                new_logs.append({
                    "timestamp": now_str,
                    "severity": "INFO",
                    "step_number": s["step_number"],
                    "message": f"Step {s['step_number']} ({s['step_name']}) rerun from beginning and completed successfully (RC 0).",
                    "is_error_highlight": False
                })
        else:
            # RESTART_FROM_FAILED_STEP (mode="E"): Retain previous successful steps, rerun failed & subsequent steps
            for s in orig_job["steps"]:
                if s["step_number"] < failed_step:
                    # Retained prior step
                    new_steps.append({
                        "step_number": s["step_number"],
                        "step_name": s["step_name"],
                        "program_name": s.get("program_name"),
                        "status": "SUCCESS",
                        "return_code": 0,
                        "start_time": s.get("start_time"),
                        "end_time": s.get("end_time")
                    })
                    new_logs.append({
                        "timestamp": now_str,
                        "severity": "INFO",
                        "step_number": s["step_number"],
                        "message": f"Step {s['step_number']} retained from previous execution (SUCCESS).",
                        "is_error_highlight": False
                    })
                else:
                    # Rerun failed & future steps
                    new_steps.append({
                        "step_number": s["step_number"],
                        "step_name": s["step_name"],
                        "program_name": s.get("program_name"),
                        "status": "SUCCESS",
                        "return_code": 0,
                        "start_time": now_str,
                        "end_time": now_str
                    })
                    new_logs.append({
                        "timestamp": now_str,
                        "severity": "INFO",
                        "step_number": s["step_number"],
                        "message": f"Step {s['step_number']} ({s['step_name']}) executed on retry (mode=E) and completed cleanly (RC 0).",
                        "is_error_highlight": False
                    })

        new_logs.append({
            "timestamp": now_str,
            "severity": "INFO",
            "step_number": failed_step,
            "message": f"Job restart executed via SAP_COM_0326 API contract (mode={restart_mode}). All steps verified Return Code 0.",
            "is_error_highlight": False
        })

        new_job = {
            "id": random.randint(1000, 9999),
            "job_name": job_name,
            "run_count": new_run_count,
            "status": "SUCCESS",
            "job_text": orig_job.get("job_text"),
            "job_user": orig_job.get("job_user", "SAP_BATCH_USER"),
            "environment": orig_job.get("environment", "MOCK_SAP_S4HANA"),
            "restart_allowed": orig_job.get("restart_allowed", True),
            "max_retries": orig_job.get("max_retries", 2),
            "retry_count": orig_job.get("retry_count", 0) + 1,
            "return_code": 0,
            "failed_step_number": None,
            "start_time": now.isoformat(),
            "end_time": (now + timedelta(seconds=15)).isoformat(),
            "steps": new_steps,
            "logs": new_logs,
            "parameters": orig_job.get("parameters", [])
        }

        # Store the new run in mock database without deleting the original failed run
        self.jobs_db[new_key] = new_job

        return {
            "success": True,
            "job_name": job_name,
            "original_run_count": run_count,
            "new_run_count": new_run_count,
            "restart_mode": restart_mode,
            "status": "SUCCESS",
            "new_job_data": new_job
        }
