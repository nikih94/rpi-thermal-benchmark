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

def read_temp():
    """Reads CPU temperature using vcgencmd."""
    try:
        result = subprocess.run(["vcgencmd", "measure_temp"], capture_output=True, text=True)
        temp_str = result.stdout.strip().replace("temp=", "").replace("'C", "")
        return float(temp_str)
    except Exception:
        return None

def measure_and_log(writer, duration_minutes, load, file_handle=None):
    """Measures temperature every 10s, logs average every minute."""
    total_seconds = duration_minutes * 60
    elapsed = 0
    buffer = []

    while elapsed < total_seconds:
        temp = read_temp()
        if temp is not None:
            buffer.append(temp)

        time.sleep(sample_interval)
        elapsed += sample_interval

        if elapsed % 60 == 0:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            avg_temp = round(mean(buffer), 2) if buffer else None
            writer.writerow([timestamp, load, avg_temp])
            if file_handle:
                file_handle.flush()  # <-- this flushes the data to disk
            print(f"{timestamp} | Load: {load}% | Avg Temp: {avg_temp}°C")
            buffer.clear()

def run_stress(load, duration_minutes):
    """Starts stress-ng with given load and duration."""
    duration_secs = duration_minutes * 60
    return subprocess.Popen([
        "stress-ng",
        f"--cpu", str(cpu_workers),
        f"--cpu-load", str(load),
        f"-t", str(duration_secs)
    ])

def main():
    with open(csv_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "load", "cpu_temp"])
        f.flush()  # flush header too

        for load in loads:
            print(f"\n[Idle] Waiting for {idle_time} min before load {load}%...")
            measure_and_log(writer, idle_time, 0, f)

            print(f"\n[Stress] Applying {load}% load for {stress_time} min...")
            proc = run_stress(load, stress_time)
            measure_and_log(writer, stress_time, load, f)
            proc.wait()

    print("\nBenchmark complete. Results saved to ", csv_file)

if __name__ == "__main__":
    main()
