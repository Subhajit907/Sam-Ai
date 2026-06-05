/**
 * ChatScreen — main conversation interface.
 * Voice input via VoiceButton, text input via keyboard.
 * TTS audio streamed from the backend and played with expo-av.
 */

import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
  ActivityIndicator,
} from "react-native";
import { Audio } from "expo-av";
import { MaterialIcons } from "@expo/vector-icons";
import * as FileSystem from "expo-file-system";
import VoiceButton from "../components/VoiceButton";
import { sendMessage, speak, resetConversation, loadHistory } from "../api/client";

const BG     = "#04040f";
const BLUE   = "#00b4ff";
const BRIGHT = "#66d9ff";
const DIM    = "#4488aa";
const ORANGE = "#ff9f43";

interface Message {
  id: string;
  role: "user" | "assistant";
  text: string;
}

export default function ChatScreen() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput]       = useState("");
  const [thinking, setThinking] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const listRef = useRef<FlatList>(null);
  const soundRef = useRef<Audio.Sound | null>(null);

  useEffect(() => {
    loadHistory().then((hist) => {
      setMessages(
        hist.map((m, i) => ({ id: String(i), role: m.role as any, text: m.content }))
      );
    }).catch(() => {});
  }, []);

  const playAudio = useCallback(async (text: string) => {
    setSpeaking(true);
    try {
      const arrayBuffer = await speak(text);
      // Write to a temp file so expo-av can load it
      const path = FileSystem.cacheDirectory + "alia_tts.mp3";
      const base64 = btoa(
        new Uint8Array(arrayBuffer).reduce((d, b) => d + String.fromCharCode(b), "")
      );
      await FileSystem.writeAsStringAsync(path, base64, {
        encoding: FileSystem.EncodingType.Base64,
      });
      if (soundRef.current) {
        await soundRef.current.unloadAsync();
      }
      const { sound } = await Audio.Sound.createAsync({ uri: path });
      soundRef.current = sound;
      await sound.playAsync();
      sound.setOnPlaybackStatusUpdate((s) => {
        if (s.isLoaded && s.didJustFinish) setSpeaking(false);
      });
    } catch {
      setSpeaking(false);
    }
  }, []);

  const addMessage = (role: "user" | "assistant", text: string) => {
    setMessages((prev) => [
      ...prev,
      { id: Date.now().toString(), role, text },
    ]);
    setTimeout(() => listRef.current?.scrollToEnd({ animated: true }), 100);
  };

  const sendText = useCallback(async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;
    addMessage("user", trimmed);
    setInput("");
    setThinking(true);
    try {
      const reply = await sendMessage(trimmed);
      addMessage("assistant", reply);
      playAudio(reply);
    } catch (e) {
      addMessage("assistant", "⚠ Could not reach the server. Check your connection.");
    } finally {
      setThinking(false);
    }
  }, [playAudio]);

  // VoiceButton returns "__audio__:<uri>" — use expo-speech for on-device STT
  const handleVoiceResult = useCallback(async (result: string) => {
    if (result.startsWith("__audio__:")) {
      // On-device: trigger system speech recognition (simplest cross-platform path)
      // For production, upload the audio file to /api/listen (Whisper) instead
      addMessage("assistant", "🎙 Voice input detected — type your message or use the keyboard for now. (STT coming soon!)");
      return;
    }
    sendText(result);
  }, [sendText]);

  const handleReset = async () => {
    await resetConversation();
    setMessages([]);
  };

  const renderItem = ({ item }: { item: Message }) => (
    <View style={[styles.bubble, item.role === "user" ? styles.userBubble : styles.aliBubble]}>
      <Text style={[styles.bubbleLabel, item.role === "user" ? styles.userLabel : styles.aliLabel]}>
        {item.role === "user" ? "YOU" : "ALIA"}
      </Text>
      <Text style={[styles.bubbleText, item.role === "user" ? styles.userText : styles.aliText]}>
        {item.text}
      </Text>
    </View>
  );

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      keyboardVerticalOffset={90}
    >
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>ALIA AI</Text>
        <View style={styles.headerRight}>
          {speaking && <Text style={styles.statusBadge}>SPEAKING</Text>}
          {thinking && <ActivityIndicator size="small" color={BLUE} />}
          <Pressable onPress={handleReset} style={styles.resetBtn}>
            <MaterialIcons name="refresh" size={20} color={DIM} />
          </Pressable>
        </View>
      </View>

      {/* Messages */}
      <FlatList
        ref={listRef}
        data={messages}
        keyExtractor={(m) => m.id}
        renderItem={renderItem}
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          <Text style={styles.emptyText}>Say "Hey" or type something to start talking to Alia.</Text>
        }
      />

      {/* Input row */}
      <View style={styles.inputRow}>
        <VoiceButton onResult={handleVoiceResult} disabled={thinking || speaking} />
        <TextInput
          style={styles.textInput}
          value={input}
          onChangeText={setInput}
          placeholder="Type a message..."
          placeholderTextColor={DIM}
          onSubmitEditing={() => sendText(input)}
          returnKeyType="send"
          editable={!thinking && !speaking}
          multiline
        />
        <Pressable
          onPress={() => sendText(input)}
          disabled={thinking || speaking || !input.trim()}
          style={[styles.sendBtn, (!input.trim() || thinking) && styles.sendBtnDisabled]}
        >
          <MaterialIcons name="send" size={22} color={input.trim() ? BRIGHT : DIM} />
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container:    { flex: 1, backgroundColor: BG },
  header:       { flexDirection: "row", justifyContent: "space-between", alignItems: "center",
                  paddingHorizontal: 16, paddingTop: 8, paddingBottom: 10,
                  borderBottomWidth: 1, borderBottomColor: "#1a3a5c" },
  headerTitle:  { color: BRIGHT, fontSize: 16, fontFamily: Platform.select({ ios: "Courier", android: "monospace" }), fontWeight: "bold" },
  headerRight:  { flexDirection: "row", alignItems: "center", gap: 10 },
  statusBadge:  { color: ORANGE, fontSize: 10, fontFamily: Platform.select({ ios: "Courier", android: "monospace" }) },
  resetBtn:     { padding: 4 },
  list:         { padding: 16, gap: 12 },
  emptyText:    { color: DIM, textAlign: "center", marginTop: 60, fontSize: 14,
                  fontFamily: Platform.select({ ios: "Courier", android: "monospace" }) },
  bubble:       { maxWidth: "82%", borderRadius: 12, padding: 12 },
  userBubble:   { alignSelf: "flex-end", backgroundColor: "#0d1e38", borderColor: "#1a3a5c", borderWidth: 1 },
  aliBubble:    { alignSelf: "flex-start", backgroundColor: "#071022", borderColor: "#003d80", borderWidth: 1 },
  bubbleLabel:  { fontSize: 9, fontFamily: Platform.select({ ios: "Courier", android: "monospace" }),
                  marginBottom: 4, fontWeight: "bold" },
  userLabel:    { color: BLUE },
  aliLabel:     { color: ORANGE },
  bubbleText:   { fontSize: 14, lineHeight: 20 },
  userText:     { color: "#e8f4ff" },
  aliText:      { color: BRIGHT },
  inputRow:     { flexDirection: "row", alignItems: "flex-end", padding: 12, gap: 10,
                  borderTopWidth: 1, borderTopColor: "#1a3a5c" },
  textInput:    { flex: 1, backgroundColor: "#0a1628", borderRadius: 20, borderWidth: 1,
                  borderColor: "#1a3a5c", paddingHorizontal: 16, paddingVertical: 10,
                  color: "#e8f4ff", fontSize: 14, maxHeight: 100 },
  sendBtn:      { padding: 8, marginBottom: 4 },
  sendBtnDisabled: { opacity: 0.3 },
});
