import { useEffect, useState } from "react";
import {
  View, Text, ScrollView, TouchableOpacity,
  StyleSheet, ActivityIndicator, Alert,
} from "react-native";
import { fusionApi, avatarsApi, aidesApi, type FusionReport, type Avatar, type Aide } from "../../src/api/client";

const C = {
  bg: "#0f0f1a", surface: "#1a1a2e", border: "#2e2e4e",
  text: "#e8e8f0", muted: "#8888aa", primary: "#6c63ff",
  secondary: "#48cfad", warning: "#fed330", danger: "#fc5c65",
};

export default function FusionScreen() {
  const [reports, setReports] = useState<FusionReport[]>([]);
  const [avatars, setAvatars] = useState<Avatar[]>([]);
  const [aides, setAides] = useState<Aide[]>([]);
  const [avatarIdx, setAvatarIdx] = useState(0);
  const [aideIdx, setAideIdx] = useState(0);
  const [loading, setLoading] = useState(true);
  const [attempting, setAttempting] = useState(false);

  // `loading` already starts true, so the mount fetch does not need to set it
  // again synchronously inside the effect (react-hooks/set-state-in-effect).
  const load = () => {
    Promise.all([fusionApi.list(), avatarsApi.list(), aidesApi.list()])
      .then(([r, a, ai]) => { setReports(r); setAvatars(a); setAides(ai); })
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const handleFusion = async () => {
    if (!avatars[avatarIdx] || !aides[aideIdx]) {
      Alert.alert("Missing", "Create at least one Avatar and one Aide first.");
      return;
    }
    setAttempting(true);
    try {
      const report = await fusionApi.attempt(
        avatars[avatarIdx].avatar_id,
        aides[aideIdx].aide_id,
      );
      setReports((prev) => [report, ...prev]);
      if (report.success) {
        Alert.alert("⚡ Fusion Successful!", "An Advocate has been created.");
      } else {
        Alert.alert("Not Ready", report.failure_reason ?? "Continue training.");
      }
    } finally {
      setAttempting(false);
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.heading}>Fusion</Text>
      <Text style={styles.subheading}>Fuse a trained Avatar + Aide into an Advocate.</Text>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Attempt Fusion</Text>
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
          style={[styles.fusionBtn, attempting && styles.btnDisabled]}
          onPress={handleFusion}
          disabled={attempting}
        >
          <Text style={styles.fusionBtnText}>{attempting ? "Fusing…" : "⚡ Attempt Fusion"}</Text>
        </TouchableOpacity>
      </View>

      {loading ? (
        <ActivityIndicator color={C.primary} />
      ) : reports.length === 0 ? (
        <Text style={styles.empty}>No fusion attempts yet.</Text>
      ) : (
        reports.map((r) => (
          <View
            key={r.fusion_id}
            style={[
              styles.reportCard,
              { borderColor: r.success ? `${C.secondary}66` : `${C.danger}66` },
            ]}
          >
            <View style={styles.row}>
              <Text style={styles.reportId}>{r.fusion_id.slice(0, 12)}…</Text>
              <View
                style={[
                  styles.badge,
                  { backgroundColor: r.success ? `${C.secondary}22` : `${C.danger}22` },
                ]}
              >
                <Text style={[styles.badgeText, { color: r.success ? C.secondary : C.danger }]}>
                  {r.success ? "SUCCESS" : "NOT READY"}
                </Text>
              </View>
            </View>
            <Text style={styles.readiness}>
              Readiness:{" "}
              <Text style={{ color: r.readiness_score >= 0.75 ? C.secondary : C.danger, fontWeight: "700" }}>
                {(r.readiness_score * 100).toFixed(1)}%
              </Text>
            </Text>
            {r.failure_reason && (
              <Text style={styles.failureReason}>{r.failure_reason}</Text>
            )}
            {r.advocate_id && (
              <Text style={styles.advocateId}>Advocate: {r.advocate_id}</Text>
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
  heading: { fontSize: 26, fontWeight: "bold", color: C.text, marginBottom: 4 },
  subheading: { fontSize: 14, color: C.muted, marginBottom: 16 },
  card: { backgroundColor: C.surface, borderWidth: 1, borderColor: C.border, borderRadius: 12, padding: 16, marginBottom: 16 },
  cardTitle: { fontSize: 15, fontWeight: "600", color: C.text, marginBottom: 10 },
  label: { fontSize: 12, color: C.muted, marginBottom: 6 },
  chip: { borderWidth: 1, borderColor: C.border, borderRadius: 20, paddingHorizontal: 12, paddingVertical: 6, marginRight: 8, backgroundColor: "#0f0f1a" },
  chipActive: { borderColor: C.primary, backgroundColor: `${C.primary}22` },
  chipText: { color: C.muted, fontSize: 12 },
  chipTextActive: { color: C.primary, fontWeight: "600" },
  fusionBtn: { borderRadius: 8, padding: 14, alignItems: "center", backgroundColor: C.primary },
  btnDisabled: { opacity: 0.5 },
  fusionBtnText: { color: "#fff", fontWeight: "700", fontSize: 15 },
  empty: { color: C.muted, textAlign: "center", marginTop: 40 },
  reportCard: { backgroundColor: C.surface, borderWidth: 1, borderRadius: 12, padding: 16, marginBottom: 12 },
  row: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 6 },
  reportId: { fontSize: 12, color: C.muted, fontFamily: "monospace" },
  badge: { borderRadius: 20, paddingHorizontal: 8, paddingVertical: 2 },
  badgeText: { fontSize: 11, fontWeight: "700" },
  readiness: { fontSize: 13, color: C.muted, marginBottom: 4 },
  failureReason: { fontSize: 12, color: C.danger, marginTop: 4 },
  advocateId: { fontSize: 12, color: C.secondary, marginTop: 4, fontFamily: "monospace" },
});
