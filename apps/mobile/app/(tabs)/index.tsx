import { useEffect, useState } from "react";
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
} from "react-native";
import { avatarsApi, aidesApi, sessionsApi, fusionApi } from "../../src/api/client";

const COLORS = {
  bg: "#0f0f1a",
  surface: "#1a1a2e",
  border: "#2e2e4e",
  text: "#e8e8f0",
  muted: "#8888aa",
  primary: "#6c63ff",
  secondary: "#48cfad",
  warning: "#fed330",
  danger: "#fc5c65",
};

interface Stats {
  avatars: number;
  aides: number;
  sessions: number;
  advocates: number;
}

const STAT_CARDS = [
  { key: "avatars" as const, label: "Avatars", color: COLORS.primary },
  { key: "aides" as const, label: "Aides", color: COLORS.secondary },
  { key: "sessions" as const, label: "Sessions", color: COLORS.warning },
  { key: "advocates" as const, label: "Advocates", color: COLORS.danger },
];

const PHASES = [
  { step: "1", title: "Avatar", desc: "Embodies a specific ADHD trait and lives through authentic struggles." },
  { step: "2", title: "Aide", desc: "Coaches the Avatar in real-time with PhD-level expertise." },
  { step: "3", title: "Training", desc: "Repeated scenario attempts build genuine resilience." },
  { step: "4", title: "Fusion", desc: "Avatar + Aide merge into an Advocate once ready." },
];

export default function DashboardScreen() {
  const [stats, setStats] = useState<Stats>({ avatars: 0, aides: 0, sessions: 0, advocates: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      avatarsApi.list(),
      aidesApi.list(),
      sessionsApi.list(),
      fusionApi.advocates(),
    ])
      .then(([avatars, aides, sessions, advocates]) => {
        setStats({
          avatars: avatars.length,
          aides: aides.length,
          sessions: sessions.length,
          advocates: advocates.length,
        });
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.heading}>Simulation Dashboard</Text>
      <Text style={styles.subheading}>
        Monitor Avatar training, Aide coaching, and Fusion outcomes.
      </Text>

      {/* Stats grid */}
      {loading ? (
        <ActivityIndicator color={COLORS.primary} style={{ marginVertical: 24 }} />
      ) : (
        <View style={styles.statsGrid}>
          {STAT_CARDS.map(({ key, label, color }) => (
            <View key={key} style={styles.statCard}>
              <Text style={styles.statLabel}>{label}</Text>
              <Text style={[styles.statValue, { color }]}>{stats[key]}</Text>
            </View>
          ))}
        </View>
      )}

      {/* Mission */}
      <View style={styles.card}>
        <Text style={[styles.cardTitle, { color: COLORS.primary }]}>Mission</Text>
        <Text style={styles.cardText}>
          &ldquo;Nothing About Us Without Us&rdquo; — neurodivergent voices lead development.
          NeuroLift trains AI Avatars with ADHD traits through authentic experiential
          learning in a Sims/RPG-style simulation.
        </Text>
      </View>

      {/* Phases */}
      {PHASES.map(({ step, title, desc }) => (
        <View key={step} style={styles.phaseCard}>
          <Text style={[styles.phaseStep, { color: COLORS.primary }]}>Phase {step}</Text>
          <Text style={styles.phaseTitle}>{title}</Text>
          <Text style={styles.phaseDesc}>{desc}</Text>
        </View>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.bg },
  content: { padding: 16, paddingBottom: 40 },
  heading: { fontSize: 26, fontWeight: "bold", color: COLORS.text, marginBottom: 4 },
  subheading: { fontSize: 14, color: COLORS.muted, marginBottom: 20 },
  statsGrid: { flexDirection: "row", flexWrap: "wrap", gap: 10, marginBottom: 20 },
  statCard: {
    flex: 1,
    minWidth: "45%",
    backgroundColor: COLORS.surface,
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: 12,
    padding: 16,
  },
  statLabel: { fontSize: 12, color: COLORS.muted, marginBottom: 4 },
  statValue: { fontSize: 32, fontWeight: "bold" },
  card: {
    backgroundColor: COLORS.surface,
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  cardTitle: { fontSize: 15, fontWeight: "600", marginBottom: 6 },
  cardText: { fontSize: 13, color: COLORS.muted, lineHeight: 20 },
  phaseCard: {
    backgroundColor: COLORS.surface,
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: 12,
    padding: 16,
    marginBottom: 10,
  },
  phaseStep: { fontSize: 13, fontWeight: "700", marginBottom: 2 },
  phaseTitle: { fontSize: 15, fontWeight: "600", color: COLORS.text, marginBottom: 4 },
  phaseDesc: { fontSize: 13, color: COLORS.muted, lineHeight: 18 },
});
