package main

import (
	"bytes"
	"io"
	"net"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
	"time"
)

// PRISM-OPT-37: user/log-visible text must not carry migration-era wording.
func TestRuntimeOutputHasNoMigrationEraWording(t *testing.T) {
	if testing.Short() {
		t.Skip("builds the runtime binary")
	}
	dir := t.TempDir()
	bin := filepath.Join(dir, "prism-test-runtime")
	if runtime.GOOS == "windows" {
		bin += ".exe"
	}
	if out, err := exec.Command("go", "build", "-o", bin, ".").CombinedOutput(); err != nil {
		t.Fatalf("go build: %v\n%s", err, out)
	}

	banned := []string{"candidate", "proof", "parity", "python"}
	assertClean := func(label, text string) {
		t.Helper()
		lower := strings.ToLower(text)
		for _, word := range banned {
			if strings.Contains(lower, word) {
				t.Errorf("%s contains %q:\n%s", label, word, text)
			}
		}
	}

	help, _ := exec.Command(bin, "-h").CombinedOutput()
	if len(help) == 0 {
		t.Fatal("expected --help output")
	}
	assertClean("--help", string(help))

	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	addr := ln.Addr().String()
	ln.Close()
	dataDir := filepath.Join(dir, "data")
	if err := os.MkdirAll(dataDir, 0o755); err != nil {
		t.Fatal(err)
	}
	var logs bytes.Buffer
	cmd := exec.Command(bin, "--addr", addr, "--data-dir", dataDir,
		"--db", filepath.Join(dataDir, "neutral.db"), "--enable-attachment-text-read")
	cmd.Stdout, cmd.Stderr = &logs, &logs
	if err := cmd.Start(); err != nil {
		t.Fatal(err)
	}
	defer func() { _ = cmd.Process.Kill(); _ = cmd.Wait() }()

	get := func(path string) (int, string) {
		resp, err := http.Get("http://" + addr + path)
		if err != nil {
			return 0, err.Error()
		}
		defer resp.Body.Close()
		b, _ := io.ReadAll(resp.Body)
		return resp.StatusCode, string(b)
	}
	deadline := time.Now().Add(20 * time.Second)
	for {
		if code, body := get("/healthz"); code == 200 {
			assertClean("/healthz", body)
			break
		}
		if time.Now().After(deadline) {
			t.Fatalf("runtime did not start:\n%s", logs.String())
		}
		time.Sleep(100 * time.Millisecond)
	}
	code, body := get("/api/attachments/1?raw=true")
	if code != http.StatusMethodNotAllowed {
		t.Fatalf("raw read with text-read only: status %d body %s", code, body)
	}
	assertClean("attachment raw error", body)
	if !strings.Contains(logs.String(), "listening on "+addr) {
		t.Fatalf("missing listening log:\n%s", logs.String())
	}
	// Data-dir paths in the logs may legitimately contain test names; check the line only.
	for _, line := range strings.Split(logs.String(), "\n") {
		if strings.Contains(line, "listening on") {
			assertClean("startup log", line)
		}
	}
}
