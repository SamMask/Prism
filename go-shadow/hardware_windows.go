//go:build windows

package main

import (
	"math"
	"syscall"
	"unsafe"
)

var (
	kernel32              = syscall.NewLazyDLL("kernel32.dll")
	procGetDiskFreeSpace  = kernel32.NewProc("GetDiskFreeSpaceExW")
	procGlobalMemoryStat  = kernel32.NewProc("GlobalMemoryStatusEx")
	procGetTickCount64    = kernel32.NewProc("GetTickCount64")
)

// readCPUTempC is intentionally unavailable on Windows. There is no standard
// API for CPU temperature; reading it reliably needs third-party kernel drivers
// (OpenHardwareMonitor/LibreHardwareMonitor). Returning nil renders as "N/A",
// which is honest rather than fabricated.
func readCPUTempC() *float64 { return nil }

// readUptimeSeconds uses GetTickCount64 (milliseconds since boot).
func readUptimeSeconds() *float64 {
	r1, _, _ := procGetTickCount64.Call()
	if r1 == 0 {
		return nil
	}
	secs := float64(uint64(r1)) / 1000.0
	return &secs
}

// readDiskInfo reports usage of the volume holding dataDir via GetDiskFreeSpaceEx.
func readDiskInfo(dataDir string) response {
	pathPtr, err := syscall.UTF16PtrFromString(dataDir)
	if err != nil {
		return diskFallback(dataDir)
	}
	var freeAvail, totalBytes, totalFree uint64
	r1, _, _ := procGetDiskFreeSpace.Call(
		uintptr(unsafe.Pointer(pathPtr)),
		uintptr(unsafe.Pointer(&freeAvail)),
		uintptr(unsafe.Pointer(&totalBytes)),
		uintptr(unsafe.Pointer(&totalFree)),
	)
	if r1 == 0 || totalBytes == 0 {
		return diskFallback(dataDir)
	}
	used := totalBytes - totalFree
	percent := math.Round(float64(used)/float64(totalBytes)*1000) / 10
	return response{
		"total_gb": gbFromBytes(totalBytes),
		"used_gb":  gbFromBytes(used),
		"free_gb":  gbFromBytes(freeAvail),
		"percent":  percent,
	}
}

// memoryStatusEx mirrors the Win32 MEMORYSTATUSEX struct.
type memoryStatusEx struct {
	dwLength                uint32
	dwMemoryLoad            uint32
	ullTotalPhys            uint64
	ullAvailPhys            uint64
	ullTotalPageFile        uint64
	ullAvailPageFile        uint64
	ullTotalVirtual         uint64
	ullAvailVirtual         uint64
	ullAvailExtendedVirtual uint64
}

// readMemoryInfo reports physical RAM via GlobalMemoryStatusEx, falling back to
// the Go process memory stats if the call fails.
func readMemoryInfo() response {
	var m memoryStatusEx
	m.dwLength = uint32(unsafe.Sizeof(m))
	r1, _, _ := procGlobalMemoryStat.Call(uintptr(unsafe.Pointer(&m)))
	if r1 == 0 || m.ullTotalPhys == 0 {
		return processMemoryInfo()
	}
	total := m.ullTotalPhys
	avail := m.ullAvailPhys
	used := total - avail
	percent := math.Round(float64(used)/float64(total)*1000) / 10
	return response{
		"total_mb":     mbFromKB(total / 1024),
		"used_mb":      mbFromKB(used / 1024),
		"available_mb": mbFromKB(avail / 1024),
		"percent":      percent,
	}
}
