import csv
import time
import subprocess
from statistics import mean

# ====== CONFIGURATION ======
stress_time = 20  # in minutes
idle_time = 20    # in minutes
loads = [20, 40, 60, 80, 100]  # load percentages to test
csv_file = "stats.csv"
cpu_workers = 4  # adjust based on number of cores
sample_interval = 10  # seconds between temperature samples
# ===========================

sensor_paths = {
    "cpu_temp": "/sys/devices/virtual/thermal/thermal_zone0/hwmon0/temp1_input",
    "nvme_temp1": "/sys/devices/platform/axi/1000110000.pcie/pci0000:00/0000:00:00.0/0000:01:00.0/nvme/nvme0/hwmon1/temp1_input",
    "nvme_temp2": "/sys/devices/platform/axi/1000110000.pcie/pci0000:00/0000:00:00.0/0000:01:00.0/nvme/nvme0/hwmon1/temp2_input",
    "adc_temp": "/sys/devices/platform/axi/1000120000.pcie/1f000c8000.adc/hwmon/hwmon2/temp1_input"
}

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

    return readings

def measure_and_log(writer, duration_minutes, load, file_handle=None):
    total_seconds = duration_minutes * 60
    elapsed = 0
    buffer = {label: [] for label in sensor_paths}

    while elapsed < total_seconds:
        temps = read_all_temps()
        for label, value in temps.items():
            if value is not None:
                buffer[label].append(value)

        time.sleep(sample_interval)
        elapsed += sample_interval

        if elapsed % 60 == 0:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            row = [timestamp, load]
            for label in sensor_paths:
                values = buffer[label]
                avg = round(mean(values), 2) if values else None
                row.append(avg)
            writer.writerow(row)
            if file_handle:
                file_handle.flush()
            print(f"{timestamp} | Load: {load}% | " + " | ".join(
                f"{label}: {row[i+2]}°C" for i, label in enumerate(sensor_paths)))
            buffer = {label: [] for label in sensor_paths}

def run_stress(load, duration_minutes):
    duration_secs = duration_minutes * 60
    return subprocess.Popen([
        "stress-ng",
        "--cpu", str(cpu_workers),
        "--cpu-load", str(load),
        "-t", str(duration_secs)
    ])

def main():
    with open(csv_file, "w", newline="") as f:
        writer = csv.writer(f)
        header = ["timestamp", "load"] + list(sensor_paths.keys()) + ["gpu_temp"]
        writer.writerow(header)
        f.flush()

        for load in loads:
            print(f"\n[Idle] Waiting for {idle_time} min before load {load}%...")
            measure_and_log(writer, idle_time, 0, f)

            print(f"\n[Stress] Applying {load}% load for {stress_time} min...")
            proc = run_stress(load, stress_time)
            measure_and_log(writer, stress_time, load, f)
            proc.wait()

    print("\nBenchmark complete. Results saved to", csv_file)

if __name__ == "__main__":
    main()
