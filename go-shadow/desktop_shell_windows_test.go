//go:build windows

package main

import (
	"os"
	"path/filepath"
	"testing"
)

func TestResolveDesktopDataDirUsesExecutableNeighborPrismData(t *testing.T) {
	exe, err := os.Executable()
	if err != nil {
		t.Fatal(err)
	}
	expected := filepath.Join(filepath.Dir(exe), "PrismData")

	actual, err := resolveDesktopDataDir(false)
	if err != nil {
		t.Fatal(err)
	}
	if actual != expected {
		t.Fatalf("desktop data dir mismatch: got %q want %q", actual, expected)
	}
}
