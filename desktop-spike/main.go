//go:build windows

package main

import (
	"flag"
	"fmt"
	"runtime"
	"time"
	"unsafe"

	"golang.org/x/sys/windows"
)

const (
	windowClassName = "PrismDesktopSpikeWindow"
	defaultTitle    = "Prism Desktop Shell Spike"
	trayID          = 1

	cmdShow = 1001
	cmdQuit = 1002

	wmDestroy       = 0x0002
	wmClose         = 0x0010
	wmCommand       = 0x0111
	wmUser          = 0x0400
	wmTrayIcon      = wmUser + 1
	wmRButtonUp     = 0x0205
	wmLButtonDblClk = 0x0203

	wsOverlappedWindow = 0x00CF0000
	wsVisible          = 0x10000000
	cwUseDefault       = ^uintptr(0x7fffffff)

	swShow = 5

	nimAdd    = 0x00000000
	nimDelete = 0x00000002

	nifMessage = 0x00000001
	nifIcon    = 0x00000002
	nifTip     = 0x00000004

	mfString       = 0x00000000
	tpmRightButton = 0x00000002

	idiApplication = 32512
	idcArrow       = 32512
)

var (
	user32   = windows.NewLazySystemDLL("user32.dll")
	shell32  = windows.NewLazySystemDLL("shell32.dll")
	kernel32 = windows.NewLazySystemDLL("kernel32.dll")

	procGetModuleHandle = kernel32.NewProc("GetModuleHandleW")
	procRegisterClassEx = user32.NewProc("RegisterClassExW")
	procCreateWindowEx  = user32.NewProc("CreateWindowExW")
	procDefWindowProc   = user32.NewProc("DefWindowProcW")
	procDestroyWindow   = user32.NewProc("DestroyWindow")
	procGetMessage      = user32.NewProc("GetMessageW")
	procTranslateMsg    = user32.NewProc("TranslateMessage")
	procDispatchMsg     = user32.NewProc("DispatchMessageW")
	procPostQuitMessage = user32.NewProc("PostQuitMessage")
	procShowWindow      = user32.NewProc("ShowWindow")
	procSetForeground   = user32.NewProc("SetForegroundWindow")
	procLoadIcon        = user32.NewProc("LoadIconW")
	procLoadCursor      = user32.NewProc("LoadCursorW")
	procCreateMenu      = user32.NewProc("CreatePopupMenu")
	procAppendMenu      = user32.NewProc("AppendMenuW")
	procTrackPopupMenu  = user32.NewProc("TrackPopupMenu")
	procDestroyMenu     = user32.NewProc("DestroyMenu")
	procGetCursorPos    = user32.NewProc("GetCursorPos")
	procPostMessage     = user32.NewProc("PostMessageW")

	procShellNotifyIcon = shell32.NewProc("Shell_NotifyIconW")

	activeApp *desktopApp
)

type point struct {
	x int32
	y int32
}

type msg struct {
	hwnd    windows.Handle
	message uint32
	wParam  uintptr
	lParam  uintptr
	time    uint32
	pt      point
}

