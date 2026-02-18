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
  const [agent, setAgent] = useState<"journal" | "pin">("journal");

  function handlePositionChange(v: number, s: number) {
    setValence(v);
    setSupportType(s);
  }

  async function handleStart() {
    setLoading(true);
    try {
      const session = await createSession(valence, supportType, undefined, agent);
      router.push({
        pathname: "/chat",
        params: {
          sessionId: session.session_id,
          initialPhase: session.phase,
          initialCommands: JSON.stringify(session.commands),
        },
      });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Failed to create session";
      Alert.alert("Error", msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Vocalise</Text>

      <View style={styles.toggle}>
        <Pressable
          style={[styles.toggleButton, styles.toggleButtonLeft, agent === "journal" && styles.toggleButtonActive]}
          onPress={() => setAgent("journal")}
        >
          <Text style={[styles.toggleText, agent === "journal" && styles.toggleTextActive]}>Journal</Text>
        </Pressable>
        <Pressable
          style={[styles.toggleButton, styles.toggleButtonRight, agent === "pin" && styles.toggleButtonActive]}
          onPress={() => setAgent("pin")}
        >
          <Text style={[styles.toggleText, agent === "pin" && styles.toggleTextActive]}>Pin</Text>
        </Pressable>
      </View>

      <Trackball onPositionChange={handlePositionChange} />

      <Text style={styles.description}>{describeEmotion(valence, supportType)}</Text>

      <Pressable
        style={[styles.button, loading && styles.buttonDisabled]}
        onPress={handleStart}
        disabled={loading}
      >
        {loading ? (
          <ActivityIndicator color="#F0F5ED" />
        ) : (
          <Text style={styles.buttonText}>{agent === "pin" ? "開始書寫" : "Start Journaling"}</Text>
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
    color: "#F0F5ED",
    fontSize: 32,
    fontWeight: "bold",
    marginBottom: 16,
  },
  toggle: {
    flexDirection: "row",
    marginBottom: 16,
  },
  toggleButton: {
    paddingVertical: 8,
    paddingHorizontal: 20,
    backgroundColor: "#555838",
  },
  toggleButtonLeft: {
    borderTopLeftRadius: 8,
    borderBottomLeftRadius: 8,
  },
  toggleButtonRight: {
    borderTopRightRadius: 8,
    borderBottomRightRadius: 8,
  },
  toggleButtonActive: {
    backgroundColor: "#59A96A",
  },
  toggleText: {
    color: "#A0B890",
    fontSize: 15,
    fontWeight: "600",
  },
  toggleTextActive: {
    color: "#F0F5ED",
  },
  description: {
    color: "#A0B890",
    fontSize: 15,
    marginTop: 16,
    textAlign: "center",
  },
  button: {
    marginTop: 32,
    backgroundColor: "#59A96A",
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
    color: "#F0F5ED",
    fontSize: 17,
    fontWeight: "600",
  },
});
