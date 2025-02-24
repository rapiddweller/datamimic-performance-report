from pathlib import Path
import shutil
import threading
import time
from loguru import logger
import psutil
import os
import uuid
import datetime
import sys
import subprocess
import json

from app.report_components.report_generator import generate_html_report


class PerformanceMonitor:
    """
    A performance monitoring utility for measuring and analyzing the performance of DataMimic operations.
    Provides functionality to measure execution time, memory usage, and generate detailed performance reports.
    """

    def __init__(self, base_dir: Path | None = None):
        """
        Initialize the PerformanceMonitor with configuration for logging and report directories.

        Args:
            base_dir: Optional base directory for storing reports and temporary files.
                     If not provided, uses the directory containing this file.
        """
        self._base_dir = base_dir or Path(__file__).resolve().parent.parent # for scripts
        self._exec_dir: Path = Path.cwd() # for execution
        self._setup_directories()
        self._setup_logging()

    @staticmethod
    def measure_performance(runnable, sample_interval=0.01):
        """
        Measures elapsed time and monitors memory consumption (including child processes)
        while executing the given callable `runnable`.

        Memory measurement:
        - Takes a baseline reading (parent + all child processes).
        - Computes extra memory as the maximum observed usage minus the baseline.
        - Samples memory usage at a configurable interval (default: 0.01 seconds).

        Returns:
            elapsed (float): Total elapsed time.
            effective_peak (int): Extra memory (in bytes) observed above the baseline.
            memory_timeline (list): List of memory measurements (in bytes) over time.
        """
        def current_memory_usage():
            try:
                parent = psutil.Process()
                mem = parent.memory_info().rss
                for child in parent.children(recursive=True):
                    try:
                        mem += child.memory_info().rss
                    except psutil.NoSuchProcess:
                        continue
                return int(mem)
            except Exception:
                logger.exception("Error obtaining memory usage:")
                return 0

        baseline = current_memory_usage()
        max_mem = baseline
        memory_timeline = [baseline]

        thread = threading.Thread(target=runnable)
        thread.start()
        start_time = time.perf_counter()
        while thread.is_alive():
            current_mem = current_memory_usage()
            memory_timeline.append(current_mem)
            if current_mem > max_mem:
                max_mem = current_mem
            time.sleep(sample_interval)
        thread.join()
        end_time = time.perf_counter()

        elapsed = end_time - start_time
        effective_peak = max_mem - baseline
        return elapsed, effective_peak, memory_timeline

    def _setup_directories(self) -> None:
        """Create necessary directories for reports and temporary files."""
        self.scripts_dir = self._base_dir / "scripts"
        self.tmp_dir = self._exec_dir / "tmp"
        self.reports_dir = self._exec_dir / "reports"
        self.result_dir: Path = self._exec_dir / "results"

        for d in [self.tmp_dir, self.reports_dir, self.result_dir]:
            d.mkdir(exist_ok=True)

    def _setup_logging(self) -> None:
        """Configure logging with loguru to match DATAMIMIC's logging format."""
        logger.remove()
        process_id = os.getpid()
        thread_id = threading.get_ident()

        # Add console handler
        import sys
        logger.add(
            sys.stdout,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <5} | PERFMON | PID-{process} TID-" + str(thread_id) + " | {message}",
            level="INFO",
        )

        # Add file handler
        log_file = self.reports_dir / "performance_monitor.log"
        logger.add(
            str(log_file),
            rotation="1 day",
            retention="7 days",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <5} | PERFMON | PID-{process} TID-" + str(thread_id) + " | {message}",
            level="DEBUG",
        )
        logger.info("Logging configured successfully")

    def install_version(self, version: str) -> None:
        """
        Install the specified version of datamimic-ce from TestPyPI.

        Args:
            version: The version string to install (e.g., "1.2.2.dev15").
        """
        command = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--index-url", "https://pypi.org/simple",
            "--extra-index-url", "https://test.pypi.org/simple/",
            f"datamimic-ce=={version}",
        ]
        logger.info(f"Installing datamimic-ce version {version} with command: {command}")
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            logger.info(f"Installation successful: {result.stdout}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Installation failed: {e.stderr}")
            raise

    def _prepare_test_script(self, script_file: Path, count: int, num_proc: int, exporter: str) -> str:
        """Prepare test script content with the given parameters."""
        with script_file.open("r") as f:
            content = f.read()

        content = content.replace("--COUNT--", str(count))
        content = content.replace("--NUM_PROCESS--", str(num_proc))
        content = content.replace("--EXPORTER--", exporter if exporter != "NoExporter" else "")
        content = content.replace("--MULTIPROCESSING--", str(num_proc > 1))
        return content

    def _write_temp_script(self, content: str) -> Path:
        """Write prepared content to a temporary file."""
        unique_id = uuid.uuid4().hex
        temp_filename = self.tmp_dir / f"temp_script_{unique_id}.xml"
        with temp_filename.open("w") as tmp_file:
            tmp_file.write(content)
        return temp_filename

    def _copy_test_resources(self) -> None:
        """
        Copy test resources required for performance testing.
        This copies the "data" and "scripts" directories from the scripts_dir to the tmp_dir.
        The dirs_exist_ok flag ensures that if the directories already exist, no error is raised.
        Additionally, this method logs the progress of copying and warns if any resource is missing.
        Before copying, it removes any existing destination directory to ensure a fresh copy.
        """
        logger.info("Copying test resources to temporary directory...")
        resources = ["data", "scripts"]
        for resource in resources:
            src = self.scripts_dir / resource
            dst = self.tmp_dir / resource
            logger.info(f"Copying {resource} from {src} to {dst}")
            if not src.exists():
                logger.warning(f"Resource directory not found: {src}. Skipping copy for '{resource}'.")
                continue

            # Remove the destination directory if it exists to ensure fresh copy
            if dst.exists():
                try:
                    shutil.rmtree(dst)
                    logger.info(f"Removed existing '{resource}' directory at {dst} before copying fresh resources.")
                except Exception as e:
                    logger.error(f"Failed to remove existing resource directory {dst}: {e}")
                    raise

            try:
                shutil.copytree(src, dst, dirs_exist_ok=True)
                logger.info(f"Successfully copied resource '{resource}' from {src} to {dst}.")
            except Exception as e:
                logger.error(f"Failed to copy resource '{resource}' from {src} to {dst}: {e}")
                raise

    def _run_subprocess(self, script_path: Path) -> None:
        """Run test using subprocess for isolation."""
        command = ["datamimic", "run", str(script_path)]
        logger.info(f"Running command: {command}")

        env = os.environ.copy()
        venv_bin_str = str(self._base_dir / ".venv" / "bin")
        env["PATH"] = f"{venv_bin_str}{os.pathsep}{env.get('PATH', '')}"
        env["VIRTUAL_ENV"] = str(self._base_dir / ".venv")

        try:
            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                env=env,
                cwd=self._base_dir,
            )
            logger.debug(f"Subprocess completed for {script_path}")
            if result.stdout:
                logger.debug(f"Subprocess stdout: {result.stdout}")
            if result.stderr:
                logger.warning(f"Subprocess stderr: {result.stderr}")
        except subprocess.CalledProcessError as e:
            logger.error(
                f"Subprocess for {script_path} failed: {e}. Output: {e.output}, Error: {e.stderr}"
            )
            raise

    def _generate_reports(self, script_file: Path, results: list[dict]) -> None:
        """Generate performance reports from test results."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file_txt = self.reports_dir / f"performance_report_{script_file.stem}_{timestamp}.txt"
        with report_file_txt.open("w") as f:
            for res in results:
                f.write(f"{res}\n")
        logger.info(f"Text report generated: {report_file_txt}")

        html_report = generate_html_report(script_file.name, results)

        report_file_html = self.reports_dir / f"performance_report_{script_file.stem}_{timestamp}.html"
        with report_file_html.open("w") as f:
            f.write(html_report)
        logger.info(f"HTML report generated: {report_file_html}")

    def _prepare_fresh_directory(self, directory: Path) -> None:
        """
        Delete the specified directory if it exists and create a fresh empty directory.

        Args:
            directory: The Path to the directory that should be reset.
        """
        if directory.exists():
            try:
                shutil.rmtree(directory)
                logger.info(f"Existing directory removed: {directory}")
            except Exception as err:
                logger.error(f"Error removing directory {directory}: {err}")
                raise
        directory.mkdir(parents=True)

    def collect_performance_data(
        self,
        counts: list[int],
        exporters: list[str],
        num_processes: list[int],
        iterations: int = 1,
        versions: list[str] | None = None,
        use_subprocess: bool = True,
        script_file: Path | None = None
    ) -> dict:
        """
        Collect performance data for each specified version by running tests across all available scripts.
        For each version, the monitor installs the given version, runs all XML scripts with the provided testing
        parameters, and collects metrics (elapsed time, peak memory, etc.).
        
        The results for each version are saved as JSON files in a 'results' directory.
        
        Args:
            counts: List of record counts to use.
            exporters: List of exporters to test.
            num_processes: List of process counts to test.
            iterations: Number of times to repeat each test configuration.
            versions: List of version strings to test from TestPyPI. If None, the currently installed version is used.
            use_subprocess: Whether to run tests via subprocess.
            script_file: Optional path to a specific script to run. If None, all scripts are processed.
        
        Returns:
            dict: Mapping of version (or "current") to the list of test result dictionaries.
        """
        overall_results = {}
        # Create a results directory if it does not exist.
        results_dir = self._exec_dir / "results"
        self._prepare_fresh_directory(results_dir)
        self._prepare_fresh_directory(self.tmp_dir)
        self._copy_test_resources()

        
        # Determine version list; if None then test only the current version.
        version_list = versions if versions is not None else ["current"]
        
        for ver in version_list:
            version_key = ver if ver != "current" else "current"
            
            if ver != "current":
                self.install_version(ver)
                logger.info(f"Running tests with datamimic-ce version {ver}")
            else:
                logger.info("Running tests with the currently installed datamimic-ce version")
            
            version_results = []
            script_files = [script_file] if script_file is not None else list(self.scripts_dir.glob("*.xml"))
            for current_script in script_files:
                logger.info(f"[{version_key}] Processing script: {current_script.name}")
                for count in counts:
                    for exporter in exporters:
                        for num_proc in num_processes:
                            for i in range(iterations):
                                logger.info(
                                    f"[{version_key}] Iteration {i + 1} | count={count}, exporter={exporter}, num_proc={num_proc} for script {current_script.name}"
                                )
                                content = self._prepare_test_script(current_script, count, num_proc, exporter)
                                temp_filename = self._write_temp_script(content)
                                try:
                                    def run_engine():
                                        self._run_subprocess(temp_filename)
    
                                    elapsed, peak_memory, memory_timeline = self.measure_performance(run_engine)
    
                                    result = {
                                        "version": version_key,
                                        "script": current_script.name,
                                        "count": count,
                                        "exporter": exporter,
                                        "num_process": num_proc,
                                        "iteration": i + 1,
                                        "elapsed_time": elapsed,
                                        "peak_memory": peak_memory,
                                        "memory_timeline": memory_timeline,
                                    }
                                    version_results.append(result)
                                    logger.debug(f"[{version_key}] Test completed: {result}")
                                finally:
                                    try:
                                        temp_filename.unlink()
                                    except Exception as cleanup_error:
                                        logger.warning(f"Error cleaning up temporary file: {cleanup_error}")
            overall_results[version_key] = version_results
            # Save the version-specific results to a JSON file.
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            outfile = results_dir / f"results_{version_key}_{timestamp}.json"
            with outfile.open("w") as f:
                json.dump(version_results, f, indent=2)
            logger.info(f"Results for version {version_key} saved to {outfile}")
        return overall_results

    def generate_consolidated_report(self, aggregated_results: dict) -> None:
        """
        Generate a consolidated performance report from aggregated results across all versions
        and all scripts. The aggregated_results is a dictionary mapping version to a list of test result dictionaries.
        All results are merged and processed to produce one final dynamic HTML report.
        The report includes throughput (measured and interpolated), memory consumption diagrams,
        and a version summary for cross-version comparisons.
        """
        import datetime

        # Merge the results from all versions into a single list.
        all_results = []
        for version_results in aggregated_results.values():
            all_results.extend(version_results)

        # Generate the consolidated report using "Consolidated Report" as the report title.
        html_report = generate_html_report("Consolidated Report", all_results)
        
        # Save the report to the reports directory.
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file_html = self.reports_dir / f"consolidated_performance_report_{timestamp}.html"
        with report_file_html.open("w") as f:
            f.write(html_report)
        logger.info(f"Consolidated HTML report generated: {report_file_html}")