type wndClassEx struct {
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

type notifyIconData struct {
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

type desktopApp struct {
	hwnd      windows.Handle
	hIcon     windows.Handle
	trayAdded bool
	selfTest  bool
}

func main() {
	selfTest := flag.Bool("self-test", false, "run a bounded hidden-window message-loop self-test")
	hideWindow := flag.Bool("hide-window", false, "start with the window hidden")
	title := flag.String("title", defaultTitle, "window title")
	flag.Parse()

	if err := runDesktopSpike(*title, !*hideWindow && !*selfTest, *selfTest); err != nil {
		fmt.Printf("desktop spike failed: %v\n", err)
		windows.Exit(1)
	}
}

func runDesktopSpike(title string, visible bool, selfTest bool) error {
	runtime.LockOSThread()
	defer runtime.UnlockOSThread()

	app := &desktopApp{selfTest: selfTest}
	activeApp = app
	defer func() { activeApp = nil }()

	if err := app.createWindow(title, visible); err != nil {
		return err
	}
	if err := app.addTrayIcon(); err != nil {
		_ = app.destroyWindow()
		return err
	}
	if selfTest {
		go app.exerciseLoop()
	}
	return app.messageLoop()
}

func (a *desktopApp) createWindow(title string, visible bool) error {
	className, err := windows.UTF16PtrFromString(windowClassName)
	if err != nil {
		return err
	}
	titlePtr, err := windows.UTF16PtrFromString(title)
	if err != nil {
		return err
	}

	hInstance, err := getModuleHandle()
	if err != nil {
		return err
	}
	a.hIcon = loadIcon()
	cursor := loadCursor()
	wndProc := windows.NewCallback(windowProc)

	wc := wndClassEx{
		cbSize:        uint32(unsafe.Sizeof(wndClassEx{})),
		lpfnWndProc:   wndProc,
		hInstance:     hInstance,
		hIcon:         a.hIcon,
		hCursor:       cursor,
		lpszClassName: className,
		hIconSm:       a.hIcon,
	}
	if r, _, err := procRegisterClassEx.Call(uintptr(unsafe.Pointer(&wc))); r == 0 {
		return fmt.Errorf("RegisterClassExW failed: %w", err)
	}

	style := uintptr(wsOverlappedWindow)
	if visible {
		style |= wsVisible
	}
	hwnd, _, err := procCreateWindowEx.Call(
		0,
		uintptr(unsafe.Pointer(className)),
		uintptr(unsafe.Pointer(titlePtr)),
		style,
		cwUseDefault,
		cwUseDefault,
		720,
		480,
		0,
		0,
		uintptr(hInstance),
		0,
	)
	if hwnd == 0 {
		return fmt.Errorf("CreateWindowExW failed: %w", err)
	}
	a.hwnd = windows.Handle(hwnd)
	return nil
}

func (a *desktopApp) addTrayIcon() error {
	var data notifyIconData
	data.cbSize = uint32(unsafe.Sizeof(data))
	data.hwnd = a.hwnd
	data.uID = trayID
	data.uFlags = nifMessage | nifIcon | nifTip
	data.uCallbackMessage = wmTrayIcon
	data.hIcon = a.hIcon
	copy(data.szTip[:], windows.StringToUTF16("Prism Desktop Spike"))

	if r, _, err := procShellNotifyIcon.Call(nimAdd, uintptr(unsafe.Pointer(&data))); r == 0 {
		return fmt.Errorf("Shell_NotifyIconW add failed: %w", err)
	}
	a.trayAdded = true
	return nil
}

func (a *desktopApp) deleteTrayIcon() {
	if !a.trayAdded {
		return
	}
	var data notifyIconData
	data.cbSize = uint32(unsafe.Sizeof(data))
	data.hwnd = a.hwnd
	data.uID = trayID
	procShellNotifyIcon.Call(nimDelete, uintptr(unsafe.Pointer(&data)))
	a.trayAdded = false
}

func (a *desktopApp) messageLoop() error {
	var m msg
	for {
		r, _, err := procGetMessage.Call(uintptr(unsafe.Pointer(&m)), 0, 0, 0)
		switch int32(r) {
		case -1:
			return fmt.Errorf("GetMessageW failed: %w", err)
		case 0:
			return nil
		default:
			procTranslateMsg.Call(uintptr(unsafe.Pointer(&m)))
			procDispatchMsg.Call(uintptr(unsafe.Pointer(&m)))
		}
	}
}

func (a *desktopApp) exerciseLoop() {
	time.Sleep(150 * time.Millisecond)
	postMessage(a.hwnd, wmCommand, cmdShow, 0)
	time.Sleep(150 * time.Millisecond)
	postMessage(a.hwnd, wmCommand, cmdQuit, 0)
}

func (a *desktopApp) showWindow() {
	procShowWindow.Call(uintptr(a.hwnd), swShow)
	procSetForeground.Call(uintptr(a.hwnd))
}

func (a *desktopApp) showTrayMenu() {
	menu, _, _ := procCreateMenu.Call()
	if menu == 0 {
		return
	}
	defer procDestroyMenu.Call(menu)

	showText := windows.StringToUTF16Ptr("Show")
	quitText := windows.StringToUTF16Ptr("Quit")
	procAppendMenu.Call(menu, mfString, cmdShow, uintptr(unsafe.Pointer(showText)))
	procAppendMenu.Call(menu, mfString, cmdQuit, uintptr(unsafe.Pointer(quitText)))

	var pt point
	if r, _, _ := procGetCursorPos.Call(uintptr(unsafe.Pointer(&pt))); r == 0 {
		return
	}
	procSetForeground.Call(uintptr(a.hwnd))
	procTrackPopupMenu.Call(menu, tpmRightButton, uintptr(pt.x), uintptr(pt.y), 0, uintptr(a.hwnd), 0)
}

func (a *desktopApp) destroyWindow() error {
	if a.hwnd == 0 {
		return nil
	}
	if r, _, err := procDestroyWindow.Call(uintptr(a.hwnd)); r == 0 {
		return fmt.Errorf("DestroyWindow failed: %w", err)
	}
	return nil
}

func windowProc(hwnd uintptr, msg uint32, wParam uintptr, lParam uintptr) uintptr {
	app := activeApp
	switch msg {
	case wmCommand:
		switch uint16(wParam & 0xffff) {
		case cmdShow:
			if app != nil {
				app.showWindow()
			}
			return 0
		case cmdQuit:
			if app != nil {
				_ = app.destroyWindow()
			}
			return 0
		}
	case wmTrayIcon:
		switch uint32(lParam) {
		case wmRButtonUp:
			if app != nil {
				app.showTrayMenu()
			}
			return 0
		case wmLButtonDblClk:
			if app != nil {
				app.showWindow()
			}
			return 0
		}
	case wmClose:
		if app != nil {
			_ = app.destroyWindow()
		}
		return 0
	case wmDestroy:
		if app != nil {
			app.deleteTrayIcon()
		}
		procPostQuitMessage.Call(0)
		return 0
	}
	r, _, _ := procDefWindowProc.Call(hwnd, uintptr(msg), wParam, lParam)
	return r
}

func loadIcon() windows.Handle {
	h, _, _ := procLoadIcon.Call(0, idiApplication)
	return windows.Handle(h)
}

func getModuleHandle() (windows.Handle, error) {
	h, _, err := procGetModuleHandle.Call(0)
	if h == 0 {
		return 0, fmt.Errorf("GetModuleHandleW failed: %w", err)
	}
	return windows.Handle(h), nil
}

func loadCursor() windows.Handle {
	h, _, _ := procLoadCursor.Call(0, idcArrow)
	return windows.Handle(h)
}

func postMessage(hwnd windows.Handle, message uint32, wParam uintptr, lParam uintptr) {
	procPostMessage.Call(uintptr(hwnd), uintptr(message), wParam, lParam)
}
