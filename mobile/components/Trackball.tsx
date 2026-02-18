import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { Gesture, GestureDetector } from "react-native-gesture-handler";
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  runOnJS,
} from "react-native-reanimated";

const BALL_SIZE = 50;
const BALL_RADIUS = BALL_SIZE / 2;

interface TrackballProps {
  onPositionChange: (valence: number, supportType: number) => void;
  size?: number;
}

export default function Trackball({
  onPositionChange,
  size = 260,
}: TrackballProps) {
  const circleRadius = size / 2;
  const maxDist = circleRadius - BALL_RADIUS;

  const offsetX = useSharedValue(0);
  const offsetY = useSharedValue(0);
  const translateX = useSharedValue(0);
  const translateY = useSharedValue(0);

  function emitPosition(x: number, y: number) {
    onPositionChange(x / maxDist, -y / maxDist);
  }

  function clamp(x: number, y: number): [number, number] {
    "worklet";
    const dist = Math.sqrt(x * x + y * y);
    if (dist <= maxDist) return [x, y];
    const scale = maxDist / dist;
    return [x * scale, y * scale];
  }

  const pan = Gesture.Pan()
    .onStart(() => {
      offsetX.value = translateX.value;
      offsetY.value = translateY.value;
    })
    .onUpdate((e) => {
      const rawX = offsetX.value + e.translationX;
      const rawY = offsetY.value + e.translationY;
      const [cx, cy] = clamp(rawX, rawY);
      translateX.value = cx;
      translateY.value = cy;
      runOnJS(emitPosition)(cx, cy);
    })
    .onEnd(() => {
      offsetX.value = translateX.value;
      offsetY.value = translateY.value;
    });

  const ballStyle = useAnimatedStyle(() => ({
    transform: [
      { translateX: translateX.value },
      { translateY: translateY.value },
    ],
  }));

  return (
    <View style={[styles.wrapper, { width: size + 80, height: size + 80 }]}>
      {/* Axis labels */}
      <Text style={[styles.label, styles.labelLeft, { left: 0 }]}>Bad</Text>
      <Text style={[styles.label, styles.labelRight, { right: 0 }]}>Good</Text>
      <Text style={[styles.label, styles.labelTop, { top: 0 }]}>Advice</Text>
      <Text style={[styles.label, styles.labelBottom, { bottom: 0 }]}>
        Compassion
      </Text>

      {/* Circle + ball */}
      <View
        style={[
          styles.circle,
          {
            width: size,
            height: size,
            borderRadius: circleRadius,
          },
        ]}
      >
        <GestureDetector gesture={pan}>
          <Animated.View style={[styles.ball, ballStyle]} />
        </GestureDetector>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    alignItems: "center",
    justifyContent: "center",
    position: "relative",
  },
  circle: {
    borderWidth: 1.5,
    borderColor: "#5A5D3E",
    alignItems: "center",
    justifyContent: "center",
  },
  ball: {
    width: BALL_SIZE,
    height: BALL_SIZE,
    borderRadius: BALL_RADIUS,
    backgroundColor: "#9BDEAC",
  },
  label: {
    position: "absolute",
    color: "#A0B890",
    fontSize: 13,
  },
  labelLeft: {
    top: "50%",
    marginTop: -8,
  },
  labelRight: {
    top: "50%",
    marginTop: -8,
  },
  labelTop: {
    left: "50%",
    marginLeft: -20,
  },
  labelBottom: {
    left: "50%",
    marginLeft: -36,
  },
});
