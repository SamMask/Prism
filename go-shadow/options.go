package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
	"time"
)

func (s *server) handleServerVersion(w http.ResponseWriter, r *http.Request) {
	if !requireGET(w, r) || !requireLocalhostRequest(w, r) || !s.requireServerSystem(w, r) {
		return
	}
	writeJSON(w, http.StatusOK, response{
		"status": "success",
		"data": response{
			"version":   prismVersion(),
			"changelog": []response{},
			"is_frozen": false,
			"v2_mode":   envBool("PRISM_V2"),
			"platform":  runtime.GOOS,
			"go_runtime": response{
				"api_surface": s.apiSurface(),
				"query_only":  s.runtime.sqliteQueryOnly,
			},
		},
	})
}

func (s *server) handlePromptOptions(w http.ResponseWriter, r *http.Request) {
	if !requireGET(w, r) || !s.requireServerSystem(w, r) {
		return
	}
	config, err := s.loadOptionConfig("prompt_options.json")
	if err != nil {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": config})
}

func (s *server) handlePromptOptionCategory(w http.ResponseWriter, r *http.Request) {
	if !s.requireServerSystem(w, r) {
		return
	}
	parts := routeParts(strings.TrimPrefix(r.URL.Path, "/api/prompt-options/category/"))
	if len(parts) == 1 && r.Method == http.MethodPost {
		s.addPromptOption(w, r, parts[0])
		return
	}
	if len(parts) == 2 && r.Method == http.MethodPut {
		s.updatePromptOption(w, r, parts[0], parts[1])
		return
	}
	if len(parts) == 2 && r.Method == http.MethodDelete {
		s.deletePromptOption(w, r, parts[0], parts[1])
		return
	}
	writeError(w, http.StatusMethodNotAllowed, "method not allowed")
}

func (s *server) handlePromptOptionTemplate(w http.ResponseWriter, r *http.Request) {
	if !requireMethod(w, r, http.MethodPost) || !s.requireServerSystem(w, r) {
		return
	}
	payload, ok := decodeJSONObject(w, r, "Request body is required")
	if !ok {
		return
	}
	name := strings.TrimSpace(stringField(payload, "name"))
	if name == "" {
		writeError(w, http.StatusBadRequest, "name is required")
		return
	}
	config, err := s.loadOptionConfig("prompt_options.json")
	if err != nil {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}
	templateID := strings.TrimSpace(stringField(payload, "id"))
	if templateID == "" {
		templateID = strings.ReplaceAll(strings.ReplaceAll(strings.ToLower(name), " ", "-"), ":", "")
	}
	template := map[string]any{
		"id":       templateID,
		"name":     name,
		"preset":   payload["preset"],
		"isCustom": true,
	}
	if template["preset"] == nil {
		template["preset"] = map[string]any{}
	}
	templates, _ := config["quickTemplates"].([]any)
	action := "created"
	index := len(templates)
	for i, item := range templates {
		if obj, ok := item.(map[string]any); ok && stringValue(obj["id"]) == templateID {
			templates[i] = template
			action = "updated"
			index = i
			break
		}
	}
	if action == "created" {
		templates = append(templates, template)
	}
	config["quickTemplates"] = templates
	status := http.StatusCreated
	if action == "updated" {
		status = http.StatusOK
	}
	if err := s.saveOptionConfig("prompt_options.json", config); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, status, response{"status": "success", "data": response{"action": action, "template": template, "index": index}})
}

