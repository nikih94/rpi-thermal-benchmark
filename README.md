# Raspberry Pi Thermal Benchmark Tool

This Python script performs a **thermal benchmark on Raspberry Pi** devices using controlled CPU loads via `stress-ng`. It monitors multiple temperature sensors—including CPU, GPU, NVMe, and ADC—while alternating between **idle** and **load** periods, and logs the average values to a CSV file every minute.

---

## 🌡️ Measured sensors

By default, the following sensors are monitored:

- CPU temperature via `/sys/class/thermal`
- GPU temperature using `vcgencmd`
- NVMe disk temperatures via `/sys/.../nvme0/.../temp*_input`
- ADC temperature from onboard ADC

---

## 🔧 What It Does

- Applies increasing CPU loads (e.g., 20%, 40%, ..., 100%) using `stress-ng`
- Each load phase is preceded by an idle (cool down) period
- Records temperature every 10 seconds
- Logs the **average temperature per minute** to a CSV file (`stats.csv`)
- Designed to test **thermal performance and cooling** of Raspberry Pi devices

---

## 📦 Requirements

- Raspberry Pi (tested on models with `vcgencmd`)
- Python 3
- `stress-ng` utility

### Install dependencies

```bash
sudo apt update
sudo apt install stress-ng
```

---

## 🚀 How to Use

### 1. Clone or copy the script

Save the script as `stressng_temp_benchmark.py`.

### 2. Configure the parameters

At the top of the script, you can configure:

```python
stress_time = 20      # minutes under load
idle_time = 20        # minutes in idle before each load phase
loads = [20, 40, 60, 80, 100]  # CPU load percentages
cpu_workers = 4       # Number of CPU stress workers (usually number of cores)
sample_interval = 10  # Temperature sampling interval (in seconds)
```

Adjust `cpu_workers` based on your Pi model (e.g., 4 for Raspberry Pi 4).

#### 2.1 Configure sensor paths

If some temperature readings are missing or incorrect, you can inspect available sensor paths with:

```bash
sudo find /sys -type f -name "temp*_input"
```

Then update the sensor_paths dictionary at the top of the script:

```python
sensor_paths = {
    "cpu_temp":    "/sys/...",
    "nvme_temp1":  "/sys/...",
    "nvme_temp2":  "/sys/...",
    "adc_temp":    "/sys/..."
}
```

### 3. Run the script

```bash
python3 stressng_temp_benchmark.py
```

The script will:
- Idle for `idle_time` minutes (logging temperature)
- Apply each load from the `loads` array for `stress_time` minutes
- Log temperature data to `stats.csv`

---

## 📄 Output: `stats.csv`

The output CSV contains:

| timestamp           | load | cpu\_temp | nvme\_temp1 | nvme\_temp2 | adc\_temp | gpu\_temp |
| ------------------- | ---- | --------- | ----------- | ----------- | --------- | --------- |
| 2025-05-23 13:00:00 | 0    | 42.5      | 24.6        | 38.9        | 51.3      | 45.8      |
| 2025-05-23 13:01:00 | 0    | 42.6      | 24.6        | 38.9        | 51.2      | 45.7      |
| 2025-05-23 13:20:00 | 20   | 48.3      | 25.1        | 40.3        | 52.1      | 49.2      |
| ...                 | ...  | ...       | ...         | ...         | ...       | ...       |


- `timestamp`: Current time (logged once per minute)
- `load`: Load % applied (0 during idle)
- Each sensor column: Average temperature for the last minute (°C)

---

## 📌 Use Cases

This tool is useful for:

- **Testing thermal throttling behavior**
- Evaluating **cooling performance** of heatsinks, fans, or cases
- Comparing different **Raspberry Pi models** under stress
- Logging temperature for **hardware validation**

---

## 📋 License

MIT License — feel free to use and modify.
