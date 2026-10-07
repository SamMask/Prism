//go:build windows

package main

import (
	"errors"
	"log"
	"os"
	"path/filepath"
	"strings"
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

func TestDesktopShouldConfirmClose(t *testing.T) {
	const unsaved = "您有未保存的變更。確定要放棄變更並關閉嗎？"
	cases := []struct {
		name    string
		msg     uint32
		wParam  uintptr
		message string
		want    bool
	}{
		{"user close with unsaved changes", desktopWMSysCommand, desktopSCClose, unsaved, true},
		{"user close without unsaved changes", desktopWMSysCommand, desktopSCClose, "", false},
		{"user close with low wParam bits", desktopWMSysCommand, 0xF063, unsaved, true},
		{"tray quit or library destroy stays unguarded", 0x0010, 0, unsaved, false},
		{"minimize is not a close", desktopWMSysCommand, 0xF020, unsaved, false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := desktopShouldConfirmClose(tc.msg, tc.wParam, tc.message); got != tc.want {
				t.Fatalf("desktopShouldConfirmClose(%#x, %#x, %q) = %v, want %v", tc.msg, tc.wParam, tc.message, got, tc.want)
			}
		})
	}
}

func TestDesktopUnsavedMessageRoundTrip(t *testing.T) {
	app := &desktopShellApp{}
	if got := app.currentUnsavedMessage(); got != "" {
		t.Fatalf("fresh app unsaved message = %q, want empty", got)
	}
	const unsaved = "未儲存的變更：筆記草稿"
	app.setUnsavedMessage(unsaved)
	if got := app.currentUnsavedMessage(); got != unsaved {
		t.Fatalf("unsaved message = %q, want %q", got, unsaved)
	}
	app.setUnsavedMessage("")
	if got := app.currentUnsavedMessage(); got != "" {
		t.Fatalf("cleared unsaved message = %q, want empty", got)
	}
}

type failingWriter struct{}

func (failingWriter) Write([]byte) (int, error) { return 0, errors.New("invalid handle") }

// A GUI build has no usable stderr: the file must still receive the log (PRISM-OPT-72).
func TestConfigureDesktopLogWritesFileWhenStderrFails(t *testing.T) {
	prevOut, prevFlags := log.Writer(), log.Flags()
	defer func() { log.SetOutput(prevOut); log.SetFlags(prevFlags) }()
	log.SetOutput(failingWriter{})

	logPath := filepath.Join(t.TempDir(), "logs", "desktop-shell.log")
	release, err := configureDesktopLog("", logPath)
	if err != nil {
		t.Fatal(err)
	}
	log.Printf("listening on 127.0.0.1:0 資料夾")
	release()

	data, err := os.ReadFile(logPath)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(data), "listening on") || !strings.Contains(string(data), "資料夾") {
		t.Fatalf("log file missing messages: %q", data)
	}
}