func (s *server) handlePromptOptionTemplateDelete(w http.ResponseWriter, r *http.Request) {
	if !requireMethod(w, r, http.MethodDelete) || !s.requireServerSystem(w, r) {
		return
	}
	parts := routeParts(strings.TrimPrefix(r.URL.Path, "/api/prompt-options/template/"))
	if len(parts) != 1 {
		writeError(w, http.StatusNotFound, "Template not found")
		return
	}
	templateID := parts[0]
	config, err := s.loadOptionConfig("prompt_options.json")
	if err != nil {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}
	templates, _ := config["quickTemplates"].([]any)
	for i, item := range templates {
		if obj, ok := item.(map[string]any); ok && stringValue(obj["id"]) == templateID {
			deleted := item
			config["quickTemplates"] = append(templates[:i], templates[i+1:]...)
			if err := s.saveOptionConfig("prompt_options.json", config); err != nil {
				writeError(w, http.StatusInternalServerError, err.Error())
				return
			}
			writeJSON(w, http.StatusOK, response{"status": "success", "data": response{"deleted": deleted}})
			return
		}
	}
	writeError(w, http.StatusNotFound, fmt.Sprintf("Template %q not found", templateID))
}

func (s *server) handleWizardOptions(w http.ResponseWriter, r *http.Request) {
	if !requireGET(w, r) || !s.requireServerSystem(w, r) {
		return
	}
	config, err := s.loadOptionConfig("wizard_options.json")
	if err != nil {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": config})
}

func (s *server) handleWizardOptionDimension(w http.ResponseWriter, r *http.Request) {
	if !s.requireServerSystem(w, r) {
		return
	}
	parts := routeParts(strings.TrimPrefix(r.URL.Path, "/api/wizard-options/dimension/"))
	if len(parts) == 1 && r.Method == http.MethodPost {
		s.addWizardOption(w, r, parts[0])
		return
	}
	if len(parts) == 2 && r.Method == http.MethodDelete {
		s.deleteWizardOption(w, r, parts[0], parts[1])
		return
	}
	writeError(w, http.StatusMethodNotAllowed, "method not allowed")
}

func routeParts(raw string) []string {
	raw = strings.Trim(raw, "/")
	if raw == "" {
		return nil
	}
	parts := strings.Split(raw, "/")
	out := []string{}
	for _, part := range parts {
		decoded, err := url.PathUnescape(part)
		if err != nil || decoded == "" {
			return nil
		}
		out = append(out, decoded)
	}
	return out
}

func (s *server) optionConfigPath(filename string) (string, error) {
	if filename != "prompt_options.json" && filename != "wizard_options.json" {
		return "", fmt.Errorf("unsupported config file %q", filename)
	}
	target := filepath.Join(s.runtime.configDir, filename)
	if !isSubpath(target, s.runtime.configDir) {
		return "", fmt.Errorf("config path escapes config dir: %s", filename)
	}
	return target, nil
}

func (s *server) loadOptionConfig(filename string) (map[string]any, error) {
	target, err := s.optionConfigPath(filename)
	if err != nil {
		return nil, err
	}
	if !fileExists(target) {
		if err := s.seedOptionConfig(filename, target); err != nil {
			return nil, err
		}
	}
	file, err := os.Open(target)
	if err != nil {
		return nil, err
	}
	defer file.Close()
	var config map[string]any
	if err := json.NewDecoder(file).Decode(&config); err != nil {
		return nil, err
	}
	if config == nil {
		return nil, errors.New("configuration file is empty")
	}
	return config, nil
}

func (s *server) seedOptionConfig(filename, target string) error {
	sourceCandidates := []string{filepath.Join(s.runtime.dataDir, "static", "config", filename)}
	if exe, err := os.Executable(); err == nil {
		exeDir := filepath.Dir(exe)
		sourceCandidates = append(sourceCandidates,
			filepath.Join(exeDir, "static", "config", filename),
			filepath.Join(exeDir, "config", filename),
		)
	}
	if cwd, err := os.Getwd(); err == nil {
		sourceCandidates = append(sourceCandidates,
			filepath.Join(cwd, "static", "config", filename),
			filepath.Join(cwd, "..", "static", "config", filename),
		)
	}
	for _, source := range sourceCandidates {
		if !fileExists(source) {
			continue
		}
		if err := os.MkdirAll(filepath.Dir(target), 0755); err != nil {
			return err
		}
		return copyFileExclusive(source, target)
	}
	return fmt.Errorf("configuration file not found: %s", filename)
}

func (s *server) saveOptionConfig(filename string, config map[string]any) error {
	target, err := s.optionConfigPath(filename)
	if err != nil {
		return err
	}
	config["lastUpdated"] = time.Now().Format("2006-01-02")
	return writeIndentedJSON(target, config)
}

func writeIndentedJSON(target string, payload any) error {
	if err := os.MkdirAll(filepath.Dir(target), 0755); err != nil {
		return err
	}
	content, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		return err
	}
	content = append(content, '\n')
	tmp := target + ".tmp"
	if err := os.WriteFile(tmp, content, 0644); err != nil {
		return err
	}
	_ = os.Remove(target)
	return os.Rename(tmp, target)
}

