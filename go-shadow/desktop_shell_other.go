//go:build !windows

package main

import "errors"

type desktopShellOptions struct {
	title     string
	targetURL string
	logPath   string
	mutexName string
	debug     bool
	selfTest  bool
}

func runDesktopShellWebViewOnly(opts desktopShellOptions) error {
	return errors.New("desktop shell is Windows-only")
}

func runDesktopShellRuntime(cfg runtimeConfig, opts desktopShellOptions) error {
	return errors.New("desktop shell is Windows-only")
}

func runDesktopShellSmoke(cfg runtimeConfig, opts desktopShellOptions) error {
	return errors.New("desktop shell smoke is Windows-only")
}

func resolveDesktopDataDir(smoke bool) (string, error) {
	return "", errors.New("desktop shell default data directory is Windows-only")
}
