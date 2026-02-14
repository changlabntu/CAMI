import { useState, useEffect, useLayoutEffect, useCallback } from "react";
import {
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Alert,
  Pressable,
  Text,
  StyleSheet,
} from "react-native";
import { useLocalSearchParams, useNavigation } from "expo-router";
import ChatBubble from "../components/ChatBubble";
import ChatInput from "../components/ChatInput";
import { getSession, sendMessage, reframe } from "../lib/api";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  isReframe?: boolean;
}

export default function ChatScreen() {
  const { sessionId } = useLocalSearchParams<{ sessionId: string }>();
  const navigation = useNavigation();

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [exchangeCount, setExchangeCount] = useState(0);

  // Load existing session messages on mount
  useEffect(() => {
    if (!sessionId) return;
    getSession(sessionId)
      .then((info) => {
        const msgs = info.messages
          .filter((m) => m.role === "user" || m.role === "assistant")
          .map((m) => ({ role: m.role as "user" | "assistant", content: m.content }));
        setMessages(msgs);
        // Count existing exchanges (pairs of user+assistant)
        const pairs = msgs.filter((m) => m.role === "assistant").length;
        setExchangeCount(pairs);
      })
      .catch((e: unknown) => {
        const msg = e instanceof Error ? e.message : "Failed to load session";
        Alert.alert("Error", msg);
      });
  }, [sessionId]);

  // Reframe handler
  const doReframe = useCallback(async () => {
    if (!sessionId) return;
    setLoading(true);
    try {
      const result = await reframe(sessionId);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: result.reframed_entry, isReframe: true },
      ]);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Reframe failed";
      Alert.alert("Error", msg);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  // Dynamic header right button for reframe
  useLayoutEffect(() => {
    if (exchangeCount < 3) {
      navigation.setOptions({ headerRight: undefined });
      return;
    }
    navigation.setOptions({
      headerRight: () => (
        <Pressable
          onPress={() =>
            Alert.alert(
              "Reframe?",
              "Generate a reframed version of your journal entry based on our conversation?",
              [
                { text: "Cancel", style: "cancel" },
                { text: "Reframe", onPress: doReframe },
              ]
            )
          }
          style={styles.headerButton}
        >
          <Text style={styles.headerButtonText}>Reframe</Text>
        </Pressable>
      ),
    });
  }, [navigation, exchangeCount, doReframe]);

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
      setExchangeCount((c) => c + 1);
    } catch (e: unknown) {
      // Remove optimistic user message on error
      setMessages((prev) => prev.slice(0, -1));
      const msg = e instanceof Error ? e.message : "Failed to send message";
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
  headerButton: {
    marginRight: 8,
    paddingVertical: 6,
    paddingHorizontal: 12,
    backgroundColor: "#2a4a3a",
    borderRadius: 8,
  },
  headerButtonText: {
    color: "#8fdfb0",
    fontSize: 14,
    fontWeight: "600",
  },
});
