//go:build windows

package main

import (
	"context"
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"time"
	"unsafe"

	webview2 "github.com/jchv/go-webview2"
	"golang.org/x/sys/windows"
)

const (
	desktopTrayClassName = "PrismDesktopShellTrayWindow"
	desktopTrayID        = 1

	desktopCmdShow = 2001
	desktopCmdQuit = 2002

	desktopWMDestroy       = 0x0002
	desktopWMCommand       = 0x0111
	desktopWMUser          = 0x0400
	desktopWMTrayIcon      = desktopWMUser + 9
	desktopWMRButtonUp     = 0x0205
	desktopWMLButtonDblClk = 0x0203

	desktopSWShow        = 5
	desktopNIMAdd        = 0x00000000
	desktopNIMDelete     = 0x00000002
	desktopNIFMessage    = 0x00000001
	desktopNIFIcon       = 0x00000002
	desktopNIFTip        = 0x00000004
	desktopMFString      = 0x00000000
	desktopTPMRightClick = 0x00000002
	desktopIDIApp        = 32512
	desktopIDCArrow      = 32512
)

var (
	desktopUser32   = windows.NewLazySystemDLL("user32.dll")
	desktopShell32  = windows.NewLazySystemDLL("shell32.dll")
	desktopKernel32 = windows.NewLazySystemDLL("kernel32.dll")

	desktopGetModuleHandle = desktopKernel32.NewProc("GetModuleHandleW")
	desktopCreateMutex     = desktopKernel32.NewProc("CreateMutexW")
	desktopReleaseMutex    = desktopKernel32.NewProc("ReleaseMutex")

	desktopRegisterClassEx = desktopUser32.NewProc("RegisterClassExW")
	desktopCreateWindowEx  = desktopUser32.NewProc("CreateWindowExW")
	desktopDefWindowProc   = desktopUser32.NewProc("DefWindowProcW")
	desktopDestroyWindow   = desktopUser32.NewProc("DestroyWindow")
	desktopShowWindow      = desktopUser32.NewProc("ShowWindow")
	desktopSetForeground   = desktopUser32.NewProc("SetForegroundWindow")
	desktopLoadIcon        = desktopUser32.NewProc("LoadIconW")
	desktopLoadCursor      = desktopUser32.NewProc("LoadCursorW")
	desktopCreateMenu      = desktopUser32.NewProc("CreatePopupMenu")
	desktopAppendMenu      = desktopUser32.NewProc("AppendMenuW")
	desktopTrackPopupMenu  = desktopUser32.NewProc("TrackPopupMenu")
	desktopDestroyMenu     = desktopUser32.NewProc("DestroyMenu")
	desktopGetCursorPos    = desktopUser32.NewProc("GetCursorPos")
	desktopPostMessage     = desktopUser32.NewProc("PostMessageW")
	desktopFindWindow      = desktopUser32.NewProc("FindWindowW")

	desktopShellNotifyIcon = desktopShell32.NewProc("Shell_NotifyIconW")

	activeDesktopShell *desktopShellApp
)

type desktopShellOptions struct {
	title     string
	targetURL string
	logPath   string
	mutexName string
	debug     bool
	selfTest  bool
}

type desktopPoint struct {
	x int32
	y int32
}

type desktopWndClassEx struct {
	cbSize        uint32
	style         uint32
	lpfnWndProc   uintptr
	cbClsExtra    int32
	cbWndExtra    int32
	hInstance     windows.Handle
	hIcon         windows.Handle
	hCursor       windows.Handle
	hbrBackground windows.Handle
	lpszMenuName  *uint16
	lpszClassName *uint16
	hIconSm       windows.Handle
}

type desktopNotifyIconData struct {
	cbSize           uint32
	hwnd             windows.Handle
	uID              uint32
	uFlags           uint32
	uCallbackMessage uint32
	hIcon            windows.Handle
	szTip            [128]uint16
	dwState          uint32
	dwStateMask      uint32
	szInfo           [256]uint16
	uVersion         uint32
	szInfoTitle      [64]uint16
	dwInfoFlags      uint32
	guidItem         windows.GUID
	hBalloonIcon     windows.Handle
}

type desktopShellApp struct {
	webview    webview2.WebView
	mainHWND   windows.Handle
	trayHWND   windows.Handle
	icon       windows.Handle
	trayAdded  bool
	mutex      windows.Handle
	releaseLog func()
}

func runDesktopShellWebViewOnly(opts desktopShellOptions) error {
	releaseLog, err := configureDesktopLog("", opts.logPath)
	if err != nil {
		return err
	}
	opts.targetURL = strings.TrimSpace(opts.targetURL)
	if opts.targetURL == "" {
		opts.targetURL = "about:blank"
	}
	return runDesktopWebView(opts, releaseLog)
}

