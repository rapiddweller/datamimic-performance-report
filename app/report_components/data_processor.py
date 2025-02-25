from collections import defaultdict

from app.report_components.interpolation import improved_interpolate


def process_report_throughput_data(results, target_processes):
    """
    Process throughput data for consolidated report generation.
    Groups results by script and version, averaging throughput measurements
    for each number of processes.

    Args:
        results (list): List of performance result dictionaries.
        target_processes (list): List of target process counts for interpolation.

    Returns:
        dict: A dictionary keyed by script, where each value is a dict with keys:
              "measured": list of datasets (each with 'version' and 'data'),
              "interpolated": similar structure using interpolated data.
    """
    throughput_measured = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for res in results:
        script = res["script"]
        version = res.get("version", "current")
        np_val = res["num_process"]
        th = (res["count"] / res["elapsed_time"]) if res["elapsed_time"] > 0 else 0
        throughput_measured[script][version][np_val].append(th)

    throughput_by_script = {}
    for script, version_data in throughput_measured.items():
        throughput_by_script[script] = {"measured": [], "interpolated": []}
        for version, np_dict in version_data.items():
            measured_x = sorted(np_dict.keys())
            measured_y = [int(round(sum(np_dict[x]) / len(np_dict[x]))) for x in measured_x]
            throughput_by_script[script]["measured"].append(
                {"version": version, "data": [{"x": x, "y": y} for x, y in zip(measured_x, measured_y, strict=False)]}
            )
            interp_y = []
            for t in target_processes:
                if t in measured_x:
                    avg_val = int(round(sum(np_dict[t]) / len(np_dict[t])))
                    interp_y.append(avg_val)
                else:
                    interp_val = int(round(improved_interpolate(t, measured_x, measured_y)))
                    interp_y.append(interp_val)
            throughput_by_script[script]["interpolated"].append(
                {
                    "version": version,
                    "data": [{"x": t, "y": v} for t, v in zip(target_processes, interp_y, strict=False)],
                }
            )
    return throughput_by_script


def process_report_memory_data(results):
    """
    Process memory consumption data for consolidated report generation.
    Separates single-process and multi-process results. For single-process,
    groups the results by script and version, averaging peak memory (in MB)
    per record count. For multi-process, groups by script then by process count.

    Returns:
        dict: A dictionary keyed by script, with two keys:
              "single_process": list of datasets for single-process memory,
              "multi_process": dict keyed by num_proc, each a list of datasets per version.
    """

    def bytes_to_mb(b):
        return b / (1024 * 1024)

    single_data = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    multi_data = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))

    for res in results:
        script = res["script"]
        version = res.get("version", "current")
        cnt = res["count"]
        num_proc = res["num_process"]
        timeline = res.get("memory_timeline", [])
        if not timeline:
            continue
        peak_mb = max(timeline) / (1024 * 1024)
        if num_proc == 1:
            single_data[script][version][cnt].append(peak_mb)
        else:
            multi_data[script][version][num_proc][cnt].append(peak_mb)

    memory_by_script = {}
    for script in set(list(single_data.keys()) + list(multi_data.keys())):
        memory_by_script[script] = {"single_process": [], "multi_process": {}}
        for version, cnt_dict in single_data.get(script, {}).items():
            counts_sorted = sorted(cnt_dict.keys())
            avg_vals = [int(round(sum(cnt_dict[c]) / len(cnt_dict[c]))) for c in counts_sorted]
            memory_by_script[script]["single_process"].append(
                {"version": version, "data": [{"x": c, "y": v} for c, v in zip(counts_sorted, avg_vals, strict=False)]}
            )
        for version, proc_dict in multi_data.get(script, {}).items():
            for num_proc, cnt_dict in proc_dict.items():
                counts_sorted = sorted(cnt_dict.keys())
                avg_vals = [int(round(sum(cnt_dict[c]) / len(cnt_dict[c]))) for c in counts_sorted]
                if num_proc not in memory_by_script[script]["multi_process"]:
                    memory_by_script[script]["multi_process"][num_proc] = []
                memory_by_script[script]["multi_process"][num_proc].append(
                    {
                        "version": version,
                        "data": [{"x": c, "y": v} for c, v in zip(counts_sorted, avg_vals, strict=False)],
                    }
                )
    return memory_by_script


def process_overall_throughput(results):
    """
    Computes overall average throughput for each version across all scripts.

    Returns:
        list: Array of dictionaries, each containing 'version' and 'throughput'.
    """
    overall = defaultdict(list)
    for res in results:
        version = res.get("version", "current")
        throughput = (res["count"] / res["elapsed_time"]) if res["elapsed_time"] > 0 else 0
        overall[version].append(throughput)
    overall_avg = []
    for version, values in overall.items():
        avg = sum(values) / len(values) if values else 0
        overall_avg.append({"version": version, "throughput": avg})
    overall_avg.sort(key=lambda x: x["version"])
    return overall_avg
