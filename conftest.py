import pytest
import logging

# Configure logger
logger = logging.getLogger(__name__)

def pytest_runtest_logreport(report):
    """
    Log test results to the configured log file.
    """
    if report.when == 'call':
        if report.passed:
            logger.info(f"PASSED: {report.nodeid}")
        elif report.failed:
            logger.error(f"FAILED: {report.nodeid}")
            if report.longrepr:
                 logger.error(f"Failure Details:\n{report.longrepr}")
        elif report.skipped:
            logger.info(f"SKIPPED: {report.nodeid}")
            
    elif report.when == 'setup' and report.failed:
        logger.error(f"SETUP FAILED: {report.nodeid}")
        
    elif report.when == 'teardown' and report.failed:
        logger.error(f"TEARDOWN FAILED: {report.nodeid}")