func (s *server) promptCategory(config map[string]any, categoryKey string) (map[string]any, []any, error) {
	categories, ok := config["categories"].(map[string]any)
	if !ok {
		return nil, nil, errors.New("categories not found")
	}
	category, ok := categories[categoryKey].(map[string]any)
	if !ok {
		return nil, nil, fmt.Errorf("Category %q not found", categoryKey)
	}
	options, _ := category["options"].([]any)
	return category, options, nil
}

func (s *server) addPromptOption(w http.ResponseWriter, r *http.Request, categoryKey string) {
	payload, ok := decodeJSONObject(w, r, "Request body is required")
	if !ok {
		return
	}
	config, err := s.loadOptionConfig("prompt_options.json")
	if err != nil {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}
	category, options, err := s.promptCategory(config, categoryKey)
	if err != nil {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}
	newOption, err := promptOptionFromPayload(payload, false)
	if err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	if text, ok := newOption.(string); ok {
		for _, option := range options {
			if existing, ok := option.(string); ok && existing == text {
				writeError(w, http.StatusBadRequest, "Option already exists")
				return
			}
		}
	}
	options = append(options, newOption)
	category["options"] = options
	if err := s.saveOptionConfig("prompt_options.json", config); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusCreated, response{"status": "success", "data": response{"index": len(options) - 1, "option": newOption}})
}

func (s *server) updatePromptOption(w http.ResponseWriter, r *http.Request, categoryKey, indexText string) {
	index, err := strconv.Atoi(indexText)
	if err != nil {
		writeError(w, http.StatusBadRequest, "Invalid index")
		return
	}
	payload, ok := decodeJSONObject(w, r, "Request body is required")
	if !ok {
		return
	}
	config, err := s.loadOptionConfig("prompt_options.json")
	if err != nil {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}
	category, options, err := s.promptCategory(config, categoryKey)
	if err != nil {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}
	if index < 0 || index >= len(options) {
		writeError(w, http.StatusBadRequest, "Index out of range")
		return
	}
	current := map[string]any{}
	if existing, ok := options[index].(map[string]any); ok {
		current = existing
	}
	newOption, err := promptOptionFromPayloadWithCurrent(payload, current)
	if err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	options[index] = newOption
	category["options"] = options
	if err := s.saveOptionConfig("prompt_options.json", config); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{"option": newOption}})
}

func (s *server) deletePromptOption(w http.ResponseWriter, r *http.Request, categoryKey, indexText string) {
	index, err := strconv.Atoi(indexText)
	if err != nil {
		writeError(w, http.StatusBadRequest, "Invalid index")
		return
	}
	config, err := s.loadOptionConfig("prompt_options.json")
	if err != nil {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}
	category, options, err := s.promptCategory(config, categoryKey)
	if err != nil {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}
	if index < 0 || index >= len(options) {
		writeError(w, http.StatusBadRequest, "Index out of range")
		return
	}
	deleted := options[index]
	category["options"] = append(options[:index], options[index+1:]...)
	if err := s.saveOptionConfig("prompt_options.json", config); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{"deleted": deleted}})
}

