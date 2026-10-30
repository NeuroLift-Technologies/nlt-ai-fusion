import { useEffect, useState } from "react";
import {
  View, Text, ScrollView, TouchableOpacity,
  StyleSheet, ActivityIndicator, Alert,
} from "react-native";
import { sessionsApi, avatarsApi, aidesApi, type TrainingSession, type Avatar, type Aide } from "../../src/api/client";

const C = {
  bg: "#0f0f1a", surface: "#1a1a2e", border: "#2e2e4e",
  text: "#e8e8f0", muted: "#8888aa", primary: "#6c63ff",
  secondary: "#48cfad", warning: "#fed330", danger: "#fc5c65",
};

const STATUS_COLORS: Record<string, string> = {
  active: C.secondary,
  completed: C.primary,
  failed: C.danger,
};

export default function SessionsScreen() {
  const [sessions, setSessions] = useState<TrainingSession[]>([]);
  const [avatars, setAvatars] = useState<Avatar[]>([]);
  const [aides, setAides] = useState<Aide[]>([]);
  const [avatarIdx, setAvatarIdx] = useState(0);
  const [aideIdx, setAideIdx] = useState(0);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);

  // `loading` already starts true, so the mount fetch does not need to set it
  // again synchronously inside the effect (react-hooks/set-state-in-effect).
  const load = () => {
    Promise.all([sessionsApi.list(), avatarsApi.list(), aidesApi.list()])
      .then(([s, a, ai]) => { setSessions(s); setAvatars(a); setAides(ai); })
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const handleCreate = async () => {
    if (!avatars[avatarIdx] || !aides[aideIdx]) {
      Alert.alert("Missing", "Create at least one Avatar and one Aide first.");
      return;
    }
    setCreating(true);
    try {
      const s = await sessionsApi.create({
        avatar_id: avatars[avatarIdx].avatar_id,
        aide_id: aides[aideIdx].aide_id,
        scenario_id: "workplace_email_overload",
      });
      setSessions((prev) => [...prev, s]);
    } finally {
      setCreating(false);
    }
  };

  const handleComplete = async (id: string) => {
    const s = await sessionsApi.complete(id);
    setSessions((prev) => prev.map((x) => (x.session_id === id ? s : x)));
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.heading}>Sessions</Text>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Start New Session</Text>
        <Text style={styles.label}>Avatar</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 10 }}>
          {avatars.map((a, i) => (
            <TouchableOpacity
              key={a.avatar_id}
              style={[styles.chip, avatarIdx === i && styles.chipActive]}
              onPress={() => setAvatarIdx(i)}
            >
              <Text style={[styles.chipText, avatarIdx === i && styles.chipTextActive]}>
                {a.trait_name.replace(/_/g, " ")}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
        <Text style={styles.label}>Aide</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 14 }}>
          {aides.map((a, i) => (
            <TouchableOpacity
              key={a.aide_id}
              style={[styles.chip, aideIdx === i && styles.chipActive]}
              onPress={() => setAideIdx(i)}
            >
              <Text style={[styles.chipText, aideIdx === i && styles.chipTextActive]}>
                {a.expertise_area}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
        <TouchableOpacity
          style={[styles.btn, creating && styles.btnDisabled]}
          onPress={handleCreate}
          disabled={creating}
        >
          <Text style={styles.btnText}>{creating ? "Starting…" : "Start Session"}</Text>
        </TouchableOpacity>
      </View>

      {loading ? (
        <ActivityIndicator color={C.primary} />
      ) : sessions.length === 0 ? (
        <Text style={styles.empty}>No sessions yet.</Text>
      ) : (
        sessions.map((s) => (
          <View key={s.session_id} style={styles.sessionCard}>
            <View style={styles.row}>
              <Text style={styles.sessionId}>{s.session_id.slice(0, 12)}…</Text>
              <View style={[styles.badge, { backgroundColor: `${STATUS_COLORS[s.status] ?? C.muted}22` }]}>
                <Text style={[styles.badgeText, { color: STATUS_COLORS[s.status] ?? C.muted }]}>
                  {s.status}
                </Text>
              </View>
            </View>
            <Text style={styles.scenarioText}>Scenario: {s.scenario_id}</Text>
            <Text style={styles.attemptsText}>Attempts: {s.task_results.length}</Text>
            {s.status === "active" && (
              <TouchableOpacity onPress={() => handleComplete(s.session_id)} style={styles.completeBtn}>
                <Text style={styles.completeBtnText}>Mark Complete</Text>
              </TouchableOpacity>
            )}
          </View>
        ))
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: C.bg },
  content: { padding: 16, paddingBottom: 40 },
  heading: { fontSize: 26, fontWeight: "bold", color: C.text, marginBottom: 16 },
  card: { backgroundColor: C.surface, borderWidth: 1, borderColor: C.border, borderRadius: 12, padding: 16, marginBottom: 16 },
  cardTitle: { fontSize: 15, fontWeight: "600", color: C.text, marginBottom: 10 },
  label: { fontSize: 12, color: C.muted, marginBottom: 6 },
  chip: { borderWidth: 1, borderColor: C.border, borderRadius: 20, paddingHorizontal: 12, paddingVertical: 6, marginRight: 8, backgroundColor: "#0f0f1a" },
  chipActive: { borderColor: C.primary, backgroundColor: `${C.primary}22` },
  chipText: { color: C.muted, fontSize: 12 },
  chipTextActive: { color: C.primary, fontWeight: "600" },
  btn: { backgroundColor: C.primary, borderRadius: 8, padding: 12, alignItems: "center" },
  btnDisabled: { opacity: 0.5 },
  btnText: { color: "#fff", fontWeight: "600" },
  empty: { color: C.muted, textAlign: "center", marginTop: 40 },
  sessionCard: { backgroundColor: C.surface, borderWidth: 1, borderColor: C.border, borderRadius: 12, padding: 16, marginBottom: 12 },
  row: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 6 },
  sessionId: { fontSize: 12, color: C.muted, fontFamily: "monospace" },
  badge: { borderRadius: 20, paddingHorizontal: 8, paddingVertical: 2 },
  badgeText: { fontSize: 11, fontWeight: "600" },
  scenarioText: { fontSize: 13, color: C.muted, marginBottom: 2 },
  attemptsText: { fontSize: 13, color: C.muted, marginBottom: 8 },
  completeBtn: { alignSelf: "flex-start" },
  completeBtnText: { color: C.secondary, fontSize: 13 },
});