func runDesktopShellRuntime(cfg runtimeConfig, opts desktopShellOptions) error {
	releaseLog, err := configureDesktopLog(cfg.dataDir, opts.logPath)
	if err != nil {
		return err
	}
	srv, cleanup, err := newRuntimeServer(cfg)
	if err != nil {
		releaseLog()
		return err
	}
	defer cleanup()

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	serverErr := make(chan error, 1)
	go func() {
		log.Printf("Prism desktop runtime listening on %s", cfg.addr)
		serverErr <- srv.listenAndServe()
	}()
	if err := waitForDesktopHealth(ctx, cfg.addr); err != nil {
		shutdownDesktopServer(srv)
		releaseLog()
		return err
	}
	if strings.TrimSpace(opts.targetURL) == "" {
		opts.targetURL = "http://" + cfg.addr + "/"
	}
	err = runDesktopWebView(opts, func() {
		shutdownDesktopServer(srv)
		if serverErr != nil {
			select {
			case listenErr := <-serverErr:
				if listenErr != nil {
					log.Printf("desktop runtime server stopped with error: %v", listenErr)
				}
			case <-time.After(2 * time.Second):
				log.Printf("desktop runtime server shutdown timed out")
			}
		}
		releaseLog()
	})
	return err
}

func runDesktopShellSmoke(cfg runtimeConfig, opts desktopShellOptions) error {
	releaseLog, err := configureDesktopLog(cfg.dataDir, opts.logPath)
	if err != nil {
		return err
	}
	defer releaseLog()
	srv, cleanup, err := newRuntimeServer(cfg)
	if err != nil {
		return err
	}
	defer cleanup()

	serverErr := make(chan error, 1)
	go func() {
		log.Printf("Prism desktop smoke runtime listening on %s", cfg.addr)
		serverErr <- srv.listenAndServe()
	}()
	if err := waitForDesktopHealth(context.Background(), cfg.addr); err != nil {
		shutdownDesktopServer(srv)
		return err
	}
	shutdownDesktopServer(srv)
	select {
	case err := <-serverErr:
		return err
	case <-time.After(2 * time.Second):
		return errors.New("desktop shell smoke server shutdown timed out")
	}
}

func runDesktopWebView(opts desktopShellOptions, releaseLog func()) error {
	runtime.LockOSThread()
	defer runtime.UnlockOSThread()
	if opts.title == "" {
		opts.title = "Prism"
	}
	acquired, mutex, err := acquireDesktopInstance(opts.mutexName, opts.title)
	if err != nil {
		releaseLog()
		return err
	}
	if !acquired {
		releaseLog()
		return nil
	}

	app := &desktopShellApp{mutex: mutex, releaseLog: releaseLog}
	activeDesktopShell = app
	defer func() {
		activeDesktopShell = nil
		app.cleanup()
	}()

	w := webview2.NewWithOptions(webview2.WebViewOptions{
		Debug: opts.debug,
		WindowOptions: webview2.WindowOptions{
			Title:  opts.title,
			Width:  1100,
			Height: 760,
			Center: true,
		},
	})
	if w == nil {
		return errors.New("WebView2 initialization failed")
	}
	app.webview = w
	app.mainHWND = windows.Handle(uintptr(w.Window()))
	if err := app.createTrayWindow(opts.title); err != nil {
		w.Destroy()
		return err
	}
	if err := app.addTrayIcon(); err != nil {
		w.Destroy()
		return err
	}
	if opts.selfTest {
		go app.exerciseDesktopLoop()
	}
	if strings.TrimSpace(opts.targetURL) == "about:blank" {
		w.SetHtml(desktopPlaceholderHTML())
	} else {
		w.Navigate(opts.targetURL)
	}
	w.Run()
	return nil
}

func configureDesktopLog(dataDir, requested string) (func(), error) {
	logPath := strings.TrimSpace(requested)
	if logPath == "" && strings.TrimSpace(dataDir) != "" {
		logPath = filepath.Join(dataDir, "logs", "desktop-shell.log")
	}
	if logPath == "" {
		return func() {}, nil
	}
	if err := os.MkdirAll(filepath.Dir(logPath), 0o755); err != nil {
		return nil, err
	}
	file, err := os.OpenFile(logPath, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o644)
	if err != nil {
		return nil, err
	}
	previous := log.Writer()
	log.SetOutput(io.MultiWriter(previous, file))
	log.Printf("desktop shell log opened: %s", logPath)
	return func() {
		log.SetOutput(previous)
		_ = file.Close()
	}, nil
}

