"""SEC EDGAR module."""

from oaa_observatory.sec.bootstrap import bootstrap_entity_resolution, load_firm_universe
from oaa_observatory.sec.client import SECClient
from oaa_observatory.sec.parser import parse_filing_bytes
from oaa_observatory.sec.pipeline import SECFilingsPipeline

__all__ = [
    "SECClient",
    "SECFilingsPipeline",
    "bootstrap_entity_resolution",
    "load_firm_universe",
    "parse_filing_bytes",
]
