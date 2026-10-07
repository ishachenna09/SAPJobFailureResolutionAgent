import time
import logging
import httpx
from typing import Optional, List

logger = logging.getLogger(__name__)

class SAPAuthClient:
    """
    Acquires and caches OAuth2 access tokens for SAP BTP Job Scheduling Service
    using the client_credentials grant flow.
    Never exposes or logs client secrets, access tokens, or authorization headers.
    """
    def __init__(
        self,
        base_url: str = "",
        client_id: str = "",
        client_secret: str = "",
        token_url: str = ""
    ):
        self.base_url = (base_url or "").rstrip("/")
        self.client_id = client_id or ""
        self.client_secret = client_secret or ""
        self.token_url = (token_url or "").strip()
        self._token: Optional[str] = None
        self._expires_at: float = 0.0

    def _get_token_endpoints(self) -> List[str]:
        endpoints = []
        if self.token_url:
            endpoints.append(self.token_url)
        
        base = self.base_url
        if base:
            endpoints.append(f"{base}/oauth/token")
            # If region host like cfapps.ap21.hana.ondemand.com, add standard BTP UAA candidates
            if "hana.ondemand.com" in base:
                parts = base.split(".")
                # Find region code (e.g. ap21, us10, eu10)
                region = next((p for p in parts if len(p) >= 3 and p[:2] in ("ap", "us", "eu", "ca", "br", "jp")), "")
                if region:
                    endpoints.append(f"https://{region}.authentication.sap.hana.ondemand.com/oauth/token")
                    endpoints.append(f"https://authentication.{region}.hana.ondemand.com/oauth/token")

        return list(dict.fromkeys(endpoints))

    async def get_access_token(self) -> str:
        """
        Retrieves a valid OAuth2 access token, using an in-memory cached token if not expired.
        """
        now = time.time()
        if self._token and now < self._expires_at - 60:
            return self._token

        if not self.client_id or not self.client_secret:
            logger.warning("SAP BTP credentials missing. Returning blank access token.")
            return ""

        candidate_endpoints = self._get_token_endpoints()
        logger.info(f"Requesting new SAP BTP OAuth2 token (candidates: {len(candidate_endpoints)})...")

        last_error = None
        async with httpx.AsyncClient(timeout=15.0) as client:
            for endpoint in candidate_endpoints:
                try:
                    # Try Basic Auth first per standard OAuth2 RFC 6749
                    res = await client.post(
                        endpoint,
                        data={"grant_type": "client_credentials"},
                        auth=(self.client_id, self.client_secret),
                        headers={"Content-Type": "application/x-www-form-urlencoded"}
                    )
                    if res.status_code in (400, 401):
                        # Fallback to form body parameters if Basic Auth fails
                        res = await client.post(
                            endpoint,
                            data={
                                "grant_type": "client_credentials",
                                "client_id": self.client_id,
                                "client_secret": self.client_secret
                            },
                            headers={"Content-Type": "application/x-www-form-urlencoded"}
                        )

                    if res.status_code == 200:
                        data = res.json()
                        token = data.get("access_token")
                        expires_in = data.get("expires_in", 3600)

                        if token:
                            self._token = token
                            self._expires_at = now + float(expires_in)
                            logger.info(f"Successfully acquired SAP BTP OAuth2 token from {endpoint}")
                            return self._token
                    else:
                        last_error = f"HTTP {res.status_code} from {endpoint}"
                except Exception as err:
                    last_error = f"{type(err).__name__} from {endpoint}: {err}"

        logger.error(f"Failed to acquire SAP BTP access token: {last_error}")
        logger.error("TIP: Please set SAP_TOKEN_URL in backend/.env to your SAP BTP UAA token URL from your SAP BTP Service Key binding (e.g. SAP_TOKEN_URL=\"https://<your-subaccount>.authentication.ap21.hana.ondemand.com/oauth/token\").")
        raise RuntimeError(f"SAP BTP authentication error: {last_error}. Please set SAP_TOKEN_URL in backend/.env to your SAP BTP UAA token URL from your SAP BTP Service Key JSON.")