func waitForDesktopHealth(ctx context.Context, addr string) error {
	url := "http://" + addr + "/healthz"
	client := http.Client{Timeout: 500 * time.Millisecond}
	deadline := time.Now().Add(10 * time.Second)
	for time.Now().Before(deadline) {
		req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
		if err != nil {
			return err
		}
		resp, err := client.Do(req)
		if err == nil {
			_ = resp.Body.Close()
			if resp.StatusCode == http.StatusOK {
				return nil
			}
		}
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-time.After(100 * time.Millisecond):
		}
	}
	return fmt.Errorf("desktop runtime health check timed out at %s", url)
}

func shutdownDesktopServer(srv *server) {
	if srv == nil || srv.httpServer == nil {
		return
	}
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()
	if err := srv.httpServer.Shutdown(ctx); err != nil {
		log.Printf("desktop runtime shutdown failed: %v", err)
	}
}

func acquireDesktopInstance(name, title string) (bool, windows.Handle, error) {
	if strings.TrimSpace(name) == "" {
		return true, 0, nil
	}
	namePtr, err := windows.UTF16PtrFromString(name)
	if err != nil {
		return false, 0, err
	}
	h, _, callErr := desktopCreateMutex.Call(0, 1, uintptr(unsafe.Pointer(namePtr)))
	if h == 0 {
		return false, 0, fmt.Errorf("CreateMutexW failed: %w", callErr)
	}
	mutex := windows.Handle(h)
	if errors.Is(callErr, windows.ERROR_ALREADY_EXISTS) {
		showExistingDesktopWindow(title)
		_ = windows.CloseHandle(mutex)
		return false, 0, nil
	}
	return true, mutex, nil
}

func showExistingDesktopWindow(title string) {
	className := windows.StringToUTF16Ptr("webview")
	titlePtr := windows.StringToUTF16Ptr(title)
	hwnd, _, _ := desktopFindWindow.Call(uintptr(unsafe.Pointer(className)), uintptr(unsafe.Pointer(titlePtr)))
	if hwnd == 0 {
		return
	}
	desktopShowWindow.Call(hwnd, desktopSWShow)
	desktopSetForeground.Call(hwnd)
}

func (a *desktopShellApp) createTrayWindow(title string) error {
	className, err := windows.UTF16PtrFromString(desktopTrayClassName)
	if err != nil {
		return err
	}
	hInstance, err := desktopModuleHandle()
	if err != nil {
		return err
	}
	a.icon = desktopLoadDefaultIcon()
	wc := desktopWndClassEx{
		cbSize:        uint32(unsafe.Sizeof(desktopWndClassEx{})),
		lpfnWndProc:   windows.NewCallback(desktopTrayWindowProc),
		hInstance:     hInstance,
		hIcon:         a.icon,
		hCursor:       desktopLoadDefaultCursor(),
		lpszClassName: className,
		hIconSm:       a.icon,
	}
	if r, _, err := desktopRegisterClassEx.Call(uintptr(unsafe.Pointer(&wc))); r == 0 {
		return fmt.Errorf("RegisterClassExW failed: %w", err)
	}
	titlePtr, err := windows.UTF16PtrFromString(title + " Tray")
	if err != nil {
		return err
	}
	hwnd, _, err := desktopCreateWindowEx.Call(
		0,
		uintptr(unsafe.Pointer(className)),
		uintptr(unsafe.Pointer(titlePtr)),
		0,
		0,
		0,
		0,
		0,
		0,
		0,
		uintptr(hInstance),
		0,
	)
	if hwnd == 0 {
		return fmt.Errorf("CreateWindowExW tray helper failed: %w", err)
	}
	a.trayHWND = windows.Handle(hwnd)
	return nil
}

func (a *desktopShellApp) addTrayIcon() error {
	var data desktopNotifyIconData
	data.cbSize = uint32(unsafe.Sizeof(data))
	data.hwnd = a.trayHWND
	data.uID = desktopTrayID
	data.uFlags = desktopNIFMessage | desktopNIFIcon | desktopNIFTip
	data.uCallbackMessage = desktopWMTrayIcon
	data.hIcon = a.icon
	copy(data.szTip[:], windows.StringToUTF16("Prism"))
	if r, _, err := desktopShellNotifyIcon.Call(desktopNIMAdd, uintptr(unsafe.Pointer(&data))); r == 0 {
		return fmt.Errorf("Shell_NotifyIconW add failed: %w", err)
	}
	a.trayAdded = true
	return nil
}

