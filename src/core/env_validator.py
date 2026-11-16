import asyncio
import shutil
import logging
import re
import importlib.util
from src.core.exceptions import SystemDependencyError

logger = logging.getLogger(__name__)

class EnvironmentValidator:
    def __init__(self):
        self.required_ncat_version = "7.0"
        self.required_libs = ["portalocker"]

    async def verify_environment(self) -> None:
        """
        Performs a full audit of the system environment.
        Raises SystemDependencyError if requirements are not met.
        """
        logger.info("Starting system environment validation...")

        # 1. Verify ncat
        ncat_path = shutil.which("ncat")
        if not ncat_path:
            logger.error("ncat binary not found in PATH.")
            raise SystemDependencyError(
                dependency_name="ncat",
                message="ncat binary not found in system PATH.",
                required_version=self.required_ncat_version
            )

        try:
            proc = await asyncio.create_subprocess_exec(
                "ncat", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            output = (stdout.decode() + stderr.decode()).strip()
            
            if proc.returncode != 0:
                raise Exception(f"ncat --version failed with exit code {proc.returncode}")

            # Robust version extraction
            matches = re.findall(r"(\d+\.\d+)", output)
            if not matches:
                raise ValueError(f"Could not parse ncat version from output: {output}")

            detected_version = matches[0]
            
            # Version comparison (major.minor...), normalized to equal length
            # so [7] vs [7,0] does not falsely compare as less.
            def parse_ver(v):
                parts = [int(x) for x in v.split(".")]
                n = max(len(parts), 2)
                return parts + [0] * (n - len(parts))

            if parse_ver(detected_version) < parse_ver(self.required_ncat_version):
                logger.error(f"ncat version {detected_version} is below required {self.required_ncat_version}")
                raise SystemDependencyError(
                    dependency_name="ncat",
                    message=f"ncat version {detected_version} is insufficient.",
                    required_version=self.required_ncat_version,
                    detected_version=detected_version
                )
            
            logger.info(f"ncat found: version {detected_version} (OK)")

        except Exception as e:
            if isinstance(e, SystemDependencyError):
                raise e
            logger.error(f"Failed to verify ncat: {e}")
            raise SystemDependencyError(
                dependency_name="ncat",
                message=f"Error during ncat verification: {str(e)}",
                required_version=self.required_ncat_version
            )

        # 2. Verify Python libraries
        for lib in self.required_libs:
            if importlib.util.find_spec(lib) is None:
                logger.error(f"Required library '{lib}' is not installed.")
                raise SystemDependencyError(
                    dependency_name=lib,
                    message=f"Python library '{lib}' is missing."
                )
            logger.info(f"Library '{lib}' found (OK)")

        logger.info("System environment validation successful.")
