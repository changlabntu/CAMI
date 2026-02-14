import { useState } from "react";
import {
  View,
  Text,
  Pressable,
  ActivityIndicator,
  StyleSheet,
  Alert,
} from "react-native";
import { useRouter } from "expo-router";
import Trackball from "../components/Trackball";
import { createSession } from "../lib/api";

function describeEmotion(valence: number, supportType: number): string {
  let feeling: string;
  if (valence < -0.5) feeling = "Feeling quite distressed";
  else if (valence < 0) feeling = "Feeling somewhat down";
  else if (valence < 0.5) feeling = "Feeling okay";
  else feeling = "Feeling quite good";

  let approach: string;
  if (supportType < -0.5) approach = "wanting compassion";
  else if (supportType < 0) approach = "leaning toward empathy";
  else if (supportType < 0.5) approach = "open to some guidance";
  else approach = "looking for advice";

  return `${feeling}, ${approach}`;
}

export default function WelcomeScreen() {
  const router = useRouter();
  const [valence, setValence] = useState(0);
  const [supportType, setSupportType] = useState(0);
  const [loading, setLoading] = useState(false);

  function handlePositionChange(v: number, s: number) {
    setValence(v);
    setSupportType(s);
  }

  async function handleStart() {
    setLoading(true);
    try {
      const session = await createSession(valence, supportType);
      router.push({ pathname: "/chat", params: { sessionId: session.session_id } });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Failed to create session";
      Alert.alert("Error", msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>CAMI</Text>

      <Trackball onPositionChange={handlePositionChange} />

      <Text style={styles.description}>{describeEmotion(valence, supportType)}</Text>

      <Pressable
        style={[styles.button, loading && styles.buttonDisabled]}
        onPress={handleStart}
        disabled={loading}
      >
        {loading ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.buttonText}>Start Journaling</Text>
        )}
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 24,
  },
  title: {
    color: "#fff",
    fontSize: 32,
    fontWeight: "bold",
    marginBottom: 24,
  },
  description: {
    color: "#aaa",
    fontSize: 15,
    marginTop: 16,
    textAlign: "center",
  },
  button: {
    marginTop: 32,
    backgroundColor: "#5E8CFF",
    paddingVertical: 14,
    paddingHorizontal: 40,
    borderRadius: 12,
    minWidth: 200,
    alignItems: "center",
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: {
    color: "#fff",
    fontSize: 17,
    fontWeight: "600",
  },
});
