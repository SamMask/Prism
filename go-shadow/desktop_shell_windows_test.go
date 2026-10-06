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
