import csv
import time
import subprocess
from statistics import mean
from datetime import datetime, timedelta
import sys
import glob

# ====== CONFIGURATION ======
stress_time = 20  # in minutes
idle_time = 20    # in minutes
loads = [20, 40, 60, 80, 100]  # load percentages to test
csv_file = "stats.csv"
cpu_workers = 4  # adjust based on number of cores
sample_interval = 10  # seconds between temperature samples
aggregate_interval = 60  # write to csv aggregates of taken measurements (default: 60s) can go down to sample_interval

# ===========================

sensor_paths = {
    "cpu_temp": "/sys/devices/virtual/thermal/thermal_zone0/hwmon0/temp1_input",
    "adc_temp": "/sys/devices/platform/axi/1000120000.pcie/1f000c8000.adc/hwmon/hwmon2/temp1_input"
}

def detect_fan_rpm_path():
    candidates = glob.glob("/sys/class/hwmon/hwmon*/fan1_input")
    return candidates[0] if candidates else None

fan_rpm_path = detect_fan_rpm_path()

def detect_nvme_temp_paths_via_find():
    nvme_paths = {}
    try:
        result = subprocess.run(
            ["find", "/sys", "-readable", "-type", "f", "-name", "temp*_input"],
            capture_output=True,
            text=True
        )
        for line in result.stdout.strip().splitlines():
            if line.endswith("nvme/nvme0/hwmon1/temp1_input"):
                nvme_paths["nvme_temp1"] = line
            elif line.endswith("nvme/nvme0/hwmon1/temp2_input"):
                nvme_paths["nvme_temp2"] = line
    except Exception as e:
        print("Failed to detect NVMe sensors:", e)
    return nvme_paths

sensor_paths.update(detect_nvme_temp_paths_via_find())

def read_all_temps():
    readings = {}
    for label, path in sensor_paths.items():
        try:
            with open(path, "r") as f:
                readings[label] = int(f.read().strip()) / 1000.0
        except Exception:
            readings[label] = None
    try:
        result = subprocess.run(["vcgencmd", "measure_temp"], capture_output=True, text=True)
        temp_str = result.stdout.strip().replace("temp=", "").replace("'C", "")
        readings["gpu_temp"] = float(temp_str)
    except Exception:
        readings["gpu_temp"] = None

    # Add fan RPM
    if fan_rpm_path:
        try:
            with open(fan_rpm_path, "r") as f:
                readings["fan_rpm"] = int(f.read().strip())
        except Exception:
            readings["fan_rpm"] = None

    return readings

def measure_and_log(writer, duration_minutes, load, file_handle=None, aggregate_interval=60):

    total_seconds = duration_minutes * 60
    elapsed = 0

    since_last_agg = 0
    # Sanity: keep aggregate interval >= sampling interval
    if aggregate_interval < sample_interval:
        print(f"⚠️ aggregate_interval ({aggregate_interval}s) < sample_interval ({sample_interval}s). Using {sample_interval}s.")
        aggregate_interval = sample_interval

    # First sample to detect all sensor labels
    first_read = read_all_temps()
    buffer = {label: [] for label in first_read}
    labels = list(first_read.keys())

    while elapsed < total_seconds:
        temps = read_all_temps()

        # Add new labels on the fly (if any)
        for label in temps:
            if label not in buffer:
                buffer[label] = []
                labels.append(label)

        for label, value in temps.items():
            if value is not None:
                buffer[label].append(value)

        time.sleep(sample_interval)
        elapsed += sample_interval
        since_last_agg += sample_interval


        # Flush every aggregate_interval, and once at the end (to not lose a partial window)
        if since_last_agg >= aggregate_interval or elapsed >= total_seconds:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            row = [timestamp, load]
            for label in labels:
                values = buffer[label]
                if values:
                    if label == "fan_rpm":
                        avg = int(round(mean(values)))  # integer RPM
                    else:
                        avg = round(mean(values), 2)   # temp with decimals
                else:
                    avg = None
                row.append(avg)
            writer.writerow(row)
            if file_handle:
                file_handle.flush()
            line = f"{timestamp} | Load: {load}% | " + " | ".join(
                f"{label}: {int(row[i+2])} rpm" if label == "fan_rpm" and row[i+2] is not None
                else f"{label}: {row[i+2]:.2f}°C" if row[i+2] is not None
                else f"{label}: N/A"
                for i, label in enumerate(labels)
            )
            sys.stdout.write("\r" + line)
            sys.stdout.flush()
            buffer = {label: [] for label in labels}
            since_last_agg = 0
    print()

def run_stress(load, duration_minutes):
    duration_secs = duration_minutes * 60
    return subprocess.Popen([
        "stress-ng",
        "--cpu", str(cpu_workers),
        "--cpu-load", str(load),
        "-t", str(duration_secs)
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def main():
    with open(csv_file, "w", newline="") as f:
        writer = csv.writer(f)
        header = ["timestamp", "load"] + list(read_all_temps().keys())
        writer.writerow(header)
        f.flush()

        stress_minutes = len(loads) * stress_time
        idle_minutes = len(loads) * idle_time
        estimated_end = datetime.now() + timedelta(minutes=(stress_minutes+idle_minutes))
        print(f"📊 Starting Raspberry Pi Thermal Benchmark")
        print(f"🕒 Total Duration: ~{(stress_minutes+idle_minutes)} min")
        print(f"⏰ Estimated Completion: {estimated_end.strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 60)


        for load in loads:
            print(f"\n[Idle] Waiting for {idle_time} min before load {load}%...")
            measure_and_log(writer, idle_time, 0, f, aggregate_interval=aggregate_interval)

            print(f"\n[Stress] Applying {load}% load for {stress_time} min...")
            proc = run_stress(load, stress_time)
            measure_and_log(writer, stress_time, load, f, aggregate_interval=aggregate_interval)
            proc.wait()

    print("\nBenchmark complete. Results saved to", csv_file)

if __name__ == "__main__":
    main()
