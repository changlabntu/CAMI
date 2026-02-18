import { useState, useEffect } from "react";
import {
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Alert,
  Pressable,
  ScrollView,
  Text,
  View,
  StyleSheet,
} from "react-native";
import { useLocalSearchParams } from "expo-router";
import ChatBubble from "../components/ChatBubble";
import ChatInput from "../components/ChatInput";
import { getSession, sendMessage, sendCommand } from "../lib/api";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  isReframe?: boolean;
}

export default function ChatScreen() {
  const { sessionId, initialPhase, initialCommands } = useLocalSearchParams<{
    sessionId: string;
    initialPhase?: string;
    initialCommands?: string;
  }>();

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [phase, setPhase] = useState(initialPhase ?? "cbt");
  const [commands, setCommands] = useState<string[]>(() => {
    try {
      return initialCommands ? JSON.parse(initialCommands) : [];
    } catch {
      return [];
    }
  });

  // Load existing session messages on mount
  useEffect(() => {
    if (!sessionId) return;
    getSession(sessionId)
      .then((info) => {
        const msgs = info.messages
          .filter((m) => m.role === "user" || m.role === "assistant")
          .map((m) => ({ role: m.role as "user" | "assistant", content: m.content }));
        setMessages(msgs);
        setPhase(info.phase);
        setCommands(info.commands);
      })
      .catch((e: unknown) => {
        const msg = e instanceof Error ? e.message : "Failed to load session";
        Alert.alert("Error", msg);
      });
  }, [sessionId]);

  // Send message
  async function handleSend(content: string) {
    if (!sessionId) return;

    const userMsg: ChatMessage = { role: "user", content };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const response = await sendMessage(sessionId, content);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: response.content },
      ]);
      setPhase(response.phase);
      setCommands(response.commands);
    } catch (e: unknown) {
      // Remove optimistic user message on error
      setMessages((prev) => prev.slice(0, -1));
      const msg = e instanceof Error ? e.message : "Failed to send message";
      Alert.alert("Error", msg);
    } finally {
      setLoading(false);
    }
  }

  // Execute a command chip
  async function handleCommand(cmd: string) {
    if (!sessionId) return;

    if (cmd === "finalize") {
      Alert.prompt(
        "Finalize Journal",
        "Enter a title for your journal entry:",
        async (title) => {
          if (!title) return;
          setLoading(true);
          try {
            const result = await sendCommand(sessionId, "finalize", { title });
            setMessages((prev) => [
              ...prev,
              { role: "assistant", content: result.content },
            ]);
            setPhase(result.phase);
            setCommands(result.commands);
          } catch (e: unknown) {
            const msg = e instanceof Error ? e.message : "Command failed";
            Alert.alert("Error", msg);
          } finally {
            setLoading(false);
          }
        },
        "plain-text",
        "",
        "Title"
      );
      return;
    }

    setLoading(true);
    try {
      const result = await sendCommand(sessionId, cmd, {});
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: result.content },
      ]);
      setPhase(result.phase);
      setCommands(result.commands);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Command failed";
      Alert.alert("Error", msg);
    } finally {
      setLoading(false);
    }
  }

  // Build display data: messages + optional typing indicator
  const displayData: ChatMessage[] = loading
    ? [...messages, { role: "assistant", content: "..." }]
    : messages;

  const reversedData = [...displayData].reverse();

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      keyboardVerticalOffset={90}
    >
      <FlatList
        data={reversedData}
        inverted
        keyExtractor={(_, index) => String(index)}
        renderItem={({ item }) => (
          <ChatBubble
            role={item.role}
            content={item.content}
            isReframe={item.isReframe}
          />
        )}
        contentContainerStyle={styles.listContent}
        keyboardDismissMode="interactive"
      />
      <View style={styles.phaseRow}>
        <Text style={styles.phaseLabel}>{phase.toUpperCase()}</Text>
      </View>
      {commands.length > 0 && (
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.chipRow}
        >
          {commands.map((cmd) => (
            <Pressable
              key={cmd}
              style={[styles.chip, loading && styles.chipDisabled]}
              onPress={() => handleCommand(cmd)}
              disabled={loading}
            >
              <Text style={styles.chipText}>{cmd}</Text>
            </Pressable>
          ))}
        </ScrollView>
      )}
      <ChatInput onSend={handleSend} disabled={loading} />
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  listContent: {
    paddingVertical: 8,
  },
  phaseRow: {
    paddingHorizontal: 16,
    paddingTop: 4,
    paddingBottom: 2,
    alignItems: "flex-end",
  },
  phaseLabel: {
    color: "#666",
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 1,
  },
  chipRow: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    gap: 8,
  },
  chip: {
    paddingVertical: 6,
    paddingHorizontal: 14,
    borderRadius: 16,
    backgroundColor: "#1e2a3a",
    borderWidth: 1,
    borderColor: "#5E8CFF",
  },
  chipDisabled: {
    opacity: 0.4,
  },
  chipText: {
    color: "#5E8CFF",
    fontSize: 13,
    fontWeight: "600",
  },
});
