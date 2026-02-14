import { View, Text, StyleSheet } from "react-native";

interface ChatBubbleProps {
  role: "user" | "assistant";
  content: string;
  isReframe?: boolean;
}

export default function ChatBubble({ role, content, isReframe }: ChatBubbleProps) {
  const isUser = role === "user";

  return (
    <View style={[styles.row, isUser ? styles.rowUser : styles.rowAssistant]}>
      <View
        style={[
          styles.bubble,
          isUser
            ? styles.bubbleUser
            : isReframe
              ? styles.bubbleReframe
              : styles.bubbleAssistant,
        ]}
      >
        {isReframe && (
          <Text style={styles.reframeHeader}>Reframed Journal Entry</Text>
        )}
        <Text style={styles.text}>{content}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    marginVertical: 4,
    paddingHorizontal: 12,
  },
  rowUser: {
    alignItems: "flex-end",
  },
  rowAssistant: {
    alignItems: "flex-start",
  },
  bubble: {
    maxWidth: "80%",
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 16,
  },
  bubbleUser: {
    backgroundColor: "#5E8CFF",
  },
  bubbleAssistant: {
    backgroundColor: "#2a2a2a",
  },
  bubbleReframe: {
    backgroundColor: "#1a3a2a",
  },
  reframeHeader: {
    color: "#8fdfb0",
    fontSize: 13,
    fontStyle: "italic",
    marginBottom: 6,
  },
  text: {
    color: "#fff",
    fontSize: 15,
    lineHeight: 21,
  },
});
