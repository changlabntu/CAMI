import { Stack } from "expo-router";
import { GestureHandlerRootView } from "react-native-gesture-handler";

export default function RootLayout() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: "#1C1E12" },
          headerTintColor: "#F0F5ED",
          contentStyle: { backgroundColor: "#252816" },
        }}
      >
        <Stack.Screen name="index" options={{ title: "Vocalise" }} />
        <Stack.Screen name="chat" options={{ title: "Journal" }} />
      </Stack>
    </GestureHandlerRootView>
  );
}