func promptOptionFromPayload(payload map[string]any, allowPartial bool) (any, error) {
	if raw, exists := payload["value"]; exists {
		value := strings.TrimSpace(stringValue(raw))
		if value == "" {
			return nil, errors.New("Option value cannot be empty")
		}
		return value, nil
	}
	display := strings.TrimSpace(stringValue(payload["display"]))
	output := strings.TrimSpace(stringValue(payload["output"]))
	if display == "" || output == "" {
		return nil, errors.New("Display and output are required")
	}
	key := strings.TrimSpace(stringValue(payload["key"]))
	if key == "" {
		key = strings.ReplaceAll(strings.ToLower(output), " ", "_")
	}
	return map[string]any{"key": key, "display": display, "output": output}, nil
}

func promptOptionFromPayloadWithCurrent(payload map[string]any, current map[string]any) (any, error) {
	if _, exists := payload["value"]; exists {
		return promptOptionFromPayload(payload, false)
	}
	if _, hasDisplay := payload["display"]; hasDisplay || payload["output"] != nil || payload["key"] != nil {
		key := strings.TrimSpace(stringValue(payload["key"]))
		if key == "" {
			key = strings.TrimSpace(stringValue(current["key"]))
		}
		display := strings.TrimSpace(stringValue(payload["display"]))
		if display == "" {
			display = strings.TrimSpace(stringValue(current["display"]))
		}
		output := strings.TrimSpace(stringValue(payload["output"]))
		if output == "" {
			output = strings.TrimSpace(stringValue(current["output"]))
		}
		if display == "" || output == "" {
			return nil, errors.New("Invalid format")
		}
		return map[string]any{"key": key, "display": display, "output": output}, nil
	}
	return nil, errors.New("Invalid format")
}

func (s *server) wizardDimension(config map[string]any, dimensionKey string) (map[string]any, []any, error) {
	dimensions, ok := config["dimensions"].(map[string]any)
	if !ok {
		return nil, nil, errors.New("dimensions not found")
	}
	dimension, ok := dimensions[dimensionKey].(map[string]any)
	if !ok {
		return nil, nil, fmt.Errorf("Dimension %q not found", dimensionKey)
	}
	options, _ := dimension["options"].([]any)
	return dimension, options, nil
}

func (s *server) addWizardOption(w http.ResponseWriter, r *http.Request, dimensionKey string) {
	payload, ok := decodeJSONObject(w, r, "Request body is required")
	if !ok {
		return
	}
	value := strings.TrimSpace(stringField(payload, "value"))
	if value == "" {
		writeError(w, http.StatusBadRequest, "value is required")
		return
	}
	config, err := s.loadOptionConfig("wizard_options.json")
	if err != nil {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}
	dimension, options, err := s.wizardDimension(config, dimensionKey)
	if err != nil {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}
	for _, option := range options {
		if existing, ok := option.(string); ok && existing == value {
			writeError(w, http.StatusBadRequest, "This option already exists")
			return
		}
	}
	options = append(options, value)
	dimension["options"] = options
	if err := s.saveOptionConfig("wizard_options.json", config); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusCreated, response{"status": "success", "data": response{"index": len(options) - 1, "option": value}})
}

func (s *server) deleteWizardOption(w http.ResponseWriter, r *http.Request, dimensionKey, indexText string) {
	index, err := strconv.Atoi(indexText)
	if err != nil {
		writeError(w, http.StatusBadRequest, "Invalid index")
		return
	}
	config, err := s.loadOptionConfig("wizard_options.json")
	if err != nil {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}
	dimension, options, err := s.wizardDimension(config, dimensionKey)
	if err != nil {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}
	if index < 0 || index >= len(options) {
		writeError(w, http.StatusBadRequest, "Index out of range")
		return
	}
	deleted := options[index]
	dimension["options"] = append(options[:index], options[index+1:]...)
	if err := s.saveOptionConfig("wizard_options.json", config); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{"deleted": deleted}})
}
