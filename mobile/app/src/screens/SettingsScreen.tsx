/**
 * SettingsScreen — configure server URL, AI backend, and API keys.
 */

import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
  Alert,
} from "react-native";
import { getBaseUrl, saveBaseUrl, getSettings, saveSettings, setRole, checkHealth } from "../api/client";

const BG     = "#04040f";
const BLUE   = "#00b4ff";
const BRIGHT = "#66d9ff";
const DIM    = "#4488aa";
const GREEN  = "#06d6a0";
const ORANGE = "#ff9f43";
const RED    = "#ff6b6b";

type Mode = "openai" | "groq" | "free";

export default function SettingsScreen() {
  const [serverUrl, setServerUrl]   = useState("");
  const [connected, setConnected]   = useState<boolean | null>(null);
  const [mode, setMode]             = useState<Mode>("openai");
  const [openaiKey, setOpenaiKey]   = useState("");
  const [groqKey, setGroqKey]       = useState("");
  const [currentRole, setCurrentRole] = useState("");
  const [roles, setRoles]           = useState<string[]>([]);
  const [saving, setSaving]         = useState(false);
  const [testing, setTesting]       = useState(false);

  useEffect(() => {
    getBaseUrl().then(setServerUrl);
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const s = await getSettings();
      setMode(s.mode as Mode);
      setCurrentRole(s.role);
      setRoles(s.roles);
    } catch {}
  };

  const testConnection = useCallback(async () => {
    setTesting(true);
    setConnected(null);
    try {
      await saveBaseUrl(serverUrl);
      const health = await checkHealth();
      setConnected(health.status === "ok");
      if (health.status === "ok") loadSettings();
    } catch {
      setConnected(false);
    } finally {
      setTesting(false);
    }
  }, [serverUrl]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await saveBaseUrl(serverUrl);
      await saveSettings(mode, openaiKey, groqKey);
      Alert.alert("Saved", "Settings updated successfully.");
      setOpenaiKey("");
      setGroqKey("");
    } catch {
      Alert.alert("Error", "Could not save — check server connection.");
    } finally {
      setSaving(false);
    }
  };

  const handleRoleChange = async (role: string) => {
    try {
      await setRole(role);
      setCurrentRole(role);
    } catch {
      Alert.alert("Error", "Could not change role.");
    }
  };

  const ModeBtn = ({ value, label }: { value: Mode; label: string }) => (
    <Pressable
      onPress={() => setMode(value)}
      style={[styles.modeBtn, mode === value && styles.modeBtnActive]}
    >
      <Text style={[styles.modeBtnText, mode === value && styles.modeBtnTextActive]}>
        {label}
      </Text>
    </Pressable>
  );

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.pageTitle}>⚙  SETTINGS</Text>

      {/* Server URL */}
      <View style={styles.section}>
        <Text style={styles.label}>BACKEND SERVER URL</Text>
        <Text style={styles.hint}>
          Your PC's local IP on the same Wi-Fi. Run{" "}
          <Text style={styles.code}>ipconfig</Text> (Windows) or{" "}
          <Text style={styles.code}>ifconfig</Text> (Mac) to find it.
        </Text>
        <View style={styles.inputRow}>
          <TextInput
            style={[styles.input, styles.inputFlex]}
            value={serverUrl}
            onChangeText={setServerUrl}
            placeholder="http://192.168.1.x:8000"
            placeholderTextColor={DIM}
            autoCapitalize="none"
            keyboardType="url"
          />
          <Pressable onPress={testConnection} style={styles.testBtn} disabled={testing}>
            {testing
              ? <ActivityIndicator size="small" color={BLUE} />
              : <Text style={styles.testBtnText}>TEST</Text>}
          </Pressable>
        </View>
        {connected === true  && <Text style={[styles.connStatus, { color: GREEN }]}>✓ Connected</Text>}
        {connected === false && <Text style={[styles.connStatus, { color: RED }]}>✗ Cannot reach server</Text>}
      </View>

      {/* AI Model */}
      <View style={styles.section}>
        <Text style={styles.label}>AI MODEL</Text>
        <View style={styles.modeRow}>
          <ModeBtn value="openai" label="OpenAI" />
          <ModeBtn value="groq"   label="Groq (Free)" />
          <ModeBtn value="free"   label="Ollama" />
        </View>
      </View>

      {/* API Keys */}
      {mode === "openai" && (
        <View style={styles.section}>
          <Text style={styles.label}>OPENAI API KEY</Text>
          <TextInput
            style={styles.input}
            value={openaiKey}
            onChangeText={setOpenaiKey}
            placeholder="sk-..."
            placeholderTextColor={DIM}
            secureTextEntry
            autoCapitalize="none"
          />
        </View>
      )}
      {mode === "groq" && (
        <View style={styles.section}>
          <Text style={styles.label}>GROQ API KEY</Text>
          <TextInput
            style={styles.input}
            value={groqKey}
            onChangeText={setGroqKey}
            placeholder="gsk_..."
            placeholderTextColor={DIM}
            secureTextEntry
            autoCapitalize="none"
          />
        </View>
      )}

      {/* Role */}
      {roles.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.label}>ALIA'S ROLE</Text>
          {roles.map((r) => (
            <Pressable
              key={r}
              onPress={() => handleRoleChange(r)}
              style={[styles.roleBtn, currentRole === r && styles.roleBtnActive]}
            >
              <Text style={[styles.roleBtnText, currentRole === r && styles.roleBtnTextActive]}>
                {r.replace("_", " ").toUpperCase()}
              </Text>
            </Pressable>
          ))}
        </View>
      )}

      {/* Save */}
      <Pressable onPress={handleSave} style={styles.saveBtn} disabled={saving}>
        {saving
          ? <ActivityIndicator color={BG} />
          : <Text style={styles.saveBtnText}>SAVE SETTINGS</Text>}
      </Pressable>
    </ScrollView>
  );
}

