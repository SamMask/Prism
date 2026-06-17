//go:build windows

package main

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestDesktopPortableConfigResolvesLocalPortableAndCustom(t *testing.T) {
	exeDir := t.TempDir()
	localDir := filepath.Join(t.TempDir(), "LocalData")
	configPath := filepath.Join(exeDir, "PrismPortable.json")

	if err := persistDesktopPortableConfig(configPath, exeDir, desktopDataDirChoice{
		Mode:    "portable",
		DataDir: filepath.Join(exeDir, "PrismData"),
	}); err != nil {
		t.Fatal(err)
	}
	content, err := os.ReadFile(configPath)
	if err != nil {
		t.Fatal(err)
	}
	if !containsAll(string(content), []string{`"mode": "portable"`, `"data_dir": "PrismData"`}) {
		t.Fatalf("portable config should persist relative PrismData path: %s", content)
	}
	dir, ok := readDesktopPortableConfig(configPath, exeDir, localDir)
	if !ok {
		t.Fatal("portable config should resolve")
	}
	if dir != filepath.Join(exeDir, "PrismData") {
		t.Fatalf("portable dir mismatch: %s", dir)
	}

	if err := os.WriteFile(configPath, []byte(`{"version":1,"mode":"local","data_dir":""}`), 0o644); err != nil {
		t.Fatal(err)
	}
	dir, ok = readDesktopPortableConfig(configPath, exeDir, localDir)
	if !ok || dir != localDir {
		t.Fatalf("local config mismatch: ok=%v dir=%s", ok, dir)
	}

	customDir := filepath.Join(t.TempDir(), "CustomData")
	if err := os.WriteFile(configPath, []byte(`{"version":1,"mode":"custom","data_dir":"`+filepath.ToSlash(customDir)+`"}`), 0o644); err != nil {
		t.Fatal(err)
	}
	dir, ok = readDesktopPortableConfig(configPath, exeDir, localDir)
	if !ok || dir != filepath.Clean(customDir) {
		t.Fatalf("custom config mismatch: ok=%v dir=%s", ok, dir)
	}
}

func TestNormalizeDesktopDataDirChoice(t *testing.T) {
	localDir := filepath.Join(t.TempDir(), "LocalData")
	portableDir := filepath.Join(t.TempDir(), "PrismData")

	choice, err := normalizeDesktopDataDirChoice("local", "", localDir, portableDir)
	if err != nil || choice.Mode != "local" || choice.DataDir != localDir {
		t.Fatalf("local choice mismatch: %#v err=%v", choice, err)
	}

	choice, err = normalizeDesktopDataDirChoice("portable", "", localDir, portableDir)
	if err != nil || choice.Mode != "portable" || choice.DataDir != portableDir {
		t.Fatalf("portable choice mismatch: %#v err=%v", choice, err)
	}

	_, err = normalizeDesktopDataDirChoice("custom", "", localDir, portableDir)
	if err == nil {
		t.Fatal("empty custom path should fail")
	}
	_, err = normalizeDesktopDataDirChoice("unknown", "", localDir, portableDir)
	if err == nil {
		t.Fatal("unknown mode should fail")
	}
}

func containsAll(value string, needles []string) bool {
	for _, needle := range needles {
		if !strings.Contains(value, needle) {
			return false
		}
	}
	return true
}
