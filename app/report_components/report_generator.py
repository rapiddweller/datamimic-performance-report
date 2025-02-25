import json
from collections import defaultdict
from typing import Any

from app.report_components.data_processor import (
    process_overall_throughput,
    process_report_memory_data,
    process_report_throughput_data,
)


def aggregate_report_data(results):
    """
    Aggregates report data for consolidated report generation.
    Processes throughput and memory data grouped by script.

    Returns:
        dict: Contains JSON strings for throughput data (measured and interpolated)
              and memory data (single process and multi-process) grouped by script.
    """
    target_processes = list(range(1, 21))
    throughput_by_script = process_report_throughput_data(results, target_processes)
    memory_by_script = process_report_memory_data(results)
    overall_throughput = process_overall_throughput(results)

    return {
        "overallThroughput_json": json.dumps(overall_throughput),
        "throughputByScriptMeasured_json": json.dumps(
            {script: data["measured"] for script, data in throughput_by_script.items()}
        ),
        "throughputByScriptInterpolated_json": json.dumps(
            {script: data["interpolated"] for script, data in throughput_by_script.items()}
        ),
        "memoryByScriptSingle_json": json.dumps(
            {script: data["single_process"] for script, data in memory_by_script.items()}
        ),
        "memoryByScriptMulti_json": json.dumps(
            {script: data["multi_process"] for script, data in memory_by_script.items()}
        ),
    }


def generate_html_report(report_title: str, results: list) -> str:
    """
    Generate a consolidated HTML performance report.

    Args:
        report_title: Title of the report.
        results: List of performance test result dictionaries.

    Returns:
        HTML content as a string.
    """
    import json

    # Aggregate performance data
    target_processes = list(range(1, 21))  # Define target process range for interpolation
    throughput_by_script = process_report_throughput_data(results, target_processes)

    # Prepare datasets arrays
    rawThroughputDatasets: list[dict[str, Any]] = []
    smoothThroughputDatasets: list[dict[str, Any]] = []

    # Process both measured and interpolated throughput data
    for script, data in throughput_by_script.items():
        # Add measured data
        for dataset in data["measured"]:
            rawThroughputDatasets.append(
                {"label": f"{script} - {dataset['version']}", "data": dataset["data"], "type": "scatter"}
            )
        # Add interpolated data
        for dataset in data["interpolated"]:
            smoothThroughputDatasets.append(
                {"label": f"{script} - {dataset['version']}", "data": dataset["data"], "type": "line"}
            )

    # Process memory data
    single_memory_data: defaultdict[str, defaultdict[str, list[dict[str, float]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    multi_memory_data: defaultdict[str, defaultdict[str, defaultdict[str, list[dict[str, float]]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )
    version_summary_temp: defaultdict[str, dict[str, list[float]]] = defaultdict(
        lambda: {"throughputs": [], "memories": []}
    )

    for res in results:
        version = res.get("version", "unknown")
        script = res.get("script", "unknown")
        count = res.get("count", 0)
        num_proc = res.get("num_process", 1)
        elapsed = res.get("elapsed_time", 0)
        peak_memory = res.get("peak_memory", 0)
        throughput = count / elapsed if elapsed > 0 else 0
        memory_MB = peak_memory / (1024 * 1024)

        if num_proc == 1:
            single_memory_data[script][version].append({"x": count, "y": memory_MB})
        else:
            multi_memory_data[script][version][str(num_proc)].append({"x": count, "y": memory_MB})

        version_summary_temp[version]["throughputs"].append(throughput)
        version_summary_temp[version]["memories"].append(memory_MB)

    rawSingleMemoryDatasets: list[dict[str, Any]] = []
    for script, versions in single_memory_data.items():
        for version, points in versions.items():
            rawSingleMemoryDatasets.append({"label": f"{script} - {version}", "data": points, "type": "line"})

    rawMultiMemoryDatasets: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for script, version_data in multi_memory_data.items():
        for version, proc_data in version_data.items():
            if version not in rawMultiMemoryDatasets:
                rawMultiMemoryDatasets[version] = {}
            for num_proc, points in proc_data.items():
                if num_proc not in rawMultiMemoryDatasets[version]:
                    rawMultiMemoryDatasets[version][num_proc] = []
                rawMultiMemoryDatasets[version][num_proc].append({"label": f"{script}", "data": points, "type": "line"})

    versionSummary = {}
    for version, data in version_summary_temp.items():
        cnt = len(data["throughputs"])
        avg_throughput = sum(data["throughputs"]) / cnt if cnt > 0 else 0
        avg_memory = sum(data["memories"]) / cnt if cnt > 0 else 0
        versionSummary[version] = {"avgThroughput": avg_throughput, "avgMemory": avg_memory, "testCount": cnt}

    overallThroughput = []
    for version, data in version_summary_temp.items():
        cnt = len(data["throughputs"])
        avg_throughput = sum(data["throughputs"]) / cnt if cnt > 0 else 0
        overallThroughput.append({"version": version, "throughput": avg_throughput})

    context = {
        "script_name": report_title,
        "rawThroughputDatasets": json.dumps(rawThroughputDatasets),
        "smoothThroughputDatasets": json.dumps(smoothThroughputDatasets),
        "rawSingleMemoryDatasets": json.dumps(rawSingleMemoryDatasets),
        "rawMultiMemoryDatasets": json.dumps(rawMultiMemoryDatasets),
        "versionSummary": json.dumps(versionSummary),
        "overallThroughput": json.dumps(overallThroughput),
    }

    import os

    import jinja2

    template_dir = os.path.join(os.path.dirname(__file__), "template")
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir))
    template = env.get_template("report_template.html.j2")
    return template.render(context)