const mono = Platform.select({ ios: "Courier", android: "monospace" });

const styles = StyleSheet.create({
  container:        { flex: 1, backgroundColor: BG },
  content:          { padding: 20, paddingBottom: 60 },
  pageTitle:        { color: BRIGHT, fontSize: 16, fontFamily: mono, fontWeight: "bold", marginBottom: 24 },
  section:          { marginBottom: 24 },
  label:            { color: DIM, fontSize: 10, fontFamily: mono, fontWeight: "bold", marginBottom: 8, letterSpacing: 1 },
  hint:             { color: DIM, fontSize: 12, marginBottom: 10, lineHeight: 18 },
  code:             { color: ORANGE, fontFamily: mono },
  inputRow:         { flexDirection: "row", gap: 10, alignItems: "center" },
  inputFlex:        { flex: 1 },
  input:            { backgroundColor: "#0a1628", borderRadius: 8, borderWidth: 1,
                      borderColor: "#1a3a5c", paddingHorizontal: 14, paddingVertical: 12,
                      color: "#e8f4ff", fontSize: 14, fontFamily: mono },
  testBtn:          { backgroundColor: "#0d1e38", borderRadius: 8, borderWidth: 1,
                      borderColor: "#1a3a5c", paddingHorizontal: 16, paddingVertical: 12 },
  testBtnText:      { color: BLUE, fontSize: 12, fontFamily: mono, fontWeight: "bold" },
  connStatus:       { fontSize: 12, fontFamily: mono, marginTop: 8 },
  modeRow:          { flexDirection: "row", gap: 10 },
  modeBtn:          { flex: 1, backgroundColor: "#0a1628", borderRadius: 8, borderWidth: 1,
                      borderColor: "#1a3a5c", paddingVertical: 12, alignItems: "center" },
  modeBtnActive:    { backgroundColor: "#112240", borderColor: BLUE },
  modeBtnText:      { color: DIM, fontSize: 12, fontFamily: mono, fontWeight: "bold" },
  modeBtnTextActive:{ color: BRIGHT },
  roleBtn:          { backgroundColor: "#0a1628", borderRadius: 8, borderWidth: 1,
                      borderColor: "#1a3a5c", paddingVertical: 12, paddingHorizontal: 16,
                      marginBottom: 8 },
  roleBtnActive:    { backgroundColor: "#1a0d00", borderColor: ORANGE },
  roleBtnText:      { color: DIM, fontSize: 12, fontFamily: mono },
  roleBtnTextActive:{ color: ORANGE },
  saveBtn:          { backgroundColor: BLUE, borderRadius: 10, paddingVertical: 16, alignItems: "center" },
  saveBtnText:      { color: BG, fontSize: 14, fontFamily: mono, fontWeight: "bold" },
});
