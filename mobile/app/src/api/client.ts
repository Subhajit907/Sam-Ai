/**
 * API client — all calls to the Alia AI backend go through here.
 * Set BASE_URL to your machine's local IP (same Wi-Fi as your phone).
 */

import axios from "axios";
import AsyncStorage from "@react-native-async-storage/async-storage";

const DEFAULT_URL = "http://192.168.1.100:8000"; // change to your PC's local IP

export async function getBaseUrl(): Promise<string> {
  return (await AsyncStorage.getItem("server_url")) ?? DEFAULT_URL;
}

export async function saveBaseUrl(url: string) {
  await AsyncStorage.setItem("server_url", url.replace(/\/$/, ""));
}

async function api() {
  const base = await getBaseUrl();
  return axios.create({ baseURL: base, timeout: 30000 });
}

// ── Health ───────────────────────────────────────────────────────────────────

export async function checkHealth() {
  const client = await api();
  const res = await client.get("/api/health");
  return res.data as { status: string; mode: string; configured: boolean; role: string };
}

// ── Chat ─────────────────────────────────────────────────────────────────────

export async function sendMessage(message: string): Promise<string> {
  const client = await api();
  const res = await client.post("/api/chat", { message });
  return res.data.reply as string;
}

// ── TTS ──────────────────────────────────────────────────────────────────────

export async function getSpeechUrl(text: string): Promise<string> {
  const base = await getBaseUrl();
  // Return URL for streaming endpoint — expo-av loads it directly
  return `${base}/api/speak-url?text=${encodeURIComponent(text)}`;
}

export async function speak(text: string): Promise<ArrayBuffer> {
  const client = await api();
  const res = await client.post(
    "/api/speak",
    { text },
    { responseType: "arraybuffer" }
  );
  return res.data as ArrayBuffer;
}

// ── Vision ───────────────────────────────────────────────────────────────────

export async function askWithVision(question: string, imageB64: string): Promise<string> {
  const client = await api();
  const res = await client.post("/api/vision", { question, image_b64: imageB64 });
  return res.data.reply as string;
}

// ── History ──────────────────────────────────────────────────────────────────

export async function loadHistory(): Promise<{ role: string; content: string }[]> {
  const client = await api();
  const res = await client.get("/api/history");
  return res.data.messages;
}

export async function resetConversation() {
  const client = await api();
  await client.post("/api/reset");
}

// ── Settings ─────────────────────────────────────────────────────────────────

export async function getSettings() {
  const client = await api();
  const res = await client.get("/api/settings");
  return res.data as {
    mode: string;
    configured: boolean;
    has_openai_key: boolean;
    has_groq_key: boolean;
    role: string;
    roles: string[];
  };
}

export async function saveSettings(mode: string, openaiKey = "", groqKey = "") {
  const client = await api();
  await client.post("/api/settings", {
    mode,
    openai_key: openaiKey,
    groq_key: groqKey,
  });
}

export async function setRole(role: string) {
  const client = await api();
  await client.post("/api/role", { role });
}
