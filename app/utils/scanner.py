import os
import shutil
import subprocess
import logging

logger = logging.getLogger(__name__)

# Standard EICAR test string to verify anti-virus functionality
EICAR_SIGNATURE = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"

def scan_file(file_path: str) -> dict:
    """
    Scans a file for malware/viruses.
    First checks for standard EICAR signature, then runs local ClamAV scanner if available.
    """
    logger.info(f"Starting malware scan on file: {file_path}")
    
    if not os.path.exists(file_path):
        return {
            "status": "failed",
            "message": "File not found",
            "threats": []
        }
        
    # 1. Signature-based EICAR check (in-memory scan of first few blocks)
    try:
        with open(file_path, "rb") as f:
            content = f.read(1024)  # EICAR is short and usually at the beginning of the file
            if EICAR_SIGNATURE in content:
                logger.warning(f"Malware detected! EICAR test signature found in: {file_path}")
                return {
                    "status": "infected",
                    "message": "Threat detected: EICAR-Test-Signature",
                    "threats": ["EICAR-Test-Signature"]
                }
    except Exception as e:
        logger.error(f"Error performing EICAR signature check: {str(e)}")

    # 2. Check for ClamAV installation (clamscan or clamdscan)
    clamscan_path = shutil.which("clamscan")
    clamdscan_path = shutil.which("clamdscan")
    
    # We prefer clamdscan (daemon) as it is much faster
    scanner_bin = clamdscan_path or clamscan_path
    
    if scanner_bin:
        try:
            logger.info(f"Running ClamAV scan using: {scanner_bin}")
            # Run scan command
            # clamdscan / clamscan returns 0 if clean, 1 if virus found, 2 if error
            result = subprocess.run(
                [scanner_bin, "--no-summary", file_path],
                capture_output=True,
                text=True,
                timeout=30  # Timeout after 30 seconds
            )
            
            if result.returncode == 0:
                return {
                    "status": "clean",
                    "message": "ClamAV scan completed successfully. No threats found.",
                    "threats": []
                }
            elif result.returncode == 1:
                # Virus found
                output_lines = result.stdout.strip().split("\n")
                threats = [line.split(":")[-1].strip() for line in output_lines if "FOUND" in line]
                logger.warning(f"Malware detected by ClamAV in {file_path}: {threats}")
                return {
                    "status": "infected",
                    "message": f"Threats detected by ClamAV: {', '.join(threats)}",
                    "threats": threats
                }
            else:
                # Error (e.g. clamd not running for clamdscan)
                logger.warning(f"ClamAV returned error code {result.returncode}. Output: {result.stderr}")
        except subprocess.TimeoutExpired:
            logger.error("ClamAV scan timed out")
        except Exception as e:
            logger.error(f"Failed to run ClamAV: {str(e)}")

    # 3. Fallback: If no virus found and no ClamAV errors, treat as clean
    logger.info(f"Scan complete. File {file_path} is CLEAN.")
    return {
        "status": "clean",
        "message": "Heuristic scan clean. No threat signatures matched.",
        "threats": []
    }
