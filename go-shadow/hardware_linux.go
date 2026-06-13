//go:build linux

package main

import (
	"math"
	"os"
	"syscall"
)

// readCPUTempC reads the SoC temperature from the kernel thermal zone (Raspberry
// Pi / generic Linux). Returns nil when the sysfs entry is missing/unreadable.
func readCPUTempC() *float64 {
	data, err := os.ReadFile("/sys/class/thermal/thermal_zone0/temp")
	if err != nil {
		return nil
	}
	if c, ok := parseCPUTempMilliC(string(data)); ok {
		return &c
	}
	return nil
}

// readUptimeSeconds reads system uptime from /proc/uptime.
func readUptimeSeconds() *float64 {
	data, err := os.ReadFile("/proc/uptime")
	if err != nil {
		return nil
	}
	if s, ok := parseUptimeSeconds(string(data)); ok {
		return &s
	}
	return nil
}

// readDiskInfo reports usage of the filesystem holding dataDir via statfs.
func readDiskInfo(dataDir string) response {
	var st syscall.Statfs_t
	if err := syscall.Statfs(dataDir, &st); err != nil {
		return diskFallback(dataDir)
	}
	bsize := uint64(st.Bsize)
	total := st.Blocks * bsize
	free := st.Bavail * bsize
	used := total - st.Bfree*bsize
	percent := 0.0
	if total > 0 {
		percent = math.Round(float64(used)/float64(total)*1000) / 10
	}
	return response{
		"total_gb": gbFromBytes(total),
		"used_gb":  gbFromBytes(used),
		"free_gb":  gbFromBytes(free),
		"percent":  percent,
	}
}

// readMemoryInfo reports system RAM from /proc/meminfo, falling back to the Go
// process memory stats if the file is unavailable or unparsable.
func readMemoryInfo() response {
	data, err := os.ReadFile("/proc/meminfo")
	if err == nil {
		if total, avail, ok := parseMeminfoKB(string(data)); ok && total > 0 {
			used := total - avail
			percent := math.Round(float64(used)/float64(total)*1000) / 10
			return response{
				"total_mb":     mbFromKB(total),
				"used_mb":      mbFromKB(used),
				"available_mb": mbFromKB(avail),
				"percent":      percent,
			}
		}
	}
	return processMemoryInfo()
}
