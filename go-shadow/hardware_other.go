//go:build !linux

package main

// Non-Linux (dev/test, e.g. Windows) fallbacks. CPU temperature and system
// uptime are only available on Linux/Raspberry Pi; disk and memory fall back to
// the cross-platform process-level stats.

func readCPUTempC() *float64 { return nil }

func readUptimeSeconds() *float64 { return nil }

func readDiskInfo(dataDir string) response { return diskFallback(dataDir) }

func readMemoryInfo() response { return processMemoryInfo() }
