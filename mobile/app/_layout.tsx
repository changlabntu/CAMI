import { Stack } from "expo-router";
import { GestureHandlerRootView } from "react-native-gesture-handler";

export default function RootLayout() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: "#1a1a1a" },
          headerTintColor: "#fff",
          contentStyle: { backgroundColor: "#121212" },
        }}
      >
        <Stack.Screen name="index" options={{ title: "CAMI" }} />
        <Stack.Screen name="chat" options={{ title: "Journal" }} />
      </Stack>
    </GestureHandlerRootView>
  );
}