func (a *desktopShellApp) deleteTrayIcon() {
	if !a.trayAdded {
		return
	}
	var data desktopNotifyIconData
	data.cbSize = uint32(unsafe.Sizeof(data))
	data.hwnd = a.trayHWND
	data.uID = desktopTrayID
	desktopShellNotifyIcon.Call(desktopNIMDelete, uintptr(unsafe.Pointer(&data)))
	a.trayAdded = false
}

func (a *desktopShellApp) showMainWindow() {
	if a.mainHWND == 0 {
		return
	}
	desktopShowWindow.Call(uintptr(a.mainHWND), desktopSWShow)
	desktopSetForeground.Call(uintptr(a.mainHWND))
}

func (a *desktopShellApp) quit() {
	if a.webview != nil {
		a.webview.Dispatch(func() {
			a.webview.Destroy()
			a.webview.Terminate()
		})
	}
}

func (a *desktopShellApp) showTrayMenu() {
	menu, _, _ := desktopCreateMenu.Call()
	if menu == 0 {
		return
	}
	defer desktopDestroyMenu.Call(menu)

	showText := windows.StringToUTF16Ptr("Show")
	quitText := windows.StringToUTF16Ptr("Quit")
	desktopAppendMenu.Call(menu, desktopMFString, desktopCmdShow, uintptr(unsafe.Pointer(showText)))
	desktopAppendMenu.Call(menu, desktopMFString, desktopCmdQuit, uintptr(unsafe.Pointer(quitText)))

	var pt desktopPoint
	if r, _, _ := desktopGetCursorPos.Call(uintptr(unsafe.Pointer(&pt))); r == 0 {
		return
	}
	desktopSetForeground.Call(uintptr(a.trayHWND))
	desktopTrackPopupMenu.Call(menu, desktopTPMRightClick, uintptr(pt.x), uintptr(pt.y), 0, uintptr(a.trayHWND), 0)
}

func (a *desktopShellApp) exerciseDesktopLoop() {
	time.Sleep(300 * time.Millisecond)
	desktopPostMessage.Call(uintptr(a.trayHWND), desktopWMCommand, desktopCmdShow, 0)
	time.Sleep(300 * time.Millisecond)
	desktopPostMessage.Call(uintptr(a.trayHWND), desktopWMCommand, desktopCmdQuit, 0)
}

func (a *desktopShellApp) cleanup() {
	a.deleteTrayIcon()
	if a.trayHWND != 0 {
		desktopDestroyWindow.Call(uintptr(a.trayHWND))
		a.trayHWND = 0
	}
	if a.mutex != 0 {
		desktopReleaseMutex.Call(uintptr(a.mutex))
		_ = windows.CloseHandle(a.mutex)
		a.mutex = 0
	}
	if a.releaseLog != nil {
		a.releaseLog()
		a.releaseLog = nil
	}
}

func desktopTrayWindowProc(hwnd uintptr, msg uint32, wParam uintptr, lParam uintptr) uintptr {
	app := activeDesktopShell
	switch msg {
	case desktopWMCommand:
		switch uint16(wParam & 0xffff) {
		case desktopCmdShow:
			if app != nil {
				app.showMainWindow()
			}
			return 0
		case desktopCmdQuit:
			if app != nil {
				app.quit()
			}
			return 0
		}
	case desktopWMTrayIcon:
		switch uint32(lParam) {
		case desktopWMRButtonUp:
			if app != nil {
				app.showTrayMenu()
			}
			return 0
		case desktopWMLButtonDblClk:
			if app != nil {
				app.showMainWindow()
			}
			return 0
		}
	case desktopWMDestroy:
		return 0
	}
	r, _, _ := desktopDefWindowProc.Call(hwnd, uintptr(msg), wParam, lParam)
	return r
}

func desktopModuleHandle() (windows.Handle, error) {
	h, _, err := desktopGetModuleHandle.Call(0)
	if h == 0 {
		return 0, fmt.Errorf("GetModuleHandleW failed: %w", err)
	}
	return windows.Handle(h), nil
}

func desktopLoadDefaultIcon() windows.Handle {
	h, _, _ := desktopLoadIcon.Call(0, desktopIDIApp)
	return windows.Handle(h)
}

func desktopLoadDefaultCursor() windows.Handle {
	h, _, _ := desktopLoadCursor.Call(0, desktopIDCArrow)
	return windows.Handle(h)
}

func desktopPlaceholderHTML() string {
	return `<!doctype html><html><head><meta charset="utf-8"><title>Prism</title></head><body style="font-family:Segoe UI,Arial,sans-serif;margin:32px;color:#1f2937"><h1>Prism Desktop Shell</h1><p>WebView2 is running in the Windows desktop shell.</p></body></html>`
}
