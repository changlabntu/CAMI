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
  isHighlighted?: boolean;
}

const BOTTOM_ROW_HEIGHT = 80;

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
      const highlighted = cmd === "reframe" || cmd === "summarize";
      const result = await sendCommand(sessionId, cmd, {});
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: result.content, isHighlighted: highlighted },
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

  // Split assistant messages on double-newlines so each paragraph is its own bubble
  function expandMessages(msgs: ChatMessage[]): ChatMessage[] {
    const result: ChatMessage[] = [];
    for (const msg of msgs) {
      if (msg.role === "assistant" && !msg.isReframe && !msg.isHighlighted && msg.content !== "...") {
        const parts = msg.content.split(/\n\n+/).filter((p) => p.trim());
        for (const part of parts) {
          result.push({ ...msg, content: part.trim() });
        }
      } else {
        result.push(msg);
      }
    }
    return result;
  }

  // Build display data: messages + optional typing indicator
  const displayData: ChatMessage[] = loading
    ? [...expandMessages(messages), { role: "assistant", content: "..." }]
    : expandMessages(messages);

  const reversedData = [...displayData].reverse();

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      keyboardVerticalOffset={90}
    >
      <FlatList
        style={{ flex: 1 }}
        data={reversedData}
        inverted
        keyExtractor={(item, index) => `${index}-${item.content.slice(0, 20)}`}
        renderItem={({ item }) => (
          <ChatBubble
            role={item.role}
            content={item.content}
            isReframe={item.isReframe}
            isHighlighted={item.isHighlighted}
          />
        )}
        contentContainerStyle={styles.listContent}
        keyboardDismissMode="interactive"
      />
      {commands.length > 0 && (
        <View style={styles.chipRowContainer}>
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.chipRow}
            style={styles.chipScroll}
          >
            {commands.map((cmd) => (
              <Pressable
                key={cmd}
                style={({ pressed }) => [
                  styles.chip,
                  loading && styles.chipDisabled,
                  pressed && styles.chipPressed,
                ]}
                onPress={() => handleCommand(cmd)}
                disabled={loading}
              >
                <Text style={styles.chipText}>{cmd}</Text>
              </Pressable>
            ))}
          </ScrollView>
          <View style={styles.phaseChip}>
            <Text style={styles.phaseChipText}>{phase.toUpperCase()}</Text>
          </View>
        </View>
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
  chipRowContainer: {
    height: BOTTOM_ROW_HEIGHT,
    flexDirection: "row",
    alignItems: "center",
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: "#5A5D3E",
  },
  chipScroll: {
    flex: 1,
  },
  chipRow: {
    paddingHorizontal: 12,
    gap: 8,
    alignItems: "center",
  },
  phaseChip: {
    paddingVertical: 6,
    paddingHorizontal: 14,
    borderRadius: 16,
    backgroundColor: "#3A4A35",
    borderWidth: 1,
    borderColor: "#9BDEAC",
    marginRight: 12,
  },
  phaseChipText: {
    color: "#9BDEAC",
    fontSize: 13,
    fontWeight: "600",
  },
  chip: {
    paddingVertical: 6,
    paddingHorizontal: 14,
    borderRadius: 16,
    backgroundColor: "#3A4A35",
    borderWidth: 1,
    borderColor: "#9BDEAC",
  },
  chipPressed: {
    opacity: 0.6,
    transform: [{ scale: 0.95 }],
  },
  chipDisabled: {
    opacity: 0.4,
  },
  chipText: {
    color: "#9BDEAC",
    fontSize: 16,
    fontWeight: "600",
  },
});
