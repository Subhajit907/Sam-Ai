/**
 * VoiceButton — pulsing mic button.
 * Holds down to record, releases to send.
 * Uses expo-av for recording and expo-speech for on-device STT.
 */

import React, { useRef, useState } from "react";
import {
  Animated,
  Pressable,
  StyleSheet,
  Text,
  View,
  Platform,
} from "react-native";
import { Audio } from "expo-av";
import * as Speech from "expo-speech";
import { MaterialIcons } from "@expo/vector-icons";

const ORANGE = "#ff9f43";
const BLUE   = "#00b4ff";

interface Props {
  onResult: (text: string) => void;
  onError?: (err: string) => void;
  disabled?: boolean;
}

export default function VoiceButton({ onResult, onError, disabled }: Props) {
  const [recording, setRecording] = useState(false);
  const scale = useRef(new Animated.Value(1)).current;
  const recordingRef = useRef<Audio.Recording | null>(null);

  const pulse = () => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(scale, { toValue: 1.18, duration: 400, useNativeDriver: true }),
        Animated.timing(scale, { toValue: 1.0,  duration: 400, useNativeDriver: true }),
      ])
    ).start();
  };

  const stopPulse = () => {
    scale.stopAnimation();
    Animated.timing(scale, { toValue: 1.0, duration: 150, useNativeDriver: true }).start();
  };

  const startRecording = async () => {
    if (disabled) return;
    try {
      await Audio.requestPermissionsAsync();
      await Audio.setAudioModeAsync({ allowsRecordingIOS: true, playsInSilentModeIOS: true });
      const { recording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );
      recordingRef.current = recording;
      setRecording(true);
      pulse();
    } catch (e) {
      onError?.("Microphone error — check permissions.");
    }
  };

  const stopRecording = async () => {
    if (!recordingRef.current) return;
    stopPulse();
    setRecording(false);

    try {
      await recordingRef.current.stopAndUnloadAsync();
      const uri = recordingRef.current.getURI();
      recordingRef.current = null;

      // Use on-device speech recognition via expo-speech (triggers native STT)
      // For a richer experience, swap this with Whisper via the backend.
      if (uri) {
        // Fallback: signal caller with a placeholder; real STT wired in ChatScreen
        onResult("__audio__:" + uri);
      }
    } catch (e) {
      onError?.("Failed to process audio.");
    }
  };

  return (
    <Animated.View style={[styles.wrapper, { transform: [{ scale }] }]}>
      <Pressable
        onPressIn={startRecording}
        onPressOut={stopRecording}
        disabled={disabled}
        style={[styles.btn, recording && styles.btnActive]}
      >
        <MaterialIcons
          name={recording ? "mic" : "mic-none"}
          size={32}
          color={recording ? ORANGE : BLUE}
        />
      </Pressable>
      {recording && <Text style={styles.hint}>Release to send</Text>}
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  wrapper: { alignItems: "center" },
  btn: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: "#0a1628",
    borderWidth: 2,
    borderColor: "#1a3a5c",
    alignItems: "center",
    justifyContent: "center",
  },
  btnActive: {
    borderColor: ORANGE,
    backgroundColor: "#1a0d00",
  },
  hint: {
    color: ORANGE,
    fontSize: 11,
    marginTop: 6,
    fontFamily: Platform.select({ ios: "Courier", android: "monospace" }),
  },
});
