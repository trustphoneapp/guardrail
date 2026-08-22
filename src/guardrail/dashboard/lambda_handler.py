"""Lambda entrypoint for the dashboard: the same FastAPI app behind a Function
URL, adapted by Mangum. GUARDRAIL_TABLE must be set on the function or every
lookup lands in an empty in-process dict and every token is 'unknown'."""

from mangum import Mangum

from guardrail.dashboard.server import app

handler = Mangum(app)
