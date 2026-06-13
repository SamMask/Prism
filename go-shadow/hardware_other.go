//go:build !linux && !windows

package main

// Fallbacks for platforms without a dedicated hardware reader (e.g. macOS dev).
// Linux and Windows have their own implementations; here CPU temperature and
// uptime are unavailable and disk/memory fall back to process-level stats.

func readCPUTempC() *float64 { return nil }

func readUptimeSeconds() *float64 { return nil }

func readDiskInfo(dataDir string) response { return diskFallback(dataDir) }

func readMemoryInfo() response { return processMemoryInfo() }
