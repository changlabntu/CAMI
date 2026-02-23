import React from "react";
import { StyleSheet, Text, View, Platform } from "react-native";
import { Gesture, GestureDetector } from "react-native-gesture-handler";
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  runOnJS,
} from "react-native-reanimated";
import Svg, {
  Circle as SvgCircle,
  Defs,
  RadialGradient,
  Stop,
} from "react-native-svg";

const BALL_SIZE = 70;
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

  const shadowCanvasSize = BALL_SIZE + 20;
  const shadowOffset = -10;

  return (
    <View style={[styles.wrapper, { width: size + 80, height: size + 80 }]}>
      {/* Axis labels */}
      <Text style={[styles.label, styles.labelLeft, { left: 0 }]}>Bad</Text>
      <Text style={[styles.label, styles.labelRight, { right: 0 }]}>Good</Text>
      <Text style={[styles.label, styles.labelTop, { top: 0 }]}>Advice</Text>
      <Text style={[styles.label, styles.labelBottom, { bottom: 0 }]}>
        Compassion
      </Text>

      {/* Outer glow */}
      <View
        style={[
          styles.circleGlow,
          {
            width: size,
            height: size,
            borderRadius: circleRadius,
          },
        ]}
      >
        {/* Glass fill */}
        <View
          style={[
            styles.circleGlass,
            {
              width: size,
              height: size,
              borderRadius: circleRadius,
            },
          ]}
        >
          {/* Neumorphic inset shadows — light from top-left */}
          <Svg
            width={size}
            height={size}
            style={StyleSheet.absoluteFill}
            pointerEvents="none"
          >
            <Defs>
              {/* Dark shadow on top-left edges (carved depth) */}
              <RadialGradient id="innerShadowDark" cx="65%" cy="65%" r="55%">
                <Stop offset="0" stopColor="black" stopOpacity="0" />
                <Stop offset="0.6" stopColor="black" stopOpacity="0" />
                <Stop offset="0.85" stopColor="black" stopOpacity="0.30" />
                <Stop offset="1" stopColor="black" stopOpacity="0.55" />
              </RadialGradient>
              {/* Light rim on bottom-right edge */}
              <RadialGradient id="innerShadowLight" cx="35%" cy="35%" r="55%">
                <Stop offset="0" stopColor="white" stopOpacity="0" />
                <Stop offset="0.8" stopColor="white" stopOpacity="0" />
                <Stop offset="1" stopColor="white" stopOpacity="0.06" />
              </RadialGradient>
            </Defs>
            <SvgCircle
              cx={circleRadius}
              cy={circleRadius}
              r={circleRadius}
              fill="url(#innerShadowDark)"
            />
            <SvgCircle
              cx={circleRadius}
              cy={circleRadius}
              r={circleRadius}
              fill="url(#innerShadowLight)"
            />
          </Svg>

          {/* Ball */}
          <GestureDetector gesture={pan}>
            <Animated.View style={[styles.ballContainer, ballStyle]}>
              {/* Dark shadow (bottom-right) */}
              <Svg
                width={shadowCanvasSize}
                height={shadowCanvasSize}
                style={{
                  position: "absolute",
                  left: shadowOffset,
                  top: shadowOffset,
                }}
                pointerEvents="none"
              >
                <Defs>
                  <RadialGradient id="ballShadow" cx="58%" cy="58%" r="50%">
                    <Stop offset="0" stopColor="black" stopOpacity="0.6" />
                    <Stop offset="0.7" stopColor="black" stopOpacity="0.2" />
                    <Stop offset="1" stopColor="black" stopOpacity="0" />
                  </RadialGradient>
                </Defs>
                <SvgCircle
                  cx={shadowCanvasSize / 2}
                  cy={shadowCanvasSize / 2}
                  r={shadowCanvasSize / 2}
                  fill="url(#ballShadow)"
                />
              </Svg>

              {/* Light highlight shadow (top-left — neumorphic) */}
              <Svg
                width={shadowCanvasSize}
                height={shadowCanvasSize}
                style={{
                  position: "absolute",
                  left: shadowOffset,
                  top: shadowOffset,
                }}
                pointerEvents="none"
              >
                <Defs>
                  <RadialGradient id="ballLightShadow" cx="42%" cy="42%" r="50%">
                    <Stop offset="0" stopColor="white" stopOpacity="0.18" />
                    <Stop offset="0.5" stopColor="white" stopOpacity="0.05" />
                    <Stop offset="1" stopColor="white" stopOpacity="0" />
                  </RadialGradient>
                </Defs>
                <SvgCircle
                  cx={shadowCanvasSize / 2}
                  cy={shadowCanvasSize / 2}
                  r={shadowCanvasSize / 2}
                  fill="url(#ballLightShadow)"
                />
              </Svg>

              {/* Green ball base — radial gradient for convex shading */}
              <Svg
                width={BALL_SIZE}
                height={BALL_SIZE}
                style={styles.ball}
                pointerEvents="none"
              >
                <Defs>
                  <RadialGradient id="ballFill" cx="38%" cy="38%" r="55%">
                    <Stop offset="0" stopColor="#8CCF9A" stopOpacity="1" />
                    <Stop offset="0.5" stopColor="#5FA870" stopOpacity="1" />
                    <Stop offset="1" stopColor="#3D7A4E" stopOpacity="1" />
                  </RadialGradient>
                </Defs>
                <SvgCircle
                  cx={BALL_RADIUS}
                  cy={BALL_RADIUS}
                  r={BALL_RADIUS}
                  fill="url(#ballFill)"
                />
              </Svg>

              {/* Specular highlight (top-left) */}
              <Svg
                width={BALL_SIZE}
                height={BALL_SIZE}
                style={StyleSheet.absoluteFill}
                pointerEvents="none"
              >
                <Defs>
                  <RadialGradient
                    id="ballHighlight"
                    cx="35%"
                    cy="30%"
                    r="40%"
                  >
                    <Stop offset="0" stopColor="white" stopOpacity="0.50" />
                    <Stop offset="1" stopColor="white" stopOpacity="0" />
                  </RadialGradient>
                </Defs>
                <SvgCircle
                  cx={BALL_RADIUS}
                  cy={BALL_RADIUS}
                  r={BALL_RADIUS}
                  fill="url(#ballHighlight)"
                />
              </Svg>
            </Animated.View>
          </GestureDetector>
        </View>
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
  circleGlow: {
    alignItems: "center",
    justifyContent: "center",
    ...Platform.select({
      ios: {
        shadowColor: "#4A8A5A",
        shadowOffset: { width: 0, height: 0 },
        shadowOpacity: 0.3,
        shadowRadius: 20,
      },
      android: {
        elevation: 12,
      },
    }),
  },
  circleGlass: {
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "rgba(160, 184, 144, 0.07)",
    borderWidth: 1,
    borderColor: "rgba(240, 245, 237, 0.12)",
    overflow: "hidden",
  },
  ballContainer: {
    width: BALL_SIZE,
    height: BALL_SIZE,
    borderRadius: BALL_RADIUS,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.15)",
    alignItems: "center",
    justifyContent: "center",
  },
  ball: {
    position: "absolute",
    width: BALL_SIZE,
    height: BALL_SIZE,
    borderRadius: BALL_RADIUS,
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
