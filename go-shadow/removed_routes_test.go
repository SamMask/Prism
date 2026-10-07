package main

import (
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// PRISM-OPT-42 (2026-10-07): these routes were removed. With every route class
// enabled they must fall through to the /api/ JSON 404, not a handler or the SPA,
// and must not write their old marker files into the data dir.
func TestRemovedOPT42RoutesReturnAPINotFound(t *testing.T) {
	dataDir := t.TempDir()
	cfg, err := resolveRuntimeConfig("127.0.0.1:0", "prism_opt42_test.db", dataDir,
		true, true, true, true, true, true,
		true, true, true, true, true, true, true)
	if err != nil {
		t.Fatal(err)
	}
	srv, cleanup, err := newRuntimeServer(cfg)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(cleanup)
	e := &inlineEnv{t: t, srv: srv, dataDir: cfg.dataDir}
	cases := []struct{ method, target, body string }{
		{http.MethodGet, "/api/system/port-config", ""},
		{http.MethodPost, "/api/system/port-config", `{"preferred_port":5678}`},
		{http.MethodGet, "/api/system/startup-preference", ""},
		{http.MethodPost, "/api/system/startup-preference", `{"auto_open_browser":false}`},
		{http.MethodGet, "/api/system/check-update", ""},
		{http.MethodPost, "/api/upload/extract-prompt", `{"image_path":"/static/uploads/提示詞.png"}`},
	}
	for _, c := range cases {
		rec := e.do(c.method, c.target, c.body)
		if rec.Code != http.StatusNotFound {
			t.Errorf("%s %s: expected 404, got %d body=%s", c.method, c.target, rec.Code, rec.Body.String())
			continue
		}
		if ct := rec.Header().Get("Content-Type"); !strings.Contains(ct, "application/json") {
			t.Errorf("%s %s: expected JSON 404, got content-type %q", c.method, c.target, ct)
		}
		if !strings.Contains(rec.Body.String(), "API route not found") {
			t.Errorf("%s %s: expected API route not found, got %s", c.method, c.target, rec.Body.String())
		}
	}
	for _, name := range []string{".port_config", ".auto_open_yes", ".auto_open_no"} {
		if _, err := os.Stat(filepath.Join(e.dataDir, name)); !os.IsNotExist(err) {
			t.Errorf("removed route must not write %s (stat err=%v)", name, err)
		}
	}
}
