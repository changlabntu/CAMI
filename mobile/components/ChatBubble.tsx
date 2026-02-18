import { View, Text, StyleSheet } from "react-native";
import { LinearGradient } from "expo-linear-gradient";

interface ChatBubbleProps {
  role: "user" | "assistant";
  content: string;
  isReframe?: boolean;
  isHighlighted?: boolean;
}

export default function ChatBubble({ role, content, isReframe, isHighlighted }: ChatBubbleProps) {
  const isUser = role === "user";
  const useGradient = !isUser && !isReframe;

  const bubbleStyle = [
    styles.bubble,
    isUser
      ? styles.bubbleUser
      : isReframe
        ? styles.bubbleReframe
        : undefined,
    isHighlighted && styles.bubbleHighlighted,
  ];

  const inner = (
    <>
      {isReframe && (
        <Text style={styles.reframeHeader}>Reframed Journal Entry</Text>
      )}
      <Text style={styles.text}>{content}</Text>
    </>
  );

  return (
    <View style={[styles.row, isUser ? styles.rowUser : styles.rowAssistant]}>
      {useGradient ? (
        <LinearGradient
          colors={["#1E4229", "#152E1E", "#0D1F16"]}
          locations={[0, 0.45, 1]}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={[styles.bubble, isHighlighted && styles.bubbleHighlighted]}
        >
          {inner}
        </LinearGradient>
      ) : (
        <View style={bubbleStyle}>
          {inner}
        </View>
      )}
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
    overflow: "hidden",
  },
  bubbleUser: {
    backgroundColor: "#636940",
  },
  bubbleReframe: {
    backgroundColor: "#3A5A3A",
  },
  bubbleHighlighted: {
    borderWidth: 1,
    borderColor: "#B4E7CE",
  },
  reframeHeader: {
    color: "#B4E7CE",
    fontSize: 13,
    fontStyle: "italic",
    marginBottom: 6,
  },
  text: {
    color: "#F0F5ED",
    fontSize: 15,
    lineHeight: 21,
  },
});
