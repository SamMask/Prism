//go:build windows

package main

import (
	"os"
	"testing"
)

// On any real Windows host these reads must return live, non-zero values — this
// is the regression that the local dashboard showed 0 GB / N/A before the
// dedicated hardware_windows.go reader existed.
func TestWindowsHardwareReadsAreLive(t *testing.T) {
	wd, _ := os.Getwd()
	disk := readDiskInfo(wd)
	if total, ok := disk["total_gb"].(float64); !ok || total <= 0 {
		t.Fatalf("disk total_gb should be > 0, got %v", disk["total_gb"])
	}

	mem := readMemoryInfo()
	if total, ok := mem["total_mb"].(float64); !ok || total <= 0 {
		t.Fatalf("memory total_mb should be > 0, got %v", mem["total_mb"])
	}

	if up := readUptimeSeconds(); up == nil || *up <= 0 {
		t.Fatalf("uptime should be a positive number, got %v", up)
	}
}
